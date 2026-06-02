"""
群聊相关的 Pydantic Schema 定义

用于 API 请求验证和响应序列化
"""

from datetime import datetime

from pydantic import BaseModel, Field


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
    group_type: str
    is_active: bool


class GroupChatSummary(BaseModel):
    """群聊摘要（列表展示）"""

    group_chat_id: str
    group_chat_name: str
    project_path: str
    is_active: bool
    created_at: datetime


class GroupChatMember(BaseModel):
    """群聊成员（运行时信息）"""

    name: str
    main_session: str | None
    btw_session: list[str]
    cwd: str | None
    use_docker: bool = False
