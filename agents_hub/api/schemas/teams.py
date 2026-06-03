"""API schemas for teams."""

from pydantic import BaseModel

from agents_hub.teams.models import TeamInfo


class TeamCreateRequest(BaseModel):
    """创建团队请求"""

    name: str
    members: list[str]


class TeamUpdateRequest(BaseModel):
    """更新团队请求"""

    name: str | None = None
    members: list[str] | None = None


class TeamResponse(BaseModel):
    """团队响应"""

    name: str
    members: list[str]

    @classmethod
    def from_domain(cls, team_info: TeamInfo) -> "TeamResponse":
        """从领域模型转换"""
        return cls(name=team_info.name, members=team_info.members)
