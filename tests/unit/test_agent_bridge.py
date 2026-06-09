"""AgentBridge 单元测试"""

from unittest.mock import patch

import pytest

from agents_hub.agent_bridge.bridge import AgentBridge
from agents_hub.agent_bridge.exceptions import (
    CLIExecutionError,
    CLINotFoundError,
    PlatformNotSupportedError,
)
from agents_hub.agent_bridge.models import AgentEventType, StreamEvent
from agents_hub.config.types import AgentPlatform, RoleType
from agents_hub.roles.models import RoleConfig


@pytest.fixture
def bridge():
    return AgentBridge()


@pytest.fixture
def opencode_config():
    return RoleConfig(
        name="test-agent",
        platform=AgentPlatform.OPENCODE,
        work_root="D:\\test",
    )


@pytest.fixture
def claude_config():
    return RoleConfig(
        name="test-agent",
        platform=AgentPlatform.CLAUDE,
    )


def make_stream_event(event_type, text="", session_id="sess_123"):
    """创建测试用的 StreamEvent"""
    if event_type == AgentEventType.TEXT_DELTA:
        content = {"text": text}
    elif event_type == AgentEventType.TURN_COMPLETE:
        content = {"usage": {"input_tokens": 10, "output_tokens": 20}}
    else:
        content = {}

    return StreamEvent(
        type=event_type,
        content=content,
        session_id=session_id,
        timestamp="2025-01-01T00:00:00",
        agent_name="",
        platform=AgentPlatform.OPENCODE,
        role_type=RoleType.TEAM_MEMBER,
    )


def make_opencode_event(event_type, text="", session_id="sess_123"):
    """创建 OpenCode 格式的事件 dict"""
    if event_type == "init":
        return {"type": "init", "session_id": session_id, "timestamp": 1234567890, "data": {}}
    elif event_type == "text_delta":
        return {
            "type": "text_delta",
            "text": text,
            "session_id": session_id,
            "timestamp": 1234567890,
        }
    elif event_type == "turn_complete":
        return {
            "type": "turn_complete",
            "session_id": session_id,
            "timestamp": 1234567890,
            "tokens": {"input_tokens": 10, "output_tokens": 20},
            "cost": 0.01,
            "reason": "stop",
        }
    return {"type": event_type}


class MockOpenCodeExecutor:
    """模拟 OpenCode 执行器，返回 dict 事件"""

    def __init__(self, events):
        self._events = events

    async def execute(self, *args, **kwargs):
        for event in self._events:
            yield event


class MockStringExecutor:
    """模拟执行器，返回 str（用于 Claude/Codex）"""

    def __init__(self, events):
        self._events = events

    async def execute(self, *args, **kwargs):
        for event in self._events:
            yield event


# =============================================================================
# execute_stream
# =============================================================================


