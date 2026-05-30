"""Codex CLI 输出解析器"""

import json
import logging
from datetime import datetime
from typing import Optional
from agents_hub.agent_bridge.models import StreamEvent, AgentEventType
from agents_hub.config.types import AgentPlatform, RoleType
from agents_hub.agent_bridge.exceptions import ParseError

logger = logging.getLogger(__name__)


class CodexParser:
    """解析 Codex CLI 的流式输出"""

    def __init__(self):
        self._thread_id: str = ""

    def parse_event(self, raw_line: str) -> Optional[StreamEvent]:
        """
        解析单行 JSON 事件

        Codex 流式输出事件类型：
        - thread.started -> 记录 thread_id（会话标识）
        - item.completed (agent_message) -> text_delta
        - item.completed (command_execution) -> tool_use
        - turn.completed -> turn_complete
        """
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Codex output: {e}")
            raise ParseError(
                platform="Codex",
                raw_line=raw_line,
                reason=f"JSON decode error: {str(e)}"
            ) from e

        event_type = event.get("type")

        # 线程开始事件：记录 thread_id
        if event_type == "thread.started":
            self._thread_id = event.get("thread_id", "")
            return None

        # 项目完成事件
        if event_type == "item.completed":
            return self._parse_item_completed(event)

        # 回合完成事件
        if event_type == "turn.completed":
            return self._parse_turn_completed(event)

        return None

    def _parse_item_completed(self, event: dict) -> Optional[StreamEvent]:
        """解析项目完成事件"""
        item = event.get("item", {})
        item_type = item.get("type")

        # 优先使用事件自带的 thread_id，否则用缓存的
        session_id = event.get("thread_id", "") or self._thread_id

        # Agent 消息
        if item_type == "agent_message":
            return StreamEvent(
                type=AgentEventType.TEXT_DELTA,
                content={"text": item.get("text", "")},
                session_id=session_id,
                timestamp=datetime.now().isoformat(),
                agent_name="",  # 将在 bridge 中填充
                platform=AgentPlatform.CODEX,
                role_type=RoleType.TEAM_MEMBER  # 默认值，将在 bridge 中更新
            )

        # 命令执行
        if item_type == "command_execution":
            return StreamEvent(
                type=AgentEventType.TOOL_USE,
                content={
                    "command": item.get("command", ""),
                    "output": item.get("aggregated_output", ""),
                    "exit_code": item.get("exit_code"),
                    "status": item.get("status", ""),
                },
                session_id=session_id,
                timestamp=datetime.now().isoformat(),
                agent_name="",  # 将在 bridge 中填充
                platform=AgentPlatform.CODEX,
                role_type=RoleType.TEAM_MEMBER  # 默认值，将在 bridge 中更新
            )

        return None

    def _parse_turn_completed(self, event: dict) -> Optional[StreamEvent]:
        """解析回合完成事件"""
        usage = event.get("usage", {})
        return StreamEvent(
            type=AgentEventType.TURN_COMPLETE,
            content={"usage": usage},
            session_id=event.get("thread_id", ""),
            timestamp=datetime.now().isoformat(),
            agent_name="",  # 将在 bridge 中填充
            platform=AgentPlatform.CODEX,
            role_type=RoleType.TEAM_MEMBER  # 默认值，将在 bridge 中更新
        )
