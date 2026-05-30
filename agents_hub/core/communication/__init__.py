"""
Communication layer - 通信层

负责消息路由和调用管理，只依赖 foundation 层。
"""

from .message_router import MessageRouter
from .agent_call import AgentCall
from .agent_call_manager import AgentCallManager

__all__ = [
    "MessageRouter",
    "AgentCall",
    "AgentCallManager",
]