class TestExecuteStream:
    """execute_stream 方法测试"""

    @pytest.mark.asyncio
    async def test_execute_stream_returns_opencode_events(self, bridge, opencode_config):
        """
        契约：流式执行返回 OpenCode 事件流

        验证方式：
        1. mock executor 返回 dict 事件
        2. 调用 execute_stream
        3. 验证返回正确的事件

        如果失败，说明：事件流处理逻辑错误
        """
        mock_events = [
            make_opencode_event("text_delta", "hello"),
            make_opencode_event("text_delta", " world"),
        ]

        bridge._executors[AgentPlatform.OPENCODE] = MockOpenCodeExecutor(mock_events)

        events = []
        async for event in bridge.execute_stream("test", opencode_config):
            events.append(event)

        assert len(events) == 2
        assert events[0].type == AgentEventType.TEXT_DELTA
        assert events[0].content["text"] == "hello"
        assert events[1].content["text"] == " world"

    @pytest.mark.asyncio
    async def test_execute_stream_sets_agent_name(self, bridge, opencode_config):
        """
        契约：事件包含 agent_name

        验证方式：
        1. mock executor
        2. 调用 execute_stream
        3. 验证事件的 agent_name 被设置

        如果失败，说明：agent_name 设置逻辑错误
        """
        mock_events = [make_opencode_event("text_delta", "test")]

        bridge._executors[AgentPlatform.OPENCODE] = MockOpenCodeExecutor(mock_events)

        async for event in bridge.execute_stream("test", opencode_config):
            assert event.agent_name == "test-agent"

    @pytest.mark.asyncio
    async def test_execute_stream_sets_platform(self, bridge, opencode_config):
        """
        契约：事件包含 platform

        验证方式：
        1. mock executor
        2. 调用 execute_stream
        3. 验证事件的 platform 被设置

        如果失败，说明：platform 设置逻辑错误
        """
        mock_events = [make_opencode_event("text_delta", "test")]

        bridge._executors[AgentPlatform.OPENCODE] = MockOpenCodeExecutor(mock_events)

        async for event in bridge.execute_stream("test", opencode_config):
            assert event.platform == AgentPlatform.OPENCODE

    @pytest.mark.asyncio
    async def test_execute_stream_skips_none_parsed_events(self, bridge, opencode_config):
        """
        契约：跳过解析为 None 的事件

        验证方式：
        1. mock executor 返回未知类型事件
        2. 调用 execute_stream
        3. 验证 None 事件被跳过

        如果失败，说明：None 事件处理逻辑错误
        """
        mock_events = [
            {"type": "unknown"},
            make_opencode_event("text_delta", "test"),
        ]

        bridge._executors[AgentPlatform.OPENCODE] = MockOpenCodeExecutor(mock_events)

        events = []
        async for event in bridge.execute_stream("test", opencode_config):
            events.append(event)

        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_execute_stream_raises_on_unsupported_platform(self, bridge):
        """
        契约：不支持的平台抛出 PlatformNotSupportedError

        验证方式：
        1. 调用 execute_stream，传入不支持的平台
        2. 验证抛出 PlatformNotSupportedError

        如果失败，说明：平台验证逻辑错误
        """
        config = RoleConfig(
            name="test",
            platform=AgentPlatform.OPENCODE,
        )
        # 临时移除 OPENCODE 支持
        bridge._executors.pop(AgentPlatform.OPENCODE, None)

        with pytest.raises(PlatformNotSupportedError):
            async for _ in bridge.execute_stream("test", config):
                pass

    @pytest.mark.asyncio
    async def test_execute_stream_raises_on_cli_not_found(self, bridge, opencode_config):
        """
        契约：CLI 不存在时抛出 CLINotFoundError

        验证方式：
        1. mock executor 抛出 CLINotFoundError
        2. 调用 execute_stream
        3. 验证抛出 CLINotFoundError

        如果失败，说明：异常传递逻辑错误
        """

        class FailingExecutor:
            async def execute(self, *args, **kwargs):
                raise CLINotFoundError(platform="OpenCode", command="opencode")
                yield  # 使其成为 async generator

        bridge._executors[AgentPlatform.OPENCODE] = FailingExecutor()

        with pytest.raises(CLINotFoundError):
            async for _ in bridge.execute_stream("test", opencode_config):
                pass

    @pytest.mark.asyncio
    async def test_execute_stream_raises_on_cli_execution_error(self, bridge, opencode_config):
        """
        契约：CLI 执行失败时抛出 CLIExecutionError

        验证方式：
        1. mock executor 抛出 CLIExecutionError
        2. 调用 execute_stream
        3. 验证抛出 CLIExecutionError

        如果失败，说明：异常传递逻辑错误
        """

        class FailingExecutor:
            async def execute(self, *args, **kwargs):
                raise CLIExecutionError(platform="OpenCode", exit_code=1, stderr="error")
                yield  # 使其成为 async generator

        bridge._executors[AgentPlatform.OPENCODE] = FailingExecutor()

        with pytest.raises(CLIExecutionError):
            async for _ in bridge.execute_stream("test", opencode_config):
                pass


