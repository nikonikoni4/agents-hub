"""测试公开群聊写入路径的 token 剥离

Agent.run() 的普通执行文本默认私下保留，不再自动写入群聊。
token 剥离应发生在显式公开工具 speak_in_group_chat / finish_agent_call 中。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_hub.config.types import AgentPlatform, RoleType
from agents_hub.core.foundation import CallStatus, MessageType
from agents_hub.core.foundation.token import generate_token


<<<<<<< HEAD
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
    from agents_hub.core.context import AgentMemberInfo
    from agents_hub.core.context.group_chat_repository import GroupChatRepository
    from agents_hub.core.context.group_chat_runtime import GroupChatRuntime

    repository = GroupChatRepository("test_group", str(tmp_path))
    runtime = GroupChatRuntime("test_group", str(tmp_path), repository=repository)
    await runtime.load()
    context = GroupChatContext(runtime)

    # 添加 agent session info
    context.agent_member_info["test_agent"] = AgentMemberInfo(
        main_session="test_session", token="tok_test123456789012345678901234"
    )
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


=======
>>>>>>> 40ec740 (feat(mcp): 新增显式群聊发言和任务闭环工具)
@pytest.mark.asyncio
async def test_speak_in_group_chat_redacts_token():
    """契约：speak_in_group_chat 写群聊前剥离 token"""
    from agents_hub.mcp.server import speak_in_group_chat

    token = generate_token()
    group_chat = MagicMock()
    group_chat.group_chat_context.add_message = AsyncMock()

<<<<<<< HEAD
    # Mock execute 返回包含 token 的结果
    async def mock_execute(prompt, role_config, session_id, cwd=None, use_docker=False, group_chat_id=None):
        return AgentResult(
            text=result_text,
            session_id=session_id or "test_session",
            timestamp=datetime.now().isoformat(),
            agent_name="test_agent",
            platform=AgentPlatform.CLAUDE,
            role_type=RoleType.TEAM_MEMBER,
=======
    with patch("agents_hub.mcp.server.group_chat_manager") as manager:
        manager.resolve_token.return_value = ("worker", "group_1")
        manager.get_group_chat.return_value = group_chat

        result = await speak_in_group_chat(
            agent_token="agent_token",
            content=f"公开内容包含 {token}",
            send_to="Leader",
>>>>>>> 40ec740 (feat(mcp): 新增显式群聊发言和任务闭环工具)
        )

    assert result == {"ok": True}
    group_chat.group_chat_context.add_message.assert_called_once()
    agent_result = group_chat.group_chat_context.add_message.call_args.args[0]
    assert "[REDACTED]" in agent_result.text
    assert token not in agent_result.text
    assert agent_result.text.startswith("@Leader ")


@pytest.mark.asyncio
<<<<<<< HEAD
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
=======
async def test_finish_agent_call_redacts_token_before_result_and_group_chat():
    """契约：finish_agent_call 写 call result 和群聊前都剥离 token"""
    from agents_hub.mcp.server import finish_agent_call
>>>>>>> 40ec740 (feat(mcp): 新增显式群聊发言和任务闭环工具)

    token = generate_token()
    group_chat = MagicMock()
    group_chat.group_chat_context.add_message = AsyncMock()
    call = MagicMock()
    call.call_id = "call_1"
    call.send_from = "Leader"
    call.send_to = "worker"
    call.message_type = MessageType.TASK
    call.has_agent_response = False
    group_chat.agent_call_manager.get_call.return_value = call

<<<<<<< HEAD
    # Mock execute
    async def mock_execute(prompt, role_config, session_id, cwd=None, use_docker=False, group_chat_id=None):
        return AgentResult(
            text=result_text,
            session_id=session_id or "test_session",
            timestamp=datetime.now().isoformat(),
            agent_name="test_agent",
            platform=AgentPlatform.CLAUDE,
            role_type=RoleType.TEAM_MEMBER,
=======
    with patch("agents_hub.mcp.server.group_chat_manager") as manager:
        manager.resolve_token.return_value = ("worker", "group_1")
        manager.get_group_chat.return_value = group_chat

        result = await finish_agent_call(
            agent_token="agent_token",
            call_id="call_1",
            content=f"任务完成，token={token}",
            success=True,
>>>>>>> 40ec740 (feat(mcp): 新增显式群聊发言和任务闭环工具)
        )

    assert result == {"call_id": "call_1", "status": CallStatus.COMPLETED.value}
    group_chat.agent_call_manager.mark_agent_response.assert_called_once_with(
        call_id="call_1",
        content="任务完成，token=[REDACTED]",
        success=True,
    )
    group_chat.group_chat_context.add_message.assert_called_once()
    agent_result = group_chat.group_chat_context.add_message.call_args.args[0]
    assert "[REDACTED]" in agent_result.text
    assert token not in agent_result.text
    assert agent_result.text.startswith("@Leader ")


@pytest.mark.asyncio
async def test_speak_in_group_chat_uses_agent_metadata():
    """契约：群聊消息沿用发言 Agent 的平台和角色元数据"""
    from agents_hub.mcp.server import speak_in_group_chat

    group_chat = MagicMock()
    group_chat.group_chat_context.add_message = AsyncMock()
    worker = MagicMock()
    worker.name = "worker"
    worker.role_type = RoleType.LEADER
    worker.role_config.platform = AgentPlatform.CODEX
    group_chat.manager = None
    group_chat.workers = {"worker": worker}

    with patch("agents_hub.mcp.server.group_chat_manager") as manager:
        manager.resolve_token.return_value = ("worker", "group_1")
        manager.get_group_chat.return_value = group_chat

        result = await speak_in_group_chat(
            agent_token="agent_token",
            content="公开内容",
        )

    assert result == {"ok": True}
    agent_result = group_chat.group_chat_context.add_message.call_args.args[0]
    assert agent_result.platform == AgentPlatform.CODEX
    assert agent_result.role_type == RoleType.LEADER
