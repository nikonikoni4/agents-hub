# agents_hub/api/routes/skills.py
from fastapi import APIRouter, Depends

from agents_hub.api.schemas.skills import SkillCreateRequest, SkillResponse
from agents_hub.api.services.skill_service import SkillService

router = APIRouter(prefix="/skills", tags=["skills"])


def get_skill_service() -> SkillService:
    """获取 SkillService 实例（依赖注入）"""
    return SkillService()


@router.get("", response_model=list[SkillResponse])
def list_skills(service: SkillService = Depends(get_skill_service)):
    """获取所有 skills"""
    skills = service.list_skills()
    return [SkillResponse.from_domain(s) for s in skills]


@router.get("/{skill_name}", response_model=SkillResponse)
def get_skill(skill_name: str, service: SkillService = Depends(get_skill_service)):
    """获取单个 skill"""
    skill = service.get_skill(skill_name)
    return SkillResponse.from_domain(skill)


@router.delete("/{skill_name}", response_model=dict[str, str])
def delete_skill(skill_name: str, service: SkillService = Depends(get_skill_service)):
    """删除 skill"""
    service.delete_skill(skill_name)
    return {"message": f"Skill '{skill_name}' 删除成功"}


@router.post("", response_model=SkillResponse)
def add_skill(request: SkillCreateRequest, service: SkillService = Depends(get_skill_service)):
    """从网络添加 skill(预留接口)"""
    skill = service.add_skill_from_url(request.url)
    return SkillResponse.from_domain(skill)
