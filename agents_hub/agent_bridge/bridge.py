"""AgentBridge 统一接口"""

import logging
from collections.abc import AsyncIterator
from datetime import datetime

from agents_hub.agent_bridge.exceptions import (
    CLIExecutionError,
    CLINotFoundError,
    ParseError,
    PlatformNotSupportedError,
)
from agents_hub.agent_bridge.executors.claude import ClaudeExecutor
from agents_hub.agent_bridge.executors.codex import CodexExecutor
from agents_hub.agent_bridge.executors.opencode import OpenCodeExecutor
from agents_hub.agent_bridge.models import AgentEventType, AgentResult, StreamEvent
from agents_hub.agent_bridge.parsers.claude import ClaudeParser
from agents_hub.agent_bridge.parsers.codex import CodexParser
from agents_hub.agent_bridge.parsers.opencode import OpenCodeParser
from agents_hub.config.types import AgentPlatform
from agents_hub.roles import RoleManager
from agents_hub.roles.models import RoleConfig

logger = logging.getLogger(__name__)

_BARE_ROLE_NAME = "bare_claude"


class AgentBridge:
    """统一的 Agent 调用接口"""

    def __init__(self):
        # 创建执行器和解析器实例（可复用）
        self._executors: dict[AgentPlatform, ClaudeExecutor | CodexExecutor | OpenCodeExecutor] = {
            AgentPlatform.CLAUDE: ClaudeExecutor(),
            AgentPlatform.CODEX: CodexExecutor(),
            AgentPlatform.OPENCODE: OpenCodeExecutor(),
        }
        self._parsers: dict[AgentPlatform, ClaudeParser | CodexParser | OpenCodeParser] = {
            AgentPlatform.CLAUDE: ClaudeParser(),
            AgentPlatform.CODEX: CodexParser(),
            AgentPlatform.OPENCODE: OpenCodeParser(),
        }

        # Docker manager 和 executors（延迟导入，避免循环依赖）
        from agents_hub.agent_bridge.docker.manager import DockerManager
        from agents_hub.agent_bridge.executors.docker_claude import DockerClaudeExecutor
        from agents_hub.agent_bridge.executors.docker_codex import DockerCodexExecutor

        self._docker_manager = DockerManager()
        self._docker_executors: dict[AgentPlatform, DockerClaudeExecutor | DockerCodexExecutor] = {
            AgentPlatform.CLAUDE: DockerClaudeExecutor(self._docker_manager),
            AgentPlatform.CODEX: DockerCodexExecutor(self._docker_manager),
        }

        self._role_manager = RoleManager()
        self._bare_config = self._init_bare_config()

    async def execute_stream(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None = None,
        cwd: str | None = None,
        fork_from: str | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """
        流式执行 Agent 调用

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选，用于恢复之前的会话）
            cwd: 项目目录路径（可选，设置 CLI 工作目录）
            fork_from: 源会话 ID（可选，用于从群聊 fork 会话到单聊）

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
            supported = [p.value for p in self._executors]
            raise PlatformNotSupportedError(
                platform=config.platform.value, supported_platforms=supported
            )

        executor = self._executors[config.platform]
        parser = self._parsers[config.platform]

        try:
            raw_stream = executor.execute(
                prompt, config, session_id, cwd, fork_from=fork_from, system_prompt=system_prompt
            )
            async for raw_line in raw_stream:
                # OpenCode executor 返回 dict，其他返回 str
                if isinstance(raw_line, dict):
                    # OpenCode 已经转换好的事件
                    parsed_event = self._dict_to_stream_event(raw_line, config)
                    if parsed_event is not None:
                        yield parsed_event
                elif isinstance(raw_line, str) and raw_line.strip():
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

    def _dict_to_stream_event(self, event_dict: dict, config: RoleConfig) -> StreamEvent | None:
        """将 dict 转换为 StreamEvent（用于 OpenCode）"""
        event_type = event_dict.get("type", "")

        if event_type == "init":
            return StreamEvent(
                type=AgentEventType.INIT,
                content=event_dict.get("data", {}),
                session_id=event_dict.get("session_id", ""),
                timestamp=event_dict.get("timestamp", ""),
                agent_name=config.name,
                platform=config.platform,
                role_type=config.role_type,
            )
        elif event_type == "text_delta":
            return StreamEvent(
                type=AgentEventType.TEXT_DELTA,
                content={"text": event_dict.get("text", "")},
                session_id=event_dict.get("session_id", ""),
                timestamp=event_dict.get("timestamp", ""),
                agent_name=config.name,
                platform=config.platform,
                role_type=config.role_type,
            )
        elif event_type == "turn_complete":
            return StreamEvent(
                type=AgentEventType.TURN_COMPLETE,
                content={
                    "usage": event_dict.get("tokens", {}),
                    "cost": event_dict.get("cost", 0),
                    "reason": event_dict.get("reason", ""),
                },
                session_id=event_dict.get("session_id", ""),
                timestamp=event_dict.get("timestamp", ""),
                agent_name=config.name,
                platform=config.platform,
                role_type=config.role_type,
            )
        return None

    async def execute(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None = None,
        cwd: str | None = None,
        use_docker: bool = False,
        group_chat_id: str | None = None,
        system_prompt: str | None = None,
    ) -> AgentResult:
        """
        非流式执行，返回完整结果

        根据 use_docker 选择本地或 Docker 执行器。

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选）
            cwd: 项目目录路径（可选）
            use_docker: 是否使用 Docker 沙箱执行
            group_chat_id: 群聊 ID（Docker 模式下必填）

        Returns:
            AgentResult: 完整结果
        """
        full_text = []
        usage = None
        result_session_id = session_id or ""

        if use_docker:
            # Docker 模式：直接使用 Docker executor
            executor = self._docker_executors[config.platform]
            async for raw_line in executor.execute(
                prompt, config, session_id, cwd, group_chat_id, system_prompt=system_prompt
            ):
                if raw_line.strip():
                    try:
                        parsed_event = self._parsers[config.platform].parse_event(raw_line)
                        if parsed_event is not None:
                            if parsed_event.type == AgentEventType.TEXT_DELTA:
                                full_text.append(parsed_event.content["text"])
                            elif parsed_event.type == AgentEventType.TURN_COMPLETE:
                                usage = parsed_event.content.get("usage")
                            if not result_session_id and parsed_event.session_id:
                                result_session_id = parsed_event.session_id
                    except ParseError:
                        logger.warning(f"Skipping unparseable line from {config.platform.value}")
                        continue
        else:
            # 本地模式：使用本地 executor
            async for event in self.execute_stream(
                prompt, config, session_id, cwd, system_prompt=system_prompt
            ):
                if event.type == AgentEventType.TEXT_DELTA:
                    full_text.append(event.content["text"])
                elif event.type == AgentEventType.TURN_COMPLETE:
                    usage = event.content.get("usage")
                if not result_session_id and event.session_id:
                    result_session_id = event.session_id

        return AgentResult(
            text="".join(full_text),
            session_id=result_session_id,
            timestamp=datetime.now().isoformat(),
            agent_name=config.name,
            platform=config.platform,
            role_type=config.role_type,
            usage=usage,
        )

    async def bare_claude_call(self, prompt: str) -> AgentResult:
        """用于一次性的快速 LLM 调用，不涉及角色等内容。"""
        return await self.execute(prompt, self._bare_config)

    def _init_bare_config(self) -> RoleConfig:
        """初始化 bare 角色配置，不存在则创建。"""
        try:
            role = self._role_manager.get_role(_BARE_ROLE_NAME)
        except Exception:
            role = self._role_manager.create_role(
                name=_BARE_ROLE_NAME,
                platform=AgentPlatform.CLAUDE,
                description="内部 bare 角色，用于一次性快速 LLM 调用",
            )
        config = role.get_role_config()
        config.bare = True
        return config
