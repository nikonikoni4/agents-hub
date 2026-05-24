"""角色配置模块的自定义异常"""


class RoleError(Exception):
    """角色配置异常基类"""
    pass


class RoleNotFoundError(RoleError):
    """角色不存在"""
    pass


class RoleAlreadyExistsError(RoleError):
    """角色已存在"""
    pass


class PlatformConfigNotFoundError(RoleError):
    """平台配置目录不存在 (如 ~/.claude 或 ~/.codex)"""
    pass


class SkillNotFoundError(RoleError):
    """Skill 不存在"""
    pass


class SkillAlreadyExistsError(RoleError):
    """Skill 已存在于角色中"""
    pass
