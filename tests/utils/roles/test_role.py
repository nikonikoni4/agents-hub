"""Role 类的单元测试"""

import json
from unittest.mock import patch

import pytest

from agents_hub.agent_bridge.models import AgentPlatform
from agents_hub.roles.exceptions import SkillAlreadyExistsError, SkillNotFoundError
from agents_hub.roles.models import RoleInfo
from agents_hub.roles.role import Role


@pytest.fixture
def role_dir(tmp_path):
    """创建测试用的角色目录"""
    role_dir = tmp_path / "local_data" / "agents" / "test_role"
    role_dir.mkdir(parents=True)
    work_root = role_dir / "work_root"
    work_root.mkdir()
    (work_root / "skills").mkdir()
    return role_dir


@pytest.fixture
def claude_role(role_dir):
    """创建 Claude 平台的测试角色"""
    role_json = {
        "name": "test_role",
        "platform": "claude",
        "avatar": None,
        "abilities": ["coding", "review"],
        "type": None,
        "scope": None,
    }
    (role_dir / "role.json").write_text(json.dumps(role_json, ensure_ascii=False), encoding="utf-8")
    (role_dir / "work_root" / "CLAUDE.md").write_text("# Test Role", encoding="utf-8")
    return Role(role_dir)


def test_get_info(claude_role):
    """测试获取角色摘要信息"""
    info = claude_role.get_info()
    assert isinstance(info, RoleInfo)
    assert info.name == "test_role"
    assert info.platform == AgentPlatform.CLAUDE
    assert info.avatar is None
    assert info.abilities == ["coding", "review"]
    assert info.type is None
    assert info.scope is None


def test_update_name(claude_role):
    """测试更新角色名称"""
    claude_role.update_name("new_role_name")

    # 验证 role.json 已更新
    role_json = json.loads((claude_role.role_dir / "role.json").read_text(encoding="utf-8"))
    assert role_json["name"] == "new_role_name"

    # 验证目录已重命名
    assert claude_role.role_dir.name == "new_role_name"

    # 验证后续操作仍然正常
    info = claude_role.get_info()
    assert info.name == "new_role_name"


def test_update_abilities(claude_role):
    """测试更新能力标签"""
    claude_role.update_abilities(["coding", "testing", "documentation"])
    info = claude_role.get_info()
    assert info.abilities == ["coding", "testing", "documentation"]

    # 验证 role.json 已更新
    role_json = json.loads((claude_role.role_dir / "role.json").read_text(encoding="utf-8"))
    assert role_json["abilities"] == ["coding", "testing", "documentation"]


def test_update_avatar(claude_role):
    """测试更新头像文件名引用"""
    claude_role.update_avatar("test_avatar.png")
    info = claude_role.get_info()
    assert info.avatar == "test_avatar.png"


def test_list_skills_empty(claude_role):
    """测试列出空的 skills"""
    skills = claude_role.list_skills()
    assert skills == []


def test_add_skill_creates_symlink_without_role_json_mutation(claude_role):
    """添加 skill 默认创建指向全局 skill 的目录链接，不写 role.json"""
    global_skill_dir = claude_role.role_dir.parent.parent / "skills" / "test_skill"
    global_skill_dir.mkdir(parents=True)
    (global_skill_dir / "skill.json").write_text(
        json.dumps(
            {
                "id": "test_skill",
                "name": "Test Skill",
                "description": "A test skill",
            }
        ),
        encoding="utf-8",
    )

    before = json.loads((claude_role.role_dir / "role.json").read_text(encoding="utf-8"))

    claude_role.add_skill("test_skill")

    skill_dir = claude_role.role_dir / "work_root" / "skills" / "test_skill"
    assert skill_dir.exists()
    assert skill_dir.is_symlink()
    assert (skill_dir / "skill.json").read_text(encoding="utf-8") == (
        global_skill_dir / "skill.json"
    ).read_text(encoding="utf-8")
    assert claude_role.list_skills()[0].id == "test_skill"
    after = json.loads((claude_role.role_dir / "role.json").read_text(encoding="utf-8"))
    assert after == before
    assert "skills" not in after


