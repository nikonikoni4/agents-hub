import base64
import logging
import os

import httpx

logger = logging.getLogger(__name__)

ILINK_APP_ID = "bot"
ILINK_APP_CLIENT_VERSION = 0x020101
BASE_INFO = {"channel_version": "2.1.1"}


class WechatClient:
    """微信 ilinkai API 异步 HTTP 客户端"""

    def __init__(self, base_url: str, token: str = ""):
        self.base_url = base_url
        self.token = token
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=60.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    @staticmethod
    def _random_wechat_uin() -> str:
        uint32 = int.from_bytes(os.urandom(4), "big")
        return base64.b64encode(str(uint32).encode()).decode()

    def _make_headers(self, auth: bool = True) -> dict[str, str]:
        headers = {
            "X-WECHAT-UIN": self._random_wechat_uin(),
            "Content-Type": "application/json",
            "AuthorizationType": "ilink_bot_token",
            "iLink-App-Id": ILINK_APP_ID,
            "iLink-App-ClientVersion": str(ILINK_APP_CLIENT_VERSION),
        }
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def api_get(self, endpoint: str, params: dict | None = None, auth: bool = True) -> dict:
        if not self._client:
            raise RuntimeError("Client not initialized")
        url = f"{self.base_url}/{endpoint}"
        resp = await self._client.get(url, params=params, headers=self._make_headers(auth=auth))
        resp.raise_for_status()
        return resp.json()

    async def api_post(self, endpoint: str, body: dict | None = None, auth: bool = True) -> dict:
        if not self._client:
            raise RuntimeError("Client not initialized")
        url = f"{self.base_url}/{endpoint}"
        payload = body or {}
        if "base_info" not in payload:
            payload["base_info"] = BASE_INFO
        resp = await self._client.post(url, json=payload, headers=self._make_headers(auth=auth))
        resp.raise_for_status()
        return resp.json()
