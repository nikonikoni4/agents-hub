# tests/api/test_websocket_manager.py
"""WebSocketManager 单元测试"""

from unittest.mock import AsyncMock

import pytest

from agents_hub.api.websocket.manager import WebSocketManager


@pytest.fixture
def manager():
    """创建 WebSocketManager 实例"""
    return WebSocketManager()


@pytest.fixture
def mock_websocket():
    """创建 mock WebSocket"""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_connect(manager, mock_websocket):
    """测试：连接加入房间"""
    await manager.connect(mock_websocket, "chat-123")

    assert "chat-123" in manager.rooms
    assert mock_websocket in manager.rooms["chat-123"]
    mock_websocket.accept.assert_called_once()


@pytest.mark.asyncio
async def test_connect_multiple_rooms(manager, mock_websocket):
    """测试：不同房间独立"""
    ws2 = AsyncMock()

    await manager.connect(mock_websocket, "chat-1")
    await manager.connect(ws2, "chat-2")

    assert len(manager.rooms) == 2
    assert mock_websocket in manager.rooms["chat-1"]
    assert ws2 in manager.rooms["chat-2"]


@pytest.mark.asyncio
async def test_disconnect(manager, mock_websocket):
    """测试：断开连接从房间移除"""
    await manager.connect(mock_websocket, "chat-123")
    await manager.disconnect(mock_websocket, "chat-123")

    assert "chat-123" not in manager.rooms


@pytest.mark.asyncio
async def test_disconnect_nonexistent_room(manager, mock_websocket):
    """测试：断开不存在的房间不报错"""
    await manager.disconnect(mock_websocket, "nonexistent")


@pytest.mark.asyncio
async def test_disconnect_nonexistent_websocket(manager, mock_websocket):
    """测试：断开不存在的连接不报错"""
    ws2 = AsyncMock()
    await manager.connect(mock_websocket, "chat-123")
    await manager.disconnect(ws2, "chat-123")

    # 原连接仍在房间
    assert mock_websocket in manager.rooms["chat-123"]


@pytest.mark.asyncio
async def test_broadcast(manager, mock_websocket):
    """测试：广播消息到房间"""
    ws2 = AsyncMock()
    await manager.connect(mock_websocket, "chat-123")
    await manager.connect(ws2, "chat-123")

    message = {"type": "refresh", "group_chat_id": "chat-123"}
    await manager.broadcast("chat-123", message)

    mock_websocket.send_json.assert_called_once_with(message)
    ws2.send_json.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_broadcast_empty_room(manager):
    """测试：广播到空房间不报错"""
    await manager.broadcast("nonexistent", {"type": "refresh"})


@pytest.mark.asyncio
async def test_broadcast_failed_connection(manager, mock_websocket):
    """测试：广播失败时清理连接"""
    mock_websocket.send_json.side_effect = Exception("Connection closed")

    await manager.connect(mock_websocket, "chat-123")
    await manager.broadcast("chat-123", {"type": "refresh"})

    # 失败的连接被清理
    assert "chat-123" not in manager.rooms


@pytest.mark.asyncio
async def test_broadcast_partial_failure(manager, mock_websocket):
    """测试：广播部分失败时继续发送给其他连接"""
    ws2 = AsyncMock()
    ws3 = AsyncMock()

    # ws1 和 ws3 成功，ws2 失败
    mock_websocket.send_json = AsyncMock()
    ws2.send_json = AsyncMock(side_effect=Exception("Connection closed"))
    ws3.send_json = AsyncMock()

    await manager.connect(mock_websocket, "chat-123")
    await manager.connect(ws2, "chat-123")
    await manager.connect(ws3, "chat-123")

    message = {"type": "refresh", "group_chat_id": "chat-123"}
    await manager.broadcast("chat-123", message)

    # ws1 和 ws3 收到消息
    mock_websocket.send_json.assert_called_once_with(message)
    ws3.send_json.assert_called_once_with(message)

    # ws2 被清理，但房间仍存在（还有 ws1 和 ws3）
    assert "chat-123" in manager.rooms
    assert ws2 not in manager.rooms["chat-123"]
    assert mock_websocket in manager.rooms["chat-123"]
    assert ws3 in manager.rooms["chat-123"]
