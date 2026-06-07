"""群聊 API 路由"""

from pathlib import Path

from fastapi import APIRouter, Depends, Query

from agents_hub.api.schemas.group_chats import (
    AddMembersRequest,
    AgentCallInfo,
    GroupChatCreate,
    GroupChatInfo,
    GroupChatMember,
    MessageCreate,
    MessageInfo,
    PinMessageRequest,
    PinnedMessageInfo,
    PinOperationResponse,
    TaskListInfo,
    UseDockerUpdate,
)
from agents_hub.api.services.group_chat_service import GroupChatService
from agents_hub.config import config
from agents_hub.core.foundation.file_snapshot import get_snapshot_content, get_snapshot_diff
from agents_hub.core.orchestration import group_chat_manager as _group_chat_manager
from agents_hub.exceptions import ResourceNotFoundError

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
    response_model=PinOperationResponse,
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
    await service.pin_message(group_chat_id, body.message_id)
    return PinOperationResponse()


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
    # 1. 验证群聊存在
    await service.group_chat_manager.load_group_chat(group_chat_id)

    # 2. 构建快照目录路径
    group_chat = await service.group_chat_manager.load_group_chat(group_chat_id)
    snapshot_dir = (
        Path(config.data_path)
        / "teams"
        / group_chat.runtime.get_project_path()
        / group_chat_id
        / "file_snapshots"
    )

    # 3. 读取内容
    try:
        content = get_snapshot_content(snapshot_dir, snapshot_id)
        return {"content": content}
    except ValueError as e:
        raise ResourceNotFoundError(
            f"快照不存在: {snapshot_id}",
            details={"snapshot_id": snapshot_id, "group_chat_id": group_chat_id},
        ) from e


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
    # 1. 验证群聊存在
    await service.group_chat_manager.load_group_chat(group_chat_id)

    # 2. 构建快照目录路径
    group_chat = await service.group_chat_manager.load_group_chat(group_chat_id)
    snapshot_dir = (
        Path(config.data_path)
        / "teams"
        / group_chat.runtime.get_project_path()
        / group_chat_id
        / "file_snapshots"
    )

    # 3. 读取 diff
    try:
        diff = get_snapshot_diff(snapshot_dir, snapshot_id)
        return {"diff": diff}
    except ValueError as e:
        raise ResourceNotFoundError(
            f"快照不存在: {snapshot_id}",
            details={"snapshot_id": snapshot_id, "group_chat_id": group_chat_id},
        ) from e
