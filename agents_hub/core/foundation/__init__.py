"""
Foundation layer - 基础层（零依赖）

提供基础数据模型、枚举、异常类和常量定义。
"""

from .models import SessionType, MessageType, CallStatus, GroupChatType
from .message import AgentMessage
from agents_hub.agent_bridge import AgentResult,RoleType
from agents_hub.roles import Role,RoleConfig
from .exceptions import (
    AgentsHubError,
    AgentNotFoundError,
    GroupChatNotFoundError,
    MessageDeliveryError,
    AgentExecutionError,
    AgentTimeoutError,
    InvalidMessageError,
    FileSystemError,
    CompactionError,
)
from .constants import MAX_TOKEN, LOCAL_DATA_PATH
from .renderer import render_for_llm, render_for_chat, parse_chat_input

__all__ = [
    # models
    "SessionType",
    "MessageType",
    "CallStatus",
    "GroupChatType",
    "AgentResult", # 从agent_bridge中导入
    "RoleType",
    "Role",
    "RoleConfig",
    # message
    "AgentMessage",
    # exceptions
    "AgentsHubError",
    "AgentNotFoundError",
    "GroupChatNotFoundError",
    "MessageDeliveryError",
    "AgentExecutionError",
    "AgentTimeoutError",
    "InvalidMessageError",
    "FileSystemError",
    "CompactionError",
    # constants
    "MAX_TOKEN",
    "LOCAL_DATA_PATH",
    # renderer
    "render_for_llm",
    "render_for_chat",
    "parse_chat_input",
]
