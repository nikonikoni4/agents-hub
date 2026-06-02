import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    """创建测试客户端"""
    from fastapi import FastAPI
    from agents_hub.api.routes.skills import router

    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


@pytest.fixture
def temp_skills_dir():
    """创建临时 skills 目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试 skill
        skill_path = Path(tmpdir) / "test-skill"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: Test skill\n---\n",
            encoding="utf-8"
        )
        yield tmpdir


@pytest.fixture
def mock_skill_manager(temp_skills_dir):
    """Mock SkillManager 以返回测试 skills"""
    from agents_hub.skills.models import SkillInfo

    test_skill = SkillInfo(
        name="test-skill",
        description="Test skill",
        path=str(Path(temp_skills_dir) / "test-skill"),
    )

    mock_manager = MagicMock()
    mock_manager.list_skills.return_value = [test_skill]
    mock_manager.get_skill.return_value = test_skill

    return mock_manager


def test_list_skills_success(client, mock_skill_manager):
    """测试：成功列出 skills"""
    with patch("agents_hub.api.services.skill_service.SkillManager", return_value=mock_skill_manager):
        response = client.get("/api/skills")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "test-skill"
        assert data[0]["description"] == "Test skill"


def test_list_skills_empty(client, mock_skill_manager):
    """测试：列出空的 skills"""
    mock_skill_manager.list_skills.return_value = []

    with patch("agents_hub.api.services.skill_service.SkillManager", return_value=mock_skill_manager):
        response = client.get("/api/skills")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


def test_get_skill_success(client, mock_skill_manager):
    """测试：获取单个 skill"""
    with patch("agents_hub.api.services.skill_service.SkillManager", return_value=mock_skill_manager):
        response = client.get("/api/skills/test-skill")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-skill"
        assert data["description"] == "Test skill"


def test_get_skill_not_found(client, mock_skill_manager):
    """测试：获取不存在的 skill"""
    from agents_hub.skills.exceptions import SkillNotFoundError

    mock_skill_manager.get_skill.side_effect = SkillNotFoundError("Skill not found")

    with patch("agents_hub.api.services.skill_service.SkillManager", return_value=mock_skill_manager):
        response = client.get("/api/skills/nonexistent")
        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]


def test_delete_skill_success(client, mock_skill_manager):
    """测试：成功删除 skill"""
    with patch("agents_hub.api.services.skill_service.SkillManager", return_value=mock_skill_manager):
        response = client.delete("/api/skills/test-skill")
        assert response.status_code == 200
        assert "删除成功" in response.json()["message"]
        mock_skill_manager.delete_skill.assert_called_once_with("test-skill")


def test_delete_skill_not_found(client, mock_skill_manager):
    """测试：删除不存在的 skill"""
    from agents_hub.skills.exceptions import SkillNotFoundError

    mock_skill_manager.delete_skill.side_effect = SkillNotFoundError("Skill not found")

    with patch("agents_hub.api.services.skill_service.SkillManager", return_value=mock_skill_manager):
        response = client.delete("/api/skills/nonexistent")
        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]


def test_add_skill_not_implemented(client, mock_skill_manager):
    """测试：添加 skill（未实现）"""
    mock_skill_manager.add_skill_from_url.side_effect = NotImplementedError(
        "从 URL 添加 skill 功能暂未实现"
    )

    with patch("agents_hub.api.services.skill_service.SkillManager", return_value=mock_skill_manager):
        response = client.post("/api/skills", json={"url": "https://example.com"})
        assert response.status_code == 501
        assert "暂未实现" in response.json()["detail"]
