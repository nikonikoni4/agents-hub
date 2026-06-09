"""角色配置模块的数据结构定义"""

from dataclasses import dataclass

from agents_hub.config.types import AgentPlatform, RoleType


@dataclass
class RoleConfig:
    """角色配置

    system_prompt 和 skills 由 CLI 从目录自动加载，不在此配置。
    - Claude: 从 CLAUDE.md 自动加载 system_prompt
    - Codex: 从 AGENTS.md 自动加载 system_prompt
    """

    name: str  # 角色名称
    platform: AgentPlatform  # 平台类型
    description: str | None = None  # 角色职责描述
    work_root: str | None = None  # 角色工作目录路径（注入 CODEX_HOME / CLAUDE_CONFIG_DIR）
    role_type: RoleType = RoleType.TEAM_MEMBER  # 角色类型，默认为团队成员
    bare: bool = (
        False  # Claude CLI 极简模式：跳过 hooks/LSP/plugin sync/auto-memory/CLAUDE.md 自动发现
    )
    # 极简模式用于——秘书工作——即简单的llm调用工作 （暂定），后续如果为了追求简单可能会设置单独的llm AIP call，而不是使用CLI


@dataclass
class RoleInfo:
    """角色摘要信息。

    用于在列表和摘要场景中表示角色的基本信息，
    不包含完整的配置数据。

    Attributes:
        name: 角色名称，与目录名一致。
        platform: 目标平台类型（claude 或 codex）。
        description: 角色职责描述，可为空。
        avatar: 头像文件的相对路径，可为空。
        abilities: 能力标签列表，用于展示和调度。
        type: 角色类型，可选值为 leader、team_member 或 system。
        scope: 所属群聊列表，MVP 阶段不实现逻辑。
        disabled_tools: 禁用的工具名称列表，可为空。
    """

    name: str
    platform: AgentPlatform
    avatar: str | None
    abilities: list[str]
    type: RoleType | None = RoleType.TEAM_MEMBER
    description: str | None = None
    scope: list[str] | None = None
    disabled_tools: list[str] | None = None


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
