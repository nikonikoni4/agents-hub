"""CodexParser 单元测试"""

import json
import pytest
from agents_hub.agent_bridge.parsers.codex import CodexParser
from agents_hub.agent_bridge.parsers.base import AgentEventType


class TestCodexParser:
    """CodexParser 测试类"""

    def setup_method(self):
        self.parser = CodexParser()

    def test_parse_agent_message(self):
        """测试解析 agent 消息事件"""
        raw_line = json.dumps({
            "type": "item.completed",
            "item": {
                "id": "item_0",
                "type": "agent_message",
                "text": "我会帮你审查代码"
            },
            "thread_id": "thread-123"
        })
        result = self.parser.parse_event(raw_line)

        assert result is not None
        assert result["type"] == AgentEventType.TEXT_DELTA
        assert result["content"]["text"] == "我会帮你审查代码"
        assert result["session_id"] == "thread-123"

    def test_parse_command_execution(self):
        """测试解析命令执行事件"""
        raw_line = json.dumps({
            "type": "item.completed",
            "item": {
                "id": "item_1",
                "type": "command_execution",
                "command": "ls -la",
                "aggregated_output": "total 0\ndrwxr-xr-x  2 user  staff  64 Jan  1 00:00 .",
                "exit_code": 0,
                "status": "completed"
            },
            "thread_id": "thread-123"
        })
        result = self.parser.parse_event(raw_line)

        assert result is not None
        assert result["type"] == AgentEventType.TOOL_USE
        assert result["content"]["command"] == "ls -la"
        assert result["content"]["exit_code"] == 0
        assert result["session_id"] == "thread-123"

    def test_parse_turn_completed(self):
        """测试解析回合完成事件"""
        raw_line = json.dumps({
            "type": "turn.completed",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "cached_input_tokens": 0
            },
            "thread_id": "thread-123"
        })
        result = self.parser.parse_event(raw_line)

        assert result is not None
        assert result["type"] == AgentEventType.TURN_COMPLETE
        assert result["content"]["usage"]["input_tokens"] == 100
        assert result["session_id"] == "thread-123"

    def test_parse_unknown_event_returns_none(self):
        """测试解析未知事件返回 None"""
        raw_line = json.dumps({
            "type": "unknown_type"
        })
        result = self.parser.parse_event(raw_line)

        assert result is None

    def test_parse_invalid_json_returns_none(self):
        """测试解析无效 JSON 返回 None"""
        result = self.parser.parse_event("invalid json")

        assert result is None
