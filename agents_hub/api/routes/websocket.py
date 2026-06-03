"""WebSocket API 路由

提供广播 API 供 Agent 调用，触发前端刷新。
"""

from fastapi import APIRouter, Depends

from agents_hub.api.schemas.websocket import BroadcastResponse, RefreshSignal
from agents_hub.api.websocket.dependencies import get_ws_manager
from agents_hub.api.websocket.manager import WebSocketManager

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.post(
    "/broadcast/{group_chat_id}",
    response_model=BroadcastResponse,
    summary="广播刷新信号到指定房间",
)
async def broadcast_message(
    group_chat_id: str,
    signal: RefreshSignal,
    manager: WebSocketManager = Depends(get_ws_manager),
) -> BroadcastResponse:
    """广播刷新信号到指定房间

    - **group_chat_id**: 群聊 ID
    - **signal**: 刷新信号内容

    前端收到信号后应调用 GET /api/v1/group_chats/{group_chat_id}/messages 拉取最新消息
    """
    # 确保 signal 中的 group_chat_id 与路径参数一致
    signal.group_chat_id = group_chat_id
    await manager.broadcast(group_chat_id, signal.model_dump(mode="json"))
    return BroadcastResponse()
