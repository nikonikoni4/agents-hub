"""Realtime and WebSocket exceptions."""

from agents_hub.exceptions import (
    AgentsHubError,
    ExternalServiceError,
    ResourceNotFoundError,
    ValidationError,
)


class WebSocketError(AgentsHubError):
    """WebSocket error base class."""

    pass


class WebSocketConnectionError(WebSocketError, ExternalServiceError):
    """WebSocket connection error."""

    pass


class WebSocketRoomNotFoundError(WebSocketError, ResourceNotFoundError):
    """WebSocket room not found."""

    pass


class WebSocketBroadcastError(WebSocketError, ExternalServiceError):
    """WebSocket broadcast error."""

    pass


class WebSocketValidationError(WebSocketError, ValidationError):
    """WebSocket validation error."""

    pass
