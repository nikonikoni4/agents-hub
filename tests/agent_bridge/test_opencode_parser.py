"""OpenCodeParser 单元测试

覆盖：
- 正常事件解析（step_start, text, step_finish, tool_use_start, error）
- 边界条件（null part、空 text、缺失字段、sessionID 缓存）
- 错误处理（无效 JSON）
"""

import json

import pytest

from agents_hub.agent_bridge.exceptions import ParseError
from agents_hub.agent_bridge.models import AgentEventType
from agents_hub.agent_bridge.parsers.opencode import OpenCodeParser
from agents_hub.config.types import AgentPlatform


@pytest.fixture
def parser():
    return OpenCodeParser()


class TestStepStart:
    """step_start 事件解析"""

    def test_basic_step_start(self, parser):
        event = parser.parse_event(json.dumps({
            "type": "step_start",
            "sessionID": "ses_123",
            "part": {"type": "step-start"},
        }))
        assert event is not None
        assert event.type == AgentEventType.INIT
        assert event.session_id == "ses_123"
        assert event.platform == AgentPlatform.OPENCODE

    def test_step_start_caches_session_id(self, parser):
        parser.parse_event(json.dumps({
            "type": "step_start",
            "sessionID": "ses_cached",
            "part": {"type": "step-start"},
        }))
        # 后续事件即使没有 sessionID 也应该使用缓存值
        event = parser.parse_event(json.dumps({
            "type": "text",
            "part": {"type": "text", "text": "hello"},
        }))
        assert event.session_id == "ses_cached"


class TestText:
    """text 事件解析"""

    def test_basic_text(self, parser):
        event = parser.parse_event(json.dumps({
            "type": "text",
            "sessionID": "ses_123",
            "part": {"type": "text", "text": "你好"},
        }))
        assert event is not None
        assert event.type == AgentEventType.TEXT_DELTA
        assert event.content["text"] == "你好"

    def test_empty_text_returns_none(self, parser):
        event = parser.parse_event(json.dumps({
            "type": "text",
            "sessionID": "ses_123",
            "part": {"type": "text", "text": ""},
        }))
        assert event is None

    def test_null_part_does_not_crash(self, parser):
        """part 为 null 时不应崩溃"""
        event = parser.parse_event(json.dumps({
            "type": "text",
            "sessionID": "ses_123",
            "part": None,
        }))
        assert event is None  # 空 text 返回 None

    def test_missing_part_does_not_crash(self, parser):
        """part 字段缺失时不应崩溃"""
        event = parser.parse_event(json.dumps({
            "type": "text",
            "sessionID": "ses_123",
        }))
        assert event is None

    def test_part_without_text_field(self, parser):
        """part 存在但没有 text 字段"""
        event = parser.parse_event(json.dumps({
            "type": "text",
            "sessionID": "ses_123",
            "part": {"type": "text"},
        }))
        assert event is None


class TestStepFinish:
    """step_finish 事件解析"""

    def test_basic_step_finish(self, parser):
        event = parser.parse_event(json.dumps({
            "type": "step_finish",
            "sessionID": "ses_123",
            "part": {
                "type": "step-finish",
                "tokens": {"input": 100, "output": 50, "total": 150, "reasoning": 10, "cache": {"read": 80, "write": 5}},
                "cost": 0.01,
            },
        }))
        assert event is not None
        assert event.type == AgentEventType.TURN_COMPLETE
        usage = event.content["usage"]
        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 50
        assert usage["cache_read_tokens"] == 80
        assert usage["cost"] == 0.01

    def test_null_part_does_not_crash(self, parser):
        event = parser.parse_event(json.dumps({
            "type": "step_finish",
            "sessionID": "ses_123",
            "part": None,
        }))
        assert event is not None
        assert event.type == AgentEventType.TURN_COMPLETE
        usage = event.content["usage"]
        assert usage["input_tokens"] == 0
        assert usage["cache_read_tokens"] == 0

    def test_null_tokens_does_not_crash(self, parser):
        """tokens 为 null 时不应崩溃"""
        event = parser.parse_event(json.dumps({
            "type": "step_finish",
            "sessionID": "ses_123",
            "part": {"type": "step-finish", "tokens": None},
        }))
        assert event is not None
        assert event.content["usage"]["input_tokens"] == 0

    def test_null_cache_does_not_crash(self, parser):
        """tokens.cache 为 null 时不应崩溃"""
        event = parser.parse_event(json.dumps({
            "type": "step_finish",
            "sessionID": "ses_123",
            "part": {"type": "step-finish", "tokens": {"input": 10, "cache": None}},
        }))
        assert event is not None
        assert event.content["usage"]["cache_read_tokens"] == 0

    def test_missing_tokens_does_not_crash(self, parser):
        event = parser.parse_event(json.dumps({
            "type": "step_finish",
            "sessionID": "ses_123",
            "part": {"type": "step-finish"},
        }))
        assert event is not None
        assert event.content["usage"]["total_tokens"] == 0


