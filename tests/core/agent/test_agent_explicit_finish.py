"""测试 Agent.run 的显式 finish_agent_call 闭环行为"""

from datetime import datetime

import pytest

from agents_hub.config.types import AgentPlatform, RoleType
from agents_hub.core.agent.base_agent import Agent
from agents_hub.core.communication import AgentCallManager, MessageRouter
from agents_hub.core.context import AgentSessionInfo, GroupChatContext
from agents_hub.core.foundation import (
    AgentMessage,
    AgentResult,
    CallStatus,
    MessageType,
    SessionType,
)
from agents_hub.utils.logger import setup_logging


@pytest.fixture(scope="session", autouse=True)
def setup_test_logging(tmp_path_factory):
    setup_logging(log_dir=tmp_path_factory.mktemp("logs"))


class MockRole:
    def __init__(self, name: str = "worker"):
        self.name = name

    def get_role_config(self):
        class MockRoleConfig:
            def __init__(self, name: str):
                self.name = name
                self.role_type = RoleType.TEAM_MEMBER
                self.platform = AgentPlatform.CLAUDE
                self.work_root = None

        return MockRoleConfig(self.name)


@pytest.fixture
async def group_chat_context(tmp_path):
    context = GroupChatContext(group_chat_id="gc_explicit_finish", project_path=str(tmp_path))
    context.agent_session_id["worker"] = AgentSessionInfo(
        main_session="session_worker",
        token="tok_worker",
    )
    await context.load()
    return context


@pytest.fixture
def agent_call_manager(tmp_path):
    return AgentCallManager(group_chat_id="gc_explicit_finish", project_path=str(tmp_path))


@pytest.fixture
def message_router():
    router = MessageRouter()
    return router


@pytest.fixture
def agent(group_chat_context, agent_call_manager, message_router):
    agent = Agent(
        role=MockRole("worker"),
        group_chat_context=group_chat_context,
        agent_call_manager=agent_call_manager,
        message_router=message_router,
    )
    message_router.register("worker", agent.message_queue)
    return agent


def make_result(text: str = "internal execution text") -> AgentResult:
    return AgentResult(
        text=text,
        session_id="session_worker",
        timestamp=datetime.now().isoformat(),
        agent_name="worker",
        platform=AgentPlatform.CLAUDE,
        role_type=RoleType.TEAM_MEMBER,
    )


@pytest.mark.asyncio
async def test_run_does_not_write_process_result_to_group_chat(agent, agent_call_manager, monkeypatch):
    """契约：_process_message 的普通结果不再通过出口 A 自动写入群聊"""

    async def mock_execute(prompt, role_config, session_id, cwd=None):
        return make_result("this should stay private")

    monkeypatch.setattr("agents_hub.agent_bridge.agent_platform_client.execute", mock_execute)

    call = agent_call_manager.create_call(
        send_from="Leader",
        send_to="worker",
        content="do work",
        message_type=MessageType.NOTIFICATION,
    )
    await agent.message_queue.put(
        AgentMessage(
            call_id=call.call_id,
            send_from="Leader",
            send_to="worker",
            content="do work",
            session_type=SessionType.MAIN,
            message_type=MessageType.NOTIFICATION,
        )
    )
    await agent.message_queue.put(
        AgentMessage(
            call_id="__STOP__",
            send_from="__SYSTEM__",
            send_to="worker",
            content="__STOP__",
            session_type=SessionType.MAIN,
            message_type=MessageType.NOTIFICATION,
        )
    )

    await agent.run()

    assert agent.group_chat_context.group_chat_session.messages == []


@pytest.mark.asyncio
async def test_unfinished_task_sends_system_prompt_to_finish_call(
    agent, agent_call_manager, monkeypatch
):
    """契约：TASK 执行结束但未显式回复时，系统提示 Agent 调用 finish_agent_call"""

    async def mock_execute(prompt, role_config, session_id, cwd=None):
        return make_result("private draft")

    monkeypatch.setattr("agents_hub.agent_bridge.agent_platform_client.execute", mock_execute)

    call = agent_call_manager.create_call(
        send_from="Leader",
        send_to="worker",
        content="do task",
        message_type=MessageType.TASK,
    )
    await agent.message_queue.put(
        AgentMessage(
            call_id=call.call_id,
            send_from="Leader",
            send_to="worker",
            content="do task",
            session_type=SessionType.MAIN,
            message_type=MessageType.TASK,
        )
    )
    await agent.message_queue.put(
        AgentMessage(
            call_id="__STOP__",
            send_from="__SYSTEM__",
            send_to="worker",
            content="__STOP__",
            session_type=SessionType.MAIN,
            message_type=MessageType.NOTIFICATION,
        )
    )

    await agent.run()

    assert call.status == CallStatus.RUNNING
    assert call.has_agent_response is False
    reminder = agent.message_queue.get_nowait()
    assert reminder.call_id == call.call_id
    assert reminder.send_from == "__SYSTEM__"
    assert reminder.send_to == "worker"
    assert "finish_agent_call" in reminder.content
    assert call.call_id in reminder.content


@pytest.mark.asyncio
async def test_finished_task_does_not_send_system_prompt(agent, agent_call_manager, monkeypatch):
    """契约：TASK 已通过 finish_agent_call 闭环时，不再发送系统提示"""

    async def mock_execute(prompt, role_config, session_id, cwd=None):
        call.has_agent_response = True
        call.status = CallStatus.COMPLETED
        return make_result("private draft")

    monkeypatch.setattr("agents_hub.agent_bridge.agent_platform_client.execute", mock_execute)

    call = agent_call_manager.create_call(
        send_from="Leader",
        send_to="worker",
        content="do task",
        message_type=MessageType.TASK,
    )
    await agent.message_queue.put(
        AgentMessage(
            call_id=call.call_id,
            send_from="Leader",
            send_to="worker",
            content="do task",
            session_type=SessionType.MAIN,
            message_type=MessageType.TASK,
        )
    )
    await agent.message_queue.put(
        AgentMessage(
            call_id="__STOP__",
            send_from="__SYSTEM__",
            send_to="worker",
            content="__STOP__",
            session_type=SessionType.MAIN,
            message_type=MessageType.NOTIFICATION,
        )
    )

    await agent.run()

    assert agent.message_queue.empty()


@pytest.mark.asyncio
async def test_failed_finished_task_status_is_not_overwritten(
    agent, agent_call_manager, monkeypatch
):
    """契约：TASK 已显式失败闭环时，_process_message 不应覆盖为 COMPLETED"""

    async def mock_execute(prompt, role_config, session_id, cwd=None):
        call.has_agent_response = True
        call.status = CallStatus.FAILED
        return make_result("private draft")

    monkeypatch.setattr("agents_hub.agent_bridge.agent_platform_client.execute", mock_execute)

    call = agent_call_manager.create_call(
        send_from="Leader",
        send_to="worker",
        content="do task",
        message_type=MessageType.TASK,
    )
    await agent.message_queue.put(
        AgentMessage(
            call_id=call.call_id,
            send_from="Leader",
            send_to="worker",
            content="do task",
            session_type=SessionType.MAIN,
            message_type=MessageType.TASK,
        )
    )
    await agent.message_queue.put(
        AgentMessage(
            call_id="__STOP__",
            send_from="__SYSTEM__",
            send_to="worker",
            content="__STOP__",
            session_type=SessionType.MAIN,
            message_type=MessageType.NOTIFICATION,
        )
    )

    await agent.run()

    assert call.status == CallStatus.FAILED
    assert agent.message_queue.empty()
