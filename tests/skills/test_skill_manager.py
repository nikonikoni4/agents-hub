import pytest
from pathlib import Path
from agents_hub.skills.skill_manager import SkillManager
from agents_hub.skills.exceptions import InvalidSkillError, SkillNotFoundError


def test_parse_skill_md_missing_file():
    """测试：SKILL.md 文件不存在"""
    manager = SkillManager()
    invalid_path = Path("tests/skills/fixtures/nonexistent")

    with pytest.raises(InvalidSkillError, match="SKILL.md not found"):
        manager._parse_skill_md(invalid_path)


def test_parse_skill_md_invalid_format():
    """测试：SKILL.md 格式错误（没有 frontmatter）"""
    manager = SkillManager()
    # 创建无效的 SKILL.md
    invalid_path = Path("tests/skills/fixtures/invalid-format")
    invalid_path.mkdir(parents=True, exist_ok=True)
    (invalid_path / "SKILL.md").write_text("No frontmatter here", encoding="utf-8")

    with pytest.raises(InvalidSkillError, match="Invalid SKILL.md format"):
        manager._parse_skill_md(invalid_path)


def test_parse_skill_md_missing_fields():
    """测试：SKILL.md 缺少必需字段"""
    manager = SkillManager()
    # 创建缺少字段的 SKILL.md
    missing_path = Path("tests/skills/fixtures/missing-fields")
    missing_path.mkdir(parents=True, exist_ok=True)
    (missing_path / "SKILL.md").write_text(
        "---\nname: test\n---\nContent", encoding="utf-8"
    )

    with pytest.raises(InvalidSkillError, match="Missing name or description"):
        manager._parse_skill_md(missing_path)


def test_parse_skill_md_success():
    """测试：成功解析 SKILL.md"""
    manager = SkillManager()
    valid_path = Path("tests/skills/fixtures/valid-skill")

    skill_info = manager._parse_skill_md(valid_path)

    assert skill_info.name == "test-skill"
    assert skill_info.description == "A test skill for unit testing"
    assert str(valid_path) in skill_info.path


def test_list_skills_empty():
    """测试：空的 skills 目录"""
    manager = SkillManager()
    # 临时修改 skills_root 为空目录
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        manager.skills_root = Path(tmpdir)
        skills = manager.list_skills()
        assert skills == []


def test_list_skills_with_valid_skills():
    """测试：列出有效的 skills"""
    manager = SkillManager()
    # 使用 fixtures 目录
    manager.skills_root = Path("tests/skills/fixtures")

    skills = manager.list_skills()

    # 应该只包含 valid-skill（跳过无效的）
    assert len(skills) >= 1
    skill_names = [s.name for s in skills]
    assert "test-skill" in skill_names


def test_get_skill_not_found():
    """测试：获取不存在的 skill"""
    manager = SkillManager()

    with pytest.raises(SkillNotFoundError, match="Skill 'nonexistent' not found"):
        manager.get_skill("nonexistent")


def test_get_skill_success():
    """测试：成功获取 skill"""
    manager = SkillManager()
    manager.skills_root = Path("tests/skills/fixtures")

    skill = manager.get_skill("valid-skill")

    assert skill.name == "test-skill"
    assert skill.description == "A test skill for unit testing"


def test_delete_skill_not_found():
    """测试：删除不存在的 skill"""
    manager = SkillManager()

    with pytest.raises(SkillNotFoundError, match="Skill 'nonexistent' not found"):
        manager.delete_skill("nonexistent")


def test_delete_skill_success():
    """测试：成功删除 skill"""
    import tempfile

    manager = SkillManager()

    # 创建临时 skill 目录
    with tempfile.TemporaryDirectory() as tmpdir:
        manager.skills_root = Path(tmpdir)
        test_skill_path = manager.skills_root / "test-delete-skill"
        test_skill_path.mkdir()
        (test_skill_path / "SKILL.md").write_text(
            "---\nname: test\ndescription: test\n---\n", encoding="utf-8"
        )

        # 删除 skill
        manager.delete_skill("test-delete-skill")

        # 验证目录已删除
        assert not test_skill_path.exists()