class TestToolUse:
    """tool_use_start 事件解析"""

    def test_basic_tool_use(self, parser):
        event = parser.parse_event(json.dumps({
            "type": "tool_use_start",
            "sessionID": "ses_123",
            "part": {"type": "tool", "name": "bash", "input": {"command": "ls"}},
        }))
        assert event is not None
        assert event.type == AgentEventType.TOOL_USE
        assert event.content["tool_name"] == "bash"
        assert event.content["tool_input"] == {"command": "ls"}

    def test_null_part_does_not_crash(self, parser):
        event = parser.parse_event(json.dumps({
            "type": "tool_use_start",
            "sessionID": "ses_123",
            "part": None,
        }))
        assert event is not None
        assert event.content["tool_name"] == ""


class TestError:
    """error 事件解析"""

    def test_error_returns_text_delta(self, parser):
        """error 事件应包装为 TEXT_DELTA 让用户可见"""
        event = parser.parse_event(json.dumps({
            "type": "error",
            "sessionID": "ses_123",
            "part": {"type": "error", "message": "认证失败"},
        }))
        assert event is not None
        assert event.type == AgentEventType.TEXT_DELTA
        assert "认证失败" in event.content["text"]
        assert "[OpenCode Error]" in event.content["text"]

    def test_null_part_does_not_crash(self, parser):
        event = parser.parse_event(json.dumps({
            "type": "error",
            "sessionID": "ses_123",
            "part": None,
        }))
        assert event is not None
        assert "unknown error" in event.content["text"]


class TestSessionIdCache:
    """sessionID 缓存逻辑"""

    def test_session_id_cached_from_step_start(self, parser):
        parser.parse_event(json.dumps({
            "type": "step_start",
            "sessionID": "ses_first",
            "part": {"type": "step-start"},
        }))
        event = parser.parse_event(json.dumps({
            "type": "text",
            "sessionID": "",
            "part": {"type": "text", "text": "hello"},
        }))
        assert event.session_id == "ses_first"

    def test_session_id_overridden_by_new_value(self, parser):
        parser.parse_event(json.dumps({
            "type": "step_start",
            "sessionID": "ses_first",
            "part": {"type": "step-start"},
        }))
        event = parser.parse_event(json.dumps({
            "type": "text",
            "sessionID": "ses_second",
            "part": {"type": "text", "text": "hello"},
        }))
        assert event.session_id == "ses_second"

    def test_empty_session_id_when_no_cache(self, parser):
        event = parser.parse_event(json.dumps({
            "type": "text",
            "sessionID": "",
            "part": {"type": "text", "text": "hello"},
        }))
        assert event.session_id == ""


class TestInvalidInput:
    """无效输入处理"""

    def test_invalid_json_raises_parse_error(self, parser):
        with pytest.raises(ParseError):
            parser.parse_event("not valid json")

    def test_unknown_event_type_returns_none(self, parser):
        event = parser.parse_event(json.dumps({
            "type": "unknown_type",
            "sessionID": "ses_123",
        }))
        assert event is None
