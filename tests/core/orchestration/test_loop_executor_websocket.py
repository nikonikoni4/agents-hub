"""LoopExecutor WebSocket 通知测试。

测试 on_state_change 回调在状态变化时被正确调用。
"""

import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents_hub.agent_bridge.models import AgentResult
from agents_hub.core.context.loop_models import Loop, LoopExecution, LoopNode, LoopNodeType
from agents_hub.core.foundation.models import LoopExecutionStatus
from agents_hub.core.orchestration.loop_executor import LoopExecutor


def _make_loop(max_iterations: int = 3) -> Loop:
    """创建测试用 Loop 定义。"""
    now = datetime.now()
    return Loop(
        loop_id="loop-1",
        group_chat_id="group-1",
        name="测试循环",
        nodes=[
            LoopNode(
                node_id="node-1",
                node_type=LoopNodeType.NORMAL.value,
                agent_name="executor",
                role_description="执行任务",
                output_schema_prompt="请输出结果",
                output_schema_fields=["# 执行结果", "**任务状态**"],
                max_retries=3,
            ),
            LoopNode(
                node_id="node-2",
                node_type=LoopNodeType.TERMINATOR.value,
                agent_name="reviewer",
                role_description="判断是否继续",
                output_schema_prompt="请输出判断",
                output_schema_fields=["# 审查结果"],
                max_retries=3,
            ),
        ],
        max_iterations=max_iterations,
        created_at=now,
        updated_at=now,
    )


def _make_execution() -> LoopExecution:
    """创建测试用 LoopExecution。"""
    now = datetime.now()
    return LoopExecution(
        execution_id="exec-1",
        loop_id="loop-1",
        initial_task="测试任务",
        status=LoopExecutionStatus.CREATED.value,
        current_iteration=1,
        current_node_index=0,
        created_at=now,
        updated_at=now,
    )


def _make_agent_result(agent_name: str, text: str) -> AgentResult:
    """创建测试用 AgentResult。"""
    return AgentResult(
        agent_name=agent_name,
        text=text,
        platform="claude",
        session_id="session-1",
        timestamp=datetime.now().isoformat(),
        role_type="team_member",
    )


@pytest.mark.asyncio
async def test_on_state_change_called_on_cleanup():
    """测试 on_state_change 在 _cleanup() 时被调用。"""
    queue = asyncio.Queue()
    on_state_change = MagicMock()

    async def send_message(message):
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
    loop = _make_loop(max_iterations=3)
    execution = _make_execution()
    executor = LoopExecutor(
        loop=loop,
        execution=execution,
        runtime=runtime,
        completion_queue=queue,
        send_message_callback=send_message,
        on_state_change=on_state_change,
    )

    await executor.run()

    assert execution.status == LoopExecutionStatus.COMPLETED.value
    # on_state_change 应该被调用至少一次（节点切换 + _cleanup）
    assert on_state_change.call_count >= 1
    # 所有调用都应该传入 loop_id
    for call in on_state_change.call_args_list:
        assert call[0][0] == "loop-1"


@pytest.mark.asyncio
async def test_on_state_change_called_on_emergency_stop():
    """测试 on_state_change 在 _emergency_stop() 时被调用。"""
    queue = asyncio.Queue()
    on_state_change = MagicMock()

    async def send_message(message):
        if message.send_to == "executor":
            await queue.put(
                {
                    "loop_id": "loop-1",
                    "call_id": message.call_id,
                    "agent_result": _make_agent_result(
                        agent_name="executor",
                        text="缺少格式字段",  # 无效输出，触发重试
                    ),
                }
            )

    runtime = SimpleNamespace(add_message=AsyncMock())
    loop = _make_loop(max_iterations=3)
    loop.nodes[0].max_retries = 0  # 禁用重试，直接触发紧急停止
    execution = _make_execution()
    executor = LoopExecutor(
        loop=loop,
        execution=execution,
        runtime=runtime,
        completion_queue=queue,
        send_message_callback=send_message,
        on_state_change=on_state_change,
    )

    await executor.run()

    assert execution.status == LoopExecutionStatus.FAILED.value
    # on_state_change 应该被调用至少一次（_emergency_stop + _cleanup）
    assert on_state_change.call_count >= 1
    # 所有调用都应该传入 loop_id
    for call in on_state_change.call_args_list:
        assert call[0][0] == "loop-1"


