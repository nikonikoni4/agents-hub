# agents_hub/api/websocket/dependencies.py
"""WebSocket 依赖注入

提供 WebSocketManager 全局单例。
"""

from agents_hub.api.websocket.manager import WebSocketManager

# 全局单例
_ws_manager: WebSocketManager | None = None


def get_ws_manager() -> WebSocketManager:
    """获取 WebSocketManager 单例"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager


def reset_ws_manager():
    """重置 WebSocketManager 单例（用于测试）"""
    global _ws_manager
    _ws_manager = None
