"""TeamManager 单元测试"""

import json
import pytest
from pathlib import Path

from agents_hub.teams.team_manager import TeamManager
from agents_hub.teams.models import TeamInfo
from agents_hub.teams.exceptions import (
    TeamAlreadyExistsError,
    InvalidTeamMembersError,
    EmptyTeamMembersError,
    TeamNotFoundError,
)


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