# =============================================================================
# execute
# =============================================================================


class TestExecute:
    """execute 方法测试"""

    @pytest.mark.asyncio
    async def test_execute_returns_agent_result(self, bridge, opencode_config):
        """
        契约：非流式执行返回 AgentResult

        验证方式：
        1. mock execute_stream 返回事件
        2. 调用 execute
        3. 验证返回 AgentResult

        如果失败，说明：结果构建逻辑错误
        """
        mock_events = [
            make_stream_event(AgentEventType.TEXT_DELTA, "hello"),
            make_stream_event(AgentEventType.TEXT_DELTA, " world"),
            make_stream_event(AgentEventType.TURN_COMPLETE),
        ]

        async def mock_execute_stream(*args, **kwargs):
            for event in mock_events:
                yield event

        with patch.object(bridge, "execute_stream", side_effect=mock_execute_stream):
            result = await bridge.execute("test", opencode_config)

        assert result.text == "hello world"
        assert result.agent_name == "test-agent"
        assert result.platform == AgentPlatform.OPENCODE

    @pytest.mark.asyncio
    async def test_execute_collects_text_deltas(self, bridge, opencode_config):
        """
        契约：收集所有 text_delta 事件的文本

        验证方式：
        1. mock execute_stream 返回多个 text_delta
        2. 调用 execute
        3. 验证文本被正确拼接

        如果失败，说明：文本收集逻辑错误
        """
        mock_events = [
            make_stream_event(AgentEventType.TEXT_DELTA, "hello"),
            make_stream_event(AgentEventType.TEXT_DELTA, " "),
            make_stream_event(AgentEventType.TEXT_DELTA, "world"),
        ]

        async def mock_execute_stream(*args, **kwargs):
            for event in mock_events:
                yield event

        with patch.object(bridge, "execute_stream", side_effect=mock_execute_stream):
            result = await bridge.execute("test", opencode_config)

        assert result.text == "hello world"

    @pytest.mark.asyncio
    async def test_execute_extracts_usage_from_turn_complete(self, bridge, opencode_config):
        """
        契约：从 turn_complete 事件提取 usage

        验证方式：
        1. mock execute_stream 返回 turn_complete 事件
        2. 调用 execute
        3. 验证 usage 被正确提取

        如果失败，说明：usage 提取逻辑错误
        """
        mock_events = [
            make_stream_event(AgentEventType.TEXT_DELTA, "test"),
            make_stream_event(AgentEventType.TURN_COMPLETE),
        ]

        async def mock_execute_stream(*args, **kwargs):
            for event in mock_events:
                yield event

        with patch.object(bridge, "execute_stream", side_effect=mock_execute_stream):
            result = await bridge.execute("test", opencode_config)

        assert result.usage == {"input_tokens": 10, "output_tokens": 20}

    @pytest.mark.asyncio
    async def test_execute_uses_provided_session_id(self, bridge, opencode_config):
        """
        契约：使用提供的 session_id

        验证方式：
        1. mock execute_stream
        2. 调用 execute，传入 session_id
        3. 验证结果使用提供的 session_id

        如果失败，说明：session_id 处理逻辑错误
        """
        mock_events = [
            make_stream_event(AgentEventType.TEXT_DELTA, "test", session_id="event_session"),
        ]

        async def mock_execute_stream(*args, **kwargs):
            for event in mock_events:
                yield event

        with patch.object(bridge, "execute_stream", side_effect=mock_execute_stream):
            result = await bridge.execute("test", opencode_config, session_id="provided_session")

        assert result.session_id == "provided_session"

    @pytest.mark.asyncio
    async def test_execute_uses_event_session_id_when_not_provided(self, bridge, opencode_config):
        """
        契约：未提供 session_id 时使用事件的 session_id

        验证方式：
        1. mock execute_stream 返回带有 session_id 的事件
        2. 调用 execute，不传 session_id
        3. 验证结果使用事件的 session_id

        如果失败，说明：session_id 回退逻辑错误
        """
        mock_events = [
            make_stream_event(AgentEventType.TEXT_DELTA, "test", session_id="event_session"),
        ]

        async def mock_execute_stream(*args, **kwargs):
            for event in mock_events:
                yield event

        with patch.object(bridge, "execute_stream", side_effect=mock_execute_stream):
            result = await bridge.execute("test", opencode_config)

        assert result.session_id == "event_session"

    @pytest.mark.asyncio
    async def test_execute_passes_system_prompt(self, bridge, opencode_config):
        """
        契约：传递 system_prompt 到 execute_stream

        验证方式：
        1. mock execute_stream
        2. 调用 execute，传入 system_prompt
        3. 验证 system_prompt 被传递

        如果失败，说明：system_prompt 传递逻辑错误
        """

        async def mock_execute_stream(*args, **kwargs):
            assert kwargs.get("system_prompt") == "nico"
            yield make_stream_event(AgentEventType.TEXT_DELTA, "test")

        with patch.object(bridge, "execute_stream", side_effect=mock_execute_stream):
            result = await bridge.execute("test", opencode_config, system_prompt="nico")

        assert result.text == "test"


