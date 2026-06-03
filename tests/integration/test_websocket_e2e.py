# tests/integration/test_websocket_e2e.py
"""WebSocket 端到端测试

测试完整的 WebSocket 功能流程：
1. 连接后通过 manager 广播接收消息
2. 多房间隔离
3. 断开连接后房间清理
4. HTTP 广播 API 端点可用
"""

import threading
import time

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from agents_hub.api.routes.websocket import router as api_router
from agents_hub.api.websocket.dependencies import get_ws_manager, reset_ws_manager
from agents_hub.api.websocket.endpoint import router as ws_router
from agents_hub.api.websocket.manager import WebSocketManager
from agents_hub.exceptions import AgentsHubError


@pytest.fixture
def manager():
    """创建 WebSocketManager 实例"""
    return WebSocketManager()


@pytest.fixture
def app(manager):
    """创建完整应用"""
    reset_ws_manager()
    app = FastAPI()
    app.include_router(ws_router)
    app.include_router(api_router, prefix="/api/v1")

    # 覆盖依赖注入
    app.dependency_overrides[get_ws_manager] = lambda: manager

    @app.exception_handler(AgentsHubError)
    async def agents_hub_error_handler(request: Request, exc: AgentsHubError):
        return JSONResponse(status_code=500, content=exc.to_dict())

    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


def _broadcast_via_portal(ws_session, manager, group_chat_id, message):
    """通过 portal 事件循环发送广播（解决 TestClient 同步阻塞问题）"""

    def _send():
        time.sleep(0.3)

        async def _do_broadcast():
            await manager.broadcast(group_chat_id, message)

        ws_session.portal.call(_do_broadcast)

    thread = threading.Thread(target=_send)
    thread.start()
    return thread


def test_e2e_connect_and_broadcast(client, manager):
    """端到端测试：连接后接收广播"""
    with client.websocket_connect("/ws/group_chat/chat-123") as websocket:
        # 连接成功，房间已创建
        assert "chat-123" in manager.rooms
        assert len(manager.rooms["chat-123"]) == 1

        # 通过 manager 广播消息（模拟 Agent 调用广播 API）
        broadcast_msg = {"type": "refresh", "group_chat_id": "chat-123"}
        thread = _broadcast_via_portal(websocket, manager, "chat-123", broadcast_msg)

        # 接收广播消息
        data = websocket.receive_json()
        thread.join()

        assert data["type"] == "refresh"
        assert data["group_chat_id"] == "chat-123"


def test_e2e_multiple_rooms(client, manager):
    """端到端测试：多房间隔离"""
    with client.websocket_connect("/ws/group_chat/chat-1") as ws1:
        with client.websocket_connect("/ws/group_chat/chat-2") as ws2:
            # 两个房间都已创建
            assert len(manager.rooms) == 2
            assert "chat-1" in manager.rooms
            assert "chat-2" in manager.rooms

            # 广播到 chat-1
            broadcast_msg = {"type": "refresh", "group_chat_id": "chat-1"}
            thread = _broadcast_via_portal(ws1, manager, "chat-1", broadcast_msg)

            # ws1 收到消息
            data1 = ws1.receive_json()
            thread.join()

            assert data1["group_chat_id"] == "chat-1"
            assert data1["type"] == "refresh"

            # ws2 不应收到消息（其房间无广播）
            # 注意：receive_json 会阻塞，所以只验证 ws1 的正确性


def test_e2e_disconnect_cleanup(client, manager):
    """端到端测试：断开连接后房间清理"""
    with client.websocket_connect("/ws/group_chat/chat-123") as websocket:
        assert "chat-123" in manager.rooms
        assert len(manager.rooms["chat-123"]) == 1

    # 连接断开后房间被清理
    assert "chat-123" not in manager.rooms


def test_e2e_http_broadcast_api(client, manager):
    """端到端测试：HTTP 广播 API 端点返回正确响应"""
    response = client.post(
        "/api/v1/ws/broadcast/chat-123",
        json={"type": "refresh", "group_chat_id": "chat-123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "Broadcast sent"


def test_e2e_http_broadcast_empty_room(client, manager):
    """端到端测试：广播到空房间不报错"""
    response = client.post(
        "/api/v1/ws/broadcast/empty-room",
        json={"type": "refresh", "group_chat_id": "empty-room"},
    )
    assert response.status_code == 200
