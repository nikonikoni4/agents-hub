"""Roles 应用服务层"""

from agents_hub.api.schemas.roles import RoleCreateRequest, RoleUpdateRequest
from agents_hub.config.types import AgentPlatform
from agents_hub.roles.exceptions import ValidationError
from agents_hub.roles.models import RoleInfo, SkillInfo
from agents_hub.roles.role_manager import RoleManager


class RoleService:
    """Roles 应用服务层

    协调 RoleManager，提供业务逻辑封装。
    """

    def __init__(self, role_manager: RoleManager | None = None):
        self.role_manager = role_manager or RoleManager()

    def list_roles(self) -> list[RoleInfo]:
        """获取所有角色"""
        return self.role_manager.list_roles()

    def get_role(self, name: str) -> RoleInfo:
        """获取单个角色"""
        role = self.role_manager.get_role(name)
        return role.get_info()

    def create_role(self, request: RoleCreateRequest) -> RoleInfo:
        """创建角色"""
        role = self.role_manager.create_role(
            name=request.name,
            platform=AgentPlatform(request.platform),
            avatar=request.avatar,
            abilities=request.abilities,
            type=request.type,
            scope=request.scope,
            description=request.description,
        )
        return role.get_info()

    def delete_role(self, name: str) -> None:
        """删除角色"""
        self.role_manager.delete_role(name)

    def update_role(self, name: str, request: RoleUpdateRequest) -> RoleInfo:
        """更新角色信息"""
        role = self.role_manager.get_role(name)
        if request.avatar is not None:
            role.update_avatar(request.avatar)
        if request.abilities is not None:
            role.update_abilities(request.abilities)
        if request.description is not None:
            role.update_description(request.description)
        return role.get_info()

    def list_role_skills(self, name: str) -> list[SkillInfo]:
        """列出角色的 skills"""
        role = self.role_manager.get_role(name)
        return role.list_skills()

    def add_role_skill(self, name: str, skill_id: str) -> SkillInfo:
        """为角色添加 skill"""
        role = self.role_manager.get_role(name)
        role.add_skill(skill_id)
        # 添加后重新获取 skill 信息
        skills = role.list_skills()
        for skill in skills:
            if skill.id == skill_id:
                return skill
        # 如果添加成功但无法获取元数据，说明全局 skill 的 skill.json 可能损坏
        raise ValidationError(
            message=f"Skill '{skill_id}' 已添加但元数据无效",
            error_code="SKILL_METADATA_INVALID",
            details={"skill_id": skill_id, "role_name": name},
        )

    def remove_role_skill(self, name: str, skill_id: str) -> None:
        """移除角色的 skill"""
        role = self.role_manager.get_role(name)
        role.remove_skill(skill_id)

    def list_avatars(self) -> list[str]:
        """列出可用头像"""
        return self.role_manager.list_avatars()
