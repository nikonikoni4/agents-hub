"""API schemas for roles."""

from typing import Literal

from pydantic import BaseModel

from agents_hub.roles.models import RoleInfo, SkillInfo


class RoleCreateRequest(BaseModel):
    """创建角色请求"""

    name: str
    platform: Literal["claude", "codex", "opencode"]
    avatar: str | None = None
    abilities: list[str] = []
    type: Literal["leader", "team_member", "system"] | None = None
    scope: list[str] | None = None
    description: str | None = None


class RoleUpdateRequest(BaseModel):
    """更新角色请求"""

    avatar: str | None = None
    abilities: list[str] | None = None
    description: str | None = None
    enabled_tools: list[str] | None = None


class RoleSkillRequest(BaseModel):
    """添加角色 skill 请求"""

    skill_id: str


class RoleResponse(BaseModel):
    """角色响应"""

    name: str
    platform: Literal["claude", "codex", "opencode"]
    avatar: str | None = None
    abilities: list[str] = []
    type: Literal["leader", "team_member", "system"] | None = None
    scope: list[str] | None = None
    description: str | None = None
    disabled_tools: list[str] = []
    skills: list["RoleSkillResponse"] = []

    @classmethod
    def from_domain(
        cls, role_info: RoleInfo, skills: list[SkillInfo] | None = None
    ) -> "RoleResponse":
        """从领域模型转换"""
        return cls(
            name=role_info.name,
            platform=role_info.platform.value,
            avatar=role_info.avatar,
            abilities=role_info.abilities,
            type=role_info.type.value if role_info.type else None,
            scope=role_info.scope,
            description=role_info.description,
            disabled_tools=role_info.disabled_tools or [],
            skills=[RoleSkillResponse.from_domain(s) for s in (skills or [])],
        )


class RoleSkillResponse(BaseModel):
    """角色关联的 Skill 响应"""

    id: str
    name: str
    description: str

    @classmethod
    def from_domain(cls, skill_info: SkillInfo) -> "RoleSkillResponse":
        """从领域模型转换"""
        return cls(
            id=skill_info.id,
            name=skill_info.name,
            description=skill_info.description,
        )


class ToolInfoResponse(BaseModel):
    name: str
    description: str


class ToolGroupResponse(BaseModel):
    name: str
    icon: str
    tools: list[ToolInfoResponse]


class ToolCatalogResponse(BaseModel):
    groups: list[ToolGroupResponse]
