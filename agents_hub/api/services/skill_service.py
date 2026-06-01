# agents_hub/api/services/skill_service.py
from agents_hub.skills.models import SkillInfo
from agents_hub.skills.skill_manager import SkillManager


class SkillService:
    """Skills 应用服务层"""

    def __init__(self):
        self.skill_manager = SkillManager()

    def list_skills(self) -> list[SkillInfo]:
        """获取所有 skills"""
        return self.skill_manager.list_skills()

    def get_skill(self, skill_name: str) -> SkillInfo:
        """获取单个 skill"""
        return self.skill_manager.get_skill(skill_name)

    def delete_skill(self, skill_name: str) -> None:
        """删除 skill"""
        self.skill_manager.delete_skill(skill_name)

    def add_skill_from_url(self, url: str) -> SkillInfo:
        """从网络添加 skill（预留）"""
        return self.skill_manager.add_skill_from_url(url)
