"""
Foundation layer - 基础层（零依赖）

提供基础数据模型、枚举、异常类和常量定义。
"""

from agents_hub.exceptions import StateError

from .constants import LOCAL_DATA_PATH, MAX_TOKEN
from .exceptions import (
    AgentBusyError,
    AgentExecutionError,
    AgentNotFoundError,
    AgentsHubError,
    AgentTimeoutError,
    CompactionError,
    FileSystemError,
    GroupChatNotFoundError,
    InvalidMessageError,
    MessageDeliveryError,
)
from .message import AgentMessage
from .models import CallStatus, GroupChatType, MessageType, SessionType
from .paths import GroupChatPaths, group_chat_paths
from .renderer import Tag, parse_chat_input, render_for_chat, render_for_llm, wrap_xml
from .types import FileMetadata

__all__ = [
    # models
    "SessionType",
    "MessageType",
    "CallStatus",
    "GroupChatType",
    # message
    "AgentMessage",
    # exceptions
    "AgentBusyError",
    "AgentsHubError",
    "AgentNotFoundError",
    "GroupChatNotFoundError",
    "MessageDeliveryError",
    "AgentExecutionError",
    "AgentTimeoutError",
    "InvalidMessageError",
    "FileSystemError",
    "CompactionError",
    "StateError",
    # constants
    "MAX_TOKEN",
    "LOCAL_DATA_PATH",
    # paths
    "GroupChatPaths",
    "group_chat_paths",
    # renderer
    "render_for_llm",
    "render_for_chat",
    "parse_chat_input",
    "wrap_xml",
    "Tag",
    # types
    "FileMetadata",
]
