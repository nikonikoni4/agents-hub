"""
AgentBridge Docker 集成测试

契约：
1. __init__() 创建 DockerManager 和 Docker executors
2. execute() 当 use_docker=True 时使用 Docker executor
3. execute() 当 use_docker=False 时使用本地 executor（原有行为）
4. Agent.execute() 传递 use_docker 和 group_chat_id 到 bridge
5. Agent._process_message() 读取 use_docker 配置并传递
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_hub.agent_bridge.bridge import AgentBridge
from agents_hub.agent_bridge.docker.manager import DockerManager
from agents_hub.agent_bridge.executors.docker_claude import DockerClaudeExecutor
from agents_hub.agent_bridge.executors.docker_codex import DockerCodexExecutor
from agents_hub.agent_bridge.models import AgentEventType, StreamEvent
from agents_hub.config.types import AgentPlatform


class TestAgentBridgeDockerInit:
    """测试 AgentBridge.__init__() 中 Docker 相关初始化"""

    def test_creates_docker_manager(self):
        """契约 1：__init__() 创建 DockerManager"""
        bridge = AgentBridge()
        assert hasattr(bridge, '_docker_manager')
        assert isinstance(bridge._docker_manager, DockerManager)

    def test_creates_docker_executors(self):
        """契约 1：__init__() 创建 Docker executors"""
        bridge = AgentBridge()
        assert hasattr(bridge, '_docker_executors')
        assert AgentPlatform.CLAUDE in bridge._docker_executors
        assert AgentPlatform.CODEX in bridge._docker_executors
        assert isinstance(bridge._docker_executors[AgentPlatform.CLAUDE], DockerClaudeExecutor)
        assert isinstance(bridge._docker_executors[AgentPlatform.CODEX], DockerCodexExecutor)

    def test_docker_executors_share_same_manager(self):
        """契约 1：所有 Docker executors 共享同一个 DockerManager"""
        bridge = AgentBridge()
        claude_executor = bridge._docker_executors[AgentPlatform.CLAUDE]
        codex_executor = bridge._docker_executors[AgentPlatform.CODEX]
        assert claude_executor._docker_manager is codex_executor._docker_manager
        assert claude_executor._docker_manager is bridge._docker_manager


class TestAgentBridgeExecuteDocker:
    """测试 AgentBridge.execute() 中 Docker 模式"""

    @pytest.mark.asyncio
    async def test_execute_uses_docker_executor_when_use_docker_true(self):
        """契约 2：use_docker=True 时使用 Docker executor"""
        bridge = AgentBridge()

        # Track calls to mock docker executor
        docker_execute_called = []

        # Mock Docker executor - use a callable class that returns an async generator
        class MockDockerExecutor:
            async def execute(self, prompt, config, session_id, cwd, group_chat_id):
                docker_execute_called.append(True)
                yield '{"type":"system","subtype":"init","session_id":"docker_123"}'
                yield '{"type":"assistant","subtype":"text_delta","content":{"text":"docker response"},"session_id":"docker_123"}'
                yield '{"type":"assistant","subtype":"turn_complete","content":{},"session_id":"docker_123"}'

        mock_docker_executor = MockDockerExecutor()
        bridge._docker_executors[AgentPlatform.CLAUDE] = mock_docker_executor

        # Mock parser - return appropriate StreamEvent based on input line
        def mock_parse(line):
            import json
            data = json.loads(line)
            subtype = data.get("subtype", "")
            if subtype == "text_delta":
                return StreamEvent(
                    type=AgentEventType.TEXT_DELTA,
                    content={"text": data["content"]["text"]},
                    session_id=data.get("session_id", "docker_123"),
                    timestamp="",
                    agent_name="test-agent",
                    platform=AgentPlatform.CLAUDE,
                    role_type=SimpleNamespace(value="team_member"),
                )
            elif subtype == "turn_complete":
                return StreamEvent(
                    type=AgentEventType.TURN_COMPLETE,
                    content=data.get("content", {}),
                    session_id=data.get("session_id", "docker_123"),
                    timestamp="",
                    agent_name="test-agent",
                    platform=AgentPlatform.CLAUDE,
                    role_type=SimpleNamespace(value="team_member"),
                )
            return None  # INIT events are skipped

        mock_parser = MagicMock()
        mock_parser.parse_event.side_effect = mock_parse
        bridge._parsers[AgentPlatform.CLAUDE] = mock_parser

        config = SimpleNamespace(
            name="test-agent",
            platform=AgentPlatform.CLAUDE,
            role_type=SimpleNamespace(value="team_member"),
        )

        result = await bridge.execute(
            "test prompt",
            config,
            session_id="old_session",
            cwd="/tmp/workspace",
            use_docker=True,
            group_chat_id="gc_test",
        )

        # 验证使用了 Docker executor
        assert result.text == "docker response"
        assert len(docker_execute_called) == 1

    @pytest.mark.asyncio
    async def test_execute_uses_local_executor_when_use_docker_false(self):
        """契约 3：use_docker=False 时使用本地 executor（原有行为）"""
        bridge = AgentBridge()

        # Mock execute_stream（本地 executor 的入口）
        async def mock_execute_stream(prompt, config, session_id=None, cwd=None):
            yield StreamEvent(
                type=AgentEventType.TEXT_DELTA,
                content={"text": "local response"},
                session_id="local_123",
                timestamp="",
                agent_name="test-agent",
                platform=AgentPlatform.CLAUDE,
                role_type=SimpleNamespace(value="team_member"),
            )
            yield StreamEvent(
                type=AgentEventType.TURN_COMPLETE,
                content={},
                session_id="local_123",
                timestamp="",
                agent_name="test-agent",
                platform=AgentPlatform.CLAUDE,
                role_type=SimpleNamespace(value="team_member"),
            )

        bridge.execute_stream = mock_execute_stream

        config = SimpleNamespace(
            name="test-agent",
            platform=AgentPlatform.CLAUDE,
            role_type=SimpleNamespace(value="team_member"),
        )

        result = await bridge.execute(
            "test prompt",
            config,
            session_id="old_session",
            cwd="/tmp/workspace",
            use_docker=False,
        )

        assert result.text == "local response"


class TestAgentExecuteDocker:
    """测试 Agent.execute() 中 Docker 参数传递"""

    @pytest.mark.asyncio
    async def test_execute_passes_use_docker_to_bridge(self):
        """契约 4：Agent.execute() 传递 use_docker 和 group_chat_id"""
        from agents_hub.core.agent.base_agent import Agent

        role = MagicMock()
        role.get_role_config.return_value = SimpleNamespace(
            name="test_agent",
            role_type=SimpleNamespace(value="team_member"),
            platform=SimpleNamespace(value="claude"),
            description="test agent",
        )

        group_chat_context = MagicMock()
        group_chat_context.agent_session_id = {
            "test_agent": SimpleNamespace(
                main_session="session_1",
                btw_session=[],
                token="test_token",
                cwd="/tmp/workspace",
                use_docker=True,
            )
        }
        group_chat_context.group_chat_id = "gc_test_123"

        agent = Agent(
            role,
            group_chat_context,
            MagicMock(),
            MagicMock(),
        )

        # Mock agent_platform_client.execute
        with patch('agents_hub.core.agent.base_agent.agent_platform_client') as mock_client:
            mock_client.execute = AsyncMock(return_value=SimpleNamespace(
                text="response",
                session_id="s1",
                timestamp="t",
                agent_name="test_agent",
                platform=SimpleNamespace(value="claude"),
                role_type=SimpleNamespace(value="team_member"),
                usage=None,
            ))

            await agent.execute("test prompt", use_docker=True, group_chat_id="gc_test_123")

            # 验证参数传递
            call_kwargs = mock_client.execute.call_args
            assert call_kwargs[1]['use_docker'] is True
            assert call_kwargs[1]['group_chat_id'] == "gc_test_123"


class TestAgentProcessMessageDocker:
    """测试 Agent._process_message() 中 Docker 配置读取和传递"""

    @pytest.mark.asyncio
    async def test_process_message_reads_use_docker(self):
        """契约 5：_process_message 读取 use_docker 配置并传递给 execute"""
        from agents_hub.core.agent.base_agent import Agent
        from agents_hub.core.foundation import AgentMessage, MessageType, SessionType
        from agents_hub.agent_bridge.models import AgentResult

        role = MagicMock()
        role.get_role_config.return_value = SimpleNamespace(
            name="test_agent",
            role_type=SimpleNamespace(value="team_member"),
            platform=SimpleNamespace(value="claude"),
            description="test agent",
        )

        group_chat_context = MagicMock()
        group_chat_context.agent_session_id = {
            "test_agent": SimpleNamespace(
                main_session="session_1",
                btw_session=[],
                token="test_token",
                cwd="/tmp/workspace",
                use_docker=True,
            )
        }
        group_chat_context.group_chat_id = "gc_test_123"

        agent = Agent(
            role,
            group_chat_context,
            MagicMock(),
            MagicMock(),
        )

        # Mock execute 方法
        mock_result = AgentResult(
            text="response",
            session_id="s1",
            timestamp="t",
            agent_name="test_agent",
            platform=SimpleNamespace(value="claude"),
            role_type=SimpleNamespace(value="team_member"),
            usage=None,
        )
        with patch.object(agent, 'execute', new_callable=AsyncMock, return_value=mock_result) as mock_execute:
            with patch.object(agent.agent_context, 'get_context', new_callable=AsyncMock, return_value=None):
                msg = AgentMessage(
                    call_id="call_1",
                    send_from="user",
                    send_to="test_agent",
                    content="hello",
                    session_type=SessionType.MAIN,
                    message_type=MessageType.NOTIFICATION,
                )

                await agent._process_message(msg, "hello")

                # 验证 execute 被调用时传递了 use_docker 和 group_chat_id
                mock_execute.assert_called_once()
                call_kwargs = mock_execute.call_args
                assert call_kwargs[1]['use_docker'] is True
                assert call_kwargs[1]['group_chat_id'] == "gc_test_123"

    @pytest.mark.asyncio
    async def test_process_message_no_session_info(self):
        """契约 5：无 session_info 时 use_docker 默认为 False"""
        from agents_hub.core.agent.base_agent import Agent
        from agents_hub.core.foundation import AgentMessage, MessageType, SessionType
        from agents_hub.agent_bridge.models import AgentResult

        role = MagicMock()
        role.get_role_config.return_value = SimpleNamespace(
            name="test_agent",
            role_type=SimpleNamespace(value="team_member"),
            platform=SimpleNamespace(value="claude"),
            description="test agent",
        )

        group_chat_context = MagicMock()
        group_chat_context.agent_session_id = {}  # 空字典
        group_chat_context.group_chat_id = "gc_test_123"

        agent = Agent(
            role,
            group_chat_context,
            MagicMock(),
            MagicMock(),
        )

        mock_result = AgentResult(
            text="response",
            session_id="s1",
            timestamp="t",
            agent_name="test_agent",
            platform=SimpleNamespace(value="claude"),
            role_type=SimpleNamespace(value="team_member"),
            usage=None,
        )
        with patch.object(agent, 'execute', new_callable=AsyncMock, return_value=mock_result) as mock_execute:
            with patch.object(agent.agent_context, 'get_context', new_callable=AsyncMock, return_value=None):
                msg = AgentMessage(
                    call_id="call_1",
                    send_from="user",
                    send_to="test_agent",
                    content="hello",
                    session_type=SessionType.MAIN,
                    message_type=MessageType.NOTIFICATION,
                )

                await agent._process_message(msg, "hello")

                # 验证 use_docker 默认为 False
                mock_execute.assert_called_once()
                call_kwargs = mock_execute.call_args
                assert call_kwargs[1]['use_docker'] is False
                assert call_kwargs[1]['group_chat_id'] == "gc_test_123"
