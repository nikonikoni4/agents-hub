import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agents_hub.agent_bridge.models import AgentResult
from agents_hub.config.types import AgentPlatform, RoleType
from agents_hub.core.context.loop_models import Loop, LoopNode, LoopNodeType
from agents_hub.core.foundation import MessageType
from agents_hub.core.foundation.models import LoopStatus
from agents_hub.core.orchestration.loop_executor import LoopExecutor


@pytest.mark.asyncio
async def test_run_sends_first_node_then_advances_until_terminator_completes():
    queue = asyncio.Queue()
    sent_messages = []

    async def send_message(message):
        sent_messages.append(message)
        if message.send_to == "executor":
            await queue.put(
                {
                    "loop_id": "loop-1",
                    "call_id": message.call_id,
                    "agent_result": _make_agent_result(
                        agent_name="executor",
                        text="# 执行结果\n已完成\n**任务状态**：完成",
                    ),
                }
            )
        elif message.send_to == "reviewer":
            await queue.put(
                {
                    "loop_id": "loop-1",
                    "call_id": message.call_id,
                    "agent_result": _make_agent_result(
                        agent_name="reviewer",
                        text=(
                            "# 审查结果\n通过\n"
                            "<loop_decision><should_continue>false</should_continue>"
                            "<reason>通过</reason></loop_decision>"
                        ),
                    ),
                }
            )

    runtime = SimpleNamespace(add_message=AsyncMock())
    agent_call_manager = _FakeAgentCallManager()
    loop = _make_loop(max_iterations=3)
    executor = LoopExecutor(
        loop=loop,
        runtime=runtime,
        completion_queue=queue,
        send_message_callback=send_message,
        agent_call_manager=agent_call_manager,
    )

    await executor.run()

    assert loop.status == LoopStatus.COMPLETED.value
    assert [message.send_to for message in sent_messages] == ["executor", "reviewer"]
    assert all(message.message_type == MessageType.LOOP_MESSAGE for message in sent_messages)
    assert sent_messages[0].metadata["loop_id"] == "loop-1"
    assert sent_messages[0].metadata["loop_iteration"] == 1
    assert "loop_context" not in sent_messages[0].metadata
    assert sent_messages[0].content
    assert len(agent_call_manager.created_calls) == 2
    assert all(
        call.message_type == MessageType.LOOP_MESSAGE
        for call in agent_call_manager.created_calls
    )
    assert runtime.add_message.await_count == 2


@pytest.mark.asyncio
async def test_run_retries_invalid_node_output_then_continues_loop():
    queue = asyncio.Queue()
    sent_messages = []
    executor_attempts = 0

    async def send_message(message):
        nonlocal executor_attempts
        sent_messages.append(message)
        if message.send_to == "executor":
            executor_attempts += 1
            text = (
                "缺少格式字段"
                if executor_attempts == 1
                else "# 执行结果\n已修正\n**任务状态**：完成"
            )
            await queue.put(
                {
                    "loop_id": "loop-1",
                    "call_id": message.call_id,
                    "agent_result": _make_agent_result(
                        agent_name="executor",
                        text=text,
                    ),
                }
            )
        elif message.send_to == "reviewer":
            await queue.put(
                {
                    "loop_id": "loop-1",
                    "call_id": message.call_id,
                    "agent_result": _make_agent_result(
                        agent_name="reviewer",
                        text=(
                            "# 审查结果\n通过\n"
                            "<loop_decision><should_continue>false</should_continue>"
                            "<reason>通过</reason></loop_decision>"
                        ),
                    ),
                }
            )

    runtime = SimpleNamespace(add_message=AsyncMock())
    loop = _make_loop(max_iterations=3)
    executor = LoopExecutor(
        loop=loop,
        runtime=runtime,
        completion_queue=queue,
        send_message_callback=send_message,
    )

    await executor.run()

    assert loop.status == LoopStatus.COMPLETED.value
    assert [message.send_to for message in sent_messages] == [
        "executor",
        "executor",
        "reviewer",
    ]
    retry_message = sent_messages[1]
    assert retry_message.call_id == sent_messages[0].call_id
    assert retry_message.metadata["loop_retry_count"] == 1
    assert "缺少以下必需字段" in retry_message.content
    assert runtime.add_message.await_count == 2


