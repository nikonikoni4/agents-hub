# agents_hub/skills/exceptions.py
class SkillNotFoundError(Exception):
    """Skill 不存在"""

    pass


class InvalidSkillError(Exception):
    """无效的 Skill（SKILL.md 格式错误）"""

    pass