def test_add_skill_falls_back_to_copy_when_symlink_fails(claude_role):
    """目录链接失败时，添加 skill 降级复制目录"""
    global_skill_dir = claude_role.role_dir.parent.parent / "skills" / "copy_skill"
    global_skill_dir.mkdir(parents=True)
    (global_skill_dir / "skill.json").write_text(
        json.dumps(
            {
                "id": "copy_skill",
                "name": "Copy Skill",
                "description": "Copied when symlink fails",
            }
        ),
        encoding="utf-8",
    )

    with patch("pathlib.Path.symlink_to", side_effect=OSError("symlink disabled")):
        claude_role.add_skill("copy_skill")

    skill_dir = claude_role.role_dir / "work_root" / "skills" / "copy_skill"
    assert skill_dir.exists()
    assert not skill_dir.is_symlink()
    assert json.loads((skill_dir / "skill.json").read_text(encoding="utf-8"))["id"] == "copy_skill"
    assert claude_role.list_skills()[0].id == "copy_skill"
    role_json = json.loads((claude_role.role_dir / "role.json").read_text(encoding="utf-8"))
    assert "skills" not in role_json


def test_add_skill_already_exists(claude_role):
    """测试添加已存在的 skill"""
    # 先创建一个 skill
    skill_dir = claude_role.role_dir / "work_root" / "skills" / "test_skill"
    skill_dir.mkdir(parents=True)

    with pytest.raises(SkillAlreadyExistsError):
        claude_role.add_skill("test_skill")


def test_remove_skill_deletes_role_entry_without_touching_global_skill(claude_role):
    """移除 skill 只删除角色入口，不修改 role.json，不影响全局 skill"""
    global_skill_dir = claude_role.role_dir.parent.parent / "skills" / "test_skill"
    global_skill_dir.mkdir(parents=True)
    (global_skill_dir / "skill.json").write_text(
        json.dumps(
            {
                "id": "test_skill",
                "name": "Test Skill",
                "description": "A test skill",
            }
        ),
        encoding="utf-8",
    )
    claude_role.add_skill("test_skill")
    before = json.loads((claude_role.role_dir / "role.json").read_text(encoding="utf-8"))

    claude_role.remove_skill("test_skill")

    role_skill_dir = claude_role.role_dir / "work_root" / "skills" / "test_skill"
    assert not role_skill_dir.exists()
    assert global_skill_dir.exists()
    assert (global_skill_dir / "skill.json").exists()
    after = json.loads((claude_role.role_dir / "role.json").read_text(encoding="utf-8"))
    assert after == before


def test_remove_skill_deletes_copied_fallback_without_touching_global_skill(claude_role):
    """移除复制 fallback 的 skill 时，也不能影响全局 skill"""
    global_skill_dir = claude_role.role_dir.parent.parent / "skills" / "copy_skill"
    global_skill_dir.mkdir(parents=True)
    (global_skill_dir / "skill.json").write_text(
        json.dumps(
            {
                "id": "copy_skill",
                "name": "Copy Skill",
                "description": "Copied when symlink fails",
            }
        ),
        encoding="utf-8",
    )
    with patch("pathlib.Path.symlink_to", side_effect=OSError("symlink disabled")):
        claude_role.add_skill("copy_skill")

    before = json.loads((claude_role.role_dir / "role.json").read_text(encoding="utf-8"))

    claude_role.remove_skill("copy_skill")

    assert not (claude_role.role_dir / "work_root" / "skills" / "copy_skill").exists()
    assert global_skill_dir.exists()
    assert (global_skill_dir / "skill.json").exists()
    after = json.loads((claude_role.role_dir / "role.json").read_text(encoding="utf-8"))
    assert after == before


def test_remove_skill_not_found(claude_role):
    """测试移除不存在的 skill"""
    with pytest.raises(SkillNotFoundError):
        claude_role.remove_skill("nonexistent_skill")


def test_get_role_config(claude_role):
    """测试构造 RoleConfig"""
    config = claude_role.get_role_config()
    assert config.platform == AgentPlatform.CLAUDE
    assert config.work_root == str(claude_role.role_dir / "work_root")
