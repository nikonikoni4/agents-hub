"""Loop 执行器。

实现 Loop 循环的核心执行逻辑，包括：
- 节点调度：按节点列表顺序执行，支持循环流转
- 输出校验：检查节点输出是否符合格式要求
- 退出判断：TERMINATOR 节点通过 <loop_decision> 标签控制循环退出
- 错误处理：输出格式错误自动重试，异常自动停止

设计决策参考：PRD 中的"消息通信机制"和"循环专用上下文"章节。
"""

import asyncio
import inspect
import logging
import re
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from agents_hub.agent_bridge.models import AgentResult
from agents_hub.core.context import GroupChatRuntime
from agents_hub.core.context.loop_models import Loop, LoopNode, LoopNodeType
from agents_hub.core.foundation import (
    AgentMessage,
    CallStatus,
    MessageType,
    SessionType,
)
from agents_hub.core.foundation.exceptions import LoopExecutionError
from agents_hub.core.foundation.models import LoopStatus
from agents_hub.core.foundation.renderer import Tag, render_for_chat, wrap_xml


async def notify_loop_completion(
    queue: asyncio.Queue | None,
    msg: AgentMessage,
    result: AgentResult | None,
) -> None:
    """将循环消息完成事件投递给 LoopExecutor 调度队列。

    当 Agent 处理完循环消息后调用此函数，将完成事件放入队列，
    由 LoopExecutor 监听并调度下一个节点。

    Args:
        queue: LoopExecutor 的完成通知队列，如果为 None 则直接返回。
        msg: Agent 处理的消息，必须是 LOOP_MESSAGE 类型。
        result: Agent 的执行结果，如果为 None 则直接返回。
    """
    if msg.message_type != MessageType.LOOP_MESSAGE:
        return
    if queue is None or result is None:
        return

    loop_id = msg.metadata.get("loop_id") if msg.metadata else None
    if not loop_id:
        return

    await queue.put(
        {
            "loop_id": loop_id,
            "agent_result": result,
            "call_id": msg.call_id,
        }
    )


