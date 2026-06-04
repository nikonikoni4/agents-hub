"""WebSocket Pydantic Schemas"""

from pydantic import BaseModel, Field

from agents_hub.realtime.events import RefreshSignal


class BroadcastResponse(BaseModel):
    """广播 API 响应体"""

    status: str = Field(default="ok", description="状态")
    message: str = Field(default="Broadcast sent", description="描述")


__all__ = ["BroadcastResponse", "RefreshSignal"]
