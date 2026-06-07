"""单聊 API 路由"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from agents_hub.api.schemas.single_chat import (
    CreateSingleChatRequest,
    CreateSingleChatResponse,
    MessageHistoryResponse,
    SendMessageRequest,
    SingleChatListResponse,
    SingleChatResponse,
)
from agents_hub.api.services.single_chat_service import SingleChatManager, single_chat_manager

router = APIRouter(prefix="/single-chats", tags=["single-chats"])


def get_single_chat_manager() -> SingleChatManager:
    """获取 SingleChatManager 实例（依赖注入）"""
    return single_chat_manager


@router.post("", response_model=CreateSingleChatResponse)
async def create_single_chat(
    request: CreateSingleChatRequest,
    manager: SingleChatManager = Depends(get_single_chat_manager),
):
    """创建单聊"""
    return await manager.create_single_chat(request)


@router.get("", response_model=SingleChatListResponse)
async def list_single_chats(
    manager: SingleChatManager = Depends(get_single_chat_manager),
):
    """列出所有单聊"""
    return manager.list_single_chats()


@router.get("/{single_chat_id}", response_model=SingleChatResponse)
async def get_single_chat(
    single_chat_id: str,
    manager: SingleChatManager = Depends(get_single_chat_manager),
):
    """获取单聊详情"""
    return manager.get_single_chat_response(single_chat_id)


@router.post("/{single_chat_id}/messages/stream")
async def send_message_stream(
    single_chat_id: str,
    request: SendMessageRequest,
    manager: SingleChatManager = Depends(get_single_chat_manager),
):
    """发送消息（流式）"""

    async def event_generator():
        async for event_json in manager.send_message_stream(single_chat_id, request.content):
            yield f"data: {event_json}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@router.get("/{single_chat_id}/messages", response_model=MessageHistoryResponse)
async def get_messages(
    single_chat_id: str,
    manager: SingleChatManager = Depends(get_single_chat_manager),
):
    """获取消息历史"""
    return await manager.get_messages_response(single_chat_id)
