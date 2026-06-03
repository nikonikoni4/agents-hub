# agents_hub/api/websocket/manager.py
"""WebSocket 连接管理器

管理 WebSocket 连接池，提供房间管理接口。
全局单例，通过依赖注入共享。
"""

import contextlib
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket 连接管理器（全局单例）"""

    def __init__(self):
        # 房间映射：group_chat_id -> [WebSocket, ...]
        self.rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, group_chat_id: str):
        """接受连接并加入房间"""
        await websocket.accept()
        self.rooms.setdefault(group_chat_id, []).append(websocket)
        logger.info(
            f"WebSocket connected to room {group_chat_id}, "
            f"total connections: {len(self.rooms[group_chat_id])}"
        )

    async def disconnect(self, websocket: WebSocket, group_chat_id: str):
        """断开连接并从房间移除"""
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
        """向房间内所有连接广播消息"""
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

        # 清理失败的连接
        for conn in failed_connections:
            with contextlib.suppress(ValueError):
                self.rooms[group_chat_id].remove(conn)

        # 清理空房间
        if not self.rooms[group_chat_id]:
            del self.rooms[group_chat_id]
            logger.info(f"Room {group_chat_id} removed (empty after broadcast cleanup)")

        logger.info(
            f"Broadcast to room {group_chat_id}: "
            f"{len(connections) - len(failed_connections)}/{len(connections)} sent"
        )
