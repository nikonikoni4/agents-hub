# agents_hub/api/websocket/exceptions.py
"""Compatibility exports for realtime WebSocket exceptions."""

from agents_hub.realtime.exceptions import (
    WebSocketBroadcastError,
    WebSocketConnectionError,
    WebSocketError,
    WebSocketRoomNotFoundError,
    WebSocketValidationError,
)

__all__ = [
    "WebSocketBroadcastError",
    "WebSocketConnectionError",
    "WebSocketError",
    "WebSocketRoomNotFoundError",
    "WebSocketValidationError",
]
