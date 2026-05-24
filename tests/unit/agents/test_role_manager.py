"""RoleManager 类的单元测试"""

import json
import tempfile
import pytest
import shutil
from pathlib import Path
from unittest.mock import patch
from agents_hub.agents.role_manager import RoleManager
from agents_hub.agents.models import RoleInfo
from agents_hub.agents.exceptions import RoleNotFoundError, RoleAlreadyExistsError, PlatformConfigNotFoundError
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

    with patch("agents_hub.agents.role_manager.Path.home", return_value=mock_home):
        role = role_manager.create_role("test_claude", AgentPlatform.CLAUDE)

    # 验证目录结构
    role_dir = agents_dir / "test_claude"
    assert role_dir.exists()
    assert (role_dir / "role.json").exists()
    assert (role_dir / "avatar").exists()
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

    with patch("agents_hub.agents.role_manager.Path.home", return_value=mock_home):
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

    with patch("agents_hub.agents.role_manager.Path.home", return_value=mock_home):
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
