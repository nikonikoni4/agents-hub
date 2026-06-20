import pytest
from unittest.mock import AsyncMock

from agents_hub.agent_bridge.models import AgentResult
from agents_hub.config.types import AgentPlatform, RoleType

from agents_hub.core.context.loop_models import Loop, LoopNode, LoopNodeType
from agents_hub.core.foundation import CallStatus
from agents_hub.core.foundation.exceptions import LoopExecutionError
from agents_hub.core.orchestration.loop_executor import LoopExecutor


def test_validate_schema_fields_accepts_output_with_all_required_fields():
    executor = LoopExecutor(loop=_make_loop())

    is_valid, error_message = executor._validate_schema_fields(
        output="# 执行结果\n完成\n**任务状态**：成功",
        required_fields=["# 执行结果", "**任务状态**"],
    )

    assert is_valid is True
    assert error_message == ""


def test_validate_schema_fields_accepts_empty_required_fields():
    executor = LoopExecutor(loop=_make_loop())

    is_valid, error_message = executor._validate_schema_fields(
        output="任意输出",
        required_fields=[],
    )

    assert is_valid is True
    assert error_message == ""


def test_validate_schema_fields_reports_all_missing_fields():
    executor = LoopExecutor(loop=_make_loop())

    is_valid, error_message = executor._validate_schema_fields(
        output="只有普通文本",
        required_fields=["# 执行结果", "**任务状态**"],
    )

    assert is_valid is False
    assert "缺少以下必需字段" in error_message
    assert "- # 执行结果" in error_message
    assert "- **任务状态**" in error_message
    assert "请重新输出" in error_message


def test_validate_terminator_output_accepts_false_decision_with_business_fields():
    executor = LoopExecutor(loop=_make_loop())
    node = LoopNode(
        node_type=LoopNodeType.TERMINATOR.value,
        agent_name="reviewer",
        role_description="判断是否继续",
        output_schema_fields=["# 审查结果"],
    )

    is_valid, error_message, should_continue = executor._validate_terminator_output(
        output=(
            "# 审查结果\n通过\n"
            "<loop_decision>\n"
            "  <should_continue> false </should_continue>\n"
            "  <reason>已通过</reason>\n"
            "</loop_decision>"
        ),
        node=node,
    )

    assert is_valid is True
    assert error_message == ""
    assert should_continue is False


def test_validate_terminator_output_accepts_true_decision_case_insensitive():
    executor = LoopExecutor(loop=_make_loop())
    node = LoopNode(
        node_type=LoopNodeType.TERMINATOR.value,
        agent_name="reviewer",
        role_description="判断是否继续",
    )

    is_valid, error_message, should_continue = executor._validate_terminator_output(
        output="<LOOP_DECISION><SHOULD_CONTINUE> TRUE </SHOULD_CONTINUE></LOOP_DECISION>",
        node=node,
    )

    assert is_valid is True
    assert error_message == ""
    assert should_continue is True


def test_validate_terminator_output_rejects_missing_loop_decision_tag():
    executor = LoopExecutor(loop=_make_loop())
    node = LoopNode(
        node_type=LoopNodeType.TERMINATOR.value,
        agent_name="reviewer",
        role_description="判断是否继续",
    )

    is_valid, error_message, should_continue = executor._validate_terminator_output(
        output="没有决策标签",
        node=node,
    )

    assert is_valid is False
    assert "loop_decision" in error_message
    assert should_continue is None


def test_validate_terminator_output_rejects_invalid_should_continue_value():
    executor = LoopExecutor(loop=_make_loop())
    node = LoopNode(
        node_type=LoopNodeType.TERMINATOR.value,
        agent_name="reviewer",
        role_description="判断是否继续",
    )

    is_valid, error_message, should_continue = executor._validate_terminator_output(
        output="<loop_decision><should_continue>maybe</should_continue></loop_decision>",
        node=node,
    )

    assert is_valid is False
    assert "should_continue" in error_message
    assert "true/false" in error_message
    assert should_continue is None


