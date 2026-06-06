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

from .exceptions import InvalidMessageError
from .message import AgentMessage

_AT_PATTERN = re.compile(
    r"^\s*@(\S+)\s*(.*)$", re.DOTALL
)  # TODO 需要避免前端连续@ 当前不支持@多个agent


# ====== 预定义 XML 标签 ======
# 喂给 LLM 的 prompt 中常用的结构标签。
# 命名规则：英文标签名（结构标记），保持平铺，避免不必要的层级嵌套。
class Tag:
    GROUP_HISTORY = "group_chat_history"  # 历史群聊摘要块
    RECENT_MESSAGES = "recent_messages"  # 群聊最新消息块
    INCOMING_MESSAGE = "incoming_message"  # 当前传入的消息（render_for_llm 输出）
    SUMMARY_OVERALL = "overall_summary"  # 摘要中的整体内容
    SUMMARY_FOR_YOU = "summary_for_you"  # 摘要中针对当前 agent 的内容


def wrap_xml(tag: str, content: str) -> str:
    """用 XML 标签包裹内容（单层，不嵌套）。

    Args:
        tag: 标签名。建议优先使用 Tag 常量，临时标签直接传字符串。
        content: 标签内的文本
    """
    return f"<{tag}>\n{content}\n</{tag}>"


def render_for_llm(msg: AgentMessage) -> str:
    """AgentMessage → 喂给 LLM 的 prompt 字符串（含 <incoming_message> 包裹）"""
    body = (
        f"[Agents Hub 平台消息]\n"
        f"来自：{msg.send_from}\n"
        f"发送给：{msg.send_to}（你）\n"
        f"内容：{msg.content}"
    )
    return wrap_xml(Tag.INCOMING_MESSAGE, body)


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
