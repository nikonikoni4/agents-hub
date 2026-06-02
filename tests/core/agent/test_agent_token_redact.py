"""测试 Agent 出口 A 写群聊时的 token 剥离

验证：
1. 包含 token 的文本被剥离
2. 不包含 token 的文本保持不变
3. 多个 token 都被剥离
4. 出口 A 写群聊时确实调用了 redact_token
"""

import pytest

from agents_hub.core.agent.base_agent import Agent
from agents_hub.core.communication import AgentCallManager, MessageRouter
from agents_hub.core.context import GroupChatContext
from agents_hub.core.foundation import (
    AgentMessage,
    AgentResult,
    MessageType,
    SessionType,
)
from agents_hub.core.foundation.token import generate_token


@pytest.fixture(scope="session", autouse=True)
def setup_logging(tmp_path_factory):
    """初始化日志系统"""
    from agents_hub.utils.logger import setup_logging

    log_dir = tmp_path_factory.mktemp("logs")
    setup_logging(log_dir=log_dir)


class MockRole:
    """Mock Role 用于测试"""

    def get_role_config(self):
        from agents_hub.config.types import AgentPlatform, RoleType

        # 创建一个简单的 RoleConfig mock
        class MockRoleConfig:
            def __init__(self):
                self.name = "test_agent"
                self.role_type = RoleType.TEAM_MEMBER
                self.platform = AgentPlatform.CLAUDE
                self.work_root = None

        return MockRoleConfig()


@pytest.fixture
async def group_chat_context(tmp_path):
    """创建测试用的 GroupChatContext"""
    from agents_hub.core.context import AgentSessionInfo

    context = GroupChatContext(group_chat_id="test_group", project_path=str(tmp_path))
    # 添加 agent session info
    context.agent_session_id["test_agent"] = AgentSessionInfo(
        main_session="test_session", token="tok_test123456789012345678901234"
    )
    # 加载上下文
    await context.load()
    return context


@pytest.fixture
def agent_call_manager(tmp_path):
    """创建测试用的 AgentCallManager"""
    return AgentCallManager(group_chat_id="test_group", project_path=str(tmp_path))


@pytest.fixture
def message_router():
    """创建测试用的 MessageRouter"""
    return MessageRouter()


@pytest.fixture
def agent(group_chat_context, agent_call_manager, message_router):
    """创建测试用的 Agent"""
    role = MockRole()
    return Agent(
        role=role,
        group_chat_context=group_chat_context,
        agent_call_manager=agent_call_manager,
        message_router=message_router,
    )


@pytest.mark.asyncio
async def test_redact_single_token_in_output(agent, agent_call_manager, monkeypatch):
    """测试：包含单个 token 的输出被剥离"""
    from datetime import datetime

    from agents_hub.config.types import AgentPlatform, RoleType

    token = generate_token()
    result_text = f"Here is your token: {token}"

    # Mock execute 返回包含 token 的结果
    async def mock_execute(prompt, role_config, session_id, cwd=None, use_docker=False, group_chat_id=None):
        return AgentResult(
            text=result_text,
            session_id=session_id or "test_session",
            timestamp=datetime.now().isoformat(),
            agent_name="test_agent",
            platform=AgentPlatform.CLAUDE,
            role_type=RoleType.TEAM_MEMBER,
        )

    monkeypatch.setattr("agents_hub.agent_bridge.agent_platform_client.execute", mock_execute)

    # 创建测试消息
    msg = AgentMessage(
        call_id="test_call",
        send_from="user",
        send_to="test_agent",
        content="Give me a token",
        session_type=SessionType.MAIN,
        message_type=MessageType.TASK,
    )

    # 注册 call
    agent_call_manager.create_call(
        send_from="user",
        send_to="test_agent",
        content="Give me a token",
        message_type=MessageType.TASK,
    )

    # 将消息放入队列
    await agent.message_queue.put(msg)

    # 启动 agent（处理一条消息后停止）
    await agent.message_queue.put(
        AgentMessage(
            call_id="__STOP__",
            send_from="__SYSTEM__",
            send_to="test_agent",
            content="__STOP__",
            session_type=SessionType.MAIN,
            message_type=MessageType.NOTIFICATION,
        )
    )

    await agent.run()

    # 验证：群聊消息中 token 被剥离
    messages = agent.group_chat_context.group_chat_session.messages
    assert len(messages) == 1
    assert "[REDACTED]" in messages[0]["content"]
    assert token not in messages[0]["content"]


