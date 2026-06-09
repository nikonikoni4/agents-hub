"""基础类型定义 - 跨模块共享的枚举和常量

此模块存放被多个模块共享的基础类型，避免循环依赖。
"""

from enum import Enum
from pathlib import Path

# 宿主机 CLI 命令路径常量
CODEX_COMMAND = str(Path.home() / "AppData" / "Roaming" / "npm" / "codex.cmd")
CLAUDE_COMMAND = str(Path.home() / ".local" / "bin" / "claude")
OPENCODE_COMMAND = str(Path.home() / "AppData" / "Roaming" / "npm" / "opencode.cmd")

# Docker 容器内 CLI 命令路径常量（npm 全局安装）
DOCKER_CLAUDE_COMMAND = "/usr/bin/claude"
DOCKER_CODEX_COMMAND = "/usr/bin/codex"


class AgentPlatform(Enum):
    """Agent 平台枚举"""

    CLAUDE = "claude"
    CODEX = "codex"
    OPENCODE = "opencode"


class RoleType(Enum):
    """角色类型枚举

    Attributes:
        LEADER: 领导者角色，负责任务分派和协调
        TEAM_MEMBER: 团队成员角色，执行具体任务
        SYSTEM: 系统角色，由系统预置的特殊角色
    """

    LEADER = "leader"
    TEAM_MEMBER = "team_member"
    SYSTEM = "system"
