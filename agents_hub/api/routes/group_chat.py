"""群聊 API 路由"""

import mimetypes

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse

from agents_hub.api.schemas.group_chats import (
    AddMembersRequest,
    AgentCallInfo,
    GroupChatCreate,
    GroupChatInfo,
    GroupChatMember,
    MessageCreate,
    MessageInfo,
    PermissionUpdateRequest,
    PermissionUpdateResponse,
    PinMessageRequest,
    PinnedMessageInfo,
    PinOperationResponse,
    TaskListInfo,
    UploadedFileInfo,
    UseDockerUpdate,
)
from agents_hub.api.services.group_chat_service import GroupChatService
from agents_hub.core.orchestration import group_chat_manager as _group_chat_manager

router = APIRouter(prefix="/group-chats", tags=["group-chats"])


def get_group_chat_service() -> GroupChatService:
    """获取 GroupChatService 实例（依赖注入）"""
    return GroupChatService(group_chat_manager=_group_chat_manager)


@router.post("", response_model=GroupChatInfo)
async def create_group_chat(
    request: GroupChatCreate,
    service: GroupChatService = Depends(get_group_chat_service),
):
    """创建并启动新群聊"""
    return await service.create_group_chat(
        team_members=request.team_members,
        project_path=request.project_path,
        group_chat_name=request.group_chat_name,
    )


@router.get("", response_model=list[GroupChatInfo])
async def list_group_chats(
    is_active_only: bool = Query(False, description="是否只返回活跃群聊"),
    service: GroupChatService = Depends(get_group_chat_service),
):
    """列出所有群聊"""
    return await service.list_group_chats(is_active_only=is_active_only)


@router.get("/{group_chat_id}", response_model=GroupChatInfo)
async def get_group_chat_info(
    group_chat_id: str,
    service: GroupChatService = Depends(get_group_chat_service),
):
    """获取群聊详细信息"""
    return await service.get_group_chat_info(group_chat_id)


@router.delete("/{group_chat_id}", response_model=dict[str, str])
async def delete_group_chat(
    group_chat_id: str,
    keep_data: bool = Query(False, description="True=仅从内存移除，False=完全删除"),
    service: GroupChatService = Depends(get_group_chat_service),
):
    """删除群聊"""
    await service.delete_group_chat(group_chat_id, keep_data=keep_data)
    return {"message": f"群聊 '{group_chat_id}' 删除成功"}


@router.get("/{group_chat_id}/members", response_model=list[GroupChatMember])
async def get_group_chat_members(
    group_chat_id: str,
    service: GroupChatService = Depends(get_group_chat_service),
):
    """获取群聊成员列表"""
    return await service.get_group_chat_members(group_chat_id)


@router.get("/{group_chat_id}/messages", response_model=list[MessageInfo])
async def get_messages(
    group_chat_id: str,
    limit: int = Query(30, ge=1, le=500, description="返回消息数量上限"),
    before: str | None = Query(None, description="游标时间戳，返回此时间之前的消息"),
    service: GroupChatService = Depends(get_group_chat_service),
):
    """获取群聊消息历史"""
    return await service.get_messages(group_chat_id, limit=limit, before=before)


@router.get("/{group_chat_id}/agent-calls", response_model=list[AgentCallInfo])
async def get_agent_calls(
    group_chat_id: str,
    service: GroupChatService = Depends(get_group_chat_service),
):
    """获取群聊的所有 Agent 调用记录"""
    return await service.get_agent_calls(group_chat_id)


@router.get("/{group_chat_id}/tasks", response_model=TaskListInfo | None)
async def get_tasks(
    group_chat_id: str,
    service: GroupChatService = Depends(get_group_chat_service),
):
    """获取群聊的当前任务列表（ACTIVE）"""
    return await service.get_tasks(group_chat_id)


@router.post("/{group_chat_id}/messages", response_model=dict[str, str])
async def send_message(
    group_chat_id: str,
    request: MessageCreate,
    service: GroupChatService = Depends(get_group_chat_service),
):
    """向群聊发送消息"""
    await service.send_message(
        group_chat_id,
        content=request.content,
        members=request.members,
        files=request.files,
    )
    return {"message": "消息已发送"}


@router.put("/{group_chat_id}/{role_name}/use-docker", response_model=GroupChatMember)
async def toggle_use_docker(
    group_chat_id: str,
    role_name: str,
    request: UseDockerUpdate,
    service: GroupChatService = Depends(get_group_chat_service),
):
    """切换指定成员的 Docker 沙箱开关"""
    return await service.toggle_use_docker(group_chat_id, role_name, request.use_docker)


@router.get(
    "/{group_chat_id}/pinned-messages",
    response_model=list[PinnedMessageInfo],
    responses={
        404: {"description": "群聊不存在"},
    },
)
async def get_pinned_messages(
    group_chat_id: str,
    service: GroupChatService = Depends(get_group_chat_service),
):
    """获取群聊中的置顶消息列表"""
    return await service.get_pinned_messages(group_chat_id)


