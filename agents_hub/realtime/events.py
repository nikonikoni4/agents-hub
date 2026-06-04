"""Realtime event models."""

from datetime import datetime

from pydantic import BaseModel, Field


class RefreshSignal(BaseModel):
    """Refresh signal sent when a group chat has changed."""

    type: str = Field(default="refresh", description="信号类型")
    group_chat_id: str = Field(..., description="群聊 ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="信号时间戳")


def make_refresh_signal(group_chat_id: str) -> RefreshSignal:
    """Create a refresh event for a group chat."""
    return RefreshSignal(group_chat_id=group_chat_id)