@pytest.mark.asyncio
async def test_no_token_in_output_unchanged(agent, agent_call_manager, monkeypatch):
    """测试：不包含 token 的输出保持不变"""
    from datetime import datetime

    from agents_hub.config.types import AgentPlatform, RoleType

    result_text = "This is a normal message without any token"

    # Mock execute 返回不包含 token 的结果
    async def mock_execute(prompt, role_config, session_id, cwd=None, use_docker=False, group_chat_id=None):
        return AgentResult(
            text=result_text,
            session_id=session_id or "test_session",
            timestamp=datetime.now().isoformat(),
            agent_name="test_agent",
            platform=AgentPlatform.CLAUDE,
            role_type=RoleType.TEAM_MEMBER,
        )

    monkeypatch.setattr("agents_hub.agent_bridge.agent_platform_client.execute", mock_execute)

    # 创建测试消息
    msg = AgentMessage(
        call_id="test_call",
        send_from="user",
        send_to="test_agent",
        content="Say something",
        session_type=SessionType.MAIN,
        message_type=MessageType.TASK,
    )

    # 注册 call
    agent_call_manager.create_call(
        send_from="user",
        send_to="test_agent",
        content="Say something",
        message_type=MessageType.TASK,
    )

    # 将消息放入队列
    await agent.message_queue.put(msg)

    # 启动 agent（处理一条消息后停止）
    await agent.message_queue.put(
        AgentMessage(
            call_id="__STOP__",
            send_from="__SYSTEM__",
            send_to="test_agent",
            content="__STOP__",
            session_type=SessionType.MAIN,
            message_type=MessageType.NOTIFICATION,
        )
    )

    await agent.run()

    # 验证：群聊消息保持不变
    messages = agent.group_chat_context.group_chat_session.messages
    assert len(messages) == 1
    assert result_text in messages[0]["content"]


@pytest.mark.asyncio
async def test_redact_multiple_tokens_in_output(agent, agent_call_manager, monkeypatch):
    """测试：包含多个 token 的输出都被剥离"""
    from datetime import datetime

    from agents_hub.config.types import AgentPlatform, RoleType

    token1 = generate_token()
    token2 = generate_token()
    result_text = f"Token 1: {token1}, Token 2: {token2}"

    # Mock execute 返回包含多个 token 的结果
    async def mock_execute(prompt, role_config, session_id, cwd=None, use_docker=False, group_chat_id=None):
        return AgentResult(
            text=result_text,
            session_id=session_id or "test_session",
            timestamp=datetime.now().isoformat(),
            agent_name="test_agent",
            platform=AgentPlatform.CLAUDE,
            role_type=RoleType.TEAM_MEMBER,
        )

    monkeypatch.setattr("agents_hub.agent_bridge.agent_platform_client.execute", mock_execute)

    # 创建测试消息
    msg = AgentMessage(
        call_id="test_call",
        send_from="user",
        send_to="test_agent",
        content="Give me tokens",
        session_type=SessionType.MAIN,
        message_type=MessageType.TASK,
    )

    # 注册 call
    agent_call_manager.create_call(
        send_from="user",
        send_to="test_agent",
        content="Give me tokens",
        message_type=MessageType.TASK,
    )

    # 将消息放入队列
    await agent.message_queue.put(msg)

    # 启动 agent（处理一条消息后停止）
    await agent.message_queue.put(
        AgentMessage(
            call_id="__STOP__",
            send_from="__SYSTEM__",
            send_to="test_agent",
            content="__STOP__",
            session_type=SessionType.MAIN,
            message_type=MessageType.NOTIFICATION,
        )
    )

    await agent.run()

    # 验证：群聊消息中所有 token 都被剥离
    messages = agent.group_chat_context.group_chat_session.messages
    assert len(messages) == 1
    assert messages[0]["content"].count("[REDACTED]") == 2
    assert token1 not in messages[0]["content"]
    assert token2 not in messages[0]["content"]


@pytest.mark.asyncio
async def test_redact_token_called_at_exit_a(agent, agent_call_manager, monkeypatch):
    """测试：出口 A 写群聊时确实调用了 redact_token"""
    from datetime import datetime
    from unittest.mock import MagicMock

    from agents_hub.config.types import AgentPlatform, RoleType

    token = generate_token()
    result_text = f"Token: {token}"

    # Mock execute
    async def mock_execute(prompt, role_config, session_id, cwd=None, use_docker=False, group_chat_id=None):
        return AgentResult(
            text=result_text,
            session_id=session_id or "test_session",
            timestamp=datetime.now().isoformat(),
            agent_name="test_agent",
            platform=AgentPlatform.CLAUDE,
            role_type=RoleType.TEAM_MEMBER,
        )

    monkeypatch.setattr("agents_hub.agent_bridge.agent_platform_client.execute", mock_execute)

    # Mock redact_token 来验证它被调用
    original_redact = __import__("agents_hub.core.foundation.token", fromlist=["redact_token"]).redact_token
    mock_redact = MagicMock(side_effect=original_redact)
    monkeypatch.setattr("agents_hub.core.agent.base_agent.redact_token", mock_redact)

    # 创建测试消息
    msg = AgentMessage(
        call_id="test_call",
        send_from="user",
        send_to="test_agent",
        content="Give me a token",
        session_type=SessionType.MAIN,
        message_type=MessageType.TASK,
    )

    # 注册 call
    agent_call_manager.create_call(
        send_from="user",
        send_to="test_agent",
        content="Give me a token",
        message_type=MessageType.TASK,
    )

    # 将消息放入队列
    await agent.message_queue.put(msg)

    # 启动 agent（处理一条消息后停止）
    await agent.message_queue.put(
        AgentMessage(
            call_id="__STOP__",
            send_from="__SYSTEM__",
            send_to="test_agent",
            content="__STOP__",
            session_type=SessionType.MAIN,
            message_type=MessageType.NOTIFICATION,
        )
    )

    await agent.run()

    # 验证：redact_token 被调用
    mock_redact.assert_called_once()
    # 验证：调用时传入的是 result.text
    assert result_text in str(mock_redact.call_args)