@pytest.mark.asyncio
async def test_execute_node_with_retry_returns_first_valid_output_without_retry():
    completion_queue = __import__("asyncio").Queue()
    await completion_queue.put(
        {
            "loop_id": "loop-1",
            "call_id": "call-1",
            "agent_result": _make_agent_result("# 执行结果\n完成\n**任务状态**：成功"),
        }
    )
    send_message = AsyncMock()
    executor = LoopExecutor(
        loop=_make_loop(),
        completion_queue=completion_queue,
        send_message_callback=send_message,
    )
    node = LoopNode(
        node_type=LoopNodeType.NORMAL.value,
        agent_name="worker",
        role_description="执行任务",
        output_schema_fields=["# 执行结果", "**任务状态**"],
    )

    result = await executor._execute_node_with_retry(
        node=node,
        input_data="初始输入",
        call_id="call-1",
    )

    assert result.text.startswith("# 执行结果")
    assert send_message.await_count == 1
    sent_message = send_message.await_args.args[0]
    assert sent_message.call_id == "call-1"
    assert sent_message.send_to == "worker"


@pytest.mark.asyncio
async def test_execute_node_with_retry_retries_with_error_prompt_and_same_call_id():
    completion_queue = __import__("asyncio").Queue()
    await completion_queue.put(
        {
            "loop_id": "loop-1",
            "call_id": "call-1",
            "agent_result": _make_agent_result("缺少格式字段"),
        }
    )
    await completion_queue.put(
        {
            "loop_id": "loop-1",
            "call_id": "call-1",
            "agent_result": _make_agent_result("# 执行结果\n修正\n**任务状态**：成功"),
        }
    )
    send_message = AsyncMock()
    executor = LoopExecutor(
        loop=_make_loop(),
        completion_queue=completion_queue,
        send_message_callback=send_message,
    )
    node = LoopNode(
        node_type=LoopNodeType.NORMAL.value,
        agent_name="worker",
        role_description="执行任务",
        output_schema_fields=["# 执行结果", "**任务状态**"],
    )

    result = await executor._execute_node_with_retry(
        node=node,
        input_data="初始输入",
        call_id="call-1",
    )

    assert result.text.startswith("# 执行结果")
    assert send_message.await_count == 2
    first_message = send_message.await_args_list[0].args[0]
    retry_message = send_message.await_args_list[1].args[0]
    assert first_message.call_id == "call-1"
    assert retry_message.call_id == "call-1"
    assert retry_message.metadata["loop_retry_count"] == 1
    assert "[循环-节点worker-第1轮-重试1]" in retry_message.content
    assert "缺少以下必需字段" in retry_message.content
    assert "- # 执行结果" in retry_message.content
    assert "- **任务状态**" in retry_message.content


@pytest.mark.asyncio
async def test_execute_node_with_retry_marks_call_failed_and_raises_after_max_retries():
    completion_queue = __import__("asyncio").Queue()
    for _ in range(3):
        await completion_queue.put(
            {
                "loop_id": "loop-1",
                "call_id": "call-1",
                "agent_result": _make_agent_result("始终缺少格式字段"),
            }
        )
    send_message = AsyncMock()
    agent_call_manager = AsyncMock()
    executor = LoopExecutor(
        loop=_make_loop(),
        completion_queue=completion_queue,
        send_message_callback=send_message,
        agent_call_manager=agent_call_manager,
    )
    node = LoopNode(
        node_type=LoopNodeType.NORMAL.value,
        agent_name="worker",
        role_description="执行任务",
        output_schema_fields=["# 执行结果"],
        max_retries=2,
    )

    with pytest.raises(LoopExecutionError) as exc_info:
        await executor._execute_node_with_retry(
            node=node,
            input_data="初始输入",
            call_id="call-1",
        )

    assert "超过最大重试次数" in str(exc_info.value)
    assert send_message.await_count == 3
    agent_call_manager.update_status.assert_awaited_once_with(
        "call-1", CallStatus.FAILED
    )


