"""AgentBridge 统一接口"""

import json
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
from agents_hub.agent_bridge.models import (
    AgentEventType,
    AgentResult,
    FirstResponseResult,
    StreamEvent,
    Usage,
)
from agents_hub.agent_bridge.parsers.claude import ClaudeParser
from agents_hub.agent_bridge.parsers.codex import CodexParser
from agents_hub.agent_bridge.parsers.opencode import OpenCodeParser
from agents_hub.config.types import AgentPlatform
from agents_hub.roles import RoleManager
from agents_hub.roles.models import RoleConfig
from agents_hub.utils.session_parser import resolve_session_path

logger = logging.getLogger(__name__)

_BARE_ROLE_NAME = "bare_claude"


class AgentBridge:
    """统一的 Agent 调用接口"""

    def __init__(self):
        # 创建执行器实例（可复用）
        self._executors: dict[AgentPlatform, ClaudeExecutor | CodexExecutor | OpenCodeExecutor] = {
            AgentPlatform.CLAUDE: ClaudeExecutor(),
            AgentPlatform.CODEX: CodexExecutor(),
            AgentPlatform.OPENCODE: OpenCodeExecutor(),
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

    def _create_parser(
        self, platform: AgentPlatform, usage_baseline: dict | None = None
    ) -> ClaudeParser | CodexParser | OpenCodeParser:
        """
        创建独立的 parser 实例

        每次调用创建新实例，避免并发场景下共享可变状态导致的竞态问题。
        参考：docs/history-bugs/2026-06-15-parser-concurrency-race-condition.md

        Args:
            platform: Agent 平台

        Returns:
            对应平台的 parser 实例
        """
        if platform == AgentPlatform.CLAUDE:
            return ClaudeParser()
        elif platform == AgentPlatform.CODEX:
            return CodexParser(usage_baseline=usage_baseline)
        elif platform == AgentPlatform.OPENCODE:
            return OpenCodeParser()
        else:
            raise PlatformNotSupportedError(platform=str(platform))

    def _read_codex_usage_baseline(self, session_path: str | None) -> dict:
        """读取 Codex session 执行前的累计 usage，用于把 resume 输出转成本轮 usage。"""
        if not session_path:
            return {}

        baseline: dict = {}
        try:
            with open(session_path, encoding="utf-8") as f:
                for line in f:
                    if '"token_count"' not in line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    payload = event.get("payload", {})
                    if payload.get("type") != "token_count":
                        continue
                    usage = payload.get("info", {}).get("total_token_usage", {})
                    if usage:
                        baseline = usage
        except OSError as exc:
            logger.warning("Failed to read Codex usage baseline: %s", exc)
            return {}
        return baseline

    def _codex_usage_baseline(self, config: RoleConfig, session_id: str | None) -> dict:
        if config.platform != AgentPlatform.CODEX or not session_id:
            return {}
        session_path = resolve_session_path(session_id, config.platform, config.work_root)
        return self._read_codex_usage_baseline(session_path)

    @staticmethod
    def _extract_usage(event: StreamEvent) -> Usage | None:
        """从 TURN_COMPLETE 事件中提取 Usage 信息"""
        if event.type != AgentEventType.TURN_COMPLETE:
            return None
        usage_data = event.content.get("usage", {})
        return Usage(
            input_tokens=usage_data.get("input_tokens", 0),
            cache_read_input_tokens=usage_data.get("cache_read_input_tokens", 0),
            max_context_window=event.content.get("max_context_window", 0),
        )

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
        usage_baseline = self._codex_usage_baseline(config, session_id)
        parser = self._create_parser(
            config.platform, usage_baseline=usage_baseline
        )  # 每次创建新的 parser 实例

        logger.info(
            "[AgentBridge] execute_stream 启动: agent=%s, platform=%s, session_id=%s",
            config.name,
            config.platform.value,
            session_id or "new",
        )

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
                            if parsed_event.type == AgentEventType.TURN_COMPLETE:
                                usage = parsed_event.content.get("usage", {})
                                logger.info(
                                    "[AgentBridge] TURN_COMPLETE yield: input=%s, cache_read=%s, agent=%s",
                                    usage.get("input_tokens", 0),
                                    usage.get("cache_read_input_tokens", 0),
                                    config.name,
                                )
                            yield parsed_event
                    except ParseError:
                        # 解析错误：记录日志，跳过该行，继续处理
                        logger.warning(f"Skipping unparseable line from {config.platform.value}")
                        continue
        except (CLINotFoundError, CLIExecutionError):
            # CLI 错误：直接向上传递
            raise
        finally:
            logger.info(
                "[AgentBridge] execute_stream 完成: agent=%s, platform=%s",
                config.name,
                config.platform.value,
            )

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
            tokens = event_dict.get("tokens", {})
            return StreamEvent(
                type=AgentEventType.TURN_COMPLETE,
                content={
                    "usage": {
                        "input_tokens": tokens.get("input", 0),
                    },
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
        fork_from: str | None = None,
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
            fork_from: 源会话 ID（可选，用于 fork 会话）

        Returns:
            AgentResult: 完整结果
        """
        full_text = []
        usage = None
        result_session_id = session_id or ""

        if use_docker:
            # Docker 模式：直接使用 Docker executor（不支持 fork_from）
            executor = self._docker_executors[config.platform]
            usage_baseline = self._codex_usage_baseline(config, session_id)
            parser = self._create_parser(config.platform, usage_baseline=usage_baseline)
            async for raw_line in executor.execute(
                prompt, config, session_id, cwd, group_chat_id, system_prompt=system_prompt
            ):
                if raw_line.strip():
                    try:
                        parsed_event = parser.parse_event(raw_line)
                        if parsed_event is not None:
                            if parsed_event.type == AgentEventType.TEXT_DELTA:
                                full_text.append(parsed_event.content["text"])
                            elif parsed_event.type == AgentEventType.TURN_COMPLETE:
                                usage_data = parsed_event.content.get("usage", {})
                                usage = Usage(
                                    input_tokens=usage_data.get("input_tokens", 0),
                                    cache_read_input_tokens=usage_data.get(
                                        "cache_read_input_tokens", 0
                                    ),
                                    max_context_window=parsed_event.content.get(
                                        "max_context_window", 0
                                    ),
                                )
                            if not result_session_id and parsed_event.session_id:
                                result_session_id = parsed_event.session_id
                    except ParseError:
                        logger.warning(f"Skipping unparseable line from {config.platform.value}")
                        continue
        else:
            # 本地模式：使用本地 executor
            async for event in self.execute_stream(
                prompt, config, session_id, cwd, fork_from=fork_from, system_prompt=system_prompt
            ):
                if event.type == AgentEventType.TEXT_DELTA:
                    full_text.append(event.content["text"])
                elif event.type == AgentEventType.TURN_COMPLETE:
                    usage_data = event.content.get("usage", {})
                    usage = Usage(
                        input_tokens=usage_data.get("input_tokens", 0),
                        cache_read_input_tokens=usage_data.get("cache_read_input_tokens", 0),
                        max_context_window=event.content.get("max_context_window", 0),
                    )
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

    async def execute_with_first_response(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None = None,
        cwd: str | None = None,
        system_prompt: str | None = None,
    ) -> FirstResponseResult:
        """
        执行 Agent 并支持首句响应检测

        封装 execute_stream()，检测 FIRST_RESPONSE 事件，返回首句文本和完整结果。
        用于群聊场景，使前端能更快看到 Agent 的响应。

        首响检测逻辑：
        - Claude：检测 content_block_stop 事件（text block 结束）
        - Codex：检测 item.completed 事件（agent_message 完成）

        回退场景：
        - Codex 首次调用（session_id 为空）：不支持流式输出，回退到 execute()，first_text 为空

        注意：Docker 模式的回退逻辑在 Agent 层处理（base_agent.py），不在本方法中。

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选，Codex 首次调用时为空会触发回退）
            cwd: 项目目录路径（可选）
            system_prompt: 系统提示词（可选）

        Returns:
            FirstResponseResult: 包含首句文本和完整结果
                - first_text: 首句文本（回退场景或纯工具调用时为空）
                - result: 完整结果（包含首句 + 剩余内容）
        """
        # Codex 首次调用不支持流式输出，回退到 execute()
        if config.platform == AgentPlatform.CODEX and not session_id:
            # Codex 首次调用不支持流式，回退
            result = await self.execute(
                prompt, config, session_id, cwd, system_prompt=system_prompt
            )
            return FirstResponseResult(first_text="", result=result)

        logger.info(
            "[AgentBridge] execute_with_first_response 启动: agent=%s, platform=%s, session_id=%s",
            config.name,
            config.platform.value,
            session_id or "new",
        )

        # 流式事件处理状态
        first_text_buffer = ""  # 首句文本缓冲
        remaining_text = ""  # 剩余文本
        first_response_detected = False  # 首句是否已检测到
        usage = None
        result_session_id = session_id or ""

        async for event in self.execute_stream(
            prompt, config, session_id, cwd, system_prompt=system_prompt
        ):
            if event.type == AgentEventType.TEXT_DELTA:
                # 累积文本内容
                if not first_response_detected:
                    first_text_buffer += event.content["text"]
                else:
                    remaining_text += event.content["text"]

            elif event.type == AgentEventType.FIRST_RESPONSE:
                # 首句完成：标记已检测到
                first_response_detected = True

            elif event.type == AgentEventType.TURN_COMPLETE:
                # 提取 usage 信息
                extracted_usage = self._extract_usage(event)
                if extracted_usage is not None:
                    usage = extracted_usage

            # 更新 session_id
            if not result_session_id and event.session_id:
                result_session_id = event.session_id

        # 组合完整结果
        full_text = "".join([first_text_buffer, remaining_text])

        result = AgentResult(
            text=full_text,
            session_id=result_session_id,
            timestamp=datetime.now().isoformat(),
            agent_name=config.name,
            platform=config.platform,
            role_type=config.role_type,
            usage=usage,
        )

        logger.info(
            "[AgentBridge] execute_with_first_response 完成: agent=%s, first_response=%s",
            config.name,
            first_response_detected,
        )

        return FirstResponseResult(
            first_text=first_text_buffer if first_response_detected else "",
            result=result,
        )

    async def bare_claude_call(self, prompt: str) -> AgentResult:
        """用于一次性的快速 LLM 调用，不涉及角色等内容。"""
        return await self.execute(prompt, self._bare_config)

    async def stop_session(
        self,
        platform: AgentPlatform,
        session_id: str,
        use_docker: bool = False,
    ):
        """
        停止指定 session 的执行

        Args:
            platform: Agent 平台
            session_id: 会话 ID
            use_docker: 是否为 Docker 模式
        """
        executor: object | None = None
        if use_docker:
            executor = self._docker_executors.get(platform)
        else:
            executor = self._executors.get(platform)

        if executor and hasattr(executor, "stop_session"):
            await executor.stop_session(session_id)
        else:
            logger.warning(
                "Platform %s executor does not support stop_session: session_id=%s",
                platform.value,
                session_id,
            )

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
