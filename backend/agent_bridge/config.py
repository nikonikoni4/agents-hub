"""配置数据类和平台枚举"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class AgentPlatform(Enum):
    """Agent 平台枚举"""
    CLAUDE = "claude"
    CODEX = "codex"


@dataclass
class RoleConfig:
    """角色配置"""
    platform: AgentPlatform    # 平台类型
    system_prompt: str         # system prompt 内容
    skills: List[str]          # skill 列表

    # Codex 专用字段
    codex_home: Optional[str] = None  # CODEX_HOME 路径

    # 留白字段（之后实现）
    permissions: Optional[dict] = None
    tools: Optional[List[str]] = None
