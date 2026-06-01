from pathlib import Path

import yaml  # type: ignore[import-untyped]

from agents_hub.config import config
from agents_hub.skills.exceptions import InvalidSkillError
from agents_hub.skills.models import SkillInfo


class SkillManager:
    """全局 Skill 管理器"""

    def __init__(self):
        self.skills_root = config.data_path / "skills"
        self.skills_root.mkdir(parents=True, exist_ok=True)

    def _parse_skill_md(self, skill_path: Path) -> SkillInfo:
        """解析 SKILL.md 的 frontmatter"""
        skill_md = skill_path / "SKILL.md"

        if not skill_md.exists():
            raise InvalidSkillError(f"SKILL.md not found in {skill_path}")

        content = skill_md.read_text(encoding="utf-8")

        # 解析 frontmatter（格式：--- ... ---）
        if not content.startswith("---"):
            raise InvalidSkillError(f"Invalid SKILL.md format in {skill_path}")

        parts = content.split("---", 2)
        if len(parts) < 3:
            raise InvalidSkillError(f"Invalid SKILL.md format in {skill_path}")

        frontmatter = yaml.safe_load(parts[1])

        if "name" not in frontmatter or "description" not in frontmatter:
            raise InvalidSkillError(f"Missing name or description in {skill_path}/SKILL.md")

        return SkillInfo(
            name=frontmatter["name"],
            description=frontmatter["description"],
            path=str(skill_path),
        )
