"""Agent Bridge 核心数据模型

StreamEvent、AgentResult 等数据传输格式定义。
"""

from dataclasses import dataclass
from enum import Enum

from agents_hub.config.types import AgentPlatform, RoleType


class AgentEventType(Enum):
    """事件类型枚举（agent_bridge 特有），避免字符串拼写错误"""

    INIT = "init"  # 会话开始元数据
    TEXT_DELTA = "text_delta"  # 文本增量（流式输出的主要内容）
    TOOL_USE = "tool_use"  # 工具调用（命令执行）
    TURN_COMPLETE = "turn_complete"  # 回合完成（包含 token 使用统计）
    RESULT = "result"  # 完整结果（非流式输出）


@dataclass
class StreamEvent:
    """流式事件格式（TEXT_DELTA、TOOL_USE、TURN_COMPLETE 等）"""

    type: AgentEventType  # 事件类型（使用枚举）
    content: dict  # 具体数据
    session_id: str  # 会话 ID
    timestamp: str  # 时间戳
    agent_name: str  # 当前 agent 名称
    platform: AgentPlatform  # agent 所属平台
    role_type: RoleType  # 角色类型


@dataclass
class AgentResult:
    """完整结果格式（非流式调用的返回值）"""

    text: str  # 完整文本
    session_id: str  # 会话 ID
    timestamp: str  # 时间戳
    agent_name: str  # 当前 agent 名称
    platform: AgentPlatform  # agent 所属平台
    role_type: RoleType  # 角色类型
    usage: dict | None = None  # token 使用统计


# 向后兼容别名（待废弃）
AgentEvent = StreamEvent
