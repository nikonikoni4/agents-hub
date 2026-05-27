"""AgentBridge 单元测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agents_hub.agent_bridge.bridge import AgentBridge
from agents_hub.agent_bridge.config import RoleConfig, AgentPlatform
from agents_hub.agent_bridge.parsers.base import AgentEventType


class TestAgentBridge:
    """AgentBridge 测试类"""

    def setup_method(self):
        self.bridge = AgentBridge()

    def test_init_creates_executors_and_parsers(self):
        """测试初始化创建执行器和解析器"""
        assert AgentPlatform.CLAUDE in self.bridge._executors
        assert AgentPlatform.CODEX in self.bridge._executors
        assert AgentPlatform.CLAUDE in self.bridge._parsers
        assert AgentPlatform.CODEX in self.bridge._parsers

    @pytest.mark.asyncio
    async def test_execute_stream_calls_correct_executor(self):
        """测试流式调用使用正确的执行器"""
        config = RoleConfig(
            platform=AgentPlatform.CLAUDE,
        )

        # Mock executor - execute() is an async generator
        async def mock_raw_stream(prompt, config, session_id):
            yield '{"type":"system","subtype":"init","session_id":"123"}'

        mock_executor = MagicMock()
        mock_executor.execute = mock_raw_stream
        self.bridge._executors[AgentPlatform.CLAUDE] = mock_executor

        # Mock parser
        mock_parser = MagicMock()
        mock_parser.parse_event.return_value = {
            "type": AgentEventType.INIT,
            "content": {},
            "session_id": "123",
            "timestamp": ""
        }
        self.bridge._parsers[AgentPlatform.CLAUDE] = mock_parser

        # 调用
        events = []
        async for event in self.bridge.execute_stream("测试", config):
            events.append(event)

        assert len(events) == 1
        assert events[0]["type"] == AgentEventType.INIT

    @pytest.mark.asyncio
    async def test_execute_returns_result_event(self):
        """测试非流式调用返回 RESULT 事件"""
        config = RoleConfig(
            platform=AgentPlatform.CLAUDE,
        )

        # Mock execute_stream
        async def mock_stream(prompt, config, session_id=None):
            yield {
                "type": AgentEventType.TEXT_DELTA,
                "content": {"text": "你好"},
                "session_id": "123",
                "timestamp": ""
            }
            yield {
                "type": AgentEventType.TURN_COMPLETE,
                "content": {"usage": {"input_tokens": 100}},
                "session_id": "123",
                "timestamp": ""
            }

        self.bridge.execute_stream = mock_stream

        result = await self.bridge.execute("测试", config)

        assert result["type"] == AgentEventType.RESULT
        assert result["content"]["text"] == "你好"
        assert result["content"]["usage"]["input_tokens"] == 100
