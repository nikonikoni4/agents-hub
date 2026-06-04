"""
Orchestration layer - 编排层

团队和群聊的编排管理，依赖所有下层。
"""

from .group_chat import GroupChat
from .group_chat_manager import GroupChatManager, group_chat_manager

__all__ = [
    "GroupChat",
    "GroupChatManager",
    "group_chat_manager",
]
