"""Realtime manager registry and broadcast helpers."""

from agents_hub.realtime.events import make_refresh_signal
from agents_hub.realtime.manager import WebSocketManager
from agents_hub.utils import get_logger

logger = get_logger(__name__)
_realtime_manager: WebSocketManager | None = None


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


async def broadcast_group_chat_refresh(
    group_chat_id: str,
    manager: WebSocketManager | None = None,
):
    """Broadcast a refresh signal to a group chat room."""

    realtime_manager = manager or get_realtime_manager()
    signal = make_refresh_signal(group_chat_id)
    logger.info("[Realtime] broadcast_group_chat_refresh: group_chat_id=%s, manager=%s",
                group_chat_id, realtime_manager)
    await realtime_manager.broadcast(group_chat_id, signal.model_dump(mode="json"))
    logger.info("[Realtime] broadcast 执行完成")
