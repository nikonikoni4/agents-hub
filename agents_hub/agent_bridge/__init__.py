"""Agent Bridge 模块 - 统一的 AI 平台 CLI 调用接口"""

from agents_hub.config.types import (
    AgentPlatform,
    RoleType,
    CODEX_COMMAND,
    CLAUDE_COMMAND,
)
from agents_hub.agent_bridge.models import (
    StreamEvent,
    AgentResult,
    AgentEventType,
    AgentEvent,  # 向后兼容别名
)
from agents_hub.agent_bridge.bridge import AgentBridge

__all__ = [
    "AgentPlatform",
    "RoleType",
    "StreamEvent",
    "AgentResult",
    "AgentEventType",
    "AgentBridge",
    "CODEX_COMMAND",
    "CLAUDE_COMMAND",
    "AgentEvent",  # 向后兼容
]
