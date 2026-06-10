"""Claude CLI 输出解析器"""

import json
import logging
from datetime import datetime

from agents_hub.agent_bridge.exceptions import ParseError
from agents_hub.agent_bridge.models import AgentEventType, StreamEvent
from agents_hub.config.types import AgentPlatform, RoleType

logger = logging.getLogger(__name__)


class ClaudeParser:
    """解析 Claude CLI 的流式输出"""

    # 工具调用解析开关
    ENABLE_TOOL_USE_PARSING = True

    def __init__(self):
        self._tool_use_blocks: dict[int, dict] = {}

    def parse_event(self, raw_line: str) -> StreamEvent | None:
        """
        解析单行 JSON 事件

        Claude 流式输出事件类型：
        - stream_event.content_block_delta → TEXT_DELTA
        - stream_event.message_delta → TURN_COMPLETE (含 usage)
        - system.init → INIT
        """
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Claude output: {e}")
            raise ParseError(
                platform="Claude", raw_line=raw_line, reason=f"JSON decode error: {str(e)}"
            ) from e

        event_type = event.get("type")
        session_id = event.get("session_id", "")

        # 流式文本事件
        if event_type == "stream_event":
            return self._parse_stream_event(event, session_id)

        # 系统事件
        if event_type == "system":
            return self._parse_system_event(event, session_id)

        # 结果事件（包含真实 usage 数据）
        if event_type == "result":
            return self._parse_result_event(event, session_id)

        return None

    def _parse_stream_event(self, event: dict, session_id: str) -> StreamEvent | None:
        """解析流式事件"""
        inner_event = event.get("event", {})
        inner_type = inner_event.get("type")

        # 内容块开始：捕获 tool_use 块
        if inner_type == "content_block_start":
            return self._handle_content_block_start(inner_event, session_id)

        # 内容增量
        if inner_type == "content_block_delta":
            return self._handle_content_block_delta(inner_event, session_id)

        # 内容块结束：emit 缓存的 tool_use 事件
        if inner_type == "content_block_stop":
            return self._handle_content_block_stop(inner_event, session_id)

        # 消息结束：提取 usage 信息
        if inner_type == "message_delta":
            return self._handle_message_delta(inner_event, session_id)

        return None

    def _handle_content_block_start(self, inner_event: dict, session_id: str) -> StreamEvent | None:
        """处理 content_block_start：缓存 tool_use 块"""
        content_block = inner_event.get("content_block", {})
        if content_block.get("type") == "tool_use" and self.ENABLE_TOOL_USE_PARSING:
            index = inner_event.get("index", 0)
            self._tool_use_blocks[index] = {
                "id": content_block.get("id", ""),
                "name": content_block.get("name", ""),
                "input_parts": [],
            }
        return None

    def _handle_content_block_delta(self, inner_event: dict, session_id: str) -> StreamEvent | None:
        """处理 content_block_delta：文本增量或工具输入增量"""
        delta = inner_event.get("delta", {})
        delta_type = delta.get("type")

        if delta_type == "text_delta":
            return StreamEvent(
                type=AgentEventType.TEXT_DELTA,
                content={"text": delta.get("text", "")},
                session_id=session_id,
                timestamp=datetime.now().isoformat(),
                agent_name="",
                platform=AgentPlatform.CLAUDE,
                role_type=RoleType.TEAM_MEMBER,
            )

        if delta_type == "input_json_delta":
            index = inner_event.get("index", 0)
            if index in self._tool_use_blocks:
                self._tool_use_blocks[index]["input_parts"].append(delta.get("partial_json", ""))

        return None

    def _handle_content_block_stop(self, inner_event: dict, session_id: str) -> StreamEvent | None:
        """处理 content_block_stop：emit 缓存的 tool_use 事件"""
        index = inner_event.get("index", 0)
        block = self._tool_use_blocks.pop(index, None)
        if block is None:
            return None

        try:
            input_data = json.loads("".join(block["input_parts"])) if block["input_parts"] else {}
        except json.JSONDecodeError:
            input_data = {}

        return StreamEvent(
            type=AgentEventType.TOOL_USE,
            content={
                "tool_id": block["id"],
                "tool_name": block["name"],
                "input": input_data,
            },
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            agent_name="",
            platform=AgentPlatform.CLAUDE,
            role_type=RoleType.TEAM_MEMBER,
        )

    def _handle_message_delta(self, inner_event: dict, session_id: str) -> StreamEvent | None:
        """
        处理 message_delta：提取 usage 信息并生成 TURN_COMPLETE 事件

        Claude API message_delta.usage 字段格式：
        {
            "input_tokens": int,                    # 输入 token 数
            "output_tokens": int,                   # 输出 token 数
            "cache_creation_input_tokens": int,     # 缓存创建的输入 token
            "cache_read_input_tokens": int          # 缓存读取的输入 token
        }

        原始事件结构：
        {
            "type": "stream_event",
            "event": {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn"},
                "usage": { ... }
            },
            "session_id": "..."
        }
        """
        usage = inner_event.get("usage", {})
        return StreamEvent(
            type=AgentEventType.TURN_COMPLETE,
            content={"usage": usage},
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            agent_name="",
            platform=AgentPlatform.CLAUDE,
            role_type=RoleType.TEAM_MEMBER,
        )

    def _parse_system_event(self, event: dict, session_id: str) -> StreamEvent | None:
        """解析系统事件"""
        subtype = event.get("subtype")

        # 初始化事件
        if subtype == "init":
            return StreamEvent(
                type=AgentEventType.INIT,
                content={
                    "model": event.get("model", ""),
                    "tools": event.get("tools", []),
                },
                session_id=session_id,
                timestamp=datetime.now().isoformat(),
                agent_name="",  # 将在 bridge 中填充
                platform=AgentPlatform.CLAUDE,
                role_type=RoleType.TEAM_MEMBER,  # 默认值，将在 bridge 中更新
            )

        return None

    def _parse_result_event(self, event: dict, session_id: str) -> StreamEvent | None:
        """
        处理 result 事件：提取 usage 信息并生成 TURN_COMPLETE 事件

        CLI --output-format stream-json 输出的 result 事件格式：
        {
            "type": "result",
            "subtype": "success",
            "usage": {
                "input_tokens": int,
                "output_tokens": int,
                "cache_read_input_tokens": int,
                ...
            },
            "session_id": "..."
        }
        """
        usage = event.get("usage", {})
        return StreamEvent(
            type=AgentEventType.TURN_COMPLETE,
            content={"usage": usage},
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            agent_name="",
            platform=AgentPlatform.CLAUDE,
            role_type=RoleType.TEAM_MEMBER,
        )
