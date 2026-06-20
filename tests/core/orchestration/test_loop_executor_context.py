import pytest

from agents_hub.agent_bridge.models import AgentResult
from agents_hub.config.types import AgentPlatform, RoleType
from agents_hub.core.context.loop_models import Loop, LoopNode, LoopNodeType
from agents_hub.core.foundation import (
    AgentMessage,
    GroupChatType,
    MessageType,
    SessionType,
)
from agents_hub.core.foundation.renderer import Tag
from agents_hub.core.orchestration.group_chat import GroupChat
from agents_hub.core.orchestration.loop_executor import (
    LoopExecutor,
    notify_loop_completion,
)


def test_build_loop_context_for_normal_node_contains_role_schema_and_previous_output():
    node = LoopNode(
        node_type=LoopNodeType.NORMAL.value,
        agent_name="worker",
        role_description="整理输入并产出摘要",
        output_schema_prompt="请输出 Markdown 摘要",
    )
    executor = LoopExecutor(loop=_make_loop([node]))

    context = executor._build_loop_context(node, previous_output="上一节点结果")

    assert f"<{Tag.LOOP_NODE_ROLE}>" in context
    assert "整理输入并产出摘要" in context
    assert f"<{Tag.LOOP_OUTPUT_SCHEMA}>" in context
    assert "请输出 Markdown 摘要" in context
    assert f"<{Tag.PREVIOUS_NODE_OUTPUT}>" in context
    assert "上一节点结果" in context
    assert f"<{Tag.LOOP_TERMINATION_CHECK}>" not in context


def test_build_loop_context_for_terminator_node_includes_termination_check():
    node = LoopNode(
        node_type=LoopNodeType.TERMINATOR.value,
        agent_name="reviewer",
        role_description="判断结果是否需要继续迭代",
        output_schema_prompt="请输出 should_continue",
    )
    executor = LoopExecutor(loop=_make_loop([node]))

    context = executor._build_loop_context(node, previous_output="待判断结果")

    assert f"<{Tag.LOOP_TERMINATION_CHECK}>" in context
    assert "should_continue" in context


def test_build_loop_message_uses_loop_message_type_and_metadata():
    node = LoopNode(
        node_type=LoopNodeType.NORMAL.value,
        agent_name="worker",
        role_description="执行节点任务",
    )
    loop = _make_loop([node], loop_id="loop-abc", current_iteration=2)
    executor = LoopExecutor(loop=loop)

    message = executor._build_loop_message(node, previous_output="input")

    assert message.message_type.value == "loop_message"
    assert message.send_from == "loop"
    assert message.send_to == "worker"
    assert message.metadata["loop_id"] == "loop-abc"
    assert message.metadata["loop_iteration"] == 2
    assert "loop_context" not in message.metadata
    assert message.content


@pytest.mark.asyncio
async def test_save_loop_result_uses_loop_chat_format():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    node = LoopNode(
        node_type=LoopNodeType.NORMAL.value,
        agent_name="worker",
        role_description="执行节点任务",
    )
    runtime = SimpleNamespace(add_message=AsyncMock())
    executor = LoopExecutor(
        loop=_make_loop([node], current_iteration=2), runtime=runtime
    )
    result = SimpleNamespace(text="节点输出")

    await executor._save_loop_result(node, result)

    assert result.text == "[循环-节点worker-第2轮] @loop 节点输出"
    runtime.add_message.assert_awaited_once_with(result)


@pytest.mark.asyncio
async def test_notify_loop_completion_puts_loop_result_on_queue():
    queue = __import__("asyncio").Queue()
    msg = _make_loop_message(metadata={"loop_id": "loop-1"})
    result = _make_agent_result()

    await notify_loop_completion(queue, msg, result)

    notification = queue.get_nowait()
    assert notification["loop_id"] == "loop-1"
    assert notification["agent_result"] is result
    assert notification["call_id"] == "call-1"


