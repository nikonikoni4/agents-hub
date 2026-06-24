"""测试 execute_with_first_response() 方法

测试覆盖：
- FirstResponseResult 数据类
- AgentBridge.execute_with_first_response() 方法
- Docker 模式回退路径
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents_hub.agent_bridge.models import (
    AgentEventType,
    AgentPlatform,
    AgentResult,
    FirstResponseResult,
    RoleType,
    StreamEvent,
    Usage,
)
from agents_hub.agent_bridge.bridge import AgentBridge
from agents_hub.config.types import AgentPlatform


class TestFirstResponseResult:
    """测试 FirstResponseResult 数据类"""

    def test_first_response_result_creation(self):
        """测试 FirstResponseResult 创建"""
        result = AgentResult(
            text="Hello World",
            session_id="test-session",
            timestamp="2026-01-01T00:00:00",
            agent_name="test-agent",
            platform=AgentPlatform.CLAUDE,
            role_type=RoleType.TEAM_MEMBER,
        )

        first_response = FirstResponseResult(
            first_text="Hello",
            result=result,
        )

        assert first_response.first_text == "Hello"
        assert first_response.result == result
        assert first_response.result.text == "Hello World"

    def test_first_response_result_empty_first_text(self):
        """测试空首句文本（纯工具调用场景）"""
        result = AgentResult(
            text="",
            session_id="test-session",
            timestamp="2026-01-01T00:00:00",
            agent_name="test-agent",
            platform=AgentPlatform.CLAUDE,
            role_type=RoleType.TEAM_MEMBER,
        )

        first_response = FirstResponseResult(
            first_text="",
            result=result,
        )

        assert first_response.first_text == ""
        assert first_response.result.text == ""


class TestExecuteWithFirstResponse:
    """测试 AgentBridge.execute_with_first_response() 方法"""

    @pytest.fixture
    def bridge(self):
        """创建 AgentBridge 实例"""
        with patch.object(AgentBridge, '__init__', lambda self: None):
            bridge = AgentBridge()
            bridge._executors = {}
            bridge._docker_executors = {}
            return bridge

    @pytest.fixture
    def mock_config(self):
        """创建模拟的 RoleConfig"""
        config = MagicMock()
        config.platform = AgentPlatform.CLAUDE
        config.name = "test-agent"
        config.role_type = RoleType.TEAM_MEMBER
        return config

    @pytest.mark.asyncio
    async def test_execute_with_first_response_success(self, bridge, mock_config):
        """测试正常执行流程：首句检测 + 完整结果"""
        # 模拟 execute_stream 返回的事件
        events = [
            StreamEvent(
                type=AgentEventType.TEXT_DELTA,
                content={"text": "Hello "},
                session_id="test-session",
                timestamp="2026-01-01T00:00:01",
                agent_name="test-agent",
                platform=AgentPlatform.CLAUDE,
                role_type=RoleType.TEAM_MEMBER,
            ),
            StreamEvent(
                type=AgentEventType.TEXT_DELTA,
                content={"text": "World"},
                session_id="test-session",
                timestamp="2026-01-01T00:00:02",
                agent_name="test-agent",
                platform=AgentPlatform.CLAUDE,
                role_type=RoleType.TEAM_MEMBER,
            ),
            StreamEvent(
                type=AgentEventType.FIRST_RESPONSE,
                content={},
                session_id="test-session",
                timestamp="2026-01-01T00:00:03",
                agent_name="test-agent",
                platform=AgentPlatform.CLAUDE,
                role_type=RoleType.TEAM_MEMBER,
            ),
            StreamEvent(
                type=AgentEventType.TEXT_DELTA,
                content={"text": " How are you?"},
                session_id="test-session",
                timestamp="2026-01-01T00:00:04",
                agent_name="test-agent",
                platform=AgentPlatform.CLAUDE,
                role_type=RoleType.TEAM_MEMBER,
            ),
            StreamEvent(
                type=AgentEventType.TURN_COMPLETE,
                content={"usage": {"input_tokens": 100, "cache_read_input_tokens": 50}},
                session_id="test-session",
                timestamp="2026-01-01T00:00:05",
                agent_name="test-agent",
                platform=AgentPlatform.CLAUDE,
                role_type=RoleType.TEAM_MEMBER,
            ),
        ]

        async def mock_execute_stream(*args, **kwargs):
            for event in events:
                yield event

        bridge.execute_stream = mock_execute_stream

        result = await bridge.execute_with_first_response(
            prompt="test prompt",
            config=mock_config,
            session_id="test-session",
        )

        assert isinstance(result, FirstResponseResult)
        assert result.first_text == "Hello World"
        assert result.result.text == "Hello World How are you?"
        assert result.result.session_id == "test-session"
        assert result.result.usage.input_tokens == 100
        assert result.result.usage.cache_read_input_tokens == 50

    @pytest.mark.asyncio
    async def test_execute_with_first_response_no_text(self, bridge, mock_config):
        """测试纯工具调用场景：无文本输出"""
        events = [
            StreamEvent(
                type=AgentEventType.TOOL_USE,
                content={"tool_name": "bash", "command": "ls"},
                session_id="test-session",
                timestamp="2026-01-01T00:00:01",
                agent_name="test-agent",
                platform=AgentPlatform.CLAUDE,
                role_type=RoleType.TEAM_MEMBER,
            ),
            StreamEvent(
                type=AgentEventType.TURN_COMPLETE,
                content={"usage": {"input_tokens": 50}},
                session_id="test-session",
                timestamp="2026-01-01T00:00:02",
                agent_name="test-agent",
                platform=AgentPlatform.CLAUDE,
                role_type=RoleType.TEAM_MEMBER,
            ),
        ]

        async def mock_execute_stream(*args, **kwargs):
            for event in events:
                yield event

        bridge.execute_stream = mock_execute_stream

        result = await bridge.execute_with_first_response(
            prompt="test prompt",
            config=mock_config,
            session_id="test-session",
        )

        assert isinstance(result, FirstResponseResult)
        assert result.first_text == ""  # 无文本，首句为空
        assert result.result.text == ""

    @pytest.mark.asyncio
    async def test_execute_with_first_response_first_response_not_detected(self, bridge, mock_config):
        """测试首句未检测到场景：没有 FIRST_RESPONSE 事件"""
        events = [
            StreamEvent(
                type=AgentEventType.TEXT_DELTA,
                content={"text": "Hello World"},
                session_id="test-session",
                timestamp="2026-01-01T00:00:01",
                agent_name="test-agent",
                platform=AgentPlatform.CLAUDE,
                role_type=RoleType.TEAM_MEMBER,
            ),
            StreamEvent(
                type=AgentEventType.TURN_COMPLETE,
                content={"usage": {}},
                session_id="test-session",
                timestamp="2026-01-01T00:00:02",
                agent_name="test-agent",
                platform=AgentPlatform.CLAUDE,
                role_type=RoleType.TEAM_MEMBER,
            ),
        ]

        async def mock_execute_stream(*args, **kwargs):
            for event in events:
                yield event

        bridge.execute_stream = mock_execute_stream

        result = await bridge.execute_with_first_response(
            prompt="test prompt",
            config=mock_config,
            session_id="test-session",
        )

        assert isinstance(result, FirstResponseResult)
        assert result.first_text == ""  # 未检测到首句，返回空
        assert result.result.text == "Hello World"

    @pytest.mark.asyncio
    async def test_execute_with_first_response_session_id_update(self, bridge, mock_config):
        """测试 session_id 更新逻辑"""
        events = [
            StreamEvent(
                type=AgentEventType.INIT,
                content={},
                session_id="new-session-id",
                timestamp="2026-01-01T00:00:01",
                agent_name="test-agent",
                platform=AgentPlatform.CLAUDE,
                role_type=RoleType.TEAM_MEMBER,
            ),
            StreamEvent(
                type=AgentEventType.TEXT_DELTA,
                content={"text": "Hello"},
                session_id="",
                timestamp="2026-01-01T00:00:02",
                agent_name="test-agent",
                platform=AgentPlatform.CLAUDE,
                role_type=RoleType.TEAM_MEMBER,
            ),
            StreamEvent(
                type=AgentEventType.TURN_COMPLETE,
                content={"usage": {}},
                session_id="",
                timestamp="2026-01-01T00:00:03",
                agent_name="test-agent",
                platform=AgentPlatform.CLAUDE,
                role_type=RoleType.TEAM_MEMBER,
            ),
        ]

        async def mock_execute_stream(*args, **kwargs):
            for event in events:
                yield event

        bridge.execute_stream = mock_execute_stream

        result = await bridge.execute_with_first_response(
            prompt="test prompt",
            config=mock_config,
            session_id=None,  # 初始 session_id 为空
        )

        assert result.result.session_id == "new-session-id"

    @pytest.mark.asyncio
    async def test_execute_with_first_response_codex_fallback(self, bridge):
        """测试 Codex 首次调用回退到 execute()"""
        mock_config = MagicMock()
        mock_config.platform = AgentPlatform.CODEX
        mock_config.name = "test-agent"
        mock_config.role_type = RoleType.TEAM_MEMBER

        expected_result = AgentResult(
            text="fallback result",
            session_id="codex-session",
            timestamp="2026-01-01T00:00:00",
            agent_name="test-agent",
            platform=AgentPlatform.CODEX,
            role_type=RoleType.TEAM_MEMBER,
        )

        bridge.execute = AsyncMock(return_value=expected_result)

        result = await bridge.execute_with_first_response(
            prompt="test prompt",
            config=mock_config,
            session_id=None,  # Codex 首次调用
        )

        assert isinstance(result, FirstResponseResult)
        assert result.first_text == ""  # 回退模式下首句为空
        assert result.result == expected_result
        bridge.execute.assert_called_once()
