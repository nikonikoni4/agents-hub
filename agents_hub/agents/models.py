"""角色配置模块的数据结构定义"""

from dataclasses import dataclass
from typing import Optional, List
from agents_hub.agent_bridge.config import AgentPlatform


@dataclass
class RoleInfo:
    """角色摘要信息"""
    name: str
    platform: AgentPlatform
    avatar: Optional[str]
    abilities: List[str]
    type: Optional[str] = None  # "leader" | "team_member" | None
    scope: Optional[List[str]] = None  # 所属群聊列表


@dataclass
class SkillInfo:
    """Skill 摘要信息"""
    id: str           # skill 标识
    name: str         # skill 名称
    description: str  # skill 描述
