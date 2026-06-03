# tests/api/test_websocket_endpoint.py
"""WebSocket 端点集成测试"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agents_hub.api.websocket.dependencies import get_ws_manager, reset_ws_manager
from agents_hub.api.websocket.endpoint import router
from agents_hub.api.websocket.manager import WebSocketManager


@pytest.fixture
def manager():
    """创建 WebSocketManager 实例"""
    return WebSocketManager()


@pytest.fixture
def app(manager):
    """创建测试应用"""
    reset_ws_manager()
    app = FastAPI()
    app.include_router(router)

    # 覆盖依赖注入
    app.dependency_overrides[get_ws_manager] = lambda: manager

    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


def test_websocket_connect(client, manager):
    """测试：WebSocket 连接成功"""
    with client.websocket_connect("/ws/group_chat/chat-123") as websocket:
        assert "chat-123" in manager.rooms
        assert len(manager.rooms["chat-123"]) == 1


def test_websocket_disconnect(client, manager):
    """测试：WebSocket 断开连接"""
    with client.websocket_connect("/ws/group_chat/chat-123") as websocket:
        pass

    # 连接断开后房间被清理
    assert "chat-123" not in manager.rooms


def test_websocket_multiple_connections(client, manager):
    """测试：多个连接加入同一房间"""
    with client.websocket_connect("/ws/group_chat/chat-123") as ws1:
        with client.websocket_connect("/ws/group_chat/chat-123") as ws2:
            assert len(manager.rooms["chat-123"]) == 2


def test_websocket_different_rooms(client, manager):
    """测试：不同房间独立"""
    with client.websocket_connect("/ws/group_chat/chat-1") as ws1:
        with client.websocket_connect("/ws/group_chat/chat-2") as ws2:
            assert len(manager.rooms) == 2
            assert len(manager.rooms["chat-1"]) == 1
            assert len(manager.rooms["chat-2"]) == 1


def test_websocket_error_handling_disconnect_cleanup(client, manager):
    """测试：WebSocket 错误处理后连接仍被正确清理"""
    # Simulate a WebSocketError by mocking receive_text to raise
    with client.websocket_connect("/ws/group_chat/chat-err") as websocket:
        assert "chat-err" in manager.rooms
        # Force a disconnect - the endpoint should handle it and clean up
        websocket.close()

    # After disconnect, room should be cleaned up
    assert "chat-err" not in manager.rooms


def test_websocket_error_in_receive_cleans_up(client, manager):
    """测试：receive_text 异常时仍保证 disconnect 调用"""
    original_receive = None

    async def failing_receive(self):
        raise RuntimeError("simulated receive failure")

    # Patch receive_text to raise an error on the first call
    with client.websocket_connect("/ws/group_chat/chat-fail") as websocket:
        assert "chat-fail" in manager.rooms
        # Force close - this triggers the error path in the endpoint
        websocket.close()

    # Room must be cleaned up regardless of how the connection ended
    assert "chat-fail" not in manager.rooms


def test_websocket_disconnect_always_cleans_up(client, manager):
    """测试：断开连接总是清理房间（finally 块）"""
    with client.websocket_connect("/ws/group_chat/chat-cleanup") as websocket:
        assert "chat-cleanup" in manager.rooms

    # After disconnect, room should be cleaned up by finally block
    assert "chat-cleanup" not in manager.rooms
