"""Session 文件解析器

解析 Claude Code 和 Codex 平台的 session 文件，返回统一格式的消息列表。
"""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from agents_hub.config.types import AgentPlatform
from agents_hub.utils.logger import get_logger

logger = get_logger(__name__)

_VALID_ROLES = frozenset({"user", "assistant", "system", "tool"})


class ToolCallInfo(BaseModel):
    """工具调用信息"""

    id: str
    name: str
    input: dict = Field(default_factory=dict)


class SessionMessage(BaseModel):
    """单聊消息类型"""

    id: str
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    timestamp: str
    model: str | None = None
    token_usage: dict | None = None
    tool_calls: list[ToolCallInfo] | None = None


def load_jsonl(file_path: Path) -> list[dict]:
    """加载 JSONL 文件"""
    messages = []
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return messages


def parse_claude_session(messages: list[dict]) -> list[SessionMessage]:
    """解析 Claude Code session 文件"""
    result = []

    for msg in messages:
        msg_type = msg.get("type")
        timestamp = msg.get("timestamp", "")

        if msg_type == "user":
            content = msg.get("message", {}).get("content", "")
            if isinstance(content, str) and content:
                result.append(
                    SessionMessage(
                        id=msg.get("uuid", ""),
                        role="user",
                        content=content,
                        timestamp=timestamp,
                    )
                )

        elif msg_type == "assistant":
            inner = msg.get("message", {})
            content_blocks = inner.get("content", [])
            text_parts = []
            tool_calls = []
            for block in content_blocks:
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    tool_calls.append(
                        ToolCallInfo(
                            id=block.get("id", ""),
                            name=block.get("name", ""),
                            input=block.get("input", {}),
                        )
                    )

            if text_parts or tool_calls:
                result.append(
                    SessionMessage(
                        id=inner.get("id", msg.get("uuid", "")),
                        role="assistant",
                        content="\n".join(text_parts),
                        timestamp=timestamp,
                        model=inner.get("model"),
                        tool_calls=tool_calls if tool_calls else None,
                    )
                )

    return result


def parse_codex_session(messages: list[dict]) -> list[SessionMessage]:
    """解析 Codex session 文件

    Codex session 格式与 Claude 不同：
    - 工具调用是顶层 response_item（payload.type = "function_call"）
    - 参数是 JSON string（payload.arguments）
    - 通过 call_id 关联 function_call 和 function_call_output
    """
    result: list[SessionMessage] = []
    pending_tool_calls: dict[str, ToolCallInfo] = {}  # call_id -> ToolCallInfo

    for msg in messages:
        if msg.get("type") != "response_item":
            continue

        payload = msg.get("payload", {})
        payload_type = payload.get("type", "")
        timestamp = msg.get("timestamp", "")

        if payload_type == "message":
            role = payload.get("role", "")
            if role not in _VALID_ROLES:
                logger.debug("Skipping codex message with unknown role: %s", role)
                continue
            texts = []
            for block in payload.get("content", []):
                bt = block.get("type", "")
                if bt in ("input_text", "output_text"):
                    texts.append(block.get("text", ""))

            if texts:
                result.append(
                    SessionMessage(
                        id=payload.get("id", ""),
                        role=role,
                        content="\n".join(texts),
                        timestamp=timestamp,
                    )
                )

        elif payload_type == "function_call":
            call_id = payload.get("call_id", "")
            name = payload.get("name", "")
            try:
                args = json.loads(payload.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            pending_tool_calls[call_id] = ToolCallInfo(
                id=call_id,
                name=name,
                input=args,
            )

        elif payload_type == "function_call_output":
            call_id = payload.get("call_id", "")
            if call_id in pending_tool_calls:
                tc = pending_tool_calls.pop(call_id)
                # 关联到最近的 assistant 消息
                for msg_item in reversed(result):
                    if msg_item.role == "assistant":
                        if msg_item.tool_calls is None:
                            msg_item.tool_calls = []
                        msg_item.tool_calls.append(tc)
                        break

    return result


def parse_session_file(file_path: Path, platform: AgentPlatform) -> list[SessionMessage]:
    """
    解析 session 文件，返回统一格式的消息列表

    Args:
        file_path: session 文件路径
        platform: 平台类型

    Returns:
        SessionMessage 列表
    """
    messages = load_jsonl(file_path)

    if platform == AgentPlatform.CLAUDE:
        return parse_claude_session(messages)
    elif platform == AgentPlatform.CODEX:
        return parse_codex_session(messages)
    else:
        raise ValueError(f"Unsupported platform: {platform}")


def resolve_session_path(
    session_id: str, platform: AgentPlatform, work_root: str | None
) -> str | None:
    """根据 session_id 和平台查找会话文件路径

    Args:
        session_id: 会话 ID
        platform: 平台类型
        work_root: 角色工作根目录（RoleConfig.work_root）

    Returns:
        会话文件路径字符串，未找到返回 None
    """
    if not work_root:
        return None
    if platform == AgentPlatform.CLAUDE:
        search_dir = Path(work_root) / "projects"
    elif platform in (AgentPlatform.CODEX, AgentPlatform.OPENCODE):
        search_dir = Path(work_root) / "sessions"
    else:
        return None
    if not search_dir.exists():
        return None
    for f in search_dir.rglob(f"*{session_id}*.jsonl"):
        return str(f)
    return None
