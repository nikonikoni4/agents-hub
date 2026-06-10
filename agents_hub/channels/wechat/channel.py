import asyncio
import logging
from pathlib import Path

import httpx

from agents_hub.channels.wechat.auth import WechatAuth
from agents_hub.channels.wechat.client import WechatClient
from agents_hub.channels.wechat.commander import Commander
from agents_hub.channels.wechat.config import WechatConfig
from agents_hub.channels.wechat.exceptions import WechatAPIError
from agents_hub.channels.wechat.message import WechatMessage

logger = logging.getLogger(__name__)


class WechatChannel:
    """微信 Channel 主类

    负责 QR 码登录、消息轮询和自动回复。
    第一阶段：收到任何消息自动回复 reply_text。
    """

    name = "wechat"

    def __init__(self, config: WechatConfig, data_path: Path):
        self.config = config
        self.wechat_dir = data_path / "channels" / "wechat"
        self.state_file = self.wechat_dir / "account.json"

        self.client: WechatClient | None = None
        self.auth: WechatAuth | None = None
        self.commander = Commander()
        self._running = False
        self._poll_task: asyncio.Task | None = None

    async def start(self) -> None:
        """启动 channel：初始化客户端 -> 登录 -> 启动轮询"""
        if self._running:
            return

        self._running = True
        logger.info("启动微信 channel")

        self.client = WechatClient(self.config.base_url)
        await self.client.__aenter__()

        self.auth = WechatAuth(self.client, self.state_file)

        # 加载已保存的 token
        token = self.auth.load_token()
        if token:
            self.client.token = token
            logger.info("使用已保存的 token")
        else:
            # QR 码登录
            success = await self.auth.qr_login()
            if not success:
                logger.error("QR 登录失败，放弃启动")
                self._running = False
                return

        # 测试 token 有效性
        try:
            await self.client.api_post("ilink/bot/getupdates", {"get_updates_buf": ""})
            logger.info("Token 有效")
        except (httpx.HTTPStatusError, httpx.RequestError, RuntimeError) as e:
            logger.error(f"Token 无效: {e}")
            self._running = False
            return

        self._poll_task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        """停止 channel"""
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        if self.client:
            await self.client.__aexit__(None, None, None)
        logger.info("微信 channel 已停止")

    async def _poll_loop(self) -> None:
        """长轮询消息循环"""
        logger.info("轮询循环已启动")
        get_updates_buf = ""

        while self._running:
            try:
                body = {"get_updates_buf": get_updates_buf}
                data = await self.client.api_post("ilink/bot/getupdates", body)

                get_updates_buf = data.get("get_updates_buf", "")
                messages = data.get("msgs", [])

                if messages:
                    logger.info(f"收到 {len(messages)} 条消息")
                    for msg in messages:
                        await self._handle_message(msg)

            except (httpx.HTTPStatusError, httpx.RequestError, RuntimeError) as e:
                logger.error(f"轮询错误: {e}")
                await asyncio.sleep(5)
            except (KeyError, ValueError) as e:
                logger.error(f"轮询数据解析错误: {e}")
                await asyncio.sleep(5)

    async def _handle_message(self, raw_msg: dict) -> None:
        """处理单条消息：解析 -> 权限检查 -> 命令处理/转发"""
        try:
            parsed = WechatMessage.parse_message(raw_msg)
            user_id = parsed["from_user_id"]
            content = parsed["content"]
            context_token = parsed["context_token"]

            if not self._is_allowed(user_id):
                logger.warning(f"拒绝未授权用户: {user_id}")
                return

            if not content.strip():
                return

            logger.info(f"收到消息: 用户={user_id}, 内容={content}")

            # 通过 commander 处理
            reply_text = await self.commander.handle(user_id, content)
            await self._send_reply(user_id, reply_text, context_token)

        except Exception as e:
            logger.error(f"处理消息失败: {e}", exc_info=True)

    async def _send_reply(
        self, to_user_id: str, text: str, context_token: str = ""
    ) -> None:
        """发送文本回复"""
        if not self.client:
            return
        try:
            body = WechatMessage.build_text_message(to_user_id, text, context_token)
            await self.client.api_post("ilink/bot/sendmessage", body)
            logger.info(f"已回复用户 {to_user_id}: {text}")
        except (httpx.HTTPStatusError, httpx.RequestError, RuntimeError) as e:
            logger.error(f"发送回复失败: {e}")
            raise WechatAPIError(f"发送回复失败: {e}") from e

    def _is_allowed(self, sender_id: str) -> bool:
        """检查发送者是否被允许"""
        allow_list = self.config.allow_from
        if not allow_list:
            return False
        if "*" in allow_list:
            return True
        return sender_id in allow_list
