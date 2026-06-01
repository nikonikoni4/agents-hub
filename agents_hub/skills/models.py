# agents_hub/skills/models.py
from dataclasses import dataclass


@dataclass
class SkillInfo:
    """Skill 信息（从 SKILL.md frontmatter 解析）"""

    name: str  # skill 名称
    description: str  # skill 描述
    path: str  # skill 目录的绝对路径（内部使用）
