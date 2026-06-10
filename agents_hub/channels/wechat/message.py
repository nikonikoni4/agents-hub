import uuid

ITEM_TEXT = 1
MESSAGE_TYPE_BOT = 2
MESSAGE_STATE_FINISH = 2
CLIENT_ID_LENGTH = 12


class WechatMessage:
    """微信消息解析和构造工具类"""

    @staticmethod
    def parse_message(msg: dict) -> dict:
        """解析接收到的微信消息

        Returns:
            {"from_user_id": str, "content": str, "context_token": str}
        """
        result = {
            "from_user_id": msg.get("from_user_id", ""),
            "content": "",
            "context_token": msg.get("context_token", ""),
        }

        for item in msg.get("item_list", []):
            if item.get("type") == ITEM_TEXT:
                text_item = item.get("text_item", {})
                result["content"] += text_item.get("text", "")

        return result

    @staticmethod
    def build_text_message(to_user_id: str, text: str, context_token: str = "") -> dict:
        """构造发送文本消息的请求体"""
        client_id = f"agents-hub-{uuid.uuid4().hex[:CLIENT_ID_LENGTH]}"
        msg = {
            "from_user_id": "",
            "to_user_id": to_user_id,
            "client_id": client_id,
            "message_type": MESSAGE_TYPE_BOT,
            "message_state": MESSAGE_STATE_FINISH,
            "item_list": [{"type": ITEM_TEXT, "text_item": {"text": text}}],
        }
        if context_token:
            msg["context_token"] = context_token
        return {"msg": msg}
