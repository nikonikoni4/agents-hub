"""Roles 应用服务层"""

from pathlib import Path

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

    def list_roles(self) -> list[tuple[RoleInfo, list[SkillInfo]]]:
        """获取所有角色（含 skills）"""
        roles_info = self.role_manager.list_roles()
        result = []
        for info in roles_info:
            role = self.role_manager.get_role(info.name)
            result.append((info, role.list_skills()))
        return result

    def get_role(self, name: str) -> tuple[RoleInfo, list[SkillInfo]]:
        """获取单个角色（含 skills）"""
        role = self.role_manager.get_role(name)
        return role.get_info(), role.list_skills()

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

    def update_role(
        self, name: str, request: RoleUpdateRequest
    ) -> tuple[RoleInfo, list[SkillInfo]]:
        """更新角色信息"""
        role = self.role_manager.get_role(name)
        if request.avatar is not None:
            role.update_avatar(request.avatar)
        if request.abilities is not None:
            role.update_abilities(request.abilities)
        if request.description is not None:
            role.update_description(request.description)
        return role.get_info(), role.list_skills()

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

    def get_avatar_file_path(self, filename: str) -> Path:
        """获取头像文件的绝对路径，做安全校验"""
        from agents_hub.config import config

        assets_dir = config.data_path / "avatars"
        file_path = (assets_dir / filename).resolve()
        if not file_path.is_relative_to(assets_dir.resolve()):
            raise ValidationError(
                message="无效的头像文件名",
                error_code="INVALID_AVATAR_PATH",
                details={"filename": filename},
            )
        if not file_path.exists():
            raise ValidationError(
                message=f"头像文件 '{filename}' 不存在",
                error_code="AVATAR_NOT_FOUND",
                details={"filename": filename},
            )
        return file_path
