# agents_hub/api/websocket/dependencies.py
"""Compatibility exports for realtime dependency helpers."""

from agents_hub.realtime.dependencies import get_realtime_manager as get_ws_manager
from agents_hub.realtime.dependencies import reset_realtime_manager as reset_ws_manager

__all__ = ["get_ws_manager", "reset_ws_manager"]
