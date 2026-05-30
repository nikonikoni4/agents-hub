"""
Team 团队定义

包含成员列表，验证成员角色是否存在。
"""
from pydantic import BaseModel, field_validator

from agents_hub.roles import RoleManager


class Team(BaseModel):
    """团队定义"""
    team_members_name: list[str]
    team_name: str = "default_team"

    @field_validator('team_members_name')
    @classmethod
    def validate_team_members(cls, team_members_name):
        if not team_members_name:
            raise ValueError('team_members 不能为空')
        role_manager = RoleManager()
        role_info_list = role_manager.list_role_names()
        for role in team_members_name:
            if role not in role_info_list:
                raise ValueError(f"错误的role_name {role}")
        return team_members_name
