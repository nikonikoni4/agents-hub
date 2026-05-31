"""配置模块 - 基础类型和常量"""

from agents_hub.config.config import Config, SystemConfig, config
from agents_hub.config.types import (
    CLAUDE_COMMAND,
    CODEX_COMMAND,
    AgentPlatform,
    RoleType,
)

__all__ = [
    # 类型和枚举
    "AgentPlatform",
    "RoleType",
    # 常量
    "CODEX_COMMAND",
    "CLAUDE_COMMAND",
    # 配置类
    "Config",
    "SystemConfig",
    # 全局实例（推荐使用 config）
    "config",
]
