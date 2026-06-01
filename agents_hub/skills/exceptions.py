# agents_hub/skills/exceptions.py
from agents_hub.exceptions import ResourceNotFoundError, ValidationError


class SkillNotFoundError(ResourceNotFoundError):
    """Skill 不存在"""

    pass


class InvalidSkillError(ValidationError):
    """无效的 Skill（SKILL.md 格式错误）"""

    pass