class LoopExecutor:
    """循环执行器。

    负责 Loop 循环的核心执行逻辑，包括节点调度、输出校验、
    退出判断和错误处理。通过事件驱动机制（completion_queue）
    接收节点完成通知，实现异步调度。

    状态机：
    - RUNNING: 正在执行循环
    - COMPLETED: TERMINATOR 节点返回 should_continue=false
    - FAILED: 达到最大循环次数、输出校验失败、异常等

    Attributes:
        loop: 循环定义对象。
        runtime: 群聊运行时，用于保存消息和查询 Agent 状态。
        completion_queue: 完成通知队列，Agent 处理完消息后投递通知。
        send_message_callback: 发送消息的回调函数，通过 GroupChat.send_message_to_agent() 注入。
        agent_call_manager: Agent 调用管理器，用于创建和更新 AgentCall。
        loop_manager: 循环管理器，用于持久化状态变更。
        agents: Agent 实例字典，用于清理 completion_queue 引用。
        logger: 日志器。
        node_result_timeout_seconds: 等待节点完成通知的超时时间（秒）。
    """

    TERMINATION_CHECK_PROMPT = (
        "这是 TERMINATOR 节点。请基于上一节点输出判断循环是否继续。\n\n"
        "你必须在输出末尾包含以下 XML 标签，明确表示循环是否继续：\n\n"
        "<loop_decision>\n"
        "  <should_continue>true</should_continue>\n"
        "  <reason>继续/结束的原因</reason>\n"
        "</loop_decision>\n\n"
        "如果缺少此标签，系统会要求你重新输出。"
    )
    """TERMINATOR 节点的退出判断提示词，附加在循环上下文中。"""

    def __init__(
        self,
        loop: Loop,
        runtime: GroupChatRuntime | None = None,
        completion_queue: asyncio.Queue | None = None,
        send_message_callback: Callable[[AgentMessage], Awaitable[None]] | None = None,
        agent_call_manager=None,
        loop_manager=None,
        agents: dict[str, Any] | None = None,
        logger: logging.Logger | None = None,
        node_result_timeout_seconds: float = 300.0,
    ):
        """初始化 LoopExecutor。

        Args:
            loop: 循环定义对象，包含节点列表、状态、迭代计数等。
            runtime: 群聊运行时，用于保存消息和查询 Agent 状态。
            completion_queue: 完成通知队列，Agent 处理完消息后投递通知。
            send_message_callback: 发送消息的回调函数，解耦 GroupChat 依赖。
            agent_call_manager: Agent 调用管理器，用于创建和更新 AgentCall。
            loop_manager: 循环管理器，用于持久化状态变更。
            agents: Agent 实例字典，键为 agent_name，用于清理 completion_queue 引用。
            logger: 日志器，如果为 None 则使用模块默认日志器。
            node_result_timeout_seconds: 等待节点完成通知的超时时间（秒），默认 300 秒。
        """
        self.loop = loop
        self.runtime = runtime
        self.completion_queue = completion_queue
        self.send_message_callback = send_message_callback
        self.agent_call_manager = agent_call_manager
        self.loop_manager = loop_manager
        self.agents = agents or {}
        self.logger = logger or logging.getLogger(__name__)
        self.node_result_timeout_seconds = node_result_timeout_seconds
        self._last_node_output = loop.initial_task

    def _build_loop_context(self, node: LoopNode, previous_output: str) -> str:
        """构造循环专用上下文，隔离群聊历史。

        为节点构造专用上下文，包含：
        - LOOP_NODE_ROLE: 节点职责描述
        - LOOP_OUTPUT_SCHEMA: 输出格式要求
        - PREVIOUS_NODE_OUTPUT: 上一节点的输出
        - LOOP_TERMINATION_CHECK: 退出判断提示（仅 TERMINATOR 节点）

        Args:
            node: 当前执行的节点。
            previous_output: 上一节点的输出内容。

        Returns:
            构造好的循环上下文字符串。
        """
        sections = [
            wrap_xml(Tag.LOOP_NODE_ROLE, node.role_description),
            wrap_xml(Tag.LOOP_OUTPUT_SCHEMA, node.output_schema_prompt or ""),
            wrap_xml(Tag.PREVIOUS_NODE_OUTPUT, previous_output),
        ]
        if node.node_type == LoopNodeType.TERMINATOR.value:
            sections.append(wrap_xml(Tag.LOOP_TERMINATION_CHECK, self.TERMINATION_CHECK_PROMPT))
        return "\n\n".join(sections)

    def _build_loop_message(self, node: LoopNode, previous_output: str) -> AgentMessage:
        """构造循环内部消息。

        构造发送给节点 Agent 的 LOOP_MESSAGE 类型消息，包含循环上下文。
        消息 metadata 携带 loop_id 和 loop_iteration，用于循环隔离和渲染。

        Args:
            node: 目标节点。
            previous_output: 上一节点的输出内容。

        Returns:
            构造好的 AgentMessage 实例。
        """
        loop_context = self._build_loop_context(node, previous_output)
        return AgentMessage(
            call_id=f"{self.loop.loop_id}:{node.node_id}:{self.loop.current_iteration}",
            content=loop_context,
            send_from=node.agent_name,
            send_to=node.agent_name,
            session_type=SessionType.MAIN,
            message_type=MessageType.LOOP_MESSAGE,
            metadata={
                "loop_id": self.loop.loop_id,
                "loop_iteration": self.loop.current_iteration,
            },
        )

    def _build_retry_loop_message(
        self,
        node: LoopNode,
        previous_output: str,
        call_id: str,
        retry_count: int,
    ) -> AgentMessage:
        """构造可复用 call_id 的循环节点消息。

        重试时复用同一个 call_id，消息内容附加重试标记。
        重试标记格式：[循环-节点{agent_name}-第{iteration}轮-重试{retry_count}]

        Args:
            node: 目标节点。
            previous_output: 上一节点的输出内容（包含错误提示）。
            call_id: 复用的调用 ID。
            retry_count: 当前重试次数，0 表示首次尝试。

        Returns:
            构造好的 AgentMessage 实例。
        """
        message = self._build_loop_message(node, previous_output)
        message.call_id = call_id
        if retry_count > 0:
            if message.metadata is None:
                message.metadata = {}
            message.metadata["loop_retry_count"] = retry_count
            retry_prefix = (
                f"[循环-节点{node.agent_name}-第{self.loop.current_iteration}轮-重试{retry_count}]"
            )
            message.content = f"{retry_prefix}\n{message.content}"
        return message

    def _validate_schema_fields(
        self,
        output: str,
        required_fields: list[str] | None,
    ) -> tuple[bool, str]:
        """校验节点输出是否包含所有必需字段。

        使用简单字符串匹配检查输出中是否包含所有必需字段。
        这是一种轻量级校验方式，适用于 Markdown 格式的输出。

        Args:
            output: 节点输出内容。
            required_fields: 必需字段列表，如果为 None 则跳过校验。

        Returns:
            (is_valid, error_message) 元组：
            - is_valid: 是否通过校验
            - error_message: 校验失败时的错误提示，成功时为空字符串
        """
        missing_fields = [field for field in (required_fields or []) if field not in output]
        if not missing_fields:
            return True, ""

        missing_lines = "\n".join(f"- {field}" for field in missing_fields)
        return (
            False,
            f"输出不符合要求：缺少以下必需字段：\n{missing_lines}\n\n请重新输出。",
        )

    def _validate_terminator_output(
        self,
        output: str,
        node: LoopNode,
    ) -> tuple[bool, str, bool | None]:
        """校验 TERMINATOR 输出并解析 should_continue。

        TERMINATOR 节点的输出必须包含：
        1. 业务字段（通过 _validate_schema_fields 校验）
        2. <loop_decision> 标签
        3. <should_continue> 标签，值为 true/false

        Args:
            output: TERMINATOR 节点的输出内容。
            node: TERMINATOR 节点定义。

        Returns:
            (is_valid, error_message, should_continue) 三元组：
            - is_valid: 是否通过校验
            - error_message: 校验失败时的错误提示
            - should_continue: 解析出的循环继续标志，校验失败时为 None
        """
        is_valid, error_message = self._validate_schema_fields(
            output,
            node.output_schema_fields,
        )
        if not is_valid:
            return False, error_message, None

        decision_match = re.search(
            r"<loop_decision[^>]*>(.*?)</loop_decision>",
            output,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if not decision_match:
            return (
                False,
                "输出不符合要求：缺少 <loop_decision> 决策标签。请重新输出。",
                None,
            )

        decision_body = decision_match.group(1)
        should_continue_match = re.search(
            r"<should_continue[^>]*>(.*?)</should_continue>",
            decision_body,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if not should_continue_match:
            return (
                False,
                "输出不符合要求：<loop_decision> 中缺少 <should_continue> 标签，值必须为 true/false。请重新输出。",
                None,
            )

        value = should_continue_match.group(1).strip().lower()
        if value == "true":
            return True, "", True
        if value == "false":
            return True, "", False
        return (
            False,
            "输出不符合要求：<should_continue> 的值必须为 true/false。请重新输出。",
            None,
        )

    def _validate_node_output(
        self,
        output: str,
        node: LoopNode,
    ) -> tuple[bool, str, bool | None]:
        """按节点类型校验输出。

        根据节点类型分发到不同的校验逻辑：
        - TERMINATOR 节点：校验业务字段 + 解析 <loop_decision> 标签
        - 普通节点：仅校验业务字段

        Args:
            output: 节点输出内容。
            node: 节点定义。

        Returns:
            (is_valid, error_message, should_continue) 三元组：
            - is_valid: 是否通过校验
            - error_message: 校验失败时的错误提示
            - should_continue: 循环继续标志（仅 TERMINATOR 节点），普通节点为 None
        """
        if node.node_type == LoopNodeType.TERMINATOR.value:
            return self._validate_terminator_output(output, node)

        is_valid, error_message = self._validate_schema_fields(output, node.output_schema_fields)
        return is_valid, error_message, None

    async def _wait_for_node_result(self, call_id: str) -> AgentResult:
        """等待指定 call_id 的循环节点输出。

        从 completion_queue 中等待匹配 call_id 的完成通知。
        使用 deadline 机制实现超时控制。

        Args:
            call_id: 等待的调用 ID。

        Returns:
            Agent 的执行结果。

        Raises:
            ValueError: completion_queue 未注入时抛出。
            TimeoutError: 等待超时时抛出。
        """
        if self.completion_queue is None:
            raise ValueError("LoopExecutor 未注入 completion_queue，无法等待节点输出")

        deadline = asyncio.get_running_loop().time() + self.node_result_timeout_seconds
        while True:
            remaining_seconds = deadline - asyncio.get_running_loop().time()
            if remaining_seconds <= 0:
                raise TimeoutError

            notification = await asyncio.wait_for(
                self.completion_queue.get(), timeout=remaining_seconds
            )
            if notification.get("loop_id") != self.loop.loop_id:
                continue
            if notification.get("call_id") != call_id:
                continue
            return notification["agent_result"]

    async def receive_node_completion(self) -> dict:
        """从完成队列接收一个通知，并交给节点完成处理入口。

        这是外部调用 LoopExecutor 的入口点之一，用于接收节点完成通知。
        接收后调用 _handle_node_completion() 处理通知并调度下一个节点。

        Returns:
            接收到的通知字典。

        Raises:
            ValueError: completion_queue 未注入时抛出。
            TimeoutError: 等待超时时抛出。
        """
        if self.completion_queue is None:
            raise ValueError("LoopExecutor 未注入 completion_queue，无法接收节点完成通知")

        notification = await asyncio.wait_for(
            self.completion_queue.get(),
            timeout=self.node_result_timeout_seconds,
        )
        await self._handle_node_completion(notification)
        return notification

    async def _handle_node_completion(self, notification: dict) -> None:
        """处理节点完成通知并调度下一个节点。

        核心调度逻辑：
        1. 校验通知来源（loop_id、agent_name）
        2. 校验节点输出格式
        3. 如果校验失败，触发重试机制
        4. 保存结果到群聊历史
        5. 检查退出条件（TERMINATOR 或最大次数）
        6. 推进到下一个节点并发送消息

        调度流程详解：
        - 首先验证通知的 loop_id 是否匹配当前循环
        - 获取当前节点并验证 agent_name 是否匹配
        - 调用 _validate_node_output() 校验输出格式
        - 如果校验失败，调用 _execute_node_with_retry() 触发重试
        - 重试成功后重新校验，如果仍然失败则紧急停止
        - 校验通过后调用 _save_loop_result() 保存到群聊历史
        - 调用 _check_exit_condition() 检查是否应该退出循环
        - 如果不退出，调用 _advance_to_next_node() 推进到下一个节点
        - 再次检查是否达到最大循环次数
        - 最后调用 _send_to_node() 发送消息给下一个节点

        Args:
            notification: 节点完成通知，包含 loop_id、call_id、agent_result。
        """
        if notification.get("loop_id") != self.loop.loop_id:
            return

        result = notification.get("agent_result")
        self.logger.debug(
            "收到节点完成通知: loop_id=%s, call_id=%s",
            notification.get("loop_id"),
            notification.get("call_id"),
        )
        if result is None:
            await self._emergency_stop("节点完成通知缺少 agent_result")
            return

        node = self.loop.nodes[self.loop.current_node_index]
        if node.agent_name != result.agent_name:
            await self._emergency_stop(
                f"节点完成通知来源不匹配: expected={node.agent_name}, actual={result.agent_name}"
            )
            return

        is_valid, error_message, should_continue = self._validate_node_output(
            result.text,
            node,
        )
        if not is_valid:
            call_id = notification.get("call_id")
            if not call_id or not isinstance(call_id, str):
                await self._emergency_stop("完成通知缺少 call_id")
                return
            try:
                result = await self._execute_node_with_retry(
                    node=node,
                    input_data=self._last_node_output,
                    call_id=call_id,
                    initial_result=result,
                    initial_error_message=error_message,
                )
            except LoopExecutionError as exc:
                await self._emergency_stop(str(exc))
                return
            is_valid, error_message, should_continue = self._validate_node_output(
                result.text,
                node,
            )
            if not is_valid:
                await self._emergency_stop(error_message)
                return

        original_output = result.text
        await self._save_loop_result(node, result)
        self._last_node_output = original_output

        if self._check_exit_condition(node, should_continue):
            self.logger.info(
                "Loop 完成: loop_id=%s, status=%s, iteration=%d",
                self.loop.loop_id,
                self.loop.status,
                self.loop.current_iteration,
            )
            await self._cleanup()
            return

        self._advance_to_next_node()
        if self._check_exit_condition():
            self.logger.info(
                "Loop 达到最大循环次数: loop_id=%s, iteration=%d, max=%d",
                self.loop.loop_id,
                self.loop.current_iteration,
                self.loop.max_iterations,
            )
            await self._cleanup()
            return

        await self._send_to_node(
            self.loop.nodes[self.loop.current_node_index],
            self._last_node_output,
        )

    async def run(self) -> None:
        """运行循环主调度。

        循环执行的入口点，启动后持续监听节点完成通知并调度下一个节点。
        执行流程：
        1. 设置循环状态为 RUNNING
        2. 发送初始任务给第一个节点
        3. 持续监听 completion_queue，处理节点完成通知
        4. 遇到超时或异常时自动停止循环

        异常处理：
        - TimeoutError: 调用 _handle_node_timeout() 处理
        - 其他异常: 调用 _emergency_stop() 停止循环

        调度逻辑：
        - 使用 while 循环持续监听 completion_queue
        - 每次收到通知后调用 _handle_node_completion() 处理
        - 超时时调用 _handle_node_timeout() 检查 Agent 状态
        - 异常时调用 _emergency_stop() 清理资源并记录错误
        """
        try:
            if self.loop.status != LoopStatus.RUNNING.value:
                self.loop.status = LoopStatus.RUNNING.value

            self.logger.info(
                "Loop 启动: loop_id=%s, nodes=%d, max_iterations=%d",
                self.loop.loop_id,
                len(self.loop.nodes),
                self.loop.max_iterations,
            )
            await self._send_to_node(
                self.loop.nodes[self.loop.current_node_index],
                self.loop.initial_task,
            )
            while self.loop.status == LoopStatus.RUNNING.value:
                try:
                    await self.receive_node_completion()
                except TimeoutError:
                    await self._handle_node_timeout()
        except Exception as exc:
            if self.loop.status == LoopStatus.RUNNING.value:
                await self._emergency_stop(str(exc))
            else:
                raise

    async def _send_to_node(self, node: LoopNode, previous_output: str) -> AgentMessage:
        """创建 AgentCall 并发送 LOOP_MESSAGE。

        构造循环消息并通过 send_message_callback 发送给目标节点 Agent。
        如果注入了 agent_call_manager，会同时创建 AgentCall 记录。

        Args:
            node: 目标节点。
            previous_output: 上一节点的输出内容。

        Returns:
            发送的 AgentMessage 实例。

        Raises:
            ValueError: send_message_callback 未注入时抛出。
        """
        if self.send_message_callback is None:
            raise ValueError("LoopExecutor 未注入 send_message_callback，无法发送循环消息")

        message = self._build_loop_message(node, previous_output)
        if self.agent_call_manager is not None:
            call = await self.agent_call_manager.create_call(
                send_from=node.agent_name,
                send_to=node.agent_name,
                content=message.content,
                message_type=MessageType.LOOP_MESSAGE,
                timeout_seconds=300,
            )
            message.call_id = call.call_id

        self.logger.info(
            "发送循环消息: loop_id=%s, node=%s, iteration=%d",
            self.loop.loop_id,
            node.agent_name,
            self.loop.current_iteration,
        )
        await self.send_message_callback(message)
        return message

    def _advance_to_next_node(self) -> None:
        """推进到下一个节点，完成一轮后递增轮次。

        节点按列表顺序循环执行（环形调度）：
        - 当前节点是最后一个节点时，下一个节点是第一个节点（index=0）
        - 此时 current_iteration 递增，表示完成一轮
        """
        next_index = (self.loop.current_node_index + 1) % len(self.loop.nodes)
        self.loop.current_node_index = next_index
        if next_index == 0:
            self.loop.current_iteration += 1
        self.loop.updated_at = datetime.now()

    def _check_exit_condition(
        self,
        node: LoopNode | None = None,
        should_continue: bool | None = None,
    ) -> bool:
        """检查循环退出条件。

        两种退出条件：
        1. TERMINATOR 节点返回 should_continue=false → COMPLETED
        2. 达到最大循环次数 → FAILED

        Args:
            node: 当前节点（可选），仅 TERMINATOR 节点触发条件 1。
            should_continue: TERMINATOR 节点的循环继续标志（可选）。

        Returns:
            True 表示循环应该退出，False 表示继续执行。
        """
        if (
            node is not None
            and node.node_type == LoopNodeType.TERMINATOR.value
            and should_continue is False
        ):
            self.loop.status = LoopStatus.COMPLETED.value
            self.loop.updated_at = datetime.now()
            return True

        if self.loop.current_iteration > self.loop.max_iterations:
            self.loop.status = LoopStatus.FAILED.value
            self.loop.error_message = "达到最大循环次数"
            self.loop.updated_at = datetime.now()
            return True

        return False

    async def _handle_node_timeout(self) -> None:
        """处理等待节点完成通知超时。

        超时时检查 Agent 状态：
        - 如果 Agent 状态为 "error"，说明 Agent CLI 执行失败
        - 否则说明节点执行超时
        """
        node = self.loop.nodes[self.loop.current_node_index]
        status = None
        if self.runtime is not None:
            agent_info = self.runtime.get_agent_member_info(node.agent_name)
            status = getattr(agent_info, "status", None) if agent_info else None
        reason = "Agent CLI 执行失败" if status == "error" else "节点执行超时"
        await self._emergency_stop(reason)

    async def _emergency_stop(self, reason: str) -> None:
        """异常停止循环并清理资源。

        将循环状态设置为 FAILED，记录错误原因，然后调用 _cleanup() 清理资源。

        Args:
            reason: 失败原因，记录到 loop.error_message。
        """
        self.loop.status = LoopStatus.FAILED.value
        self.loop.error_message = reason
        self.loop.updated_at = datetime.now()
        self.logger.error("Loop 执行失败: loop_id=%s, reason=%s", self.loop.loop_id, reason)
        await self._cleanup()

    async def _cleanup(self) -> None:
        """清理循环运行资源并持久化最终状态。

        清理流程：
        1. 恢复参与 Agent 的状态（IN_LOOP → IDLE，清除 current_loop_id）
        2. 清除 Agent 的 completion_queue 引用
        3. 通过 loop_manager 持久化循环最终状态
        """
        if self.runtime is not None:
            get_agent_member_info = getattr(self.runtime, "get_agent_member_info", None)
            if get_agent_member_info is not None:
                for node in self.loop.nodes:
                    agent_info = get_agent_member_info(node.agent_name)
                    if agent_info is not None:
                        agent_info.status = "idle"
                        if hasattr(agent_info, "current_loop_id"):
                            agent_info.current_loop_id = None
            save_agent_members = getattr(self.runtime, "save_agent_members", None)
            if save_agent_members is not None:
                await save_agent_members(context=f"Loop cleanup: {self.loop.loop_id}")

        for node in self.loop.nodes:
            agent = self.agents.get(node.agent_name)
            if agent is None:
                continue
            setter = getattr(agent, "set_loop_completion_queue", None)
            if setter is None:
                continue
            result = setter(None)
            if inspect.isawaitable(result):
                await result

        if self.loop_manager is not None:
            await self.loop_manager.update_loop_status(
                self.loop.loop_id,
                self.loop.status,
                current_iteration=self.loop.current_iteration,
                current_node_index=self.loop.current_node_index,
                error_message=self.loop.error_message,
            )

    async def _execute_node_with_retry(
        self,
        node: LoopNode,
        input_data: str,
        call_id: str,
        initial_result: AgentResult | None = None,
        initial_error_message: str | None = None,
    ) -> AgentResult:
        """执行节点并在输出格式错误时自动重试。

        重试机制详解：
        1. 如果有 initial_result，将其作为第一次尝试的结果，从第二次尝试开始重试
        2. 每次重试时，将错误提示和上一次输出拼接为新的输入
        3. 复用同一个 call_id，避免创建新的 AgentCall
        4. 超过 max_retries 次后抛出 LoopExecutionError

        重试流程：
        - 计算总尝试次数 = max_retries + 1（包含首次尝试）
        - 如果有 initial_result，从第 1 次尝试开始（跳过第 0 次）
        - 每次重试构造 _build_retry_loop_message() 消息
        - 调用 send_message_callback() 发送消息
        - 调用 _wait_for_node_result() 等待结果
        - 调用 _validate_node_output() 校验输出
        - 校验通过则返回结果，否则继续重试
        - 超时或超过重试次数时抛出 LoopExecutionError

        Args:
            node: 目标节点。
            input_data: 节点输入数据。
            call_id: 调用 ID，重试时复用。
            initial_result: 初始执行结果（可选），如果提供则跳过第一次尝试。
            initial_error_message: 初始错误提示（可选）。

        Returns:
            通过校验的 Agent 执行结果。

        Raises:
            ValueError: send_message_callback 或 call_id 未注入时抛出。
            LoopExecutionError: 超过最大重试次数或等待超时时抛出。
        """
        if self.send_message_callback is None:
            raise ValueError("LoopExecutor 未注入 send_message_callback，无法发送循环消息")
        if call_id is None:
            raise ValueError("LoopExecutor 缺少 call_id，无法重试循环节点")

        current_input = input_data
        last_error_message = initial_error_message or ""
        total_attempts = node.max_retries + 1
        start_attempt_index = 0
        if initial_result is not None:
            current_input = f"{last_error_message}\n\n上一次输出：\n{initial_result.text}"
            start_attempt_index = 1

        for attempt_index in range(start_attempt_index, total_attempts):
            message = self._build_retry_loop_message(node, current_input, call_id, attempt_index)
            await self.send_message_callback(message)

            try:
                result = await self._wait_for_node_result(call_id)
            except TimeoutError as err:
                if self.agent_call_manager is not None:
                    await self.agent_call_manager.update_status(call_id, CallStatus.FAILED)
                raise LoopExecutionError(
                    loop_id=self.loop.loop_id,
                    node_id=node.node_id,
                    agent_name=node.agent_name,
                    reason=f"等待节点输出超时（{self.node_result_timeout_seconds}秒）",
                ) from err
            is_valid, error_message, _should_continue = self._validate_node_output(
                result.text,
                node,
            )
            if is_valid:
                return result

            last_error_message = error_message
            current_input = f"{error_message}\n\n上一次输出：\n{result.text}"

        if self.agent_call_manager is not None:
            await self.agent_call_manager.update_status(call_id, CallStatus.FAILED)
        raise LoopExecutionError(
            loop_id=self.loop.loop_id,
            node_id=node.node_id,
            agent_name=node.agent_name,
            reason=f"超过最大重试次数 {node.max_retries}：{last_error_message}",
        )

    async def _save_loop_result(self, node: LoopNode, result: AgentResult) -> None:
        """保存循环节点输出到群聊历史。

        将节点输出渲染为带循环标记的消息格式，然后保存到群聊历史。
        渲染格式：[循环-节点{agent_name}-第{iteration}轮] @loop {content}

        Args:
            node: 节点定义。
            result: Agent 执行结果。

        Raises:
            ValueError: runtime 未注入时抛出。
        """
        if self.runtime is None:
            raise ValueError("LoopExecutor 未注入 runtime，无法保存循环结果")
        result.text = render_for_chat(
            node.agent_name,
            "loop",
            result.text,
            is_loop_message=True,
            loop_iteration=self.loop.current_iteration,
        )
        await self.runtime.add_message(result)
