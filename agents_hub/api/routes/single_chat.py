"""单聊 API 路由"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from agents_hub.api.schemas.single_chat import (
    CreateSingleChatRequest,
    MessageHistoryResponse,
    SendMessageRequest,
    SingleChatListResponse,
    SingleChatResponse,
    SingleChatType,
)
from agents_hub.api.services.single_chat_service import SingleChatManager, single_chat_manager

router = APIRouter(prefix="/single-chats", tags=["single-chats"])


def get_single_chat_manager() -> SingleChatManager:
    """获取 SingleChatManager 实例（依赖注入）"""
    return single_chat_manager


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


@router.post("/messages/stream")
async def send_message_stream(
    request: SendMessageRequest,
    manager: SingleChatManager = Depends(get_single_chat_manager),
):
    """发送消息（流式）

    当 request.single_chat_id 为空时，自动创建单聊（需要 agent_name）。
    响应头 X-Single-Chat-Id 返回真实的 single_chat_id。
    """
    single_chat_id = request.single_chat_id

    if not single_chat_id:
        create_req = CreateSingleChatRequest(
            type=request.type or SingleChatType.NEW,
            single_chat_name=request.single_chat_name or request.agent_name or "新对话",
            agent_name=request.agent_name or "default",
            group_chat_id=request.group_chat_id,
        )
        resp = await manager.create_single_chat(create_req)
        single_chat_id = resp.single_chat_id

    async def event_generator():
        async for event_json in manager.send_message_stream(single_chat_id, request.content):
            # SSE 规范：data 字段中的换行符必须用多行 data: 前缀
            for line in event_json.split("\n"):
                yield f"data: {line}\n"
            yield "\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"X-Single-Chat-Id": single_chat_id},
    )


@router.get("/{single_chat_id}/messages", response_model=MessageHistoryResponse)
async def get_messages(
    single_chat_id: str,
    manager: SingleChatManager = Depends(get_single_chat_manager),
):
    """获取消息历史"""
    return await manager.get_messages_response(single_chat_id)
