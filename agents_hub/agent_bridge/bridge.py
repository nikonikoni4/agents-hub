"""AgentBridge 统一接口"""

import logging
from datetime import datetime
from typing import AsyncIterator, Optional
from agents_hub.config.types import AgentPlatform
from agents_hub.agent_bridge.models import StreamEvent, AgentResult, AgentEventType
from agents_hub.roles.models import RoleConfig
from agents_hub.agent_bridge.executors.claude import ClaudeExecutor
from agents_hub.agent_bridge.executors.codex import CodexExecutor
from agents_hub.agent_bridge.parsers.claude import ClaudeParser
from agents_hub.agent_bridge.parsers.codex import CodexParser
from agents_hub.agent_bridge.exceptions import (
    PlatformNotSupportedError,
    ParseError,
    CLINotFoundError,
    CLIExecutionError
)

logger = logging.getLogger(__name__)


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
    ) -> AsyncIterator[StreamEvent]:
        """
        流式执行 Agent 调用

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选，用于恢复之前的会话）

        Yields:
            StreamEvent: 统一格式的流式事件

        Raises:
            PlatformNotSupportedError: 平台不支持
            CLINotFoundError: CLI 命令不存在
            CLIExecutionError: CLI 执行失败
            ParseError: 解析错误
        """
        # 验证平台是否支持
        if config.platform not in self._executors:
            supported = [p.value for p in self._executors.keys()]
            raise PlatformNotSupportedError(
                platform=config.platform.value,
                supported_platforms=supported
            )

        executor = self._executors[config.platform]
        parser = self._parsers[config.platform]

        try:
            raw_stream = executor.execute(prompt, config, session_id)
            async for raw_line in raw_stream:
                if raw_line.strip():
                    try:
                        parsed_event = parser.parse_event(raw_line)
                        if parsed_event is not None:
                            parsed_event.agent_name = config.name
                            parsed_event.platform = config.platform
                            parsed_event.role_type = config.role_type
                            yield parsed_event
                    except ParseError:
                        # 解析错误：记录日志，跳过该行，继续处理
                        logger.warning(f"Skipping unparseable line from {config.platform.value}")
                        continue
        except (CLINotFoundError, CLIExecutionError):
            # CLI 错误：直接向上传递
            raise

    async def execute(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: Optional[str] = None
    ) -> AgentResult:
        """
        非流式执行，返回完整结果

        内部复用 execute_stream()，拼接所有 text_delta 后返回完整结果。

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选）

        Returns:
            AgentResult: 完整结果
        """
        full_text = []
        usage = None
        result_session_id = session_id or ""

        async for event in self.execute_stream(prompt, config, session_id):
            if event.type == AgentEventType.TEXT_DELTA:
                full_text.append(event.content["text"])
            elif event.type == AgentEventType.TURN_COMPLETE:
                usage = event.content.get("usage")
            # 记录第一个返回的 session_id
            if not result_session_id and event.session_id:
                result_session_id = event.session_id

        return AgentResult(
            text="".join(full_text),
            session_id=result_session_id,
            timestamp=datetime.now().isoformat(),
            agent_name=config.name,
            platform=config.platform,
            role_type=config.role_type,
            usage=usage
        )
