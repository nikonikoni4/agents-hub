import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agents_hub.agent_bridge.models import AgentResult
from agents_hub.config.types import AgentPlatform, RoleType
from agents_hub.core.communication import MessageRouter
from agents_hub.core.foundation import AgentMessage, MessageType, SessionType
from agents_hub.core.context.loop_models import Loop, LoopExecution, LoopNode, LoopNodeType
from agents_hub.core.foundation.models import LoopExecutionStatus, SystemRoles
from agents_hub.core.orchestration.group_chat import GroupChat


@pytest.mark.asyncio
async def test_create_and_start_loop_sets_agents_in_loop_and_starts_executor():
    group_chat = _make_group_chat()
    loop = _make_loop()
    group_chat.loop_manager.loops[loop.loop_id] = loop

    result = await group_chat.create_and_start_loop(loop.loop_id, initial_task="请实现功能")

    execution_id = result["execution_id"]
    assert result["loop_id"] == loop.loop_id
    assert execution_id in group_chat.active_loops
    assert execution_id in group_chat._loop_tasks
    assert execution_id in group_chat._loop_queues
    assert group_chat.runtime.member_infos["executor"].status == "in_loop"
    assert group_chat.runtime.member_infos["executor"].current_loop_id == loop.loop_id
    assert group_chat.runtime.member_infos["reviewer"].status == "in_loop"
    assert group_chat.agents["executor"].loop_completion_queue is group_chat._loop_queues[execution_id]
    assert group_chat.agents["reviewer"].loop_completion_queue is group_chat._loop_queues[execution_id]

    await group_chat.cleanup_loop(execution_id)


@pytest.mark.asyncio
async def test_stop_loop_sends_termination_signal_restarts_agents_and_pauses_loop():
    group_chat = _make_group_chat()
    loop = _make_loop()
    group_chat.loop_manager.loops[loop.loop_id] = loop

    # 先启动 loop
    result = await group_chat.create_and_start_loop(loop.loop_id, initial_task="请实现功能")
    execution_id = result["execution_id"]

    # 设置 agent 状态为 in_loop
    for name in ("executor", "reviewer"):
        info = group_chat.runtime.member_infos[name]
        info.status = "in_loop"
        info.current_loop_id = loop.loop_id

    stopped_loop = await group_chat.stop_loop(execution_id)

    queue = group_chat._loop_queues.get(execution_id)
    if queue is not None:
        signal = await queue.get()
        assert signal == {"loop_id": loop.loop_id, "is_termination_signal": True}
    assert stopped_loop.status == LoopExecutionStatus.PAUSED.value
    assert execution_id not in group_chat.active_loops
    assert execution_id not in group_chat._loop_queues
    assert execution_id not in group_chat._loop_tasks
    assert group_chat.stopped_members == ["executor", "reviewer"]
    assert group_chat.started_members == ["executor", "reviewer"]
    assert group_chat.runtime.member_infos["executor"].status == "idle"
    assert group_chat.runtime.member_infos["executor"].current_loop_id is None
    assert group_chat.agents["executor"].loop_completion_queue is None


@pytest.mark.asyncio
async def test_loop_lifecycle_auto_completes_through_group_chat_callbacks():
    group_chat = _make_group_chat()
    loop = _make_loop()
    group_chat.loop_manager.loops[loop.loop_id] = loop

    # send_message_to_agent 必须在 create_and_start_loop 之前设置，
    # 因为 LoopExecutor 在创建时捕获该回调的引用。
    async def send_message_to_agent(message):
        assert message.message_type == MessageType.LOOP_MESSAGE
        execution_id = list(group_chat._loop_queues.keys())[0]
        queue = group_chat._loop_queues[execution_id]
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

    result = await group_chat.create_and_start_loop(loop.loop_id, initial_task="请实现功能")
    execution_id = result["execution_id"]

    await asyncio.wait_for(group_chat._loop_tasks[execution_id], timeout=5)

    status = group_chat.get_loop_status(execution_id)
    assert status["status"] == LoopExecutionStatus.COMPLETED.value
    assert group_chat.runtime.add_message.await_count == 2
    assert execution_id not in group_chat.active_loops
    assert execution_id not in group_chat._loop_queues


@pytest.mark.asyncio
async def test_loop_system_sender_can_deliver_loop_message_through_group_chat_router():
    group_chat = _make_group_chat()
    group_chat.message_router = MessageRouter()

    group_chat._register_agents_to_router()
    # 动态注册 "loop" 系统身份（与 create_and_start_loop 行为一致）
    group_chat.message_router.register(SystemRoles.LOOP, asyncio.Queue())

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
    group_chat.project_path = "D:/tmp/agents-hub-loop-test"
    group_chat.runtime = _FakeRuntime()
    group_chat.loop_manager = _FakeLoopManager()
    group_chat.loop_execution_manager = _FakeLoopExecutionManager()
    group_chat.agent_call_manager = _FakeAgentCallManager()
    group_chat.active_loops = {}
    group_chat._loop_tasks = {}
    group_chat._loop_queues = {}
    group_chat._loop_completion_queue = None
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


def _make_loop() -> Loop:
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
        max_iterations=3,
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

    def get_loop_with_lazy_load(self, loop_id):
        return self.loops[loop_id]

    async def delete_loop(self, loop_id, loop_execution_manager=None):
        del self.loops[loop_id]


class _FakeLoopExecutionManager:
    def __init__(self):
        self._executions = {}
        self._counter = 0

    async def create_execution(self, loop_id, initial_task):
        self._counter += 1
        execution = LoopExecution(
            execution_id=f"exec-{self._counter}",
            loop_id=loop_id,
            initial_task=initial_task,
            status=LoopExecutionStatus.CREATED.value,
            current_iteration=1,
            current_node_index=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self._executions[execution.execution_id] = execution
        return execution

    def get_execution(self, execution_id):
        return self._executions[execution_id]

    def get_execution_with_lazy_load(self, execution_id):
        return self._executions[execution_id]

    def clear_other_executions(self, keep_execution_id):
        to_remove = [eid for eid in self._executions if eid != keep_execution_id]
        for eid in to_remove:
            del self._executions[eid]
        return len(to_remove)

    async def update_execution_status(self, execution_id, status, **kwargs):
        execution = self._executions[execution_id]
        execution.status = status
        for k, v in kwargs.items():
            if v is not None and hasattr(execution, k):
                setattr(execution, k, v)
        return execution


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
