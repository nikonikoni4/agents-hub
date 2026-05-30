"""角色配置模块的自定义异常。

所有异常继承自顶层 agents_hub.exceptions，遵循统一的错误处理规范。
"""

from agents_hub.exceptions import ResourceNotFoundError, ValidationError


class RoleNotFoundError(ResourceNotFoundError):
    """角色不存在

    特征：请求的角色不存在
    处理策略：返回 404 类错误，提示可用角色

    示例：
    - 尝试获取不存在的角色
    - 尝试删除不存在的角色
    """

    def __init__(self, role_name: str, available_roles: list[str] | None = None):
        super().__init__(
            message=f"Role '{role_name}' 不存在",
            error_code="ROLE_NOT_FOUND",
            details={
                "role_name": role_name,
                "available_roles": available_roles or []
            }
        )


class RoleAlreadyExistsError(ValidationError):
    """角色已存在

    特征：尝试创建已存在的角色
    处理策略：返回详细错误信息，提示使用其他名称

    示例：
    - 创建重复的角色名称
    """

    def __init__(self, role_name: str):
        super().__init__(
            message=f"Role '{role_name}' 已存在",
            error_code="ROLE_ALREADY_EXISTS",
            details={"role_name": role_name}
        )


class PlatformConfigNotFoundError(ResourceNotFoundError):
    """平台配置目录不存在

    特征：平台配置目录（~/.claude 或 ~/.codex）不存在
    处理策略：返回详细错误信息，提示安装对应平台

    示例：
    - 创建角色时找不到 ~/.claude 目录
    - 创建角色时找不到 ~/.codex 目录
    """

    def __init__(self, platform: str, config_path: str):
        super().__init__(
            message=f"{platform} 配置目录不存在: {config_path}",
            error_code="PLATFORM_CONFIG_NOT_FOUND",
            details={
                "platform": platform,
                "config_path": config_path
            }
        )


class SkillNotFoundError(ResourceNotFoundError):
    """Skill 不存在

    特征：请求的 Skill 不存在
    处理策略：返回 404 类错误，提示可用 Skill

    示例：
    - 尝试添加不存在的 Skill
    - 尝试移除不存在的 Skill
    """

    def __init__(self, skill_id: str, available_skills: list[str] | None = None):
        super().__init__(
            message=f"Skill '{skill_id}' 不存在",
            error_code="SKILL_NOT_FOUND",
            details={
                "skill_id": skill_id,
                "available_skills": available_skills or []
            }
        )


class SkillAlreadyExistsError(ValidationError):
    """Skill 已存在于角色中

    特征：尝试添加已存在的 Skill
    处理策略：返回详细错误信息，提示 Skill 已添加

    示例：
    - 重复添加同一个 Skill
    """

    def __init__(self, skill_id: str, role_name: str):
        super().__init__(
            message=f"Skill '{skill_id}' 已存在于角色 '{role_name}' 中",
            error_code="SKILL_ALREADY_EXISTS",
            details={
                "skill_id": skill_id,
                "role_name": role_name
            }
        )