# =============================================================================
# _dict_to_stream_event
# =============================================================================


class TestDictToStreamEvent:
    """_dict_to_stream_event 方法测试"""

    def test_dict_to_stream_event_init(self, bridge, opencode_config):
        """
        契约：init dict 转换为 StreamEvent

        验证方式：
        1. 构造 init dict
        2. 调用 _dict_to_stream_event
        3. 验证返回 INIT 类型的 StreamEvent

        如果失败，说明：init 事件转换逻辑错误
        """
        event_dict = make_opencode_event("init")
        result = bridge._dict_to_stream_event(event_dict, opencode_config)

        assert result is not None
        assert result.type == AgentEventType.INIT
        assert result.agent_name == "test-agent"
        assert result.platform == AgentPlatform.OPENCODE

    def test_dict_to_stream_event_text_delta(self, bridge, opencode_config):
        """
        契约：text_delta dict 转换为 StreamEvent

        验证方式：
        1. 构造 text_delta dict
        2. 调用 _dict_to_stream_event
        3. 验证返回 TEXT_DELTA 类型的 StreamEvent

        如果失败，说明：text_delta 事件转换逻辑错误
        """
        event_dict = make_opencode_event("text_delta", "hello")
        result = bridge._dict_to_stream_event(event_dict, opencode_config)

        assert result is not None
        assert result.type == AgentEventType.TEXT_DELTA
        assert result.content["text"] == "hello"

    def test_dict_to_stream_event_turn_complete(self, bridge, opencode_config):
        """
        契约：turn_complete dict 转换为 StreamEvent

        验证方式：
        1. 构造 turn_complete dict
        2. 调用 _dict_to_stream_event
        3. 验证返回 TURN_COMPLETE 类型的 StreamEvent

        如果失败，说明：turn_complete 事件转换逻辑错误
        """
        event_dict = make_opencode_event("turn_complete")
        result = bridge._dict_to_stream_event(event_dict, opencode_config)

        assert result is not None
        assert result.type == AgentEventType.TURN_COMPLETE
        assert result.content["usage"] == {"input_tokens": 10, "output_tokens": 20}

    def test_dict_to_stream_event_unknown_type(self, bridge, opencode_config):
        """
        契约：未知类型返回 None

        验证方式：
        1. 构造未知类型 dict
        2. 调用 _dict_to_stream_event
        3. 验证返回 None

        如果失败，说明：未知类型处理逻辑错误
        """
        event_dict = {"type": "unknown"}
        result = bridge._dict_to_stream_event(event_dict, opencode_config)

        assert result is None
