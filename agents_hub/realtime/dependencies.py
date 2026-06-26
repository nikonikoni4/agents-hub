"""Realtime manager registry and broadcast helpers."""

from collections.abc import Awaitable, Callable

from agents_hub.realtime.events import make_refresh_signal
from agents_hub.realtime.manager import WebSocketManager
from agents_hub.utils import get_logger

logger = get_logger(__name__)
_realtime_manager: WebSocketManager | None = None
_channel_callbacks: list[Callable[[str, dict | None], Awaitable[None]]] = []


def get_realtime_manager() -> WebSocketManager:
    """Return the process-wide realtime manager."""
    global _realtime_manager
    if _realtime_manager is None:
        _realtime_manager = WebSocketManager()
    return _realtime_manager


def reset_realtime_manager():
    """Reset the process-wide realtime manager for tests."""
    global _realtime_manager
    _realtime_manager = None


def register_channel_callback(callback: Callable[[str, dict | None], Awaitable[None]]):
    """注册 Channel 回调，用于接收广播消息。

    回调签名：async def callback(group_chat_id: str, message: dict | None)
    - message 不为 None 时，包含消息内容（有新消息的广播）
    - message 为 None 时，是纯状态刷新（回调不会被调用）
    """
    _channel_callbacks.append(callback)


def reset_channel_callbacks():
    """重置所有 Channel 回调（仅用于测试）"""
    _channel_callbacks.clear()


async def broadcast_group_chat_refresh(
    group_chat_id: str,
    manager: WebSocketManager | None = None,
    message: dict | None = None,
):
    """Broadcast a refresh signal to a group chat room.

    Args:
        group_chat_id: 群聊 ID
        manager: WebSocket 管理器（可选，默认使用进程级单例）
        message: 消息内容（可选），不为 None 时附加到信号中并通知回调
    """

    realtime_manager = manager or get_realtime_manager()
    signal = make_refresh_signal(group_chat_id)
    if message:
        signal_data = signal.model_dump(mode="json")
        signal_data["message"] = message
    else:
        signal_data = signal.model_dump(mode="json")

    connection_count = len(realtime_manager.rooms.get(group_chat_id, []))
    logger.debug(
        "[Realtime] broadcast_group_chat_refresh: group_chat_id=%s, connections=%d",
        group_chat_id,
        connection_count,
    )
    await realtime_manager.broadcast(group_chat_id, signal_data)

    # 通知注册的 Channel 回调（仅当有消息内容时）
    if message and _channel_callbacks:
        for callback in _channel_callbacks:
            try:
                await callback(group_chat_id, message)
            except Exception:
                logger.warning("Channel 回调失败", exc_info=True)
