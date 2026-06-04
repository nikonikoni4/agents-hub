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
    send_to: str = Field(..., description="目标角色名（如 'manager' 或具体 worker）")


class MessageInfo(BaseModel):
    """消息信息"""

    speaker: str = Field(..., description="发送者名称（agent 角色名或 'user'）")
    content: str = Field(..., description="消息内容")
    timestamp: str = Field(..., description="时间戳")
    platform: str = Field(..., description="来源平台")
