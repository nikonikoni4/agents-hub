"""角色 API 路由"""

from fastapi import APIRouter, Depends

from agents_hub.api.schemas.roles import (
    RoleCreateRequest,
    RoleResponse,
    RoleSkillRequest,
    RoleSkillResponse,
    RoleUpdateRequest,
)
from agents_hub.api.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["roles"])


def get_role_service() -> RoleService:
    """获取 RoleService 实例（依赖注入）"""
    return RoleService()


# ========== 角色 CRUD ==========


@router.get("", response_model=list[RoleResponse])
def list_roles(service: RoleService = Depends(get_role_service)):
    """获取所有角色"""
    roles = service.list_roles()
    return [RoleResponse.from_domain(r) for r in roles]


@router.get("/avatars", response_model=list[str])
def list_avatars(service: RoleService = Depends(get_role_service)):
    """列出可用头像"""
    return service.list_avatars()


@router.get("/{name}", response_model=RoleResponse)
def get_role(name: str, service: RoleService = Depends(get_role_service)):
    """获取单个角色"""
    role = service.get_role(name)
    return RoleResponse.from_domain(role)


@router.post("", response_model=RoleResponse, status_code=201)
def create_role(request: RoleCreateRequest, service: RoleService = Depends(get_role_service)):
    """创建角色"""
    role = service.create_role(request)
    return RoleResponse.from_domain(role)


@router.delete("/{name}", response_model=dict[str, str])
def delete_role(name: str, service: RoleService = Depends(get_role_service)):
    """删除角色"""
    service.delete_role(name)
    return {"message": f"Role '{name}' 删除成功"}


# ========== 更新角色信息 ==========


@router.patch("/{name}", response_model=RoleResponse)
def update_role(
    name: str,
    request: RoleUpdateRequest,
    service: RoleService = Depends(get_role_service),
):
    """更新角色信息"""
    role = service.update_role(name, request)
    return RoleResponse.from_domain(role)


# ========== 角色 Skill 管理 ==========


@router.get("/{name}/skills", response_model=list[RoleSkillResponse])
def list_role_skills(name: str, service: RoleService = Depends(get_role_service)):
    """列出角色的 skills"""
    skills = service.list_role_skills(name)
    return [RoleSkillResponse.from_domain(s) for s in skills]


@router.post("/{name}/skills", response_model=RoleSkillResponse, status_code=201)
def add_role_skill(
    name: str,
    request: RoleSkillRequest,
    service: RoleService = Depends(get_role_service),
):
    """为角色添加 skill"""
    skill = service.add_role_skill(name, request.skill_id)
    return RoleSkillResponse.from_domain(skill)


@router.delete("/{name}/skills/{skill_id}", response_model=dict[str, str])
def remove_role_skill(name: str, skill_id: str, service: RoleService = Depends(get_role_service)):
    """移除角色的 skill"""
    service.remove_role_skill(name, skill_id)
    return {"message": f"Skill '{skill_id}' 从角色 '{name}' 移除成功"}
