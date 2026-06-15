"""Session 文件解析器

解析 Claude Code 和 Codex 平台的 session 文件，返回统一格式的消息列表。
"""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from agents_hub.config.types import AgentPlatform
from agents_hub.utils.logger import get_logger

logger = get_logger(__name__)

_VALID_ROLES = frozenset({"user", "assistant", "system", "tool"})


class SessionMessage(BaseModel):
    """单聊消息类型"""

    id: str
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    timestamp: str
    model: str | None = None
    token_usage: dict | None = None


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
            for block in content_blocks:
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))

            if text_parts:
                result.append(
                    SessionMessage(
                        id=inner.get("id", msg.get("uuid", "")),
                        role="assistant",
                        content="\n".join(text_parts),
                        timestamp=timestamp,
                        model=inner.get("model"),
                    )
                )

    return result


def parse_codex_session(messages: list[dict]) -> list[SessionMessage]:
    """解析 Codex session 文件"""
    result = []

    for msg in messages:
        msg_type = msg.get("type")
        timestamp = msg.get("timestamp", "")

        if msg_type == "response_item":
            payload = msg.get("payload", {})
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
