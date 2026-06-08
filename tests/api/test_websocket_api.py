"""WebSocket 广播 API 集成测试"""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from agents_hub.api.routes.websocket import router
from agents_hub.api.websocket.dependencies import get_ws_manager, reset_ws_manager
from agents_hub.api.websocket.manager import WebSocketManager
from agents_hub.exceptions import AgentsHubError


@pytest.fixture
def manager():
    """创建 WebSocketManager 实例"""
    return WebSocketManager()


@pytest.fixture
def client(manager):
    """创建测试客户端"""
    reset_ws_manager()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    # 覆盖依赖注入
    app.dependency_overrides[get_ws_manager] = lambda: manager

    @app.exception_handler(AgentsHubError)
    async def agents_hub_error_handler(request: Request, exc: AgentsHubError):
        return JSONResponse(status_code=500, content=exc.to_dict())

    return TestClient(app)


def test_broadcast_success(client, manager):
    """测试：成功广播消息"""
    # 添加 mock 连接
    mock_ws = AsyncMock()
    manager.rooms["chat-123"] = [mock_ws]

    response = client.post(
        "/api/v1/ws/broadcast/chat-123",
        json={"type": "refresh", "group_chat_id": "chat-123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "Broadcast sent"

    # 验证广播被调用
    mock_ws.send_json.assert_called_once()


def test_broadcast_empty_room(client):
    """测试：广播到空房间"""
    response = client.post(
        "/api/v1/ws/broadcast/nonexistent",
        json={"type": "refresh", "group_chat_id": "nonexistent"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_broadcast_invalid_signal(client):
    """测试：无效信号格式"""
    response = client.post(
        "/api/v1/ws/broadcast/chat-123",
        json={"type": "refresh"},  # 缺少 group_chat_id
    )

    assert response.status_code == 422  # Pydantic 验证错误
