"""ClaudeParser 单元测试"""

import json
import pytest
from agents_hub.agent_bridge.parsers.claude import ClaudeParser
from agents_hub.agent_bridge.models import AgentEventType


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
        assert result["type"] == AgentEventType.TEXT_DELTA
        assert result["content"]["text"] == "你好"
        assert result["session_id"] == "test-session-123"

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
        assert result["type"] == AgentEventType.INIT
        assert result["content"]["model"] == "claude-opus-4-7"
        assert "Bash" in result["content"]["tools"]

    def test_parse_unknown_event_returns_none(self):
        """测试解析未知事件返回 None"""
        raw_line = json.dumps({
            "type": "unknown_type",
            "session_id": "test-session-123"
        })
        result = self.parser.parse_event(raw_line)

        assert result is None

    def test_parse_invalid_json_returns_none(self):
        """测试解析无效 JSON 返回 None"""
        result = self.parser.parse_event("invalid json")

        assert result is None
