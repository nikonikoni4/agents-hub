"""基础类型定义 - 跨模块共享的枚举和常量

此模块存放被多个模块共享的基础类型，避免循环依赖。
"""

from enum import Enum
from pathlib import Path

# CLI 命令路径常量
CODEX_COMMAND = str(Path.home() / "AppData" / "Roaming" / "npm" / "codex.cmd")
CLAUDE_COMMAND = str(Path.home() / ".local" / "bin" / "claude")


class AgentPlatform(Enum):
    """Agent 平台枚举"""
    CLAUDE = "claude"
    CODEX = "codex"


class RoleType(Enum):
    """角色类型枚举

    Attributes:
        LEADER: 领导者角色，负责任务分派和协调
        TEAM_MEMBER: 团队成员角色，执行具体任务
    """
    LEADER = "leader"
    TEAM_MEMBER = "team_member"
