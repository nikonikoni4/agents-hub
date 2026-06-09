"""单聊数据模型"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from agents_hub.config.types import AgentPlatform


class SingleChatType(str, Enum):
    """单聊创建类型"""

    NEW = "new"
    FORK = "fork"
    CONTINUE_GROUP_CHAT = "continue_group_chat"


class SingleChatIndex(BaseModel):
    """单聊索引（持久化到文件）"""

    single_chat_id: str
    single_chat_name: str
    type: SingleChatType
    agent_name: str
    platform: AgentPlatform
    session_id: str | None = None
    session_path: str | None = None
    group_chat_id: str | None = None
    cwd: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_active_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class CreateSingleChatRequest(BaseModel):
    """创建单聊请求"""

    type: SingleChatType
    single_chat_name: str
    agent_name: str
    group_chat_id: str | None = None
    cwd: str | None = None


class CreateSingleChatResponse(BaseModel):
    """创建单聊响应"""

    single_chat_id: str
    single_chat_name: str
    type: SingleChatType


class SingleChatResponse(BaseModel):
    """单聊详情响应"""

    single_chat_id: str
    single_chat_name: str
    type: SingleChatType
    agent_name: str
    platform: AgentPlatform
    session_id: str | None = None
    group_chat_id: str | None = None
    cwd: str
    created_at: str
    last_active_at: str


class SingleChatListResponse(BaseModel):
    """单聊列表响应"""

    single_chats: list[SingleChatResponse]


class SendMessageRequest(BaseModel):
    """发送消息请求

    当 single_chat_id 为空时，首次消息会自动创建单聊。
    此时 agent_name 必填，single_chat_name 和 type 可选（默认 NEW）。
    """

    content: str
    single_chat_id: str | None = None
    single_chat_name: str | None = None
    agent_name: str | None = None
    type: SingleChatType | None = None
    group_chat_id: str | None = None


class SessionMessageResponse(BaseModel):
    """Session 消息响应"""

    id: str
    role: str
    content: str
    timestamp: str
    model: str | None = None


class MessageHistoryResponse(BaseModel):
    """消息历史响应"""

    messages: list[SessionMessageResponse]
