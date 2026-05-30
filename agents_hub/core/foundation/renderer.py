"""
渲染层 - AgentMessage 与可读字符串之间的对偶转换

约束：
- AgentMessage.content 在 Agent 之间投递时始终是原始内容，不被就地改写
- 渲染只发生在三个边界：
    1. 入口（前端→AgentMessage）：parse_chat_input
    2. LLM 出口（AgentMessage→LLM prompt）：render_for_llm
    3. jsonl/UI 出口（Agent 输出→群聊记录）：render_for_chat
"""
import re

from .message import AgentMessage
from .exceptions import InvalidMessageError


_AT_PATTERN = re.compile(r"^\s*@(\S+)\s*(.*)$", re.DOTALL)


def render_for_llm(msg: AgentMessage) -> str:
    """AgentMessage → 喂给 LLM 的 prompt 字符串"""
    return f"[{msg.send_from}] 发送消息给 [{msg.send_to}(你)]: {msg.content}"


def render_for_chat(send_from: str, send_to: str, content: str) -> str:
    """Agent 输出 → 写入 jsonl/UI 的群聊字符串

    Args:
        send_from: 当前发言的 agent（用于将来扩展元数据，当前 jsonl 由 agent_name 字段承载来源）
        send_to: 这条群聊记录在 @ 谁
        content: 原始内容
    """
    return f"@{send_to} {content}"


def parse_chat_input(raw: str) -> tuple[str, str]:
    """前端原始输入 → (send_to, content)

    输入必须以 @xxx 开头。解析失败抛 InvalidMessageError。
    """
    match = _AT_PATTERN.match(raw)
    if not match:
        raise InvalidMessageError(reason="输入必须以 @xxx 开头")
    send_to, content = match.group(1), match.group(2)
    if not send_to:
        raise InvalidMessageError(reason="@ 后必须跟 agent 名称")
    return send_to, content
