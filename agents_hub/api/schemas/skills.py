"""API schemas for skills."""

from pydantic import BaseModel

from agents_hub.skills.models import SkillInfo


class SkillResponse(BaseModel):
    """Skill 响应模型"""

    name: str
    description: str

    @classmethod
    def from_domain(cls, skill_info: SkillInfo) -> "SkillResponse":
        """从领域模型转换"""
        return cls(
            name=skill_info.name,
            description=skill_info.description,
        )


class SkillCreateRequest(BaseModel):
    """创建 Skill 请求（预留，暂不实现）"""

    url: str  # skill 的网络地址
