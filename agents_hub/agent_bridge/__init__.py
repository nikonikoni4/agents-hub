"""Agent Bridge 模块 - 统一的 AI 平台 CLI 调用接口"""

from agents_hub.agent_bridge.config import AgentPlatform, RoleConfig
from agents_hub.agent_bridge.parsers.base import AgentEvent, AgentEventType
from agents_hub.agent_bridge.bridge import AgentBridge

__all__ = [
    "AgentPlatform",
    "RoleConfig",
    "AgentEvent",
    "AgentEventType",
    "AgentBridge",
]
