"""WebSocket connection manager for realtime rooms."""

import contextlib
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manage WebSocket connections grouped by group_chat_id."""

    def __init__(self):
        self.rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, group_chat_id: str):
        """Accept a connection and add it to a room."""
        await websocket.accept()
        self.rooms.setdefault(group_chat_id, []).append(websocket)
        logger.info(
            f"WebSocket connected to room {group_chat_id}, "
            f"total connections: {len(self.rooms[group_chat_id])}"
        )

    async def disconnect(self, websocket: WebSocket, group_chat_id: str):
        """Remove a connection from a room."""
        if group_chat_id not in self.rooms:
            return
        if websocket not in self.rooms[group_chat_id]:
            return

        self.rooms[group_chat_id].remove(websocket)
        logger.info(
            f"WebSocket disconnected from room {group_chat_id}, "
            f"remaining: {len(self.rooms[group_chat_id])}"
        )

        if not self.rooms[group_chat_id]:
            del self.rooms[group_chat_id]
            logger.info(f"Room {group_chat_id} removed (empty)")

    async def broadcast(self, group_chat_id: str, message: dict):
        """Broadcast a JSON message to all connections in a room."""
        connections = self.rooms.get(group_chat_id, [])
        if not connections:
            logger.warning(f"Broadcast to empty room {group_chat_id}")
            return

        failed_connections = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to connection in room {group_chat_id}: {e}")
                failed_connections.append(connection)

        for conn in failed_connections:
            with contextlib.suppress(ValueError):
                self.rooms[group_chat_id].remove(conn)

        if not self.rooms[group_chat_id]:
            del self.rooms[group_chat_id]
            logger.info(f"Room {group_chat_id} removed (empty after broadcast cleanup)")

        logger.info(
            f"Broadcast to room {group_chat_id}: "
            f"{len(connections) - len(failed_connections)}/{len(connections)} sent"
        )
