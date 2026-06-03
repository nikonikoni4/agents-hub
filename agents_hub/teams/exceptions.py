"""团队模块异常类"""

from agents_hub.exceptions import ResourceNotFoundError, ValidationError


class TeamNotFoundError(ResourceNotFoundError):
    """团队不存在"""

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
    """团队名称已存在"""

    def __init__(self, team_name: str):
        super().__init__(
            message=f"Team '{team_name}' 已存在",
            error_code="TEAM_ALREADY_EXISTS",
            details={"team_name": team_name},
        )


class InvalidTeamMembersError(ValidationError):
    """团队成员验证失败"""

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
    """团队成员列表为空"""

    def __init__(self):
        super().__init__(
            message="团队成员列表不能为空",
            error_code="EMPTY_TEAM_MEMBERS",
            details={},
        )
