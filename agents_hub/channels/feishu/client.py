"""飞书 lark-oapi SDK 封装

提供消息发送能力，WebSocket 连接管理在 channel.py 中实现。
"""

from __future__ import annotations

import asyncio
import importlib.util
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
    """飞书 API 客户端，封装 lark-oapi SDK 的消息发送能力。

    使用方式：
        client = FeishuClient(config)
        await client.connect()
        await client.send_message(chat_id, content)
        await client.disconnect()
    """

    def __init__(self, config: FeishuConfig):
        self.config = config
        self._client: Any = None  # lark.Client 实例
        self._domain: Any = None  # FEISHU_DOMAIN 或 LARK_DOMAIN

    async def connect(self) -> None:
        """初始化 lark-oapi 客户端。"""
        lark, feishu_domain, lark_domain = _load_lark()
        self._domain = feishu_domain if self.config.domain == "feishu" else lark_domain
        self._client = (
            lark.Client.builder()
            .app_id(self.config.app_id)
            .app_secret(self.config.app_secret)
            .domain(self._domain)
            .build()
        )
        logger.info(
            "飞书客户端已连接: app_id=%s, domain=%s", self.config.app_id, self.config.domain
        )

    async def disconnect(self) -> None:
        """断开连接，清理资源。"""
        self._client = None
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