@router.post(
    "/{group_chat_id}/pinned-messages",
    response_model=PinnedMessageInfo,
    responses={
        404: {"description": "群聊不存在"},
        422: {"description": "消息不存在"},
    },
)
async def pin_message(
    group_chat_id: str,
    body: PinMessageRequest,
    service: GroupChatService = Depends(get_group_chat_service),
):
    """置顶指定消息"""
    return await service.pin_message(group_chat_id, body.message_id)


@router.delete(
    "/{group_chat_id}/pinned-messages",
    response_model=PinOperationResponse,
    responses={
        404: {"description": "群聊不存在"},
    },
)
async def unpin_message(
    group_chat_id: str,
    message_id: int = Query(..., description="消息 id"),
    service: GroupChatService = Depends(get_group_chat_service),
):
    """取消置顶消息"""
    await service.unpin_message(group_chat_id, message_id)
    return PinOperationResponse()


@router.post(
    "/{group_chat_id}/members",
    response_model=list[GroupChatMember],
    responses={
        404: {"description": "群聊不存在或角色不存在"},
    },
)
async def add_group_chat_members(
    group_chat_id: str,
    request: AddMembersRequest,
    service: GroupChatService = Depends(get_group_chat_service),
):
    """添加群成员"""
    return await service.add_group_chat_members(group_chat_id, request.member_names)


@router.get(
    "/{group_chat_id}/files/{snapshot_id}/content",
    response_model=dict[str, str],
    responses={
        404: {"description": "快照不存在或群聊不存在"},
    },
)
async def get_file_snapshot_content(
    group_chat_id: str,
    snapshot_id: str,
    service: GroupChatService = Depends(get_group_chat_service),
):
    """获取文件快照的完整内容"""
    content = await service.get_file_snapshot_content(group_chat_id, snapshot_id)
    return {"content": content}


@router.get(
    "/{group_chat_id}/files/{snapshot_id}/diff",
    response_model=dict[str, str],
    responses={
        404: {"description": "快照不存在或群聊不存在"},
    },
)
async def get_file_snapshot_diff(
    group_chat_id: str,
    snapshot_id: str,
    service: GroupChatService = Depends(get_group_chat_service),
):
    """获取文件快照的 diff"""
    diff = await service.get_file_snapshot_diff(group_chat_id, snapshot_id)
    return {"diff": diff}


@router.get("/{group_chat_id}/files/{file_path:path}")
async def get_uploaded_file(
    group_chat_id: str,
    file_path: str,
    service: GroupChatService = Depends(get_group_chat_service),
):
    """获取上传的文件"""
    full_path = await service.get_uploaded_file_path(group_chat_id, file_path)
    content_type = mimetypes.guess_type(str(full_path))[0] or "application/octet-stream"
    return FileResponse(path=str(full_path), filename=full_path.name, media_type=content_type)


@router.patch(
    "/{group_chat_id}/messages/{message_id}/permission",
    response_model=PermissionUpdateResponse,
    responses={
        404: {"description": "群聊或消息不存在"},
        422: {"description": "无效的状态值"},
    },
)
async def update_permission_status(
    group_chat_id: str,
    message_id: int,
    body: PermissionUpdateRequest,
    service: GroupChatService = Depends(get_group_chat_service),
):
    """更新消息中的权限请求状态（批准/拒绝）"""
    result = await service.update_permission_status(group_chat_id, message_id, body.status)
    return PermissionUpdateResponse(
        message_id=result["message_id"],
        new_status=result["new_status"],
    )


@router.post(
    "/{group_chat_id}/upload",
    response_model=UploadedFileInfo,
    responses={
        400: {"description": "文件类型不支持或文件大小超限"},
        404: {"description": "群聊不存在"},
    },
)
async def upload_file(
    group_chat_id: str,
    file: UploadFile = File(...),
    service: GroupChatService = Depends(get_group_chat_service),
):
    """上传文件到群聊"""
    file_content = await file.read()
    return await service.upload_file(
        group_chat_id=group_chat_id,
        file_content=file_content,
        original_filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
    )


@router.post(
    "/{group_chat_id}/members/{agent_name}/compress",
    response_model=dict,
    responses={
        404: {"description": "群聊或 Agent 不存在"},
        409: {"description": "Agent 正在执行任务"},
    },
)
async def compress_agent_context(
    group_chat_id: str,
    agent_name: str,
    service: GroupChatService = Depends(get_group_chat_service),
):
    """压缩指定 Agent 的 CLI session 上下文"""
    return await service.compress_agent_context(group_chat_id, agent_name)


@router.post(
    "/{group_chat_id}/compress-all",
    response_model=dict,
    responses={
        404: {"description": "群聊不存在"},
    },
)
async def compress_all_agents(
    group_chat_id: str,
    service: GroupChatService = Depends(get_group_chat_service),
):
    """全量压缩所有 Agent 的上下文"""
    return await service.compress_all_agents(group_chat_id)
