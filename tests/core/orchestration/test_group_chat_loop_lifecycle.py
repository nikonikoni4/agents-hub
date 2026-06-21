import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agents_hub.agent_bridge.models import AgentResult
from agents_hub.config.types import AgentPlatform, RoleType
from agents_hub.core.communication import MessageRouter
from agents_hub.core.foundation import AgentMessage, MessageType, SessionType
from agents_hub.core.context.loop_models import Loop, LoopNode, LoopNodeType
from agents_hub.core.foundation.models import LoopStatus
from agents_hub.core.orchestration.group_chat import GroupChat


@pytest.mark.asyncio
async def test_create_and_start_loop_sets_agents_in_loop_and_starts_executor():
    group_chat = _make_group_chat()
    loop = _make_loop(status=LoopStatus.CREATED.value)
    group_chat.loop_manager.loops[loop.loop_id] = loop

    started_loop = await group_chat.create_and_start_loop(loop.loop_id)

    assert started_loop.status == LoopStatus.RUNNING.value
    assert loop.loop_id in group_chat.active_loops
    assert loop.loop_id in group_chat._loop_tasks
    assert loop.loop_id in group_chat._loop_queues
    assert group_chat.runtime.member_infos["executor"].status == "in_loop"
    assert group_chat.runtime.member_infos["executor"].current_loop_id == loop.loop_id
    assert group_chat.runtime.member_infos["reviewer"].status == "in_loop"
    assert group_chat.agents["executor"].loop_completion_queue is group_chat._loop_queues[loop.loop_id]
    assert group_chat.agents["reviewer"].loop_completion_queue is group_chat._loop_queues[loop.loop_id]

    await group_chat.cleanup_loop(loop.loop_id)


@pytest.mark.asyncio
async def test_stop_loop_sends_termination_signal_restarts_agents_and_pauses_loop():
    group_chat = _make_group_chat()
    loop = _make_loop(status=LoopStatus.RUNNING.value)
    group_chat.loop_manager.loops[loop.loop_id] = loop
    queue = asyncio.Queue()
    group_chat._loop_queues[loop.loop_id] = queue
    group_chat.active_loops[loop.loop_id] = SimpleNamespace()
    group_chat._loop_tasks[loop.loop_id] = asyncio.create_task(asyncio.sleep(60))
    for name in ("executor", "reviewer"):
        info = group_chat.runtime.member_infos[name]
        info.status = "in_loop"
        info.current_loop_id = loop.loop_id

    stopped_loop = await group_chat.stop_loop(loop.loop_id)

    signal = await queue.get()
    assert signal == {"loop_id": loop.loop_id, "is_termination_signal": True}
    assert stopped_loop.status == LoopStatus.PAUSED.value
    assert loop.loop_id not in group_chat.active_loops
    assert loop.loop_id not in group_chat._loop_queues
    assert loop.loop_id not in group_chat._loop_tasks
    assert group_chat.stopped_members == ["executor", "reviewer"]
    assert group_chat.started_members == ["executor", "reviewer"]
    assert group_chat.runtime.member_infos["executor"].status == "idle"
    assert group_chat.runtime.member_infos["executor"].current_loop_id is None
    assert group_chat.agents["executor"].loop_completion_queue is None


@pytest.mark.asyncio
async def test_loop_lifecycle_auto_completes_through_group_chat_callbacks():
    group_chat = _make_group_chat()
    loop = _make_loop(status=LoopStatus.CREATED.value)
    group_chat.loop_manager.loops[loop.loop_id] = loop

    async def send_message_to_agent(message):
        assert message.message_type == MessageType.LOOP_MESSAGE
        queue = group_chat._loop_queues[loop.loop_id]
        if message.send_to == "executor":
            text = "# 执行结果\n已完成\n**任务状态**：完成"
        else:
            text = (
                "# 审查结果\n通过\n"
                "<loop_decision><should_continue>false</should_continue>"
                "<reason>通过</reason></loop_decision>"
            )
        await queue.put(
            {
                "loop_id": loop.loop_id,
                "call_id": message.call_id,
                "agent_result": _make_agent_result(message.send_to, text),
            }
        )

    group_chat.send_message_to_agent = send_message_to_agent

    await group_chat.create_and_start_loop(loop.loop_id)
    await asyncio.wait_for(group_chat._loop_tasks[loop.loop_id], timeout=1)

    assert group_chat.get_loop_status(loop.loop_id)["status"] == LoopStatus.COMPLETED.value
    assert group_chat.runtime.add_message.await_count == 2
    assert loop.loop_id not in group_chat.active_loops
    assert loop.loop_id not in group_chat._loop_queues


