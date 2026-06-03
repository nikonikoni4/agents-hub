"""WebSocket Schemas 测试"""

import pytest
from datetime import datetime

from agents_hub.api.schemas.websocket import BroadcastResponse, RefreshSignal


def test_refresh_signal_default():
    """测试：RefreshSignal 默认值"""
    signal = RefreshSignal(group_chat_id="chat-123")

    assert signal.type == "refresh"
    assert signal.group_chat_id == "chat-123"
    assert isinstance(signal.timestamp, datetime)


def test_refresh_signal_custom():
    """测试：RefreshSignal 自定义值"""
    now = datetime(2026, 6, 3, 10, 30, 0)
    signal = RefreshSignal(
        type="status_change",
        group_chat_id="chat-456",
        timestamp=now,
    )

    assert signal.type == "status_change"
    assert signal.group_chat_id == "chat-456"
    assert signal.timestamp == now


def test_refresh_signal_model_dump():
    """测试：RefreshSignal 序列化"""
    signal = RefreshSignal(group_chat_id="chat-123")
    data = signal.model_dump()

    assert data["type"] == "refresh"
    assert data["group_chat_id"] == "chat-123"
    assert "timestamp" in data


def test_broadcast_response_default():
    """测试：BroadcastResponse 默认值"""
    response = BroadcastResponse()

    assert response.status == "ok"
    assert response.message == "Broadcast sent"


def test_broadcast_response_custom():
    """测试：BroadcastResponse 自定义值"""
    response = BroadcastResponse(status="error", message="Failed")

    assert response.status == "error"
    assert response.message == "Failed"
