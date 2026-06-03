import shutil
from pathlib import Path

import yaml

from agents_hub.config import config
from agents_hub.skills.exceptions import InvalidSkillError, SkillNotFoundError
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

        if not isinstance(frontmatter["name"], str) or not isinstance(
            frontmatter["description"], str
        ):
            raise InvalidSkillError(
                f"Invalid field types in {skill_path}/SKILL.md (name and description must be strings)"
            )

        return SkillInfo(
            name=frontmatter["name"],
            description=frontmatter["description"],
            path=str(skill_path),
        )

    def list_skills(self) -> list[SkillInfo]:
        """列出所有 skills"""
        skills = []
        for skill_dir in self.skills_root.iterdir():
            if skill_dir.is_dir():
                try:
                    skill_info = self._parse_skill_md(skill_dir)
                    skills.append(skill_info)
                except InvalidSkillError:
                    # 跳过无效的 skill 目录
                    continue
        return skills

    def get_skill(self, skill_name: str) -> SkillInfo:
        """获取单个 skill 信息"""
        skill_path = (self.skills_root / skill_name).resolve()
        # Security: Prevent path traversal attacks
        if not skill_path.is_relative_to(self.skills_root.resolve()):
            raise InvalidSkillError(f"Invalid skill name: {skill_name}")
        if not skill_path.exists():
            raise SkillNotFoundError(f"Skill '{skill_name}' not found")

        return self._parse_skill_md(skill_path)

    def delete_skill(self, skill_name: str) -> None:
        """删除 skill"""
        skill_path = (self.skills_root / skill_name).resolve()
        # Security: Prevent path traversal attacks
        if not skill_path.is_relative_to(self.skills_root.resolve()):
            raise InvalidSkillError(f"Invalid skill name: {skill_name}")
        if not skill_path.exists():
            raise SkillNotFoundError(f"Skill '{skill_name}' not found")

        shutil.rmtree(skill_path)

    def add_skill_from_url(self, url: str) -> SkillInfo:
        """从网络添加 skill（预留接口，暂不实现）

        Args:
            url: skill 的网络地址

        Returns:
            SkillInfo: 添加的 skill 信息

        Raises:
            NotImplementedError: 功能暂未实现

        未来实现：
            1. 下载 skill 压缩包
            2. 解压到临时目录
            3. 验证 SKILL.md 格式
            4. 移动到 skills_root
        """
        raise NotImplementedError("网络获取功能暂未实现")
