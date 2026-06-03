"""WebSocket Pydantic Schemas"""

from datetime import datetime

from pydantic import BaseModel, Field


class RefreshSignal(BaseModel):
    """刷新信号请求体"""

    type: str = Field(default="refresh", description="信号类型")
    group_chat_id: str = Field(..., description="群聊 ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="信号时间戳")


class BroadcastResponse(BaseModel):
    """广播 API 响应体"""

    status: str = Field(default="ok", description="状态")
    message: str = Field(default="Broadcast sent", description="描述")
