"""Realtime dependency registry tests"""

from agents_hub.realtime.dependencies import get_realtime_manager, reset_realtime_manager
from agents_hub.realtime.manager import WebSocketManager


def test_get_realtime_manager_returns_singleton():
    reset_realtime_manager()

    manager1 = get_realtime_manager()
    manager2 = get_realtime_manager()

    assert isinstance(manager1, WebSocketManager)
    assert manager1 is manager2


def test_reset_realtime_manager_creates_new_instance():
    manager1 = get_realtime_manager()
    reset_realtime_manager()
    manager2 = get_realtime_manager()

    assert manager1 is not manager2