@pytest.mark.asyncio
async def test_execute_node_with_retry_does_not_retry_when_max_retries_is_zero():
    completion_queue = __import__("asyncio").Queue()
    await completion_queue.put(
        {
            "loop_id": "loop-1",
            "call_id": "call-1",
            "agent_result": _make_agent_result("缺少格式字段"),
        }
    )
    send_message = AsyncMock()
    agent_call_manager = AsyncMock()
    executor = LoopExecutor(
        loop=_make_loop(),
        completion_queue=completion_queue,
        send_message_callback=send_message,
        agent_call_manager=agent_call_manager,
    )
    node = LoopNode(
        node_type=LoopNodeType.NORMAL.value,
        agent_name="worker",
        role_description="执行任务",
        output_schema_fields=["# 执行结果"],
        max_retries=0,
    )

    with pytest.raises(LoopExecutionError):
        await executor._execute_node_with_retry(
            node=node,
            input_data="初始输入",
            call_id="call-1",
        )

    assert send_message.await_count == 1
    agent_call_manager.update_status.assert_awaited_once_with(
        "call-1", CallStatus.FAILED
    )


@pytest.mark.asyncio
async def test_execute_node_with_retry_times_out_and_marks_call_failed_when_no_result():
    send_message = AsyncMock()
    agent_call_manager = AsyncMock()
    executor = LoopExecutor(
        loop=_make_loop(),
        completion_queue=__import__("asyncio").Queue(),
        send_message_callback=send_message,
        agent_call_manager=agent_call_manager,
        node_result_timeout_seconds=0.01,
    )
    node = LoopNode(
        node_type=LoopNodeType.NORMAL.value,
        agent_name="worker",
        role_description="执行任务",
        output_schema_fields=["# 执行结果"],
    )

    with pytest.raises(LoopExecutionError) as exc_info:
        await executor._execute_node_with_retry(
            node=node,
            input_data="初始输入",
            call_id="call-1",
        )

    assert "等待节点输出超时" in str(exc_info.value)
    assert send_message.await_count == 1
    agent_call_manager.update_status.assert_awaited_once_with(
        "call-1", CallStatus.FAILED
    )


@pytest.mark.asyncio
async def test_execute_node_with_retry_times_out_when_only_unrelated_results_arrive():
    completion_queue = __import__("asyncio").Queue()
    await completion_queue.put(
        {
            "loop_id": "other-loop",
            "call_id": "call-1",
            "agent_result": _make_agent_result("# 执行结果\n完成"),
        }
    )
    await completion_queue.put(
        {
            "loop_id": "loop-1",
            "call_id": "other-call",
            "agent_result": _make_agent_result("# 执行结果\n完成"),
        }
    )
    send_message = AsyncMock()
    agent_call_manager = AsyncMock()
    executor = LoopExecutor(
        loop=_make_loop(),
        completion_queue=completion_queue,
        send_message_callback=send_message,
        agent_call_manager=agent_call_manager,
        node_result_timeout_seconds=0.01,
    )
    node = LoopNode(
        node_type=LoopNodeType.NORMAL.value,
        agent_name="worker",
        role_description="执行任务",
        output_schema_fields=["# 执行结果"],
    )

    with pytest.raises(LoopExecutionError):
        await executor._execute_node_with_retry(
            node=node,
            input_data="初始输入",
            call_id="call-1",
        )

    assert send_message.await_count == 1
    agent_call_manager.update_status.assert_awaited_once_with(
        "call-1", CallStatus.FAILED
    )


def _make_loop() -> Loop:
    from datetime import datetime

    now = datetime.now()
    node = LoopNode(
        node_type=LoopNodeType.NORMAL.value,
        agent_name="worker",
        role_description="执行任务",
    )
    return Loop(
        loop_id="loop-1",
        group_chat_id="group-1",
        nodes=[node],
        status="created",
        max_iterations=3,
        current_iteration=1,
        current_node_index=0,
        initial_task="初始任务",
        created_at=now,
        updated_at=now,
    )


def _make_agent_result(text: str) -> AgentResult:
    return AgentResult(
        text=text,
        session_id="session-1",
        timestamp="2026-06-20T00:00:00",
        agent_name="worker",
        platform=AgentPlatform.CLAUDE,
        role_type=RoleType.TEAM_MEMBER,
    )
