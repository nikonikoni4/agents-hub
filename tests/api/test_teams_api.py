"""Team API 集成测试"""

import pytest
from fastapi.testclient import TestClient

from agents_hub.api.app import app


@pytest.fixture
def client():
    """测试客户端"""
    return TestClient(app)


@pytest.fixture
def cleanup_teams(monkeypatch, tmp_path):
    """清理测试数据"""
    from agents_hub.config import config

    # Monkeypatch the internal _config_data dictionary to use tmp_path
    monkeypatch.setitem(config.system._config_data, "data_path", str(tmp_path))
    yield
    teams_file = tmp_path / "teams" / "teams.json"
    if teams_file.exists():
        teams_file.unlink()


@pytest.fixture
def mock_roles(monkeypatch):
    """Mock RoleManager"""

    def mock_list_role_names(self):
        return ["alice", "bob", "charlie"]

    monkeypatch.setattr(
        "agents_hub.teams.team_manager.RoleManager.list_role_names", mock_list_role_names
    )


def test_create_team(client, cleanup_teams, mock_roles):
    """测试创建团队"""
    response = client.post(
        "/api/v1/teams",
        json={"name": "test-team", "members": ["alice", "bob"]},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test-team"
    assert data["members"] == ["alice", "bob"]


def test_create_team_empty_members(client, cleanup_teams):
    """测试创建团队时成员为空"""
    response = client.post(
        "/api/v1/teams",
        json={"name": "test-team", "members": []},
    )
    assert response.status_code == 400
    assert "EMPTY_TEAM_MEMBERS" in response.text


def test_create_team_invalid_members(client, cleanup_teams, mock_roles):
    """测试创建团队时成员不存在"""
    response = client.post(
        "/api/v1/teams",
        json={"name": "test-team", "members": ["invalid"]},
    )
    assert response.status_code == 400
    assert "INVALID_TEAM_MEMBERS" in response.text


def test_list_teams(client, cleanup_teams, mock_roles):
    """测试列出所有团队"""
    # 创建两个团队
    client.post("/api/v1/teams", json={"name": "team1", "members": ["alice"]})
    client.post("/api/v1/teams", json={"name": "team2", "members": ["bob"]})

    response = client.get("/api/v1/teams")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "team1"
    assert data[1]["name"] == "team2"


def test_get_team(client, cleanup_teams, mock_roles):
    """测试获取单个团队"""
    client.post("/api/v1/teams", json={"name": "test-team", "members": ["alice"]})

    response = client.get("/api/v1/teams/test-team")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-team"
    assert data["members"] == ["alice"]


def test_get_team_not_found(client, cleanup_teams):
    """测试获取不存在的团队"""
    response = client.get("/api/v1/teams/nonexistent")
    assert response.status_code == 404
    assert "TEAM_NOT_FOUND" in response.text


def test_update_team_name(client, cleanup_teams, mock_roles):
    """测试更新团队名称"""
    client.post("/api/v1/teams", json={"name": "old-name", "members": ["alice"]})

    response = client.patch("/api/v1/teams/old-name", json={"name": "new-name"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "new-name"
    assert data["members"] == ["alice"]


def test_update_team_members(client, cleanup_teams, mock_roles):
    """测试更新团队成员"""
    client.post("/api/v1/teams", json={"name": "test-team", "members": ["alice"]})

    response = client.patch("/api/v1/teams/test-team", json={"members": ["bob", "charlie"]})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-team"
    assert data["members"] == ["bob", "charlie"]


def test_update_team_not_found(client, cleanup_teams):
    """测试更新不存在的团队"""
    response = client.patch("/api/v1/teams/nonexistent", json={"name": "new-name"})
    assert response.status_code == 404


def test_delete_team(client, cleanup_teams, mock_roles):
    """测试删除团队"""
    client.post("/api/v1/teams", json={"name": "test-team", "members": ["alice"]})

    response = client.delete("/api/v1/teams/test-team")
    assert response.status_code == 200
    assert "删除成功" in response.json()["message"]

    # 验证已删除
    response = client.get("/api/v1/teams/test-team")
    assert response.status_code == 404


def test_delete_team_not_found(client, cleanup_teams):
    """测试删除不存在的团队"""
    response = client.delete("/api/v1/teams/nonexistent")
    assert response.status_code == 404