@pytest.mark.asyncio
async def test_loop_system_sender_can_deliver_loop_message_through_group_chat_router():
    group_chat = _make_group_chat()
    group_chat.message_router = MessageRouter()

    group_chat._register_agents_to_router()

    await group_chat.message_router.send_message(
        AgentMessage(
            call_id="loop-call-1",
            content="循环节点任务",
            send_from="executor",
            send_to="executor",
            session_type=SessionType.MAIN,
            message_type=MessageType.LOOP_MESSAGE,
            metadata={"loop_id": "loop-1"},
        )
    )

    received = group_chat.agents["executor"].message_queue.get_nowait()
    assert received.call_id == "loop-call-1"
    assert received.send_from == "executor"
    assert received.message_type == MessageType.LOOP_MESSAGE


def _make_group_chat():
    group_chat = GroupChat.__new__(GroupChat)
    group_chat.group_chat_id = "group-1"
    group_chat.runtime = _FakeRuntime()
    group_chat.loop_manager = _FakeLoopManager()
    group_chat.agent_call_manager = _FakeAgentCallManager()
    group_chat.active_loops = {}
    group_chat._loop_tasks = {}
    group_chat._loop_queues = {}
    group_chat.stopped_members = []
    group_chat.started_members = []
    group_chat.agents = {
        "executor": _FakeAgent("executor"),
        "reviewer": _FakeAgent("reviewer"),
    }
    group_chat.manager = _FakeAgent("manager")
    group_chat.workers = group_chat.agents

    # 添加 message_router
    from agents_hub.core.communication.message_router import MessageRouter
    group_chat.message_router = MessageRouter()
    for agent_name, agent in group_chat.agents.items():
        group_chat.message_router.register(agent_name, agent.message_queue)
    group_chat.message_router.register(group_chat.manager.name, group_chat.manager.message_queue)

    def find_agent(agent_name):
        return group_chat.agents.get(agent_name)

    async def send_message_to_agent(_message):
        return None

    async def stop_member(agent_name):
        group_chat.stopped_members.append(agent_name)
        group_chat.runtime.member_infos[agent_name].status = "stopped"
        return {"agent_name": agent_name, "status": "stopped"}

    async def start_member(agent_name):
        group_chat.started_members.append(agent_name)
        group_chat.runtime.member_infos[agent_name].status = "idle"
        return {"agent_name": agent_name, "status": "idle"}

    group_chat._find_agent = find_agent
    group_chat.send_message_to_agent = send_message_to_agent
    group_chat.stop_member = stop_member
    group_chat.start_member = start_member
    return group_chat


def _make_loop(status: str) -> Loop:
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
            ),
            LoopNode(
                node_id="node-reviewer",
                node_type=LoopNodeType.TERMINATOR.value,
                agent_name="reviewer",
                role_description="审查任务",
            ),
        ],
        status=status,
        max_iterations=3,
        current_iteration=1,
        current_node_index=0,
        initial_task="请实现功能",
        created_at=now,
        updated_at=now,
    )


class _FakeAgent:
    def __init__(self, name: str):
        self.name = name
        self.message_queue = asyncio.Queue()
        self.loop_completion_queue = None

    def set_loop_completion_queue(self, queue):
        self.loop_completion_queue = queue


class _FakeRuntime:
    def __init__(self):
        self.member_infos = {
            "executor": SimpleNamespace(status="idle", current_loop_id=None),
            "reviewer": SimpleNamespace(status="idle", current_loop_id=None),
        }
        self.save_agent_members = AsyncMock()
        self.add_message = AsyncMock()

    def get_or_create_agent_member_info(self, agent_name):
        return self.member_infos.setdefault(
            agent_name,
            SimpleNamespace(status="idle", current_loop_id=None),
        )

    def get_agent_member_info(self, agent_name):
        return self.member_infos.get(agent_name)


class _FakeLoopManager:
    def __init__(self):
        self.loops = {}

    def get_loop(self, loop_id):
        return self.loops[loop_id]

    async def update_loop_status(
        self,
        loop_id,
        status,
        current_iteration=None,
        current_node_index=None,
        error_message=None,
    ):
        loop = self.loops[loop_id]
        loop.status = status
        if current_iteration is not None:
            loop.current_iteration = current_iteration
        if current_node_index is not None:
            loop.current_node_index = current_node_index
        loop.error_message = error_message
        return loop

    async def delete_loop(self, loop_id):
        del self.loops[loop_id]


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


def _make_agent_result(agent_name: str, text: str) -> AgentResult:
    return AgentResult(
        text=text,
        session_id=f"session-{agent_name}",
        timestamp="2026-06-20T00:00:00",
        agent_name=agent_name,
        platform=AgentPlatform.CLAUDE,
        role_type=RoleType.TEAM_MEMBER,
    )
