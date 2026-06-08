"""TeamManager 单元测试"""

import json

import pytest

from agents_hub.teams.exceptions import (
    EmptyTeamMembersError,
    InvalidTeamMembersError,
    TeamAlreadyExistsError,
    TeamNotFoundError,
)
from agents_hub.teams.team_manager import TeamManager


@pytest.fixture
def temp_teams_dir(tmp_path):
    """临时团队目录"""
    teams_dir = tmp_path / "teams"
    teams_dir.mkdir()
    return teams_dir


@pytest.fixture
def team_manager(temp_teams_dir, monkeypatch):
    """TeamManager 实例"""
    from agents_hub.config import config
    # Mock the data_path property to return temp directory
    monkeypatch.setattr(config.system, "_config_data", {
        **config.system._config_data,
        "data_path": str(temp_teams_dir.parent)
    })
    return TeamManager()


def test_create_team_success(team_manager, monkeypatch):
    """测试创建团队成功"""
    # Mock RoleManager.list_role_names
    def mock_list_role_names(self):
        return ["alice", "bob", "charlie"]

    monkeypatch.setattr(
        "agents_hub.teams.team_manager.RoleManager.list_role_names",
        mock_list_role_names
    )

    team = team_manager.create_team("test-team", ["alice", "bob"])

    assert team.name == "test-team"
    assert team.members == ["alice", "bob"]

    # 验证文件存在
    teams_file = team_manager.teams_file
    assert teams_file.exists()

    # 验证文件内容
    with open(teams_file) as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["name"] == "test-team"
    assert data[0]["members"] == ["alice", "bob"]


def test_create_team_empty_members(team_manager):
    """测试创建团队时成员列表为空"""
    with pytest.raises(EmptyTeamMembersError):
        team_manager.create_team("test-team", [])


def test_create_team_invalid_members(team_manager, monkeypatch):
    """测试创建团队时成员不存在"""
    def mock_list_role_names(self):
        return ["alice", "bob"]

    monkeypatch.setattr(
        "agents_hub.teams.team_manager.RoleManager.list_role_names",
        mock_list_role_names
    )

    with pytest.raises(InvalidTeamMembersError) as exc_info:
        team_manager.create_team("test-team", ["alice", "charlie", "david"])

    assert "charlie" in exc_info.value.details["invalid_members"]
    assert "david" in exc_info.value.details["invalid_members"]


def test_create_team_already_exists(team_manager, monkeypatch):
    """测试创建重名团队"""
    def mock_list_role_names(self):
        return ["alice", "bob"]

    monkeypatch.setattr(
        "agents_hub.teams.team_manager.RoleManager.list_role_names",
        mock_list_role_names
    )

    team_manager.create_team("test-team", ["alice"])

    with pytest.raises(TeamAlreadyExistsError):
        team_manager.create_team("test-team", ["bob"])


def test_get_team_success(team_manager, monkeypatch):
    """测试获取团队成功"""
    def mock_list_role_names(self):
        return ["alice", "bob"]

    monkeypatch.setattr(
        "agents_hub.teams.team_manager.RoleManager.list_role_names",
        mock_list_role_names
    )

    team_manager.create_team("test-team", ["alice", "bob"])

    team = team_manager.get_team("test-team")
    assert team.name == "test-team"
    assert team.members == ["alice", "bob"]


def test_get_team_not_found(team_manager):
    """测试获取不存在的团队"""
    with pytest.raises(TeamNotFoundError) as exc_info:
        team_manager.get_team("nonexistent")

    assert exc_info.value.details["team_name"] == "nonexistent"


def test_list_teams(team_manager, monkeypatch):
    """测试列出所有团队"""
    def mock_list_role_names(self):
        return ["alice", "bob", "charlie"]

    monkeypatch.setattr(
        "agents_hub.teams.team_manager.RoleManager.list_role_names",
        mock_list_role_names
    )

    team_manager.create_team("team1", ["alice"])
    team_manager.create_team("team2", ["bob", "charlie"])

    teams = team_manager.list_teams()
    assert len(teams) == 2
    assert teams[0].name == "team1"
    assert teams[1].name == "team2"


def test_list_teams_empty(team_manager):
    """测试列出空团队列表"""
    teams = team_manager.list_teams()
    assert teams == []


def test_update_team_name(team_manager, monkeypatch):
    """测试更新团队名称"""
    def mock_list_role_names(self):
        return ["alice", "bob"]

    monkeypatch.setattr(
        "agents_hub.teams.team_manager.RoleManager.list_role_names",
        mock_list_role_names
    )

    team_manager.create_team("old-name", ["alice"])

    updated = team_manager.update_team("old-name", new_name="new-name", new_members=None)
    assert updated.name == "new-name"
    assert updated.members == ["alice"]

    # 验证旧名称不存在
    with pytest.raises(TeamNotFoundError):
        team_manager.get_team("old-name")


def test_update_team_members(team_manager, monkeypatch):
    """测试更新团队成员"""
    def mock_list_role_names(self):
        return ["alice", "bob", "charlie"]

    monkeypatch.setattr(
        "agents_hub.teams.team_manager.RoleManager.list_role_names",
        mock_list_role_names
    )

    team_manager.create_team("test-team", ["alice"])

    updated = team_manager.update_team("test-team", new_name=None, new_members=["bob", "charlie"])
    assert updated.name == "test-team"
    assert updated.members == ["bob", "charlie"]


def test_update_team_both(team_manager, monkeypatch):
    """测试同时更新名称和成员"""
    def mock_list_role_names(self):
        return ["alice", "bob"]

    monkeypatch.setattr(
        "agents_hub.teams.team_manager.RoleManager.list_role_names",
        mock_list_role_names
    )

    team_manager.create_team("old", ["alice"])

    updated = team_manager.update_team("old", new_name="new", new_members=["bob"])
    assert updated.name == "new"
    assert updated.members == ["bob"]


def test_update_team_not_found(team_manager):
    """测试更新不存在的团队"""
    with pytest.raises(TeamNotFoundError):
        team_manager.update_team("nonexistent", new_name="new", new_members=None)


def test_update_team_name_conflict(team_manager, monkeypatch):
    """测试更新名称时与其他团队冲突"""
    def mock_list_role_names(self):
        return ["alice", "bob"]

    monkeypatch.setattr(
        "agents_hub.teams.team_manager.RoleManager.list_role_names",
        mock_list_role_names
    )

    team_manager.create_team("team1", ["alice"])
    team_manager.create_team("team2", ["bob"])

    with pytest.raises(TeamAlreadyExistsError):
        team_manager.update_team("team1", new_name="team2", new_members=None)


def test_delete_team_success(team_manager, monkeypatch):
    """测试删除团队成功"""
    def mock_list_role_names(self):
        return ["alice", "bob"]

    monkeypatch.setattr(
        "agents_hub.teams.team_manager.RoleManager.list_role_names",
        mock_list_role_names
    )

    team_manager.create_team("team1", ["alice"])
    team_manager.create_team("team2", ["bob"])

    team_manager.delete_team("team1")

    # 验证团队已删除
    with pytest.raises(TeamNotFoundError):
        team_manager.get_team("team1")

    # 验证其他团队还在
    team2 = team_manager.get_team("team2")
    assert team2.name == "team2"


def test_delete_team_not_found(team_manager):
    """测试删除不存在的团队"""
    with pytest.raises(TeamNotFoundError):
        team_manager.delete_team("nonexistent")
