# agents_hub/api/services/team_service.py
"""团队服务层"""

from agents_hub.api.schemas.teams import TeamCreateRequest, TeamUpdateRequest
from agents_hub.teams import TeamManager
from agents_hub.teams.models import TeamInfo


class TeamService:
    """Team Service 层

    职责：
    1. 协调 TeamManager 调用
    2. 处理 Request Schema → 领域模型转换
    3. 处理领域模型 → Response Schema 转换
    """

    def __init__(self):
        self.team_manager = TeamManager()

    def create_team(self, request: TeamCreateRequest) -> TeamInfo:
        """创建团队"""
        return self.team_manager.create_team(request.name, request.members)

    def get_team(self, name: str) -> TeamInfo:
        """获取团队"""
        return self.team_manager.get_team(name)

    def list_teams(self) -> list[TeamInfo]:
        """列出所有团队"""
        return self.team_manager.list_teams()

    def update_team(self, name: str, request: TeamUpdateRequest) -> TeamInfo:
        """更新团队"""
        return self.team_manager.update_team(name, request.name, request.members)

    def delete_team(self, name: str) -> None:
        """删除团队"""
        self.team_manager.delete_team(name)
