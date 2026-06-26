"""飞书消息解析模块

提供消息解析、@agent_name 解析、mention 占位符替换和消息去重功能。
"""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from typing import Any


def parse_message(event: dict[str, Any]) -> dict[str, Any]:
    """解析飞书消息事件。

    Args:
        event: 飞书事件对象，包含 message 字段

    Returns:
        解析后的消息字典，包含：
        - message_id: 消息 ID
        - chat_id: 群聊 ID
        - content: 消息内容（纯文本）
        - msg_type: 消息类型
        - sender_id: 发送者 ID
        - sender_type: 发送者类型（user/app）
        - mentions: mention 列表
    """
    message = event.get("message", {})
    sender = message.get("sender", {})
    sender_id_obj = sender.get("sender_id", {})

    # 解析 content JSON
    content_str = message.get("content", "{}")
    try:
        content_obj = json.loads(content_str)
        content = content_obj.get("text", "")
    except (json.JSONDecodeError, TypeError):
        content = ""

    # 解析 mentions
    raw_mentions = message.get("mentions", [])
    mentions = [
        {
            "key": m.get("key", ""),
            "id": m.get("id", {}).get("user_id", ""),
            "name": m.get("name", ""),
        }
        for m in raw_mentions
    ]

    return {
        "message_id": message.get("message_id", ""),
        "chat_id": message.get("chat_id", ""),
        "content": content,
        "msg_type": message.get("message_type", "text"),
        "sender_id": sender_id_obj.get("user_id", ""),
        "sender_type": sender.get("sender_type", ""),
        "mentions": mentions,
    }


def parse_agent_name(content: str, members: list[str]) -> tuple[str, str]:
    """解析消息中的 @agent_name。

    Args:
        content: 消息内容
        members: 群聊成员列表

    Returns:
        (target_agent, clean_content) - 目标 agent 名称和清理后的消息内容
    """
    if not content:
        return "manager", content

    # 匹配 @agent_name 格式（行首）
    match = re.match(r"^@(\w+)\s+(.+)", content, re.DOTALL)
    if match:
        agent_name = match.group(1)
        clean_content = match.group(2)
        if agent_name in members:
            return agent_name, clean_content

    # 默认发送给 manager
    return "manager", content


def parse_mentions(content: str, mentions: list[dict[str, str]]) -> str:
    """将 mention 占位符替换为实际名称。

    Args:
        content: 消息内容
        mentions: mention 列表，每项包含 key、id、name

    Returns:
        替换后的消息内容
    """
    result = content
    for mention in mentions:
        key = mention.get("key", "")
        name = mention.get("name", "")
        if key and name:
            result = result.replace(key, f"@{name}")
    return result


class MessageDeduplicator:
    """消息去重器，使用 OrderedDict 缓存 message_id。

    Args:
        max_size: 缓存最大容量，默认 1000
    """

    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, bool] = OrderedDict()
        self._max_size = max_size

    def is_duplicate(self, message_id: str) -> bool:
        """检查消息是否重复。

        Args:
            message_id: 消息 ID

        Returns:
            True 如果消息已存在（重复），False 如果是新消息
        """
        if message_id in self._cache:
            # 访问时移动到末尾
            self._cache.move_to_end(message_id)
            return True

        # 新消息，添加到缓存
        self._cache[message_id] = True

        # 淘汰最旧的条目
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

        return False
