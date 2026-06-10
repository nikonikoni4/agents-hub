# tests/api/test_websocket_dependencies.py
"""WebSocket 依赖注入测试"""

from agents_hub.api.websocket.dependencies import get_ws_manager, reset_ws_manager
from agents_hub.api.websocket.manager import WebSocketManager


def test_get_ws_manager_singleton():
    """测试：get_ws_manager 返回单例"""
    reset_ws_manager()  # 重置状态

    manager1 = get_ws_manager()
    manager2 = get_ws_manager()

    assert isinstance(manager1, WebSocketManager)
    assert manager1 is manager2


def test_reset_ws_manager():
    """测试：reset_ws_manager 重置单例"""
    manager1 = get_ws_manager()
    reset_ws_manager()
    manager2 = get_ws_manager()

    assert manager1 is not manager2
