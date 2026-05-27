"""角色配置模块的数据结构定义。"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

from agents_hub.agent_bridge.models import AgentPlatform


@dataclass
class RoleConfig:
    """角色配置

    system_prompt 和 skills 由 CLI 从目录自动加载，不在此配置。
    - Claude: 从 CLAUDE.md 自动加载 system_prompt
    - Codex: 从 AGENTS.md 自动加载 system_prompt
    """
    name: str                  # 角色名称
    platform: AgentPlatform    # 平台类型
    work_root: Optional[str] = None  # 角色工作目录路径（注入 CODEX_HOME / CLAUDE_CONFIG_DIR）


class RoleType(Enum):
    """角色类型枚举。

    Attributes:
        LEADER: 领导者角色，负责任务分派和协调。
        TEAM_MEMBER: 团队成员角色，执行具体任务。
    """
    LEADER = "leader"
    TEAM_MEMBER = "team_member"


@dataclass
class RoleInfo:
    """角色摘要信息。

    用于在列表和摘要场景中表示角色的基本信息，
    不包含完整的配置数据。

    Attributes:
        name: 角色名称，与目录名一致。
        platform: 目标平台类型（claude 或 codex）。
        avatar: 头像文件的相对路径，可为空。
        abilities: 能力标签列表，用于展示和调度。
        type: 角色类型，可选值为 leader 或 team_member。
        scope: 所属群聊列表，MVP 阶段不实现逻辑。
    """
    name: str
    platform: AgentPlatform
    avatar: Optional[str]
    abilities: List[str]
    type: Optional[RoleType] = RoleType.TEAM_MEMBER
    scope: Optional[List[str]] = None


@dataclass
class SkillInfo:
    """Skill 摘要信息。

    表示一个已启用的 Skill 的基本信息。

    Attributes:
        id: Skill 的唯一标识符。
        name: Skill 的显示名称。
        description: Skill 的功能描述。
    """
    id: str
    name: str
    description: str
