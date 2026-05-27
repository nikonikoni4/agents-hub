"""Agent Bridge 核心数据模型

合并原 config.py（平台枚举、CLI 路径）和 parsers/base.py（事件类型），
消除交叉引用，作为 agent_bridge 子系统的 SSOT。
"""

from enum import Enum
from pathlib import Path
from typing import TypedDict

# CLI 命令路径
CODEX_COMMAND = str(Path.home() / "AppData" / "Roaming" / "npm" / "codex.cmd")
CLAUDE_COMMAND = str(Path.home() / ".local" / "bin" / "claude")


# ── 平台枚举 ──────────────────────────────────────────────

class AgentPlatform(Enum):
    """Agent 平台枚举"""
    CLAUDE = "claude"
    CODEX = "codex"


# ── 事件类型 ──────────────────────────────────────────────

class AgentEventType(Enum):
    """事件类型枚举，避免字符串拼写错误"""
    INIT = "init"                       # 会话开始元数据
    TEXT_DELTA = "text_delta"           # 文本增量（流式输出的主要内容）
    TOOL_USE = "tool_use"               # 工具调用（命令执行）
    TURN_COMPLETE = "turn_complete"     # 回合完成（包含 token 使用统计）
    RESULT = "result"                   # 完整结果（非流式输出）


class AgentEvent(TypedDict):
    """统一事件格式"""
    type: AgentEventType        # 事件类型（使用枚举）
    content: dict               # 具体数据
    session_id: str             # 会话 ID
    timestamp: str              # 时间戳
    agent_name: str             # 当前 agent 名称
    platform: AgentPlatform     # agent 所属平台
