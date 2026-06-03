# agents_hub/api/websocket/endpoint.py
"""WebSocket 端点

处理 WebSocket 连接生命周期。
"""

import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from agents_hub.api.websocket.dependencies import get_ws_manager
from agents_hub.api.websocket.exceptions import WebSocketError
from agents_hub.api.websocket.manager import WebSocketManager

logger = logging.getLogger(__name__)

router = APIRouter()


async def handle_websocket_error(websocket: WebSocket, error: WebSocketError):
    """处理 WebSocket 错误，通过连接发送错误消息"""
    error_message = {
        "type": "error",
        "error_code": error.error_code,
        "message": error.message,
        "details": error.details,
    }
    await websocket.send_json(error_message)


@router.websocket("/ws/group_chat/{group_chat_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    group_chat_id: str,
    manager: WebSocketManager = Depends(get_ws_manager),
):
    """WebSocket 端点

    前端通过此端点连接到指定群聊房间，接收刷新信号。
    """
    try:
        await manager.connect(websocket, group_chat_id)
        while True:
            # 保持连接，接收前端消息（如心跳）
            data = await websocket.receive_text()
            logger.debug(f"Received from {group_chat_id}: {data}")
    except WebSocketDisconnect:
        pass  # Normal disconnect, cleanup below
    except WebSocketError as e:
        try:
            await handle_websocket_error(websocket, e)
        except Exception:
            logger.exception("Failed to send error message to client")
    except Exception as e:
        logger.exception(f"WebSocket error in room {group_chat_id}")
        ws_error = WebSocketError(
            message=str(e),
            error_code="UNKNOWN_ERROR",
            cause=e,
        )
        try:
            await handle_websocket_error(websocket, ws_error)
        except Exception:
            logger.exception("Failed to send error message to client")
    finally:
        await manager.disconnect(websocket, group_chat_id)
