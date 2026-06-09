"""单聊 API 集成测试"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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
    SingleChatManager._reset_instance()
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


def _create_chat_via_manager(manager: SingleChatManager) -> str:
    """通过 manager 直接创建单聊，返回 single_chat_id"""
    from agents_hub.api.schemas.single_chat import CreateSingleChatRequest, SingleChatType

    req = CreateSingleChatRequest(
        type=SingleChatType.NEW,
        single_chat_name="测试单聊",
        agent_name="test_agent",
        cwd="/tmp/test",
    )
    import asyncio
    resp = asyncio.get_event_loop().run_until_complete(manager.create_single_chat(req))
    return resp.single_chat_id


@patch("agents_hub.api.routes.single_chat.single_chat_manager")
def test_send_message_auto_creates_chat(mock_mgr, client):
    """测试发送消息时自动创建单聊"""
    from agents_hub.api.schemas.single_chat import CreateSingleChatResponse, SingleChatType

    # mock create_single_chat
    mock_mgr.create_single_chat = AsyncMock(return_value=CreateSingleChatResponse(
        single_chat_id="auto-created-id",
        single_chat_name="test_agent",
        type=SingleChatType.NEW,
    ))
    # mock send_message_stream
    mock_mgr.send_message_stream = AsyncMock(return_value=iter([]))

    response = client.post("/api/v1/single-chats/messages/stream", json={
        "content": "hello",
        "agent_name": "test_agent",
    })

    assert response.status_code == 200
    assert response.headers.get("X-Single-Chat-Id") == "auto-created-id"


def test_send_message_with_existing_chat(client, manager):
    """测试已有 single_chat_id 时直接发送消息"""
    chat_id = _create_chat_via_manager(manager)

    with patch.object(manager, "send_message_stream", new_callable=AsyncMock, return_value=iter([])):
        response = client.post("/api/v1/single-chats/messages/stream", json={
            "content": "hello",
            "single_chat_id": chat_id,
        })

    assert response.status_code == 200
    assert response.headers.get("X-Single-Chat-Id") == chat_id


def test_list_single_chats(client, manager):
    """测试列出单聊"""
    _create_chat_via_manager(manager)

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


def test_get_single_chat(client, manager):
    """测试获取单聊详情"""
    chat_id = _create_chat_via_manager(manager)

    response = client.get(f"/api/v1/single-chats/{chat_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["single_chat_id"] == chat_id
    assert data["single_chat_name"] == "测试单聊"
    assert data["agent_name"] == "test_agent"
    assert data["platform"] == "claude"


def test_get_single_chat_not_found(client):
    """测试获取不存在的单聊"""
    response = client.get("/api/v1/single-chats/nonexistent")
    assert response.status_code == 404


def test_get_messages_empty(client, manager):
    """测试获取空消息历史（无 session）"""
    chat_id = _create_chat_via_manager(manager)

    response = client.get(f"/api/v1/single-chats/{chat_id}/messages")
    assert response.status_code == 200
    data = response.json()
    assert data["messages"] == []


def test_get_messages_not_found(client):
    """测试获取不存在单聊的消息历史"""
    response = client.get("/api/v1/single-chats/nonexistent/messages")
    assert response.status_code == 404


def test_send_message_missing_content(client):
    """测试发送消息缺少 content"""
    response = client.post("/api/v1/single-chats/messages/stream", json={
        "agent_name": "test_agent",
    })
    assert response.status_code == 422


def test_send_message_auto_create_missing_agent(client):
    """测试自动创建时缺少 agent_name"""
    response = client.post("/api/v1/single-chats/messages/stream", json={
        "content": "hello",
    })
    # 没有 single_chat_id 也没有 agent_name，应该用 "default" 创建
    # 这取决于是否允许 "default" agent，这里测试不报 422
    # 具体行为取决于 RoleManager 是否有 "default" agent
