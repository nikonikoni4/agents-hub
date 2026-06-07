"""单聊 API 集成测试"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from agents_hub.api.routes.single_chat import get_single_chat_manager, router
from agents_hub.api.services.single_chat_service import SingleChatManager
from agents_hub.config.types import AgentPlatform, RoleType
from agents_hub.exceptions import AgentsHubError, ResourceNotFoundError, ValidationError
from agents_hub.roles.exceptions import RoleNotFoundError
from agents_hub.roles.models import RoleConfig


def _make_mock_role(name: str = "test_agent") -> MagicMock:
    """创建 mock Role"""
    role = MagicMock()
    role.name = name
    role.get_role_config.return_value = RoleConfig(
        name=name,
        platform=AgentPlatform.CLAUDE,
        role_type=RoleType.TEAM_MEMBER,
    )
    return role


@pytest.fixture
def temp_data_dir():
    """创建临时数据目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def manager_and_mock(temp_data_dir):
    """创建 SingleChatManager 并同时 patch RoleManager

    必须在 RoleManager mock 激活期间实例化 SingleChatManager，
    因为其 __init__ 中会调用 RoleManager()。
    """
    mock_rm = MagicMock()
    mock_rm.get_role.return_value = _make_mock_role()
    with patch(
        "agents_hub.api.services.single_chat_service.RoleManager",
        return_value=mock_rm,
    ):
        mgr = SingleChatManager(data_path=temp_data_dir / "single_chats")
        yield mgr, mock_rm


@pytest.fixture
def manager(manager_and_mock):
    """获取 SingleChatManager 实例"""
    return manager_and_mock[0]


@pytest.fixture
def mock_role_manager(manager_and_mock):
    """获取 mock RoleManager"""
    return manager_and_mock[1]


@pytest.fixture
def app(manager):
    """创建测试用 FastAPI 应用（含全局异常处理器）"""
    _app = FastAPI()
    _app.include_router(router, prefix="/api/v1")
    _app.dependency_overrides[get_single_chat_manager] = lambda: manager

    @_app.exception_handler(AgentsHubError)
    async def agents_hub_error_handler(request: Request, exc: AgentsHubError) -> JSONResponse:
        status = 404 if isinstance(exc, ResourceNotFoundError) else 400 if isinstance(exc, ValidationError) else 500
        return JSONResponse(status_code=status, content=exc.to_dict())

    @_app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error_code": "INTERNAL_ERROR", "message": str(exc), "type": "InternalError"},
        )

    return _app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app, raise_server_exceptions=False)


def test_create_single_chat(client):
    """测试创建单聊"""
    response = client.post("/api/v1/single-chats", json={
        "type": "new",
        "single_chat_name": "测试单聊",
        "agent_name": "test_agent",
        "cwd": "/tmp/test",
    })

    assert response.status_code == 200
    data = response.json()
    assert "single_chat_id" in data
    assert data["single_chat_name"] == "测试单聊"
    assert data["type"] == "new"


def test_create_single_chat_agent_not_found(client, mock_role_manager):
    """测试创建单聊时 agent 不存在"""
    mock_role_manager.get_role.side_effect = RoleNotFoundError(role_name="nonexistent_agent")

    response = client.post("/api/v1/single-chats", json={
        "type": "new",
        "single_chat_name": "测试单聊",
        "agent_name": "nonexistent_agent",
        "cwd": "/tmp/test",
    })

    assert response.status_code == 404
    assert "不存在" in response.json()["message"]


def test_list_single_chats(client):
    """测试列出单聊"""
    # 先创建一个
    client.post("/api/v1/single-chats", json={
        "type": "new",
        "single_chat_name": "测试单聊",
        "agent_name": "test_agent",
        "cwd": "/tmp/test",
    })

    response = client.get("/api/v1/single-chats")
    assert response.status_code == 200
    data = response.json()
    assert "single_chats" in data
    assert len(data["single_chats"]) == 1
    assert data["single_chats"][0]["single_chat_name"] == "测试单聊"


def test_list_single_chats_empty(client):
    """测试列出空单聊列表"""
    response = client.get("/api/v1/single-chats")
    assert response.status_code == 200
    data = response.json()
    assert data["single_chats"] == []


def test_get_single_chat(client):
    """测试获取单聊详情"""
    create_resp = client.post("/api/v1/single-chats", json={
        "type": "new",
        "single_chat_name": "测试单聊",
        "agent_name": "test_agent",
        "cwd": "/tmp/test",
    })
    single_chat_id = create_resp.json()["single_chat_id"]

    response = client.get(f"/api/v1/single-chats/{single_chat_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["single_chat_id"] == single_chat_id
    assert data["single_chat_name"] == "测试单聊"
    assert data["agent_name"] == "test_agent"
    assert data["platform"] == "claude"


def test_get_single_chat_not_found(client):
    """测试获取不存在的单聊"""
    response = client.get("/api/v1/single-chats/nonexistent")
    assert response.status_code == 404


def test_get_messages_empty(client):
    """测试获取空消息历史（无 session）"""
    create_resp = client.post("/api/v1/single-chats", json={
        "type": "new",
        "single_chat_name": "测试单聊",
        "agent_name": "test_agent",
        "cwd": "/tmp/test",
    })
    single_chat_id = create_resp.json()["single_chat_id"]

    response = client.get(f"/api/v1/single-chats/{single_chat_id}/messages")
    assert response.status_code == 200
    data = response.json()
    assert data["messages"] == []


def test_get_messages_not_found(client):
    """测试获取不存在单聊的消息历史"""
    response = client.get("/api/v1/single-chats/nonexistent/messages")
    assert response.status_code == 404


def test_create_single_chat_missing_fields(client):
    """测试创建单聊缺少必填字段"""
    response = client.post("/api/v1/single-chats", json={
        "type": "new",
    })
    assert response.status_code == 422  # FastAPI validation error


def test_create_single_chat_invalid_type(client):
    """测试创建单聊使用无效类型"""
    response = client.post("/api/v1/single-chats", json={
        "type": "invalid_type",
        "single_chat_name": "测试单聊",
        "agent_name": "test_agent",
        "cwd": "/tmp/test",
    })
    assert response.status_code == 422
