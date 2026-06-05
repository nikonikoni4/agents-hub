"""群聊 API 路由"""

from fastapi import APIRouter, Depends, Query

from agents_hub.api.schemas.group_chats import (
    GroupChatCreate,
    GroupChatInfo,
    GroupChatMember,
    MessageCreate,
    MessageInfo,
    UseDockerUpdate,
)
from agents_hub.api.services.group_chat_service import GroupChatService
from agents_hub.core.foundation import GroupChatType
from agents_hub.core.orchestration import GroupChat, GroupChatManager

router = APIRouter(prefix="/group-chats", tags=["group-chats"])

# 全局单例
_group_chat_manager = GroupChatManager()


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
    limit: int = Query(50, ge=1, le=200, description="返回消息数量上限"),
    offset: int = Query(0, ge=0, description="跳过前 N 条消息"),
    service: GroupChatService = Depends(get_group_chat_service),
):
    """获取群聊消息历史"""
    return await service.get_messages(group_chat_id, limit=limit, offset=offset)


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
        send_to=request.send_to,
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


@router.post("/test/create-and-start", response_model=dict[str, str])
async def test_create_and_start_group_chat():
    """测试端点：直接创建 GroupChat 并启动"""
    # 1. 设置参数
    team_members = ["测试", "E2E测试角色", "manager"]
    project_path = r"D:\desktop\软件开发\agents-hub\.claude\worktrees\feat_group_chat"
    group_chat_name = "测试群聊"

    # 2. 直接创建 GroupChat 实例
    group_chat = GroupChat(
        team_members_name=team_members,
        group_type=GroupChatType.MANAGER_ORCHESTRATE,
        project_path=project_path,
        group_chat_name=group_chat_name,
    )

    # 3. 启动群聊
    await group_chat.start()

    return {
        "group_chat_id": group_chat.group_chat_id,
        "group_chat_name": group_chat.group_chat_name,
        "is_active": str(group_chat._activated),
    }


@router.post("/test/bridge-execute", response_model=dict[str, str])
async def test_bridge_execute():
    """测试端点：直接调用 bridge 执行"""
    from agents_hub.agent_bridge.bridge import AgentBridge
    from agents_hub.roles.role_manager import RoleManager

    # 1. 获取角色
    role_manager = RoleManager()
    role = role_manager.get_role("测试")
    config = role.get_role_config()

    # 2. 调用 bridge
    bridge = AgentBridge()
    result = await bridge.execute(
        prompt="请简单介绍一下你自己",
        config=config,
        cwd=r"D:\desktop\软件开发\agents-hub\.claude\worktrees\feat_group_chat",
    )

    return {
        "agent_name": result.agent_name,
        "text": result.text[:200],  # 截断前200字符
        "session_id": result.session_id,
    }


@router.post("/test/subprocess", response_model=dict[str, str])
async def test_subprocess():
    """测试端点：测试 asyncio.create_subprocess_exec"""
    import asyncio

    try:
        process = await asyncio.create_subprocess_exec(
            "cmd",
            "/c",
            "echo hello",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return {
            "status": "success",
            "returncode": str(process.returncode),
            "stdout": stdout.decode().strip(),
            "event_loop": type(asyncio.get_event_loop()).__name__,
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error": str(e),
            "event_loop": type(asyncio.get_event_loop()).__name__,
        }
