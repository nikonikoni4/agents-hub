"""Codex CLI 输出解析器"""

import json
import logging
from datetime import datetime

from agents_hub.agent_bridge.exceptions import ParseError
from agents_hub.agent_bridge.models import AgentEventType, StreamEvent
from agents_hub.config.types import AgentPlatform, RoleType

logger = logging.getLogger(__name__)


class CodexParser:
    """解析 Codex CLI 的流式输出"""

    def __init__(self, usage_baseline: dict | None = None):
        self._thread_id: str = ""
        self._usage_baseline = usage_baseline or {}

    def parse_event(self, raw_line: str) -> StreamEvent | None:
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
                platform="Codex", raw_line=raw_line, reason=f"JSON decode error: {str(e)}"
            ) from e

        event_type = event.get("type")

        # 线程开始事件：记录 thread_id 并生成 INIT 事件
        if event_type == "thread.started":
            self._thread_id = event.get("thread_id", "")
            return StreamEvent(
                type=AgentEventType.INIT,
                content={},
                session_id=self._thread_id,
                timestamp=datetime.now().isoformat(),
                agent_name="",
                platform=AgentPlatform.CODEX,
                role_type=RoleType.TEAM_MEMBER,
            )

        # 项目完成事件
        if event_type == "item.completed":
            return self._parse_item_completed(event)

        # 回合完成事件
        if event_type == "turn.completed":
            return self._parse_turn_completed(event)

        return None

    def _parse_item_completed(self, event: dict) -> StreamEvent | None:
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
                role_type=RoleType.TEAM_MEMBER,  # 默认值，将在 bridge 中更新
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
                role_type=RoleType.TEAM_MEMBER,  # 默认值，将在 bridge 中更新
            )

        return None

    def _parse_turn_completed(self, event: dict) -> StreamEvent | None:
        """解析回合完成事件

        Codex turn.completed 事件的 usage 字段结构：
        {
            "input_tokens": int,          # session 累计输入 token 数，不是最后一次 LLM 调用输入
            "cached_input_tokens": int,   # 缓存的输入 token 数
            "output_tokens": int,         # 输出 token 数
            "reasoning_output_tokens": int # 推理输出 token 数（思维链）
        }

        注意：usage 数据最终会传递到 AgentResult.usage
        """
        usage = event.get("usage", {})
        if self._usage_baseline:
            usage = self._usage_delta(usage)
        return StreamEvent(
            type=AgentEventType.TURN_COMPLETE,
            content={"usage": usage},
            session_id=event.get("thread_id", ""),
            timestamp=datetime.now().isoformat(),
            agent_name="",  # 将在 bridge 中填充
            platform=AgentPlatform.CODEX,
            role_type=RoleType.TEAM_MEMBER,  # 默认值，将在 bridge 中更新
        )

    def _usage_delta(self, usage: dict) -> dict:
        """Codex resume 的 turn.completed usage 是累计值，转成本轮用量。

        `codex exec --json` stdout 没有 last_token_usage；该字段只写入
        session JSONL。bridge 在启动 CLI 前读取执行前累计值作为 baseline，
        parser 在 turn.completed 到达时做差分，避免把累计 token 当作窗口占用。

        """
        result = dict(usage)
        for key in (
            "input_tokens",
            "cached_input_tokens",
            "output_tokens",
            "reasoning_output_tokens",
            "total_tokens",
        ):
            if key in usage:
                result[key] = max(0, usage.get(key, 0) - self._usage_baseline.get(key, 0))
        return result
