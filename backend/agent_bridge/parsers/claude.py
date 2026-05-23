"""Claude CLI 输出解析器"""

import json
from typing import Optional
from .base import AgentEvent, AgentEventType


class ClaudeParser:
    """解析 Claude CLI 的流式输出"""

    def parse_event(self, raw_line: str) -> Optional[AgentEvent]:
        """
        解析单行 JSON 事件

        Claude 流式输出事件类型：
        - stream_event.content_block_delta → text_delta
        - system.init → init
        """
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError:
            return None

        event_type = event.get("type")
        session_id = event.get("session_id", "")

        # 流式文本事件
        if event_type == "stream_event":
            return self._parse_stream_event(event, session_id)

        # 系统事件
        if event_type == "system":
            return self._parse_system_event(event, session_id)

        return None

    def _parse_stream_event(self, event: dict, session_id: str) -> Optional[AgentEvent]:
        """解析流式事件"""
        inner_event = event.get("event", {})
        inner_type = inner_event.get("type")

        # 文本增量
        if inner_type == "content_block_delta":
            delta = inner_event.get("delta", {})
            if delta.get("type") == "text_delta":
                return AgentEvent(
                    type=AgentEventType.TEXT_DELTA,
                    data={"text": delta.get("text", "")},
                    session_id=session_id,
                    timestamp=""
                )

        return None

    def _parse_system_event(self, event: dict, session_id: str) -> Optional[AgentEvent]:
        """解析系统事件"""
        subtype = event.get("subtype")

        # 初始化事件
        if subtype == "init":
            return AgentEvent(
                type=AgentEventType.INIT,
                data={
                    "model": event.get("model", ""),
                    "tools": event.get("tools", []),
                },
                session_id=session_id,
                timestamp=""
            )

        return None
