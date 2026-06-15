"""WebSocket connection manager for realtime rooms."""

import contextlib

from fastapi import WebSocket

from agents_hub.utils import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """Manage WebSocket connections grouped by group_chat_id."""

    def __init__(self):
        self.rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, group_chat_id: str):
        """Accept a connection and add it to a room."""
        await websocket.accept()
        self.rooms.setdefault(group_chat_id, []).append(websocket)
        logger.info(
            "WebSocket connected to room %s, total connections: %d",
            group_chat_id,
            len(self.rooms[group_chat_id]),
        )

    async def disconnect(self, websocket: WebSocket, group_chat_id: str):
        """Remove a connection from a room."""
        if group_chat_id not in self.rooms:
            return
        if websocket not in self.rooms[group_chat_id]:
            return

        self.rooms[group_chat_id].remove(websocket)
        logger.info(
            "WebSocket disconnected from room %s, remaining: %d",
            group_chat_id,
            len(self.rooms[group_chat_id]),
        )

        if not self.rooms[group_chat_id]:
            del self.rooms[group_chat_id]
            logger.info("Room %s removed (empty)", group_chat_id)

    async def broadcast(self, group_chat_id: str, message: dict):
        """Broadcast a JSON message to all connections in a room."""
        connections = self.rooms.get(group_chat_id, [])
        if not connections:
            logger.warning("Broadcast to empty room %s", group_chat_id)
            return

        failed_connections = []
        for connection in list(connections):
            try:
                await connection.send_json(message)
            except Exception:
                failed_connections.append(connection)

        for conn in failed_connections:
            with contextlib.suppress(ValueError):
                self.rooms[group_chat_id].remove(conn)

        if not self.rooms[group_chat_id]:
            del self.rooms[group_chat_id]
            logger.info("Room %s removed (empty after broadcast cleanup)", group_chat_id)

        if failed_connections:
            logger.warning(
                "广播部分失败: room=%s, 成功=%d, 失败=%d, 总数=%d",
                group_chat_id,
                len(connections) - len(failed_connections),
                len(failed_connections),
                len(connections),
            )
        else:
            logger.info("广播完成: room=%s, 发送=%d", group_chat_id, len(connections))
