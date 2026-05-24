"""RoleManager 类的单元测试"""

import json
import tempfile
import pytest
import shutil
from pathlib import Path
from unittest.mock import patch
from agents_hub.roles.role_manager import RoleManager
from agents_hub.roles.models import RoleInfo, RoleType
from agents_hub.roles.exceptions import RoleNotFoundError, RoleAlreadyExistsError, PlatformConfigNotFoundError
from agents_hub.agent_bridge.config import AgentPlatform


@pytest.fixture
def agents_dir():
    """创建测试用的 agents 目录"""
    tmp_dir = tempfile.mkdtemp()
    agents_dir = Path(tmp_dir) / "local_data" / "agents"
    agents_dir.mkdir(parents=True)
    yield agents_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def role_manager(agents_dir):
    """创建 RoleManager 实例"""
    return RoleManager(agents_dir)


def test_list_roles_empty(role_manager):
    """测试列出空的角色列表"""
    roles = role_manager.list_roles()
    assert roles == []


def test_create_claude_role(role_manager, agents_dir):
    """测试创建 Claude 平台角色"""
    # 创建模拟的 ~/.claude 目录
    mock_home = Path(tempfile.mkdtemp())
    mock_claude = mock_home / ".claude"
    mock_claude.mkdir()
    (mock_claude / "settings.json").write_text('{"permissions": {}}', encoding="utf-8")

    with patch("agents_hub.roles.role_manager.Path.home", return_value=mock_home):
        role = role_manager.create_role("test_claude", AgentPlatform.CLAUDE)

    # 验证目录结构
    role_dir = agents_dir / "test_claude"
    assert role_dir.exists()
    assert (role_dir / "role.json").exists()
    assert (role_dir / "work_root").exists()
    assert (role_dir / "work_root" / "skills").exists()
    assert (role_dir / "work_root" / "CLAUDE.md").exists()
    assert (role_dir / "work_root" / "settings.json").exists()

    # 验证 role.json 内容
    role_json = json.loads((role_dir / "role.json").read_text(encoding="utf-8"))
    assert role_json["name"] == "test_claude"
    assert role_json["platform"] == "claude"
    assert "scope" in role_json
    assert "type" in role_json


def test_create_codex_role(role_manager, agents_dir):
    """测试创建 Codex 平台角色"""
    # 创建模拟的 ~/.codex 目录
    mock_home = Path(tempfile.mkdtemp())
    mock_codex = mock_home / ".codex"
    mock_codex.mkdir()
    (mock_codex / "auth.json").write_text('{}', encoding="utf-8")
    (mock_codex / "config.toml").write_text('', encoding="utf-8")
    (mock_codex / "rules").mkdir()

    with patch("agents_hub.roles.role_manager.Path.home", return_value=mock_home):
        role = role_manager.create_role("test_codex", AgentPlatform.CODEX)

    # 验证目录结构
    role_dir = agents_dir / "test_codex"
    assert role_dir.exists()
    assert (role_dir / "work_root" / "auth.json").exists()
    assert (role_dir / "work_root" / "config.toml").exists()
    assert (role_dir / "work_root" / "rules").exists()
    assert (role_dir / "work_root" / "AGENTS.md").exists()


def test_create_role_already_exists(role_manager, agents_dir):
    """测试创建已存在的角色"""
    # 创建第一个角色
    (agents_dir / "existing_role").mkdir()

    with pytest.raises(RoleAlreadyExistsError):
        role_manager.create_role("existing_role", AgentPlatform.CLAUDE)


def test_create_role_platform_config_not_found(role_manager):
    """测试平台配置目录不存在"""
    mock_home = Path(tempfile.mkdtemp()) / "empty_home"
    mock_home.mkdir()

    with patch("agents_hub.roles.role_manager.Path.home", return_value=mock_home):
        with pytest.raises(PlatformConfigNotFoundError):
            role_manager.create_role("test_role", AgentPlatform.CLAUDE)


def test_get_role(role_manager, agents_dir):
    """测试获取角色"""
    # 创建测试角色
    role_dir = agents_dir / "test_role"
    role_dir.mkdir()
    role_json = {
        "name": "test_role",
        "platform": "claude",
        "avatar": None,
        "abilities": []
    }
    (role_dir / "role.json").write_text(json.dumps(role_json), encoding="utf-8")

    role = role_manager.get_role("test_role")
    assert role is not None
    assert role.get_info().name == "test_role"


def test_get_role_not_found(role_manager):
    """测试获取不存在的角色"""
    with pytest.raises(RoleNotFoundError):
        role_manager.get_role("nonexistent_role")


