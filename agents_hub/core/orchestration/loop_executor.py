"""Loop 执行器。"""

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
    """将循环消息完成事件投递给 LoopExecutor 调度队列。"""
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
    """循环执行器。"""

    TERMINATION_CHECK_PROMPT = (
        "这是 TERMINATOR 节点。请基于上一节点输出判断循环是否继续。\n\n"
        "你必须在输出末尾包含以下 XML 标签，明确表示循环是否继续：\n\n"
        "<loop_decision>\n"
        "  <should_continue>true</should_continue>\n"
        "  <reason>继续/结束的原因</reason>\n"
        "</loop_decision>\n\n"
        "如果缺少此标签，系统会要求你重新输出。"
    )

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
        """构造循环专用上下文，隔离群聊历史。"""
        sections = [
            wrap_xml(Tag.LOOP_NODE_ROLE, node.role_description),
            wrap_xml(Tag.LOOP_OUTPUT_SCHEMA, node.output_schema_prompt or ""),
            wrap_xml(Tag.PREVIOUS_NODE_OUTPUT, previous_output),
        ]
        if node.node_type == LoopNodeType.TERMINATOR.value:
            sections.append(wrap_xml(Tag.LOOP_TERMINATION_CHECK, self.TERMINATION_CHECK_PROMPT))
        return "\n\n".join(sections)

    def _build_loop_message(self, node: LoopNode, previous_output: str) -> AgentMessage:
        """构造循环内部消息。"""
        loop_context = self._build_loop_context(node, previous_output)
        return AgentMessage(
            call_id=f"{self.loop.loop_id}:{node.node_id}:{self.loop.current_iteration}",
            content=loop_context,
            send_from="loop",
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
        """构造可复用 call_id 的循环节点消息。"""
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
        """校验节点输出是否包含所有必需字段。"""
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
        """校验 TERMINATOR 输出并解析 should_continue。"""
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
        """按节点类型校验输出。"""
        if node.node_type == LoopNodeType.TERMINATOR.value:
            return self._validate_terminator_output(output, node)

        is_valid, error_message = self._validate_schema_fields(output, node.output_schema_fields)
        return is_valid, error_message, None

    async def _wait_for_node_result(self, call_id: str) -> AgentResult:
        """等待指定 call_id 的循环节点输出。"""
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
        """从完成队列接收一个通知，并交给节点完成处理入口。"""
        if self.completion_queue is None:
            raise ValueError("LoopExecutor 未注入 completion_queue，无法接收节点完成通知")

        notification = await asyncio.wait_for(
            self.completion_queue.get(),
            timeout=self.node_result_timeout_seconds,
        )
        await self._handle_node_completion(notification)
        return notification

    async def _handle_node_completion(self, notification: dict) -> None:
        """处理节点完成通知并调度下一个节点。"""
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
        """运行循环主调度。"""
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
        """创建 AgentCall 并发送 LOOP_MESSAGE。"""
        if self.send_message_callback is None:
            raise ValueError("LoopExecutor 未注入 send_message_callback，无法发送循环消息")

        message = self._build_loop_message(node, previous_output)
        if self.agent_call_manager is not None:
            call = await self.agent_call_manager.create_call(
                send_from="loop",
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
        """推进到下一个节点，完成一轮后递增轮次。"""
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
        """检查循环退出条件。"""
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
        """处理等待节点完成通知超时。"""
        node = self.loop.nodes[self.loop.current_node_index]
        status = None
        if self.runtime is not None:
            agent_info = self.runtime.get_agent_member_info(node.agent_name)
            status = getattr(agent_info, "status", None) if agent_info else None
        reason = "Agent CLI 执行失败" if status == "error" else "节点执行超时"
        await self._emergency_stop(reason)

    async def _emergency_stop(self, reason: str) -> None:
        """异常停止循环并清理资源。"""
        self.loop.status = LoopStatus.FAILED.value
        self.loop.error_message = reason
        self.loop.updated_at = datetime.now()
        self.logger.error("Loop 执行失败: loop_id=%s, reason=%s", self.loop.loop_id, reason)
        await self._cleanup()

    async def _cleanup(self) -> None:
        """清理循环运行资源并持久化最终状态。"""
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
        """执行节点并在输出格式错误时自动重试。"""
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
        """保存循环节点输出到群聊历史。"""
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
