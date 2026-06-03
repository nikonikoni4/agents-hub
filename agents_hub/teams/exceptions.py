"""团队模块的自定义异常。

所有异常继承自顶层 agents_hub.exceptions，遵循统一的错误处理规范。
"""

from agents_hub.exceptions import ResourceNotFoundError, ValidationError


class TeamNotFoundError(ResourceNotFoundError):
    """团队不存在

    特征：请求的团队不存在
    处理策略：返回 404 类错误，提示可用团队

    示例：
    - 尝试获取不存在的团队
    - 尝试更新不存在的团队
    - 尝试删除不存在的团队
    """

    def __init__(self, team_name: str, available_teams: list[str] | None = None):
        super().__init__(
            message=f"Team '{team_name}' 不存在",
            error_code="TEAM_NOT_FOUND",
            details={
                "team_name": team_name,
                "available_teams": available_teams or [],
            },
        )


class TeamAlreadyExistsError(ValidationError):
    """团队已存在

    特征：尝试创建已存在的团队
    处理策略：返回详细错误信息，提示使用其他名称

    示例：
    - 创建重复的团队名称
    """

    def __init__(self, team_name: str):
        super().__init__(
            message=f"Team '{team_name}' 已存在",
            error_code="TEAM_ALREADY_EXISTS",
            details={"team_name": team_name},
        )


class InvalidTeamMembersError(ValidationError):
    """团队成员验证失败

    特征：团队成员列表中包含无效的角色名称
    处理策略：返回详细错误信息，提示无效成员和可用角色

    示例：
    - 尝试添加不存在的角色到团队
    - 尝试更新团队时使用无效的角色名称
    """

    def __init__(self, invalid_members: list[str], available_roles: list[str]):
        super().__init__(
            message=f"无效的团队成员: {', '.join(invalid_members)}",
            error_code="INVALID_TEAM_MEMBERS",
            details={
                "invalid_members": invalid_members,
                "available_roles": available_roles,
            },
        )


class EmptyTeamMembersError(ValidationError):
    """团队成员列表为空

    特征：尝试创建或更新团队时成员列表为空
    处理策略：返回详细错误信息，提示必须至少包含一个成员

    示例：
    - 创建团队时没有提供任何成员
    - 更新团队时清空所有成员
    """

    def __init__(self):
        super().__init__(
            message="团队成员列表不能为空",
            error_code="EMPTY_TEAM_MEMBERS",
            details={},
        )