def test_list_roles(role_manager, agents_dir):
    """测试列出多个角色"""
    # 创建两个测试角色
    for name in ["role1", "role2"]:
        role_dir = agents_dir / name
        role_dir.mkdir()
        role_json = {
            "name": name,
            "platform": "claude",
            "avatar": None,
            "abilities": []
        }
        (role_dir / "role.json").write_text(json.dumps(role_json), encoding="utf-8")

    roles = role_manager.list_roles()
    assert len(roles) == 2
    role_names = [r.name for r in roles]
    assert "role1" in role_names
    assert "role2" in role_names


def test_delete_role(role_manager, agents_dir):
    """测试删除角色"""
    # 创建测试角色
    role_dir = agents_dir / "test_role"
    role_dir.mkdir()

    role_manager.delete_role("test_role")
    assert not role_dir.exists()


def test_delete_role_not_found(role_manager):
    """测试删除不存在的角色"""
    with pytest.raises(RoleNotFoundError):
        role_manager.delete_role("nonexistent_role")


def test_create_role_invalid_name(role_manager):
    """测试创建角色时名称验证"""
    # 空名称
    with pytest.raises(ValueError, match="cannot be empty"):
        role_manager.create_role("", AgentPlatform.CLAUDE)

    # 包含特殊字符
    with pytest.raises(ValueError, match="Invalid role name"):
        role_manager.create_role("test/role", AgentPlatform.CLAUDE)

    # 包含空格
    with pytest.raises(ValueError, match="Invalid role name"):
        role_manager.create_role("test role", AgentPlatform.CLAUDE)

    # 以点开头
    with pytest.raises(ValueError, match="Invalid role name"):
        role_manager.create_role(".hidden", AgentPlatform.CLAUDE)

    # 以连字符开头
    with pytest.raises(ValueError, match="cannot start with"):
        role_manager.create_role("-test", AgentPlatform.CLAUDE)


def test_list_roles_with_corrupted_json(role_manager, agents_dir):
    """测试列出角色时遇到损坏的 role.json"""
    # 创建一个有效的角色
    valid_dir = agents_dir / "valid_role"
    valid_dir.mkdir()
    valid_json = {"name": "valid_role", "platform": "claude", "avatar": None, "abilities": []}
    (valid_dir / "role.json").write_text(json.dumps(valid_json), encoding="utf-8")

    # 创建一个损坏的角色
    corrupted_dir = agents_dir / "corrupted_role"
    corrupted_dir.mkdir()
    (corrupted_dir / "role.json").write_text("invalid json", encoding="utf-8")

    # 应该只返回有效的角色
    roles = role_manager.list_roles()
    assert len(roles) == 1
    assert roles[0].name == "valid_role"


def test_create_role_cleanup_on_failure(role_manager, agents_dir):
    """测试创建角色失败时清理目录"""
    mock_home = Path(tempfile.mkdtemp()) / "empty_home"
    mock_home.mkdir()

    with patch("agents_hub.roles.role_manager.Path.home", return_value=mock_home):
        with pytest.raises(PlatformConfigNotFoundError):
            role_manager.create_role("test_role", AgentPlatform.CLAUDE)

    # 验证目录已被清理
    role_dir = agents_dir / "test_role"
    assert not role_dir.exists()


def test_get_role_invalid_name(role_manager):
    """测试获取角色时名称验证"""
    with pytest.raises(ValueError, match="Invalid role name"):
        role_manager.get_role("test/role")


def test_delete_role_invalid_name(role_manager):
    """测试删除角色时名称验证"""
    with pytest.raises(ValueError, match="Invalid role name"):
        role_manager.delete_role("test/role")


def test_list_avatars_empty(role_manager):
    """测试列出头像 - assets 目录不存在"""
    avatars = role_manager.list_avatars()
    assert avatars == []


def test_list_avatars(role_manager, agents_dir):
    """测试列出头像 - 正常情况"""
    assets_dir = agents_dir / "assets"
    assets_dir.mkdir()

    # 创建图片文件
    (assets_dir / "avatar_01.png").write_bytes(b"fake png")
    (assets_dir / "avatar_02.jpg").write_bytes(b"fake jpg")
    (assets_dir / "readme.txt").write_text("not an image")

    avatars = role_manager.list_avatars()
    assert len(avatars) == 2
    assert "avatar_01.png" in avatars
    assert "avatar_02.jpg" in avatars
    assert "readme.txt" not in avatars
