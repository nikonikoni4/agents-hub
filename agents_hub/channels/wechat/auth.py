import asyncio
import json
import logging
from pathlib import Path

import httpx
import qrcode

from agents_hub.channels.wechat.client import WechatClient
from agents_hub.channels.wechat.exceptions import WechatAuthError

logger = logging.getLogger(__name__)


class WechatAuth:
    """微信认证模块：QR 码登录 + token 持久化"""

    def __init__(self, client: WechatClient, state_file: Path):
        self.client = client
        self.state_file = state_file

    def _print_qr_code(self, data: str) -> None:
        qr = qrcode.QRCode()
        qr.add_data(data)
        qr.make()
        qr.print_ascii()
        logger.info("请使用微信扫描上方二维码登录")

    def load_token(self) -> str:
        """从 account.json 加载 token，不存在返回空字符串"""
        if not self.state_file.exists():
            return ""
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            return data.get("token", "")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"加载 token 失败: {e}")
            return ""

    def save_token(self, token: str) -> None:
        """保存 token 到 account.json"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        state = {"token": token}
        if self.state_file.exists():
            try:
                existing = json.loads(self.state_file.read_text(encoding="utf-8"))
                existing["token"] = token
                state = existing
            except (json.JSONDecodeError, OSError):
                pass
        self.state_file.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("Token 已保存")

    async def qr_login(self, timeout: int = 300) -> bool:
        """QR 码登录流程

        1. 获取 QR 码并打印到终端
        2. 轮询扫码状态
        3. 确认后保存 token
        """
        try:
            data = await self.client.api_get(
                "ilink/bot/get_bot_qrcode", params={"bot_type": "3"}, auth=False
            )
            qrcode_id = data.get("qrcode", "")
            qrcode_img = data.get("qrcode_img_content", qrcode_id)
            if not qrcode_id:
                logger.error("获取 QR 码失败")
                return False

            self._print_qr_code(qrcode_img)

            loop = asyncio.get_event_loop()
            start_time = loop.time()
            while True:
                if loop.time() - start_time > timeout:
                    logger.error(f"登录超时（{timeout}秒）")
                    return False

                status_data = await self.client.api_get(
                    "ilink/bot/get_qrcode_status",
                    params={"qrcode": qrcode_id},
                    auth=False,
                )
                status = status_data.get("status", "")

                if status == "confirmed":
                    token = status_data.get("bot_token", "")
                    if token:
                        self.client.token = token
                        self.save_token(token)
                        logger.info("登录成功")
                        return True
                    logger.error("登录确认但未返回 token")
                    return False
                elif status == "expired":
                    logger.error("QR 码已过期")
                    return False

                await asyncio.sleep(1)
        except (httpx.HTTPStatusError, httpx.RequestError, RuntimeError) as e:
            logger.error(f"登录网络错误: {e}")
            raise WechatAuthError(f"登录失败: {e}") from e