@pytest.mark.asyncio
async def test_notify_loop_completion_ignores_none_result():
    queue = __import__("asyncio").Queue()
    msg = _make_loop_message(metadata={"loop_id": "loop-1"})

    await notify_loop_completion(queue, msg, None)

    assert queue.empty()


@pytest.mark.asyncio
async def test_notify_loop_completion_ignores_missing_queue():
    msg = _make_loop_message(metadata={"loop_id": "loop-1"})

    await notify_loop_completion(None, msg, _make_agent_result())


@pytest.mark.asyncio
async def test_notify_loop_completion_ignores_missing_loop_id():
    queue = __import__("asyncio").Queue()
    msg = _make_loop_message(metadata={})

    await notify_loop_completion(queue, msg, _make_agent_result())

    assert queue.empty()


@pytest.mark.asyncio
async def test_group_chat_registers_loop_completion_handler_on_agents(monkeypatch):
    created_agents = []

    class FakeRole:
        def __init__(self, name):
            self.name = name

        def get_role_config(self):
            return type(
                "RoleConfig", (), {"name": self.name, "role_type": RoleType.TEAM_MEMBER}
            )()

    class FakeRoleManager:
        def get_role(self, name):
            return FakeRole(name)

    class FakeAgent:
        def __init__(self, role, *args):
            self.name = role.name
            self.message_queue = __import__("asyncio").Queue()
            self.handlers = []
            created_agents.append(self)

        def add_message_completion_handler(self, handler):
            self.handlers.append(handler)

    class FakeRuntime:
        def __init__(self, group_chat_id, project_path, on_change=None):
            self.group_chat_id = group_chat_id
            self.project_path = project_path

    class FakeManager:
        def __init__(self, *args):
            pass

    monkeypatch.setattr(
        "agents_hub.core.orchestration.group_chat.RoleManager", FakeRoleManager
    )
    monkeypatch.setattr("agents_hub.core.orchestration.group_chat.Manager", FakeAgent)
    monkeypatch.setattr("agents_hub.core.orchestration.group_chat.Worker", FakeAgent)
    monkeypatch.setattr(
        "agents_hub.core.orchestration.group_chat.GroupChatRuntime", FakeRuntime
    )
    monkeypatch.setattr(
        "agents_hub.core.orchestration.group_chat.AgentCallManager", FakeManager
    )
    monkeypatch.setattr(
        "agents_hub.core.orchestration.group_chat.TaskManager", FakeManager
    )

    group_chat = GroupChat(
        team_members_name=["worker"],
        group_type=GroupChatType.SEQUENCE_EXECUTE,
        project_path="D:/tmp/agents-hub-loop-test",
        group_chat_id="group-1",
    )

    await group_chat._init_agents()

    assert created_agents
    assert all(len(agent.handlers) == 1 for agent in created_agents)


def _make_loop(
    nodes: list[LoopNode],
    loop_id: str = "loop-1",
    current_iteration: int = 1,
) -> Loop:
    from datetime import datetime

    now = datetime.now()
    return Loop(
        loop_id=loop_id,
        group_chat_id="group-1",
        nodes=nodes,
        status="created",
        max_iterations=3,
        current_iteration=current_iteration,
        current_node_index=0,
        initial_task="初始任务",
        created_at=now,
        updated_at=now,
    )


def _make_loop_message(metadata: dict) -> AgentMessage:
    return AgentMessage(
        call_id="call-1",
        send_from="loop",
        send_to="worker",
        content="loop context",
        session_type=SessionType.MAIN,
        message_type=MessageType.LOOP_MESSAGE,
        metadata=metadata,
    )


def _make_agent_result() -> AgentResult:
    return AgentResult(
        text="done",
        session_id="session-1",
        timestamp="2026-06-20T00:00:00",
        agent_name="worker",
        platform=AgentPlatform.CLAUDE,
        role_type=RoleType.TEAM_MEMBER,
    )
