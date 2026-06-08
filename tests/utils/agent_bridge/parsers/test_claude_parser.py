"""ClaudeParser 单元测试"""

import json

import pytest

from agents_hub.agent_bridge.exceptions import ParseError
from agents_hub.agent_bridge.models import AgentEventType
from agents_hub.agent_bridge.parsers.claude import ClaudeParser


class TestClaudeParser:
    """ClaudeParser 测试类"""

    def setup_method(self):
        self.parser = ClaudeParser()

    def test_parse_text_delta(self):
        """测试解析文本增量事件"""
        raw_line = json.dumps({
            "type": "stream_event",
            "event": {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "你好"}
            },
            "session_id": "test-session-123"
        })
        result = self.parser.parse_event(raw_line)

        assert result is not None
        assert result.type == AgentEventType.TEXT_DELTA
        assert result.content["text"] == "你好"
        assert result.session_id == "test-session-123"

    def test_parse_init(self):
        """测试解析初始化事件"""
        raw_line = json.dumps({
            "type": "system",
            "subtype": "init",
            "session_id": "test-session-123",
            "model": "claude-opus-4-7",
            "tools": ["Bash", "Read", "Write"]
        })
        result = self.parser.parse_event(raw_line)

        assert result is not None
        assert result.type == AgentEventType.INIT
        assert result.content["model"] == "claude-opus-4-7"
        assert "Bash" in result.content["tools"]

    def test_parse_unknown_event_returns_none(self):
        """测试解析未知事件返回 None"""
        raw_line = json.dumps({
            "type": "unknown_type",
            "session_id": "test-session-123"
        })
        result = self.parser.parse_event(raw_line)

        assert result is None

    def test_parse_invalid_json_raises_parse_error(self):
        """测试解析无效 JSON 抛出 ParseError"""
        with pytest.raises(ParseError):
            self.parser.parse_event("invalid json")

    def test_parse_tool_use_disabled_by_default(self):
        """
        契约：默认关闭工具调用解析，tool_use 事件被忽略

        验证方式：
        1. 确认 ENABLE_TOOL_USE_PARSING 为 False
        2. 发送完整的 tool_use 事件流（start → delta → stop）
        3. 验证所有事件都返回 None
        """
        assert ClaudeParser.ENABLE_TOOL_USE_PARSING is False

        for line in [
            {"type": "stream_event", "event": {"type": "content_block_start", "index": 0,
              "content_block": {"type": "tool_use", "id": "toolu_01", "name": "Bash", "input": {}}},
             "session_id": "s1"},
            {"type": "stream_event", "event": {"type": "content_block_delta", "index": 0,
              "delta": {"type": "input_json_delta", "partial_json": "{\"command\":\"ls\"}"}},
             "session_id": "s1"},
            {"type": "stream_event", "event": {"type": "content_block_stop", "index": 0},
             "session_id": "s1"},
        ]:
            assert self.parser.parse_event(json.dumps(line)) is None


class TestClaudeParserToolUse:
    """工具调用解析测试（需启用 ENABLE_TOOL_USE_PARSING）"""

    def setup_method(self):
        self.parser = ClaudeParser()
        self.parser.ENABLE_TOOL_USE_PARSING = True

    def test_parse_tool_use_emits_on_block_stop(self):
        """
        契约：完整的 tool_use 事件流（start → delta → stop）最终 emit TOOL_USE 事件

        验证方式：
        1. 发送 content_block_start（tool_use）
        2. 发送 content_block_delta（input_json_delta）
        3. 发送 content_block_stop
        4. 验证 stop 时 emit 的 TOOL_USE 事件包含正确的 tool_id、tool_name、input
        """
        # start：不 emit 事件
        start_line = json.dumps({
            "type": "stream_event",
            "event": {
                "type": "content_block_start",
                "index": 1,
                "content_block": {
                    "type": "tool_use",
                    "id": "toolu_01ABC123",
                    "name": "Bash",
                    "input": {}
                }
            },
            "session_id": "sess-456"
        })
        result = self.parser.parse_event(start_line)
        assert result is None

        # delta：累积输入，不 emit 事件
        delta1 = json.dumps({
            "type": "stream_event",
            "event": {
                "type": "content_block_delta",
                "index": 1,
                "delta": {"type": "input_json_delta", "partial_json": "{\"command\":"}
            },
            "session_id": "sess-456"
        })
        result = self.parser.parse_event(delta1)
        assert result is None

        delta2 = json.dumps({
            "type": "stream_event",
            "event": {
                "type": "content_block_delta",
                "index": 1,
                "delta": {"type": "input_json_delta", "partial_json": "\"ls -la\"}"}
            },
            "session_id": "sess-456"
        })
        result = self.parser.parse_event(delta2)
        assert result is None

        # stop：emit TOOL_USE 事件
        stop_line = json.dumps({
            "type": "stream_event",
            "event": {
                "type": "content_block_stop",
                "index": 1
            },
            "session_id": "sess-456"
        })
        result = self.parser.parse_event(stop_line)

        assert result is not None
        assert result.type == AgentEventType.TOOL_USE
        assert result.content["tool_id"] == "toolu_01ABC123"
        assert result.content["tool_name"] == "Bash"
        assert result.content["input"] == {"command": "ls -la"}
        assert result.session_id == "sess-456"

    def test_parse_tool_use_empty_input(self):
        """
        契约：无参数的工具调用（input 为空）也能正确解析

        验证方式：
        1. 发送 content_block_start（tool_use，无 input delta）
        2. 直接发送 content_block_stop
        3. 验证 input 为空 dict
        """
        start_line = json.dumps({
            "type": "stream_event",
            "event": {
                "type": "content_block_start",
                "index": 0,
                "content_block": {
                    "type": "tool_use",
                    "id": "toolu_02DEF456",
                    "name": "Read",
                    "input": {}
                }
            },
            "session_id": "sess-789"
        })
        self.parser.parse_event(start_line)

        stop_line = json.dumps({
            "type": "stream_event",
            "event": {
                "type": "content_block_stop",
                "index": 0
            },
            "session_id": "sess-789"
        })
        result = self.parser.parse_event(stop_line)

        assert result is not None
        assert result.type == AgentEventType.TOOL_USE
        assert result.content["tool_id"] == "toolu_02DEF456"
        assert result.content["tool_name"] == "Read"
        assert result.content["input"] == {}

    def test_parse_text_block_stop_returns_none(self):
        """
        契约：非 tool_use 的 content_block_stop 不 emit 事件

        验证方式：
        1. 不缓存任何 tool_use 块
        2. 发送 content_block_stop
        3. 验证返回 None
        """
        stop_line = json.dumps({
            "type": "stream_event",
            "event": {
                "type": "content_block_stop",
                "index": 0
            },
            "session_id": "sess-000"
        })
        result = self.parser.parse_event(stop_line)
        assert result is None

    def test_parse_text_start_returns_none(self):
        """
        契约：text 类型的 content_block_start 不缓存，返回 None

        验证方式：
        1. 发送 content_block_start（text 类型）
        2. 验证返回 None
        """
        start_line = json.dumps({
            "type": "stream_event",
            "event": {
                "type": "content_block_start",
                "index": 0,
                "content_block": {
                    "type": "text",
                    "text": ""
                }
            },
            "session_id": "sess-111"
        })
        result = self.parser.parse_event(start_line)
        assert result is None
