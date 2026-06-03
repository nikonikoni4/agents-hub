# agents_hub/api/websocket/exceptions.py
"""WebSocket 异常类

继承现有 agents_hub/exceptions.py 分类体系，按"谁应该处理"分类。
"""

from agents_hub.exceptions import (
    AgentsHubError,
    ExternalServiceError,
    ResourceNotFoundError,
    ValidationError,
)


class WebSocketError(AgentsHubError):
    """WebSocket 错误基类"""

    pass


class WebSocketConnectionError(WebSocketError, ExternalServiceError):
    """WebSocket 连接错误（网络层问题）"""

    pass


class WebSocketRoomNotFoundError(WebSocketError, ResourceNotFoundError):
    """房间不存在错误"""

    pass


class WebSocketBroadcastError(WebSocketError, ExternalServiceError):
    """广播错误（发送失败）"""

    pass


class WebSocketValidationError(WebSocketError, ValidationError):
    """WebSocket 消息验证错误"""

    pass
