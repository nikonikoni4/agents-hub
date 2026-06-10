"""WebSocket exception classes unit tests"""

from agents_hub.api.websocket.exceptions import (
    WebSocketBroadcastError,
    WebSocketConnectionError,
    WebSocketError,
    WebSocketRoomNotFoundError,
    WebSocketValidationError,
)
from agents_hub.exceptions import (
    AgentsHubError,
    ExternalServiceError,
    ResourceNotFoundError,
    ValidationError,
)


class TestWebSocketError:
    """WebSocketError 基类测试"""

    def test_construction_with_message(self):
        err = WebSocketError("something failed")
        assert str(err) == "[WebSocketError] something failed"

    def test_isinstance_agents_hub_error(self):
        err = WebSocketError("test")
        assert isinstance(err, AgentsHubError)
        assert isinstance(err, Exception)

    def test_to_dict_fields(self):
        err = WebSocketError("boom", error_code="WS_001", details={"k": "v"})
        d = err.to_dict()
        assert d["error_code"] == "WS_001"
        assert d["message"] == "boom"
        assert d["details"] == {"k": "v"}
        assert d["type"] == "WebSocketError"

    def test_error_code_defaults_to_class_name(self):
        err = WebSocketError("test")
        assert err.error_code == "WebSocketError"


class TestWebSocketConnectionError:
    def test_isinstance_hierarchy(self):
        err = WebSocketConnectionError("conn lost")
        assert isinstance(err, WebSocketError)
        assert isinstance(err, AgentsHubError)
        assert isinstance(err, ExternalServiceError)

    def test_to_dict(self):
        err = WebSocketConnectionError("timeout", details={"host": "localhost"})
        d = err.to_dict()
        assert d["error_code"] == "WebSocketConnectionError"
        assert d["message"] == "timeout"
        assert d["details"] == {"host": "localhost"}
        assert d["type"] == "WebSocketConnectionError"


class TestWebSocketRoomNotFoundError:
    def test_isinstance_hierarchy(self):
        err = WebSocketRoomNotFoundError("room missing")
        assert isinstance(err, WebSocketError)
        assert isinstance(err, AgentsHubError)
        assert isinstance(err, ResourceNotFoundError)

    def test_to_dict(self):
        err = WebSocketRoomNotFoundError("no room", details={"room_id": "r1"})
        d = err.to_dict()
        assert d["error_code"] == "WebSocketRoomNotFoundError"
        assert d["message"] == "no room"
        assert d["details"] == {"room_id": "r1"}
        assert d["type"] == "WebSocketRoomNotFoundError"


class TestWebSocketBroadcastError:
    def test_isinstance_hierarchy(self):
        err = WebSocketBroadcastError("broadcast failed")
        assert isinstance(err, WebSocketError)
        assert isinstance(err, AgentsHubError)
        assert isinstance(err, ExternalServiceError)

    def test_to_dict(self):
        err = WebSocketBroadcastError("send error")
        d = err.to_dict()
        assert d["error_code"] == "WebSocketBroadcastError"
        assert d["message"] == "send error"
        assert d["type"] == "WebSocketBroadcastError"


class TestWebSocketValidationError:
    def test_isinstance_hierarchy(self):
        err = WebSocketValidationError("bad payload")
        assert isinstance(err, WebSocketError)
        assert isinstance(err, AgentsHubError)
        assert isinstance(err, ValidationError)

    def test_to_dict(self):
        err = WebSocketValidationError("invalid", details={"field": "text"})
        d = err.to_dict()
        assert d["error_code"] == "WebSocketValidationError"
        assert d["message"] == "invalid"
        assert d["details"] == {"field": "text"}
        assert d["type"] == "WebSocketValidationError"


class TestReExports:
    """Verify __init__.py re-exports are accessible"""

    def test_all_importable_from_package(self):
        from agents_hub.api.websocket import (
            WebSocketBroadcastError,
            WebSocketConnectionError,
            WebSocketError,
            WebSocketRoomNotFoundError,
            WebSocketValidationError,
        )

        assert WebSocketError is not None
        assert WebSocketConnectionError is not None
        assert WebSocketRoomNotFoundError is not None
        assert WebSocketBroadcastError is not None
        assert WebSocketValidationError is not None
