"""Executor 和 Parser 协议定义"""

from typing import Protocol, AsyncIterator, Optional
from agents_hub.agent_bridge.config import RoleConfig
from agents_hub.agent_bridge.parsers.base import AgentEvent


class Executor(Protocol):
    """执行器协议：负责启动 CLI 并返回原始输出流"""

    async def execute(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        启动 CLI 并返回原始输出流

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选，用于恢复已有会话或指定新会话 ID）

        Returns:
            AsyncIterator[str]: 原始 JSON 字符串流（每行一个事件）
        """
        ...


class Parser(Protocol):
    """解析器协议：负责解析原始输出为统一格式"""

    def parse_event(self, raw_line: str) -> Optional[AgentEvent]:
        """
        解析单行 JSON 事件

        Args:
            raw_line: 原始 JSON 字符串

        Returns:
            Optional[AgentEvent]: 统一格式的事件（如果无法解析则返回 None）
        """
        ...
