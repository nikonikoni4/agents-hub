"""角色配置模块"""

from agents_hub.roles.role import Role
from agents_hub.roles.role_manager import RoleManager
from agents_hub.roles.models import RoleInfo, SkillInfo, RoleType
from agents_hub.roles.exceptions import (
    RoleNotFoundError,
    RoleAlreadyExistsError,
    PlatformConfigNotFoundError,
)

__all__ = [
    "Role",
    "RoleManager",
    "RoleInfo",
    "SkillInfo",
    "RoleType",
    "RoleNotFoundError",
    "RoleAlreadyExistsError",
    "PlatformConfigNotFoundError",
]
