"""角色配置模块的自定义异常。"""


class RoleError(Exception):
    """角色配置异常基类。

    所有角色配置相关异常的父类，可用于统一捕获。
    """
    pass


class RoleNotFoundError(RoleError):
    """角色不存在。

    当尝试访问或操作一个不存在的角色时抛出。

    Attributes:
        message: 错误描述信息。
    """
    pass


class RoleAlreadyExistsError(RoleError):
    """角色已存在。

    当尝试创建一个已存在的角色时抛出。

    Attributes:
        message: 错误描述信息。
    """
    pass


class PlatformConfigNotFoundError(RoleError):
    """平台配置目录不存在。

    当 Claude (~/.claude) 或 Codex (~/.codex) 的配置目录不存在时抛出。

    Attributes:
        message: 错误描述信息。
    """
    pass


class SkillNotFoundError(RoleError):
    """Skill 不存在。

    当尝试访问或移除一个不存在的 Skill 时抛出。

    Attributes:
        message: 错误描述信息。
    """
    pass


class SkillAlreadyExistsError(RoleError):
    """Skill 已存在于角色中。

    当尝试添加一个已存在的 Skill 时抛出。

    Attributes:
        message: 错误描述信息。
    """
    pass
