"""Roles API 集成测试"""

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from agents_hub.api.routes.roles import router
from agents_hub.config.types import AgentPlatform
from agents_hub.exceptions import (
    AgentsHubError,
    ResourceNotFoundError,
    ValidationError,
)
from agents_hub.roles.exceptions import (
    RoleAlreadyExistsError,
    RoleNotFoundError,
    SkillAlreadyExistsError,
    SkillNotFoundError,
)
from agents_hub.roles.models import RoleInfo, RoleType, SkillInfo


_STATUS_MAP: dict[type[AgentsHubError], int] = {
    ValidationError: 400,
    ResourceNotFoundError: 404,
}


def _resolve_status(exc: AgentsHubError) -> int:
    for exc_cls, status in _STATUS_MAP.items():
        if isinstance(exc, exc_cls):
            return status
    return 500


@pytest.fixture
def client():
    """创建测试客户端（含全局异常处理器）"""
    app = FastAPI()
    app.include_router(router, prefix="/api")

    @app.exception_handler(AgentsHubError)
    async def agents_hub_error_handler(request: Request, exc: AgentsHubError):
        status = _resolve_status(exc)
        return JSONResponse(status_code=status, content=exc.to_dict())

    return TestClient(app)


@pytest.fixture
def mock_role_service():
    """Mock RoleService"""
    with patch("agents_hub.api.routes.roles.RoleService") as mock_cls:
        svc = mock_cls.return_value
        # 默认返回值：避免未配置时调用报错
        svc.list_roles.return_value = []
        svc.list_avatars.return_value = []
        yield svc


# ========== GET /roles ==========


def test_list_roles_success(client, mock_role_service):
    """测试：成功列出角色"""
    mock_role_service.list_roles.return_value = [
        RoleInfo(
            name="role-1",
            platform=AgentPlatform.CLAUDE,
            avatar=None,
            abilities=[],
            type=RoleType.TEAM_MEMBER,
        ),
        RoleInfo(
            name="role-2",
            platform=AgentPlatform.CODEX,
            avatar="avatar.png",
            abilities=["coding"],
            type=RoleType.LEADER,
        ),
    ]

    response = client.get("/api/roles")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "role-1"
    assert data[0]["platform"] == "claude"
    assert data[1]["name"] == "role-2"
    assert data[1]["platform"] == "codex"
    assert data[1]["avatar"] == "avatar.png"
    assert data[1]["abilities"] == ["coding"]
    assert data[1]["type"] == "leader"


def test_list_roles_empty(client, mock_role_service):
    """测试：列出空角色列表"""
    response = client.get("/api/roles")
    assert response.status_code == 200
    assert response.json() == []


# ========== GET /roles/{name} ==========


def test_get_role_success(client, mock_role_service):
    """测试：成功获取角色"""
    mock_role_service.get_role.return_value = RoleInfo(
        name="test-role",
        platform=AgentPlatform.CLAUDE,
        avatar=None,
        abilities=[],
        type=RoleType.TEAM_MEMBER,
    )

    response = client.get("/api/roles/test-role")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-role"
    assert data["platform"] == "claude"
    assert data["type"] == "team_member"


