"""Loop 执行器。

当前切片只实现循环消息上下文构造和消息封装，核心调度逻辑在后续切片补齐。
"""

from agents_hub.core.context.group_chat_session import Loop, LoopNode
from agents_hub.core.foundation import AgentMessage, MessageType, SessionType
from agents_hub.core.foundation.models import LoopNodeType
from agents_hub.core.foundation.renderer import Tag, render_for_chat, wrap_xml


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

    def __init__(self, loop: Loop, runtime=None):
        self.loop = loop
        self.runtime = runtime

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
                "loop_context": loop_context,
                "is_loop_message": True,
                "loop_iteration": self.loop.current_iteration,
            },
        )

    async def _save_loop_result(self, node: LoopNode, result) -> None:
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
