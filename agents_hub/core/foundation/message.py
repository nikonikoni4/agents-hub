"""
消息类定义

定义 Agent 之间传递的消息结构。
"""

from dataclasses import dataclass, field
from datetime import datetime

from .models import MessageType, SessionType


@dataclass
class AgentMessage:
    """Agent 之间传递的消息"""

    call_id: str
    content: str
    send_from: str
    send_to: str
    session_type: SessionType = SessionType.MAIN  # 用于判断是单聊还是群聊
    message_type: MessageType = MessageType.NOTIFICATION  # 用于判断系统是否需要自动回复
    timestamp: datetime = field(default_factory=datetime.now)