def test_get_role_not_found(client, mock_role_service):
    """测试：获取不存在的角色 -> 404"""
    mock_role_service.get_role.side_effect = RoleNotFoundError(role_name="nonexistent")

    response = client.get("/api/roles/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "ROLE_NOT_FOUND"


# ========== POST /roles ==========


def test_create_role_success(client, mock_role_service):
    """测试：成功创建角色"""
    mock_role_service.create_role.return_value = RoleInfo(
        name="new-role",
        platform=AgentPlatform.CLAUDE,
        avatar=None,
        abilities=[],
        type=RoleType.TEAM_MEMBER,
    )

    response = client.post(
        "/api/roles",
        json={"name": "new-role", "platform": "claude"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "new-role"
    assert data["platform"] == "claude"


def test_create_role_already_exists(client, mock_role_service):
    """测试：创建已存在的角色 -> 400"""
    mock_role_service.create_role.side_effect = RoleAlreadyExistsError(
        role_name="existing-role"
    )

    response = client.post(
        "/api/roles",
        json={"name": "existing-role", "platform": "claude"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "ROLE_ALREADY_EXISTS"


# ========== DELETE /roles/{name} ==========


def test_delete_role_success(client, mock_role_service):
    """测试：成功删除角色"""
    response = client.delete("/api/roles/test-role")
    assert response.status_code == 200
    data = response.json()
    assert "删除成功" in data["message"]


def test_delete_role_not_found(client, mock_role_service):
    """测试：删除不存在的角色 -> 404"""
    mock_role_service.delete_role.side_effect = RoleNotFoundError(
        role_name="nonexistent"
    )

    response = client.delete("/api/roles/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "ROLE_NOT_FOUND"


# ========== PATCH /roles/{name} ==========


def test_update_role_success(client, mock_role_service):
    """测试：成功更新角色"""
    mock_role_service.update_role.return_value = RoleInfo(
        name="test-role",
        platform=AgentPlatform.CLAUDE,
        avatar="new-avatar.png",
        abilities=["coding"],
        type=RoleType.TEAM_MEMBER,
    )

    response = client.patch(
        "/api/roles/test-role",
        json={"avatar": "new-avatar.png", "abilities": ["coding"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["avatar"] == "new-avatar.png"
    assert data["abilities"] == ["coding"]


def test_update_role_not_found(client, mock_role_service):
    """测试：更新不存在的角色 -> 404"""
    mock_role_service.update_role.side_effect = RoleNotFoundError(
        role_name="nonexistent"
    )

    response = client.patch(
        "/api/roles/nonexistent",
        json={"avatar": "new-avatar.png"},
    )
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "ROLE_NOT_FOUND"


# ========== GET /roles/{name}/skills ==========


def test_list_role_skills_success(client, mock_role_service):
    """测试：成功列出角色 skills"""
    mock_role_service.list_role_skills.return_value = [
        SkillInfo(id="skill-1", name="Skill 1", description="Description 1"),
        SkillInfo(id="skill-2", name="Skill 2", description="Description 2"),
    ]

    response = client.get("/api/roles/test-role/skills")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == "skill-1"
    assert data[0]["name"] == "Skill 1"
    assert data[1]["id"] == "skill-2"


def test_list_role_skills_role_not_found(client, mock_role_service):
    """测试：列出不存在角色的 skills -> 404"""
    mock_role_service.list_role_skills.side_effect = RoleNotFoundError(
        role_name="nonexistent"
    )

    response = client.get("/api/roles/nonexistent/skills")
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "ROLE_NOT_FOUND"


# ========== POST /roles/{name}/skills ==========


def test_add_role_skill_success(client, mock_role_service):
    """测试：成功为角色添加 skill"""
    mock_role_service.add_role_skill.return_value = SkillInfo(
        id="skill-1", name="Skill 1", description="Description 1"
    )

    response = client.post(
        "/api/roles/test-role/skills",
        json={"skill_id": "skill-1"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "skill-1"
    assert data["name"] == "Skill 1"


def test_add_role_skill_not_found(client, mock_role_service):
    """测试：添加不存在的 skill -> 404"""
    mock_role_service.add_role_skill.side_effect = SkillNotFoundError(
        skill_id="nonexistent"
    )

    response = client.post(
        "/api/roles/test-role/skills",
        json={"skill_id": "nonexistent"},
    )
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "SKILL_NOT_FOUND"


def test_add_role_skill_already_exists(client, mock_role_service):
    """测试：添加已存在的 skill -> 400"""
    mock_role_service.add_role_skill.side_effect = SkillAlreadyExistsError(
        skill_id="skill-1", role_name="test-role"
    )

    response = client.post(
        "/api/roles/test-role/skills",
        json={"skill_id": "skill-1"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "SKILL_ALREADY_EXISTS"


# ========== DELETE /roles/{name}/skills/{skill_id} ==========


def test_remove_role_skill_success(client, mock_role_service):
    """测试：成功移除角色 skill"""
    response = client.delete("/api/roles/test-role/skills/skill-1")
    assert response.status_code == 200
    data = response.json()
    assert "移除成功" in data["message"]


def test_remove_role_skill_not_found(client, mock_role_service):
    """测试：移除不存在的 skill -> 404"""
    mock_role_service.remove_role_skill.side_effect = SkillNotFoundError(
        skill_id="nonexistent"
    )

    response = client.delete("/api/roles/test-role/skills/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "SKILL_NOT_FOUND"


# ========== GET /avatars ==========


def test_list_avatars_success(client, mock_role_service):
    """测试：成功列出头像"""
    mock_role_service.list_avatars.return_value = [
        "avatar1.png",
        "avatar2.png",
    ]

    response = client.get("/api/avatars")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0] == "avatar1.png"
    assert data[1] == "avatar2.png"


def test_list_avatars_empty(client, mock_role_service):
    """测试：列出空头像列表"""
    response = client.get("/api/avatars")
    assert response.status_code == 200
    assert response.json() == []
