"""
API 路由定义

定义所有 HTTP API 端点。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents_hub.core.foundation import (
    AgentMessage,
    AgentNotFoundError,
    GroupChatNotFoundError,
    InvalidMessageError,
    MessageType,
)
from agents_hub.core.orchestration.group_chat_manager import group_chat_manager

router = APIRouter()


class SendMessageRequest(BaseModel):
    """发送消息请求体"""

    send_to: str
    content: str


class SendMessageResponse(BaseModel):
    """发送消息响应体"""

    success: bool
    call_id: str | None = None
    error_code: str | None = None
    message: str | None = None
    details: dict | None = None


@router.post("/group_chats/{group_chat_id}/send_message", response_model=SendMessageResponse)
async def user_send_message(
    group_chat_id: str,
    request: SendMessageRequest,
) -> SendMessageResponse:
    """
    User 通过前端发送消息给 Agent（不走 MCP）

    Args:
        group_chat_id: 群聊 ID
        request: 发送消息请求体

    Returns:
        SendMessageResponse: 包含 call_id 的响应

    Raises:
        HTTPException: 当 group_chat_id 或 send_to 不存在时
    """
    try:
        # 1. 获取 GroupChat
        group_chat = group_chat_manager.get_group_chat(group_chat_id)

        # 2. 创建 AgentCall
        call = group_chat.agent_call_manager.create_call(
            send_from="user",
            send_to=request.send_to,
            content=request.content,
            message_type=MessageType.TASK,
        )

        # 3. 通过 MessageRouter 发送消息
        group_chat.message_router.send_message(
            AgentMessage(
                call_id=call.call_id,
                send_from=call.send_from,
                send_to=call.send_to,
                content=call.content,
                message_type=call.message_type,
            )
        )

        return SendMessageResponse(success=True, call_id=call.call_id)

    except GroupChatNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=e.to_mcp_response(),
        ) from e
    except AgentNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=e.to_mcp_response(),
        ) from e
    except InvalidMessageError as e:
        raise HTTPException(
            status_code=400,
            detail=e.to_mcp_response(),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            },
        ) from e
