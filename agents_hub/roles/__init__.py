"""角色配置模块"""

from agents_hub.roles.exceptions import (
    PlatformConfigNotFoundError,
    RoleAlreadyExistsError,
    RoleNotFoundError,
)
from agents_hub.roles.models import RoleConfig, RoleInfo, RoleType, SkillInfo
from agents_hub.roles.role import Role
from agents_hub.roles.role_manager import RoleManager

__all__ = [
    "Role",
    "RoleManager",
    "RoleConfig",
    "RoleInfo",
    "SkillInfo",
    "RoleType",
    "RoleNotFoundError",
    "RoleAlreadyExistsError",
    "PlatformConfigNotFoundError",
]
