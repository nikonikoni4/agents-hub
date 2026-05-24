"""角色配置模块"""

# Role 和 RoleManager 将在后续 Task 2/3 中实现，届时取消注释
# from agents_hub.agents.role import Role
# from agents_hub.agents.role_manager import RoleManager
from agents_hub.agents.models import RoleInfo, SkillInfo
from agents_hub.agents.exceptions import (
    RoleNotFoundError,
    RoleAlreadyExistsError,
    PlatformConfigNotFoundError,
)

__all__ = [
    # "Role",
    # "RoleManager",
    "RoleInfo",
    "SkillInfo",
    "RoleNotFoundError",
    "RoleAlreadyExistsError",
    "PlatformConfigNotFoundError",
]