@pytest.mark.asyncio
async def test_run_cycles_nodes_and_fails_when_max_iterations_is_exceeded():
    queue = asyncio.Queue()
    sent_messages = []

    async def send_message(message):
        sent_messages.append(message)
        if message.send_to == "executor":
            await queue.put(
                {
                    "loop_id": "loop-1",
                    "call_id": message.call_id,
                    "agent_result": _make_agent_result(
                        agent_name="executor",
                        text="# 执行结果\n仍需审查\n**任务状态**：完成",
                    ),
                }
            )
        elif message.send_to == "reviewer":
            await queue.put(
                {
                    "loop_id": "loop-1",
                    "call_id": message.call_id,
                    "agent_result": _make_agent_result(
                        agent_name="reviewer",
                        text=(
                            "# 审查结果\n继续\n"
                            "<loop_decision><should_continue>true</should_continue>"
                            "<reason>继续完善</reason></loop_decision>"
                        ),
                    ),
                }
            )

    loop = _make_loop(max_iterations=1)
    executor = LoopExecutor(
        loop=loop,
        runtime=SimpleNamespace(add_message=AsyncMock()),
        completion_queue=queue,
        send_message_callback=send_message,
        agent_call_manager=_FakeAgentCallManager(),
    )

    await executor.run()

    assert loop.status == LoopStatus.FAILED.value
    assert loop.error_message == "达到最大循环次数"
    assert loop.current_iteration == 2
    assert [message.send_to for message in sent_messages] == ["executor", "reviewer"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("agent_status", "expected_error"),
    [
        ("error", "Agent CLI 执行失败"),
        ("busy", "节点执行超时"),
    ],
)
async def test_run_times_out_with_reason_from_current_agent_status(
    agent_status,
    expected_error,
):
    async def send_message(_message):
        return None

    loop = _make_loop(max_iterations=3)
    runtime = _FakeRuntime(agent_status=agent_status)
    executor = LoopExecutor(
        loop=loop,
        runtime=runtime,
        completion_queue=asyncio.Queue(),
        send_message_callback=send_message,
        agent_call_manager=_FakeAgentCallManager(),
    )
    executor.receive_node_completion = AsyncMock(side_effect=TimeoutError)

    await executor.run()

    assert loop.status == LoopStatus.FAILED.value
    assert loop.error_message == expected_error
    assert runtime.member_infos["executor"].status == "idle"
    assert runtime.save_agent_members.await_count == 1


@pytest.mark.asyncio
async def test_cleanup_restores_agent_state_clears_queue_reference_and_persists_status():
    runtime = _FakeRuntime(agent_status="in_loop")
    loop_manager = SimpleNamespace(update_loop_status=AsyncMock())
    agents = {
        "executor": SimpleNamespace(set_loop_completion_queue=AsyncMock()),
        "reviewer": SimpleNamespace(set_loop_completion_queue=AsyncMock()),
    }
    loop = _make_loop(max_iterations=3)
    loop.status = LoopStatus.COMPLETED.value
    executor = LoopExecutor(
        loop=loop,
        runtime=runtime,
        loop_manager=loop_manager,
        agents=agents,
    )

    await executor._cleanup()

    assert runtime.member_infos["executor"].status == "idle"
    assert runtime.member_infos["executor"].current_loop_id is None
    assert runtime.member_infos["reviewer"].status == "idle"
    assert runtime.member_infos["reviewer"].current_loop_id is None
    agents["executor"].set_loop_completion_queue.assert_awaited_once_with(None)
    agents["reviewer"].set_loop_completion_queue.assert_awaited_once_with(None)
    loop_manager.update_loop_status.assert_awaited_once_with(
        "loop-1",
        LoopStatus.COMPLETED.value,
        current_iteration=1,
        current_node_index=0,
        error_message=None,
    )


class _FakeAgentCallManager:
    def __init__(self):
        self.created_calls = []

    async def create_call(self, send_from, send_to, content, message_type, timeout_seconds=None):
        call = SimpleNamespace(
            call_id=f"call-{len(self.created_calls) + 1}",
            send_from=send_from,
            send_to=send_to,
            content=content,
            message_type=message_type,
            timeout_seconds=timeout_seconds,
        )
        self.created_calls.append(call)
        return call

    async def update_status(self, call_id, status):
        return None


class _FakeRuntime:
    def __init__(self, agent_status: str = "idle"):
        self.add_message = AsyncMock()
        self.save_agent_members = AsyncMock()
        self.member_infos = {
            "executor": SimpleNamespace(status=agent_status, current_loop_id="loop-1"),
            "reviewer": SimpleNamespace(status="busy", current_loop_id="loop-1"),
        }

    def get_agent_member_info(self, agent_name):
        return self.member_infos.get(agent_name)


def _make_loop(max_iterations: int) -> Loop:
    now = datetime.now()
    return Loop(
        loop_id="loop-1",
        group_chat_id="group-1",
        nodes=[
            LoopNode(
                node_id="node-executor",
                node_type=LoopNodeType.NORMAL.value,
                agent_name="executor",
                role_description="执行任务",
                output_schema_fields=["# 执行结果", "**任务状态**"],
            ),
            LoopNode(
                node_id="node-reviewer",
                node_type=LoopNodeType.TERMINATOR.value,
                agent_name="reviewer",
                role_description="审查结果",
                output_schema_fields=["# 审查结果"],
            ),
        ],
        status=LoopStatus.RUNNING.value,
        max_iterations=max_iterations,
        current_iteration=1,
        current_node_index=0,
        initial_task="请实现功能",
        created_at=now,
        updated_at=now,
    )


def _make_agent_result(agent_name: str, text: str) -> AgentResult:
    return AgentResult(
        text=text,
        session_id=f"session-{agent_name}",
        timestamp="2026-06-20T00:00:00",
        agent_name=agent_name,
        platform=AgentPlatform.CLAUDE,
        role_type=RoleType.TEAM_MEMBER,
    )
