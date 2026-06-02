# agents_hub/api/routes/skills.py
from fastapi import APIRouter, Depends, HTTPException

from agents_hub.api.schemas.skills import SkillCreateRequest, SkillResponse
from agents_hub.api.services.skill_service import SkillService
from agents_hub.skills.exceptions import SkillNotFoundError

router = APIRouter()


def get_skill_service() -> SkillService:
    """获取 SkillService 实例（依赖注入）"""
    return SkillService()


@router.get("/skills", response_model=list[SkillResponse])
def list_skills(service: SkillService = Depends(get_skill_service)):
    """获取所有 skills

    Returns:
        list[SkillResponse]: skills 列表
    """
    skills = service.list_skills()
    return [SkillResponse.from_domain(s) for s in skills]


@router.get("/skills/{skill_name}", response_model=SkillResponse)
def get_skill(skill_name: str, service: SkillService = Depends(get_skill_service)):
    """获取单个 skill

    Args:
        skill_name: skill 名称

    Returns:
        SkillResponse: skill 信息

    Raises:
        HTTPException: 404 - skill 不存在
    """
    try:
        skill = service.get_skill(skill_name)
        return SkillResponse.from_domain(skill)
    except SkillNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' 不存在") from e


@router.delete("/skills/{skill_name}", response_model=dict[str, str])
def delete_skill(skill_name: str, service: SkillService = Depends(get_skill_service)):
    """删除 skill

    Args:
        skill_name: skill 名称

    Returns:
        dict: 成功消息

    Raises:
        HTTPException: 404 - skill 不存在
    """
    try:
        service.delete_skill(skill_name)
        return {"message": f"Skill '{skill_name}' 删除成功"}
    except SkillNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' 不存在") from e


@router.post("/skills", response_model=SkillResponse)
def add_skill(request: SkillCreateRequest, service: SkillService = Depends(get_skill_service)):
    """从网络添加 skill(预留接口)

    Args:
        request: 包含 skill URL 的请求

    Returns:
        SkillResponse: 添加的 skill 信息

    Raises:
        HTTPException: 501 - 功能暂未实现
    """
    try:
        skill = service.add_skill_from_url(request.url)
        return SkillResponse.from_domain(skill)
    except NotImplementedError as e:
        raise HTTPException(
            status_code=501, detail=f"从 URL 添加 skill 功能暂未实现: {request.url}"
        ) from e
