"""
群聊相关的 Pydantic Schema 定义

用于 API 请求验证和响应序列化
"""

from datetime import datetime

from pydantic import BaseModel, Field

from agents_hub.core.foundation.models import GroupChatType


class GroupChatCreate(BaseModel):
    """创建群聊请求"""

    team_members: list[str] = Field(..., min_length=1, description="团队成员角色名列表")
    project_path: str = Field(..., description="项目路径")
    group_chat_name: str | None = Field(None, description="群聊名称，不提供则使用 group_chat_id")


class GroupChatInfo(BaseModel):
    """群聊详细信息"""

    group_chat_id: str
    group_chat_name: str
    project_path: str
    created_at: datetime
    group_type: GroupChatType
    is_active: bool
    last_speaker: str | None = None
    last_message: str | None = None
    last_update_time: str | None = None


class GroupChatMember(BaseModel):
    """群聊成员（运行时信息）"""

    name: str
    main_session: str | None
    btw_session: list[str]
    cwd: str | None
    use_docker: bool = False


class UseDockerUpdate(BaseModel):
    """切换成员 Docker 沙箱开关请求"""

    use_docker: bool = Field(..., description="是否启用 Docker 沙箱执行")


class MessageCreate(BaseModel):
    """发送消息请求"""

    content: str = Field(..., min_length=1, description="消息内容")
    members: list[str] = Field(..., min_length=1, description="群聊中所有 agent 名称列表")


class MessageInfo(BaseModel):
    """消息信息"""

    id: int = Field(..., description="消息自增 id")
    speaker: str = Field(..., description="发送者名称（agent 角色名或 'user'）")
    content: str = Field(..., description="消息内容")
    timestamp: str = Field(..., description="时间戳")
    platform: str = Field(..., description="来源平台")
    cwd: str | None = Field(None, description="Agent 工作目录")
    modified_files: list[dict] | None = Field(None, description="修改的文件列表")
    git_diff_range: str | None = Field(None, description="Git diff 范围")


# --- Pin Messages Schemas ---


class PinMessageRequest(BaseModel):
    """POST /pinned-messages 请求体"""

    message_id: int = Field(..., description="消息 id")


class PinnedMessageInfo(BaseModel):
    """GET /pinned-messages 响应列表项"""

    message_id: int = Field(..., description="消息 id")
    speaker: str = Field(..., description="消息发送者名称")
    content: str = Field(..., description="消息完整内容（快照）")
    timestamp: str = Field(..., description="消息原始时间戳")
    platform: str = Field(..., description="消息来源平台")
    pinned_at: str = Field(..., description="置顶操作时间")


class PinOperationResponse(BaseModel):
    """POST/DELETE /pinned-messages 成功响应"""

    ok: bool = Field(default=True, description="操作是否成功")


class PinErrorResponse(BaseModel):
    """错误响应的统一格式"""

    error_code: str = Field(..., description="错误码")
    message: str = Field(..., description="人类可读的错误描述")


# --- Group Chat Members Schemas ---


class AddMembersRequest(BaseModel):
    """添加群成员请求"""

    member_names: list[str] = Field(..., min_length=1, description="成员角色名列表")


# --- Agent Calls Schemas ---


class AgentCallInfo(BaseModel):
    """Agent 调用信息（用于前端展示）"""

    call_id: str = Field(..., description="调用 ID")
    send_from: str = Field(..., description="发送者名称")
    send_to: str = Field(..., description="接收者名称")
    content: str = Field(..., description="消息内容")
    message_type: str = Field(..., description="消息类型：task/notification")
    status: str = Field(..., description="调用状态：pending/running/completed/failed/timeout")
    created_at: str = Field(..., description="创建时间 ISO 8601")
    started_at: str | None = Field(None, description="开始时间 ISO 8601")
    completed_at: str | None = Field(None, description="完成时间 ISO 8601")
    error: str | None = Field(None, description="错误信息")

    @classmethod
    def from_agent_call(cls, call) -> "AgentCallInfo":
        """从 AgentCall 领域模型转换为 API Schema"""
        return cls(
            call_id=call.call_id,
            send_from=call.send_from,
            send_to=call.send_to,
            content=call.content,
            message_type=call.message_type.value,
            status=call.status.value,
            created_at=call.created_at.isoformat(),
            started_at=call.started_at.isoformat() if call.started_at else None,
            completed_at=call.completed_at.isoformat() if call.completed_at else None,
            error=call.error,
        )


# --- Tasks Schemas ---


class TaskInfo(BaseModel):
    """单个任务信息"""

    task_id: str = Field(..., description="任务 ID")
    owner: str = Field(..., description="任务负责人")
    content: str = Field(..., description="任务描述")
    status: str = Field(..., description="任务状态：pending/running/completed/failed")
    created_at: str = Field(..., description="创建时间 ISO 8601")
    updated_at: str = Field(..., description="更新时间 ISO 8601")

    @classmethod
    def from_task(cls, task) -> "TaskInfo":
        """从 Task 领域模型转换为 API Schema"""
        return cls(
            task_id=task.task_id,
            owner=task.owner,
            content=task.content,
            status=task.status.value,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
        )


class TaskListInfo(BaseModel):
    """任务列表信息（用于前端展示）"""

    list_id: str = Field(..., description="任务列表 ID")
    status: str = Field(..., description="列表状态：active/archived")
    tasks: list[TaskInfo] = Field(..., description="任务列表")
    created_at: str = Field(..., description="创建时间 ISO 8601")
    archived_at: str | None = Field(None, description="归档时间 ISO 8601")

    @classmethod
    def from_task_list(cls, task_list) -> "TaskListInfo":
        """从 TaskList 领域模型转换为 API Schema"""
        return cls(
            list_id=task_list.list_id,
            status=task_list.status.value,
            tasks=[TaskInfo.from_task(task) for task in task_list.tasks],
            created_at=task_list.created_at.isoformat(),
            archived_at=task_list.archived_at.isoformat() if task_list.archived_at else None,
        )