@pytest.mark.asyncio
async def test_on_state_change_called_on_node_completion():
    """测试 on_state_change 在 _handle_node_completion() 时被调用（节点切换）。"""
    queue = asyncio.Queue()
    on_state_change = MagicMock()
    call_count = 0

    async def send_message(message):
        nonlocal call_count
        call_count += 1
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
            if call_count <= 2:
                # 第一轮：继续循环
                await queue.put(
                    {
                        "loop_id": "loop-1",
                        "call_id": message.call_id,
                        "agent_result": _make_agent_result(
                            agent_name="reviewer",
                            text=(
                                "# 审查结果\n继续\n"
                                "<loop_decision><should_continue>true</should_continue>"
                                "<reason>继续</reason></loop_decision>"
                            ),
                        ),
                    }
                )
            else:
                # 第二轮：结束循环
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
    execution = _make_execution()
    executor = LoopExecutor(
        loop=loop,
        execution=execution,
        runtime=runtime,
        completion_queue=queue,
        send_message_callback=send_message,
        on_state_change=on_state_change,
    )

    await executor.run()

    assert execution.status == LoopExecutionStatus.COMPLETED.value
    # on_state_change 应该被调用多次：
    # 1. 节点切换时（executor -> reviewer）
    # 2. 节点切换时（reviewer -> executor，轮次递增）
    # 3. 节点切换时（executor -> reviewer）
    # 4. _cleanup() 时
    assert on_state_change.call_count >= 2
    # 所有调用都应该传入 loop_id
    for call in on_state_change.call_args_list:
        assert call[0][0] == "loop-1"


@pytest.mark.asyncio
async def test_on_state_change_exception_does_not_block_cleanup():
    """测试 _emergency_stop() 中回调异常不会阻止清理逻辑。"""
    queue = asyncio.Queue()

    def on_state_change_that_raises(loop_id):
        raise RuntimeError("WebSocket 广播失败")

    async def send_message(message):
        if message.send_to == "executor":
            await queue.put(
                {
                    "loop_id": "loop-1",
                    "call_id": message.call_id,
                    "agent_result": _make_agent_result(
                        agent_name="executor",
                        text="缺少格式字段",  # 无效输出，触发重试
                    ),
                }
            )

    runtime = SimpleNamespace(add_message=AsyncMock())
    loop = _make_loop(max_iterations=3)
    loop.nodes[0].max_retries = 0  # 禁用重试，直接触发紧急停止
    execution = _make_execution()
    executor = LoopExecutor(
        loop=loop,
        execution=execution,
        runtime=runtime,
        completion_queue=queue,
        send_message_callback=send_message,
        on_state_change=on_state_change_that_raises,
    )

    # 不应该抛出异常
    await executor.run()

    assert execution.status == LoopExecutionStatus.FAILED.value


@pytest.mark.asyncio
async def test_on_state_change_none_is_safe():
    """测试 on_state_change 为 None 时不会报错。"""
    queue = asyncio.Queue()

    async def send_message(message):
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
    loop = _make_loop(max_iterations=3)
    execution = _make_execution()
    executor = LoopExecutor(
        loop=loop,
        execution=execution,
        runtime=runtime,
        completion_queue=queue,
        send_message_callback=send_message,
        on_state_change=None,
    )

    # 不应该抛出异常
    await executor.run()

    assert execution.status == LoopExecutionStatus.COMPLETED.value
