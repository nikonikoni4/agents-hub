"""Realtime WebSocketManager 单元测试"""

from unittest.mock import AsyncMock

import pytest

from agents_hub.realtime.manager import WebSocketManager


@pytest.fixture
def manager():
    return WebSocketManager()


@pytest.fixture
def mock_websocket():
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_connect_adds_websocket_to_room(manager, mock_websocket):
    await manager.connect(mock_websocket, "chat-123")

    assert mock_websocket in manager.rooms["chat-123"]
    mock_websocket.accept.assert_called_once()


@pytest.mark.asyncio
async def test_broadcast_sends_message_to_room(manager, mock_websocket):
    await manager.connect(mock_websocket, "chat-123")

    message = {"type": "refresh", "group_chat_id": "chat-123"}
    await manager.broadcast("chat-123", message)

    mock_websocket.send_json.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_broadcast_removes_failed_connection(manager, mock_websocket):
    mock_websocket.send_json.side_effect = RuntimeError("closed")
    await manager.connect(mock_websocket, "chat-123")

    await manager.broadcast("chat-123", {"type": "refresh"})

    assert "chat-123" not in manager.rooms
