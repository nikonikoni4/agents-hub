"""Agent Bridge 模块 - 统一的 AI 平台 CLI 调用接口"""

from .config import AgentPlatform, RoleConfig
from .parsers.base import AgentEvent, AgentEventType
from .bridge import AgentBridge

__all__ = [
    "AgentPlatform",
    "RoleConfig",
    "AgentEvent",
    "AgentEventType",
    "AgentBridge",
]
