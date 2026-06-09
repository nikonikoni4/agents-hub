"""OpenCode CLI 输出解析器"""

import json
import logging
from datetime import datetime

from agents_hub.agent_bridge.exceptions import ParseError
from agents_hub.agent_bridge.models import AgentEventType, StreamEvent
from agents_hub.config.types import AgentPlatform, RoleType

logger = logging.getLogger(__name__)


class OpenCodeParser:
    """解析 OpenCode CLI 的流式输出"""

    def parse_event(self, raw_line: str) -> StreamEvent | None:
        """
        解析单行 JSON 事件

        OpenCode 流式输出事件类型：
        - step_start -> INIT
        - text -> TEXT_DELTA
        - step_finish -> TURN_COMPLETE
        """
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse OpenCode output: {e}")
            raise ParseError(
                platform="OpenCode", raw_line=raw_line, reason=f"JSON decode error: {str(e)}"
            ) from e

        event_type = event.get("type", "")
        session_id = event.get("sessionID", "")
        part = event.get("part", {})
        timestamp = event.get("timestamp", 0)

        # 步骤开始事件
        if event_type == "step_start":
            return StreamEvent(
                type=AgentEventType.INIT,
                content={
                    "model": "",
                    "tools": [],
                },
                session_id=session_id,
                timestamp=datetime.fromtimestamp(timestamp / 1000).isoformat()
                if timestamp
                else datetime.now().isoformat(),
                agent_name="",
                platform=AgentPlatform.OPENCODE,
                role_type=RoleType.TEAM_MEMBER,
            )

        # 文本增量事件
        if event_type == "text":
            return StreamEvent(
                type=AgentEventType.TEXT_DELTA,
                content={"text": part.get("text", "")},
                session_id=session_id,
                timestamp=datetime.fromtimestamp(timestamp / 1000).isoformat()
                if timestamp
                else datetime.now().isoformat(),
                agent_name="",
                platform=AgentPlatform.OPENCODE,
                role_type=RoleType.TEAM_MEMBER,
            )

        # 步骤完成事件
        if event_type == "step_finish":
            tokens = part.get("tokens", {})
            return StreamEvent(
                type=AgentEventType.TURN_COMPLETE,
                content={
                    "usage": {
                        "input_tokens": tokens.get("input", 0),
                        "output_tokens": tokens.get("output", 0),
                        "total_tokens": tokens.get("total", 0),
                        "cache_read": tokens.get("cache", {}).get("read", 0),
                        "cache_write": tokens.get("cache", {}).get("write", 0),
                    },
                    "cost": part.get("cost", 0),
                    "reason": part.get("reason", ""),
                },
                session_id=session_id,
                timestamp=datetime.fromtimestamp(timestamp / 1000).isoformat()
                if timestamp
                else datetime.now().isoformat(),
                agent_name="",
                platform=AgentPlatform.OPENCODE,
                role_type=RoleType.TEAM_MEMBER,
            )

        return None
