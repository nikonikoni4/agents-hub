"""Codex CLI 输出解析器"""

import json
from typing import Optional
from .base import AgentEvent, AgentEventType


class CodexParser:
    """解析 Codex CLI 的流式输出"""

    def parse_event(self, raw_line: str) -> Optional[AgentEvent]:
        """
        解析单行 JSON 事件

        Codex 流式输出事件类型：
        - item.completed (agent_message) -> text_delta
        - item.completed (command_execution) -> tool_use
        - turn.completed -> turn_complete
        """
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError:
            return None

        event_type = event.get("type")

        # 项目完成事件
        if event_type == "item.completed":
            return self._parse_item_completed(event)

        # 回合完成事件
        if event_type == "turn.completed":
            return self._parse_turn_completed(event)

        return None

    def _parse_item_completed(self, event: dict) -> Optional[AgentEvent]:
        """解析项目完成事件"""
        item = event.get("item", {})
        item_type = item.get("type")

        # Codex CLI 的 JSON 输出使用 thread_id 作为会话标识
        session_id = event.get("thread_id", "")

        # Agent 消息
        if item_type == "agent_message":
            return AgentEvent(
                type=AgentEventType.TEXT_DELTA,
                data={"text": item.get("text", "")},
                session_id=session_id,
                timestamp=""
            )

        # 命令执行
        if item_type == "command_execution":
            return AgentEvent(
                type=AgentEventType.TOOL_USE,
                data={
                    "command": item.get("command", ""),
                    "output": item.get("aggregated_output", ""),
                    "exit_code": item.get("exit_code"),
                    "status": item.get("status", ""),
                },
                session_id=session_id,
                timestamp=""
            )

        return None

    def _parse_turn_completed(self, event: dict) -> Optional[AgentEvent]:
        """解析回合完成事件"""
        usage = event.get("usage", {})
        return AgentEvent(
            type=AgentEventType.TURN_COMPLETE,
            data={"usage": usage},
            session_id=event.get("thread_id", ""),
            timestamp=""
        )
