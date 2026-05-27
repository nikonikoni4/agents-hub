"""AgentBridge 统一接口"""

from datetime import datetime
from typing import AsyncIterator, Optional
from agents_hub.agent_bridge.models import AgentPlatform, AgentEvent, AgentEventType
from agents_hub.roles.models import RoleConfig
from agents_hub.agent_bridge.executors.claude import ClaudeExecutor
from agents_hub.agent_bridge.executors.codex import CodexExecutor
from agents_hub.agent_bridge.parsers.claude import ClaudeParser
from agents_hub.agent_bridge.parsers.codex import CodexParser


class AgentBridge:
    """统一的 Agent 调用接口"""

    def __init__(self):
        # 创建执行器和解析器实例（可复用）
        self._executors = {
            AgentPlatform.CLAUDE: ClaudeExecutor(),
            AgentPlatform.CODEX: CodexExecutor()
        }
        self._parsers = {
            AgentPlatform.CLAUDE: ClaudeParser(),
            AgentPlatform.CODEX: CodexParser()
        }

    async def execute_stream(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: Optional[str] = None
    ) -> AsyncIterator[AgentEvent]:
        """
        流式执行 Agent 调用（给人看）

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选，用于恢复之前的会话）

        Yields:
            AgentEvent: 统一格式的事件流
        """
        executor = self._executors[config.platform]
        parser = self._parsers[config.platform]

        raw_stream = executor.execute(prompt, config, session_id)
        async for raw_line in raw_stream:
            if raw_line.strip():
                parsed_event = parser.parse_event(raw_line)
                if parsed_event is not None:
                    parsed_event["agent_name"] = config.name
                    parsed_event["platform"] = config.platform
                    yield parsed_event

    async def execute(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: Optional[str] = None
    ) -> AgentEvent:
        """
        非流式执行，返回完整结果（给 A2A 用）

        内部复用 execute_stream()，拼接所有 text_delta 后返回单个 RESULT 事件。

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选）

        Returns:
            AgentEvent: type 为 AgentEventType.RESULT 的完整结果事件
        """
        full_text = []
        usage = None
        result_session_id = session_id or ""

        async for event in self.execute_stream(prompt, config, session_id):
            if event["type"] == AgentEventType.TEXT_DELTA:
                full_text.append(event["content"]["text"])
            elif event["type"] == AgentEventType.TURN_COMPLETE:
                usage = event["content"].get("usage")
            # 记录第一个返回的 session_id
            if not result_session_id and event.get("session_id"):
                result_session_id = event["session_id"]

        return AgentEvent(
            type=AgentEventType.RESULT,
            content={"text": "".join(full_text), "usage": usage},
            session_id=result_session_id,
            timestamp=datetime.now().isoformat(),
            agent_name=config.name,
            platform=config.platform,
        )
