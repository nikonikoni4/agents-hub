# agents_hub/api/routes/teams.py
"""团队 API 路由"""

from fastapi import APIRouter, Depends

from agents_hub.api.schemas.teams import (
    TeamCreateRequest,
    TeamResponse,
    TeamUpdateRequest,
)
from agents_hub.api.services.team_service import TeamService

router = APIRouter(prefix="/teams", tags=["teams"])


def get_team_service() -> TeamService:
    """获取 TeamService 实例(依赖注入)"""
    return TeamService()


@router.get("", response_model=list[TeamResponse])
def list_teams(service: TeamService = Depends(get_team_service)):
    """获取所有团队"""
    teams = service.list_teams()
    return [TeamResponse.from_domain(t) for t in teams]


@router.get("/{name}", response_model=TeamResponse)
def get_team(name: str, service: TeamService = Depends(get_team_service)):
    """获取单个团队"""
    team = service.get_team(name)
    return TeamResponse.from_domain(team)


@router.post("", response_model=TeamResponse, status_code=201)
def create_team(request: TeamCreateRequest, service: TeamService = Depends(get_team_service)):
    """创建团队"""
    team = service.create_team(request)
    return TeamResponse.from_domain(team)


@router.patch("/{name}", response_model=TeamResponse)
def update_team(
    name: str,
    request: TeamUpdateRequest,
    service: TeamService = Depends(get_team_service),
):
    """更新团队信息"""
    team = service.update_team(name, request)
    return TeamResponse.from_domain(team)


@router.delete("/{name}", response_model=dict[str, str])
def delete_team(name: str, service: TeamService = Depends(get_team_service)):
    """删除团队"""
    service.delete_team(name)
    return {"message": f"Team '{name}' 删除成功"}
