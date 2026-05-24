"""角色配置模块"""

from agents_hub.agents.role import Role
from agents_hub.agents.role_manager import RoleManager
from agents_hub.agents.models import RoleInfo, SkillInfo
from agents_hub.agents.exceptions import (
    RoleNotFoundError,
    RoleAlreadyExistsError,
    PlatformConfigNotFoundError,
)

__all__ = [
    "Role",
    "RoleManager",
    "RoleInfo",
    "SkillInfo",
    "RoleNotFoundError",
    "RoleAlreadyExistsError",
    "PlatformConfigNotFoundError",
]
