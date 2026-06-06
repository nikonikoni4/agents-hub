"""
群聊会话

管理群聊的消息历史和元数据。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class AgentContextState:
    """Agent 的上下文加载状态"""

    last_loaded_compact_index: int = 0  # 已加载到第几条压缩历史
    last_loaded_message_index: int = 0  # 已加载到第几条原始消息


@dataclass
class AgentMemberInfo:
    """Agent 的会话信息"""

    main_session: str | None = None  # 主会话 ID
    btw_session: list[str] = field(default_factory=list)  # by the way session 列表
    context_state: AgentContextState = field(default_factory=AgentContextState)  # 上下文加载状态
    token: str = ""  # Agent 的 token，用于 MCP 工具身份验证
    cwd: str = ""  # CLI 命令启动的工作目录路径
    use_docker: bool = False  # 是否使用 Docker 沙箱执行


@dataclass
class GroupChatSession:
    """
    群聊会话

    用于管理群聊的消息历史，对于每个 agent 的单聊和具体内容由各自的平台管理。
    """

    # TODO 缺乏锁
    group_chat_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = field(default_factory=lambda: f"session_{datetime.now().strftime('%Y%m%d%H%M')}")
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_compacted_loc: int = 0  # 上一次 compact 的位置
    next_message_id: int = 1  # 下一个可用的消息 id

    def add_message(self, agent_result):
        """
        添加消息到历史记录

        Args:
            agent_result: Agent 执行结果（AgentResult）
                需要包含: agent_name, text, timestamp, platform
        """
        self.messages.append(
            {
                "id": self.next_message_id,
                "agent_name": agent_result.agent_name,
                "content": agent_result.text,
                "timestamp": agent_result.timestamp,
                "platform": agent_result.platform.value,
            }
        )
        self.next_message_id += 1

    def get_uncompact_messages(self) -> list[dict]:
        """
        获取未压缩的消息

        Returns:
            list[dict]: 从 last_compacted_loc 到最新的消息列表
        """
        return self.messages[self.last_compacted_loc :]
