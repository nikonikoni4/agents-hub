"""AgentBridge 单元测试"""

from unittest.mock import MagicMock

import pytest

from agents_hub.agent_bridge.bridge import AgentBridge
from agents_hub.agent_bridge.models import AgentEventType, AgentPlatform, AgentResult, StreamEvent
from agents_hub.config.types import RoleType
from agents_hub.roles.models import RoleConfig


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
            name="test-agent",
            platform=AgentPlatform.CLAUDE,
        )

        # Mock executor - execute() is an async generator
        async def mock_raw_stream(prompt, config, session_id, cwd=None, fork_from=None, system_prompt=None):
            yield '{"type":"system","subtype":"init","session_id":"123"}'

        mock_executor = MagicMock()
        mock_executor.execute = mock_raw_stream
        self.bridge._executors[AgentPlatform.CLAUDE] = mock_executor

        # Mock parser - returns StreamEvent dataclass, not dict
        mock_parser = MagicMock()
        mock_parser.parse_event.return_value = StreamEvent(
            type=AgentEventType.INIT,
            content={},
            session_id="123",
            timestamp="",
            agent_name="",
            platform=AgentPlatform.CLAUDE,
            role_type=RoleType.TEAM_MEMBER,
        )
        self.bridge._parsers[AgentPlatform.CLAUDE] = mock_parser

        # 调用
        events = []
        async for event in self.bridge.execute_stream("测试", config):
            events.append(event)

        assert len(events) == 1
        assert events[0].type == AgentEventType.INIT

    @pytest.mark.asyncio
    async def test_execute_returns_result(self):
        """测试非流式调用返回 AgentResult"""
        config = RoleConfig(
            name="test-agent",
            platform=AgentPlatform.CLAUDE,
        )

        # Mock execute_stream - yields StreamEvent dataclass instances
        async def mock_stream(prompt, config, session_id=None, cwd=None, fork_from=None, system_prompt=None):
            yield StreamEvent(
                type=AgentEventType.TEXT_DELTA,
                content={"text": "你好"},
                session_id="123",
                timestamp="",
                agent_name="test-agent",
                platform=AgentPlatform.CLAUDE,
                role_type=RoleType.TEAM_MEMBER,
            )
            yield StreamEvent(
                type=AgentEventType.TURN_COMPLETE,
                content={"usage": {"input_tokens": 100}},
                session_id="123",
                timestamp="",
                agent_name="test-agent",
                platform=AgentPlatform.CLAUDE,
                role_type=RoleType.TEAM_MEMBER,
            )

        self.bridge.execute_stream = mock_stream

        result = await self.bridge.execute("测试", config)

        assert isinstance(result, AgentResult)
        assert result.text == "你好"
        assert result.usage.input_tokens == 100
        assert result.session_id == "123"
