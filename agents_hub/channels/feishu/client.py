"""飞书 lark-oapi SDK 封装

提供消息发送和 WebSocket 消息接收能力。
"""

from __future__ import annotations

import asyncio
import importlib.util
import threading
from collections.abc import Awaitable, Callable
from typing import Any

from agents_hub.channels.feishu.config import FeishuConfig
from agents_hub.channels.feishu.exceptions import FeishuAPIError, FeishuAuthError
from agents_hub.utils import get_logger

logger = get_logger(__name__)

FEISHU_AVAILABLE = importlib.util.find_spec("lark_oapi") is not None


def _load_lark():
    """延迟加载 lark-oapi SDK，避免模块导入时的副作用。"""
    if not FEISHU_AVAILABLE:
        raise ImportError("lark-oapi is not installed. Install it with: pip install lark-oapi")
    import lark_oapi as lark
    from lark_oapi.core.const import FEISHU_DOMAIN, LARK_DOMAIN

    return lark, FEISHU_DOMAIN, LARK_DOMAIN


class FeishuClient:
    """飞书 API 客户端，封装 lark-oapi SDK 的消息发送和 WebSocket 接收能力。

    使用方式：
        client = FeishuClient(config)
        client.on_message = callback  # 设置消息回调
        await client.connect()
        await client.send_message(chat_id, content)
        await client.disconnect()
    """

    def __init__(self, config: FeishuConfig):
        self.config = config
        self._client: Any = None  # lark.Client 实例
        self._domain: Any = None  # FEISHU_DOMAIN 或 LARK_DOMAIN
        self._ws_client: Any = None  # lark.ws.Client 实例
        self._ws_thread: threading.Thread | None = None
        self.on_message: Callable[[dict[str, Any]], Awaitable[None]] | None = None

    async def connect(self) -> None:
        """初始化 lark-oapi 客户端并启动 WebSocket 连接。"""
        lark, feishu_domain, lark_domain = _load_lark()
        self._domain = feishu_domain if self.config.domain == "feishu" else lark_domain

        # 创建 API 客户端（用于发送消息）
        self._client = (
            lark.Client.builder()
            .app_id(self.config.app_id)
            .app_secret(self.config.app_secret)
            .domain(self._domain)
            .build()
        )

        # 创建事件处理器
        handler = (
            lark.EventDispatcherHandler.builder(
                self.config.encrypt_key, self.config.verification_token
            )
            .register_p2_im_message_receive_v1(self._handle_message_event)
            .build()
        )

        # 创建 WebSocket 客户端（用于接收消息）
        self._ws_client = lark.ws.Client(
            app_id=self.config.app_id,
            app_secret=self.config.app_secret,
            event_handler=handler,
            domain=str(self._domain),
            auto_reconnect=True,
        )

        # 在后台线程启动 WebSocket（start() 是阻塞的）
        self._ws_thread = threading.Thread(target=self._start_ws, daemon=True)
        self._ws_thread.start()

        logger.info(
            "飞书客户端已连接: app_id=%s, domain=%s", self.config.app_id, self.config.domain
        )

    def _start_ws(self):
        """在后台线程中启动 WebSocket 连接（阻塞）。

        lark.ws.Client.start() 内部使用全局 loop 变量（模块加载时获取），
        需要在线程中替换这个全局变量。
        """
        import asyncio

        try:
            logger.info("飞书 WebSocket 连接启动中...")

            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 应用 nest_asyncio 允许嵌套事件循环
            try:
                import nest_asyncio

                nest_asyncio.apply(loop)
            except ImportError:
                logger.warning("nest_asyncio 未安装，可能导致事件循环冲突")

            # Hack: 替换 lark_oapi.ws.client 模块中的全局 loop 变量
            # 这是因为 lark SDK 在模块加载时就固定了 loop = asyncio.get_event_loop()
            import lark_oapi.ws.client as ws_client_module

            old_loop = getattr(ws_client_module, "loop", None)
            ws_client_module.loop = loop
            logger.debug("替换 lark SDK 全局 loop: old=%s, new=%s", old_loop, loop)

            # 启动 WebSocket（阻塞调用）
            self._ws_client.start()
        except Exception as e:
            logger.error("飞书 WebSocket 连接失败: %s", e, exc_info=True)

    def _handle_message_event(self, event: Any) -> None:
        """处理飞书消息事件（同步回调，需要转为异步）。"""
        try:
            # 提取消息数据
            message_data = event.event if hasattr(event, "event") else event
            # 转换为字典格式
            if hasattr(message_data, "__dict__"):
                event_dict = message_data.__dict__
            else:
                event_dict = message_data

            logger.info("收到飞书消息事件: %s", str(event_dict)[:200])

            # 在事件循环中执行异步回调
            if self.on_message:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(self.on_message(event_dict), loop)
                else:
                    loop.run_until_complete(self.on_message(event_dict))
        except Exception as e:
            logger.error("处理飞书消息事件失败: %s", e, exc_info=True)

    async def disconnect(self) -> None:
        """断开连接，清理资源。"""
        self._ws_client = None
        self._client = None
        if self._ws_thread and self._ws_thread.is_alive():
            # WebSocket 线程会自动退出（daemon=True）
            self._ws_thread = None
        logger.info("飞书客户端已断开")

    async def send_message(self, chat_id: str, content: str, msg_type: str = "text") -> dict:
        """发送消息到飞书群。

        Args:
            chat_id: 飞书群 ID（oc_xxx）
            content: 消息内容（JSON 字符串或纯文本）
            msg_type: 消息类型，默认 "text"

        Returns:
            飞书 API 响应

        Raises:
            FeishuAuthError: 认证失败
            FeishuAPIError: API 调用失败
        """
        if not self._client:
            raise RuntimeError("Client not connected. Call connect() first.")

        from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

        body = (
            CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type(msg_type)
            .content(content)
            .build()
        )
        request = (
            CreateMessageRequest.builder().receive_id_type("chat_id").request_body(body).build()
        )

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._client.im.v1.message.create(request)
            )
        except Exception as e:
            logger.error("飞书消息发送失败: chat_id=%s, error=%s", chat_id, str(e))
            raise FeishuAPIError(
                message=f"消息发送失败: {e}",
                details={"chat_id": chat_id},
                cause=e,
            ) from e

        if not response.success():
            error_msg = f"code={response.code}, msg={response.msg}"
            logger.error("飞书消息发送失败: chat_id=%s, %s", chat_id, error_msg)
            if response.code == 99991663:
                raise FeishuAuthError(
                    message=f"飞书认证失败: {error_msg}",
                    details={"chat_id": chat_id, "code": response.code},
                )
            raise FeishuAPIError(
                message=f"飞书 API 错误: {error_msg}",
                details={"chat_id": chat_id, "code": response.code},
            )

        logger.info("飞书消息发送成功: chat_id=%s", chat_id)
        return {"message_id": response.data.message_id if response.data else None}
