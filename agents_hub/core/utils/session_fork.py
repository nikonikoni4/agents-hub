"""Session fork 工具 - 复制并创建新会话"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from agents_hub.utils.logger import get_logger
from agents_hub.utils.session_parser import load_jsonl

logger = get_logger(__name__)


def fork_codex_session(session_id: str, session_path: str) -> str:
    """复制会话文件并创建新会话 ID

    Args:
        session_id: 原会话 ID
        session_path: 原会话文件路径

    Returns:
        新会话 ID

    Raises:
        FileNotFoundError: 会话文件不存在
    """
    src = Path(session_path)
    if not src.exists():
        raise FileNotFoundError(f"Session file not found: {session_path}")

    # 生成新 ID 和时间戳
    new_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

    # 构造新文件名
    new_name = f"rollout-{now}-{new_id}.jsonl"
    dst = src.parent / new_name

    # 读取原文件并修改
    messages = load_jsonl(src)
    modified = []
    for msg in messages:
        # 修改 session_meta 中的 id 和 forked_from_id
        if msg.get("type") == "session_meta":
            payload = msg.get("payload", {})
            payload["forked_from_id"] = payload.get("id", session_id)
            payload["id"] = new_id
            payload["timestamp"] = datetime.now(timezone.utc).isoformat()
            msg["payload"] = payload
            msg["timestamp"] = datetime.now(timezone.utc).isoformat()
        modified.append(msg)

    # 写入新文件
    with open(dst, "w", encoding="utf-8") as f:
        for msg in modified:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    logger.info("Forked session %s -> %s", session_id, new_id)
    return new_id
