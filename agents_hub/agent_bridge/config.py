"""配置数据类和平台枚举"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from enum import Enum

# CLI 命令路径
CODEX_COMMAND = str(Path.home() / "AppData" / "Roaming" / "npm" / "codex.cmd")
CLAUDE_COMMAND = str(Path.home() / ".local" / "bin" / "claude")


class AgentPlatform(Enum):
    """Agent 平台枚举"""
    CLAUDE = "claude"
    CODEX = "codex"


@dataclass
class RoleConfig:
    """角色配置

    system_prompt 和 skills 由 CLI 从目录自动加载，不在此配置。
    - Claude: 从 CLAUDE.md 自动加载 system_prompt
    - Codex: 从 AGENTS.md 自动加载 system_prompt
    """
    platform: AgentPlatform    # 平台类型
    work_root: Optional[str] = None  # 角色工作目录路径（注入 CODEX_HOME / CLAUDE_CONFIG_DIR）
