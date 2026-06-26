"""广播机制扩展测试：支持携带消息内容"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agents_hub.realtime.dependencies import (
    broadcast_group_chat_refresh,
    get_realtime_manager,
    register_channel_callback,
    reset_channel_callbacks,
    reset_realtime_manager,
)
from agents_hub.realtime.manager import WebSocketManager


@pytest.fixture
def mock_manager():
    """创建模拟的 WebSocketManager"""
    manager = MagicMock(spec=WebSocketManager)
    manager.broadcast = AsyncMock()
    manager.rooms = {"gc_1": [MagicMock()]}
    return manager


@pytest.fixture
def clean_callbacks():
    """测试前清理回调，测试后恢复"""
    reset_channel_callbacks()
    yield
    reset_channel_callbacks()


# ==================== broadcast_group_chat_refresh 测试 ====================


async def test_broadcast_without_message_backward_compatible(mock_manager, clean_callbacks):
    """向后兼容：不传 message 时行为不变"""
    await broadcast_group_chat_refresh("gc_1", manager=mock_manager)

    mock_manager.broadcast.assert_called_once()
    call_args = mock_manager.broadcast.call_args
    signal = call_args[0][1]  # broadcast(group_chat_id, signal)

    assert signal["type"] == "refresh"
    assert signal["group_chat_id"] == "gc_1"
    assert "message" not in signal


async def test_broadcast_with_message(mock_manager, clean_callbacks):
    """扩展：传入 message 时，信号中包含消息内容"""
    message = {
        "id": 1,
        "content": "hello",
        "send_from": "Worker1",
        "send_to": "manager",
        "timestamp": "2026-06-26T10:00:00",
    }

    await broadcast_group_chat_refresh("gc_1", manager=mock_manager, message=message)

    mock_manager.broadcast.assert_called_once()
    call_args = mock_manager.broadcast.call_args
    signal = call_args[0][1]

    assert signal["type"] == "refresh"
    assert signal["group_chat_id"] == "gc_1"
    assert signal["message"] == message


async def test_broadcast_with_none_message(mock_manager, clean_callbacks):
    """传入 None 时，信号中不包含 message 字段"""
    await broadcast_group_chat_refresh("gc_1", manager=mock_manager, message=None)

    mock_manager.broadcast.assert_called_once()
    call_args = mock_manager.broadcast.call_args
    signal = call_args[0][1]

    assert "message" not in signal


# ==================== 回调订阅机制测试 ====================


async def test_register_channel_callback(mock_manager, clean_callbacks):
    """注册回调后，广播时会被调用"""
    callback = AsyncMock()
    register_channel_callback(callback)

    message = {"id": 1, "content": "hello"}
    await broadcast_group_chat_refresh("gc_1", manager=mock_manager, message=message)

    callback.assert_called_once_with("gc_1", message)


async def test_multiple_callbacks_all_called(mock_manager, clean_callbacks):
    """多个回调都会被调用"""
    callback1 = AsyncMock()
    callback2 = AsyncMock()
    register_channel_callback(callback1)
    register_channel_callback(callback2)

    message = {"id": 1, "content": "hello"}
    await broadcast_group_chat_refresh("gc_1", manager=mock_manager, message=message)

    callback1.assert_called_once_with("gc_1", message)
    callback2.assert_called_once_with("gc_1", message)


async def test_callback_not_called_without_message(mock_manager, clean_callbacks):
    """没有 message 时，回调不被调用（过滤纯状态刷新）"""
    callback = AsyncMock()
    register_channel_callback(callback)

    await broadcast_group_chat_refresh("gc_1", manager=mock_manager, message=None)

    callback.assert_not_called()


async def test_callback_exception_does_not_break_broadcast(mock_manager, clean_callbacks):
    """回调异常不影响广播和后续回调"""
    failing_callback = AsyncMock(side_effect=Exception("callback error"))
    success_callback = AsyncMock()
    register_channel_callback(failing_callback)
    register_channel_callback(success_callback)

    message = {"id": 1, "content": "hello"}
    # 不应抛出异常
    await broadcast_group_chat_refresh("gc_1", manager=mock_manager, message=message)

    # 广播仍然成功
    mock_manager.broadcast.assert_called_once()
    # 第二个回调仍然被调用
    success_callback.assert_called_once_with("gc_1", message)


async def test_reset_channel_callbacks(mock_manager, clean_callbacks):
    """重置回调后，不再调用"""
    callback = AsyncMock()
    register_channel_callback(callback)

    reset_channel_callbacks()

    message = {"id": 1, "content": "hello"}
    await broadcast_group_chat_refresh("gc_1", manager=mock_manager, message=message)

    callback.assert_not_called()
