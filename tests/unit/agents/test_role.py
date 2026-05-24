"""Role 类的单元测试"""

import json
import pytest
from pathlib import Path
from agents_hub.agents.role import Role
from agents_hub.agents.models import RoleInfo, SkillInfo, RoleType
from agents_hub.agents.exceptions import SkillNotFoundError, SkillAlreadyExistsError
from agents_hub.agent_bridge.config import AgentPlatform


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
        "skills": []
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
    """测试更新头像"""
    avatar_dir = claude_role.role_dir / "avatar"
    avatar_dir.mkdir(exist_ok=True)
    (avatar_dir / "test_avatar.png").write_bytes(b"fake image")

    claude_role.update_avatar("test_avatar.png")
    info = claude_role.get_info()
    assert info.avatar == "test_avatar.png"


def test_list_skills_empty(claude_role):
    """测试列出空的 skills"""
    skills = claude_role.list_skills()
    assert skills == []


def test_add_skill(claude_role):
    """测试添加 skill"""
    # 创建全局 skill 库
    global_skills_dir = claude_role.role_dir.parent.parent / "skills" / "test_skill"
    global_skills_dir.mkdir(parents=True)
    (global_skills_dir / "skill.json").write_text(json.dumps({
        "id": "test_skill",
        "name": "Test Skill",
        "description": "A test skill"
    }), encoding="utf-8")

    claude_role.add_skill("test_skill")
    skills = claude_role.list_skills()
    assert len(skills) == 1
    assert skills[0].id == "test_skill"


def test_add_skill_already_exists(claude_role):
    """测试添加已存在的 skill"""
    # 先创建一个 skill
    skill_dir = claude_role.role_dir / "work_root" / "skills" / "test_skill"
    skill_dir.mkdir(parents=True)

    with pytest.raises(SkillAlreadyExistsError):
        claude_role.add_skill("test_skill")


def test_remove_skill(claude_role):
    """测试移除 skill"""
    # 先添加一个 skill
    skill_dir = claude_role.role_dir / "work_root" / "skills" / "test_skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill.json").write_text(json.dumps({
        "id": "test_skill",
        "name": "Test Skill",
        "description": "A test skill"
    }), encoding="utf-8")

    # 更新 role.json 中的 skills
    role_json = json.loads((claude_role.role_dir / "role.json").read_text(encoding="utf-8"))
    role_json["skills"] = ["test_skill"]
    (claude_role.role_dir / "role.json").write_text(json.dumps(role_json), encoding="utf-8")

    claude_role.remove_skill("test_skill")
    skills = claude_role.list_skills()
    assert len(skills) == 0


def test_remove_skill_not_found(claude_role):
    """测试移除不存在的 skill"""
    with pytest.raises(SkillNotFoundError):
        claude_role.remove_skill("nonexistent_skill")


def test_get_role_config(claude_role):
    """测试构造 RoleConfig"""
    config = claude_role.get_role_config()
    assert config.platform == AgentPlatform.CLAUDE
    assert config.claude_config_dir == str(claude_role.role_dir / "work_root")
    assert config.codex_home is None


def test_get_permissions_config(claude_role):
    """测试获取权限配置"""
    # 创建 settings.json
    settings = {
        "permissions": {
            "allow": ["Read"],
            "deny": ["Bash"],
            "ask": ["Write"]
        }
    }
    (claude_role.role_dir / "work_root" / "settings.json").write_text(
        json.dumps(settings), encoding="utf-8"
    )

    config = claude_role.get_permissions_config()
    assert "permissions" in config
    assert config["permissions"]["allow"] == ["Read"]


def test_update_permissions_config(claude_role):
    """测试更新权限配置"""
    # 创建初始 settings.json
    settings = {"permissions": {"allow": ["Read"]}}
    (claude_role.role_dir / "work_root" / "settings.json").write_text(
        json.dumps(settings), encoding="utf-8"
    )

    # 更新配置
    new_config = {"permissions": {"allow": ["Read", "Write"], "deny": ["Bash"]}}
    claude_role.update_permissions_config(new_config)

    # 验证更新
    updated = json.loads((claude_role.role_dir / "work_root" / "settings.json").read_text(encoding="utf-8"))
    assert updated["permissions"]["allow"] == ["Read", "Write"]
    assert updated["permissions"]["deny"] == ["Bash"]
