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
