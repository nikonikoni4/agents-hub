"""
Agent 基类

所有 Agent 的基类，包含消息处理、执行逻辑。

渲染分工（参见 foundation/renderer.py）：
- 入站 LLM prompt：render_for_llm（msg.content 始终为原始内容，不被改写）
- 对外公开发言：通过 MCP 工具显式写入群聊
- 任务闭环回复：通过 complete_task 显式完成调用
"""

import asyncio
import re
from collections.abc import Awaitable, Callable
from pathlib import Path

from agents_hub.agent_bridge import AgentResult, agent_platform_client
from agents_hub.config import config
from agents_hub.core.communication import AgentCallManager, MessageRouter
from agents_hub.core.context import AgentContext, GroupChatRuntime
from agents_hub.core.foundation import (
    AgentExecutionError,
    AgentMessage,
    CallStatus,
    MessageType,
    SessionType,
    render_for_chat,
    render_for_llm,
)
from agents_hub.core.foundation.exceptions import DockerConfigError
from agents_hub.core.foundation.token import redact_token
from agents_hub.roles import Role, RoleConfig
from agents_hub.utils.logger import get_logger


class Agent:
    ROLE_INSTRUCTIONS: str = ""

    SHARED_RULES = """\
## 群聊消息显示规则

1. 直接输出的内容会显示在群聊中
2. 如果涉及文件修改或网页预览，在输出末尾添加 <changes> XML 块
"""

    def __init__(
        self,
        role: Role,
        runtime: GroupChatRuntime,
        agent_call_manager: AgentCallManager,
        message_router: MessageRouter,
        task_manager=None,
    ):
        self.role_config: RoleConfig = role.get_role_config()
        self.name = self.role_config.name
        self.role_type = self.role_config.role_type
        self.message_queue: asyncio.Queue[AgentMessage] = asyncio.Queue()  # 私有队列
        self.runtime = runtime
        self.agent_context = AgentContext(self.name, runtime, self.role_type)
        self.message_router = message_router
        self.agent_call_manager = agent_call_manager
        self.task_manager = task_manager
        self._run = True
        self._consecutive_no_finish_count: int = 0  # 连续未闭环计数
        self.max_consecutive_no_finish: int = 30  # 阈值
        self._message_completion_handlers: list[
            Callable[[AgentMessage, AgentResult | None], Awaitable[None]]
        ] = []
        self._loop_completion_queue: asyncio.Queue | None = None
        self.logger = get_logger(f"agent.{self.name}")

    @property
    def agent_token(self) -> str:
        info = self.runtime.get_agent_member_info(self.name)
        return info.token if info else ""

    @property
    def agent_cwd(self) -> str:
        info = self.runtime.get_agent_member_info(self.name)
        return info.cwd if info else ""

    @property
    def context_usage(self) -> int:
        info = self.runtime.get_agent_member_info(self.name)
        return info.context_usage if info else 0

    def set_run(self, run: bool):
        """设置该agent是否工作"""
        # TODO 后续使用，暂时占位
        self._run = run

    def add_message_completion_handler(
        self,
        handler: Callable[[AgentMessage, AgentResult | None], Awaitable[None]],
    ) -> None:
        """注册消息处理完成后的通用回调。"""
        self._message_completion_handlers.append(handler)

    def set_loop_completion_queue(self, queue: asyncio.Queue | None) -> None:
        """注入或清除 LoopExecutor 使用的节点完成通知队列。"""
        self._loop_completion_queue = queue

    def _should_accept_message(self, msg: AgentMessage) -> bool:
        """判断当前状态下是否应该接收该消息

        白名单规则（仅在 status='in_loop' 时生效）：
        - 接收：来自同一循环的消息（msg.metadata.get("loop_id") == self.current_loop_id）
        - 接收：来自 Manager 的控制信号（msg.send_from == config.default_manager_name）
        - 拒绝：其他所有消息

        Args:
            msg: 待判断的消息

        Returns:
            True: 接收消息，继续处理
            False: 拒绝消息，记录 WARNING 并跳过
        """
        agent_member_info = self.runtime.get_agent_member_info(self.name)
        if not agent_member_info:
            return True

        # 只有 in_loop 状态才启用白名单过滤
        if agent_member_info.status != "in_loop":
            return True

        # in_loop 状态：检查白名单
        current_loop_id = agent_member_info.current_loop_id
        msg_loop_id = msg.metadata.get("loop_id") if msg.metadata else None

        # 白名单 1：来自同一循环的消息
        if msg_loop_id and msg_loop_id == current_loop_id:
            return True

        # 白名单 2：来自 Manager 的控制信号
        if msg.send_from == config.default_manager_name:
            return True

        # 拒绝：不在白名单内
        self.logger.warning(
            "消息被白名单拒绝: agent=%s, call_id=%s, send_from=%s, "
            "reason=Agent 处于循环中（loop_id=%s），只接收循环内消息和 Manager 控制信号",
            self.name,
            msg.call_id,
            msg.send_from,
            current_loop_id,
        )
        return False

    async def stop(self):
        """
        停止 Agent 的 run() 循环

        使用双重保险机制：
        1. 设置 _run 标志为 False
        2. 发送哨兵消息唤醒可能阻塞在 queue.get() 的任务

        哨兵消息会被 run() 循环识别并跳过处理，直接退出循环。
        """
        # 设置停止标志
        self._run = False

        # 发送哨兵消息，唤醒可能阻塞的 get()
        try:
            sentinel = AgentMessage(
                call_id="__STOP__",
                send_from="__SYSTEM__",
                send_to=self.name,
                content="__STOP__",
                session_type=SessionType.MAIN,
                message_type=MessageType.NOTIFICATION,
            )
            self.message_queue.put_nowait(sentinel)
        except asyncio.QueueFull:
            # 队列满了也没关系，_run=False 会让循环在处理完当前消息后退出
            pass

    async def execute(
        self,
        prompt,
        use_docker: bool = False,
        group_chat_id: str | None = None,
        system_prompt: str | None = None,
        fork_from: str | None = None,
        session_id: str | None = None,
    ) -> AgentResult:
        """执行主会话（群聊）

        Args:
            prompt: 渲染好的 LLM prompt 字符串
            use_docker: 是否使用 Docker 沙箱执行
            group_chat_id: 群聊 ID（Docker 模式下必填）
            system_prompt: 系统提示词（可选，通过 CLI 参数注入）
            fork_from: 源会话 ID（可选，用于 Claude fork 会话）
            session_id: 会话 ID 覆盖（可选，用于 Codex fork 后恢复新会话）
        """
        cwd = self.agent_cwd if self.agent_cwd else None
        return await agent_platform_client.execute(
            prompt,
            self.role_config,
            session_id or self.main_session_id,
            cwd,
            use_docker=use_docker,
            group_chat_id=group_chat_id,
            system_prompt=system_prompt,
            fork_from=fork_from,
        )

    async def btw_execute(
        self, prompt, session: str | None = None, system_prompt: str | None = None
    ) -> AgentResult:
        """执行单聊（by the way）"""
        self.logger.debug("执行单聊: agent=%s, content=%s", self.name, prompt[:20])
        cwd = self.agent_cwd if self.agent_cwd else None
        return await agent_platform_client.execute(
            prompt, self.role_config, session, cwd, system_prompt=system_prompt
        )

    @property
    def main_session_id(self):
        info = self.runtime.get_agent_member_info(self.name)
        if info:
            if info.main_session:
                return info.main_session
            else:
                self.logger.warning("%s 在当前群聊中无历史记录", self.name)
        else:
            self.logger.warning(
                "当前群聊无 %s 的 main session 记录（如果是初始化会话忽略该警告）", self.name
            )
        return None

    def _validate_docker_config(self):
        """校验 Docker 配置（在 _process_message 中调用）"""
        agent_member_info = self.runtime.get_agent_member_info(self.name)
        if not agent_member_info:
            return

        use_docker = getattr(agent_member_info, "use_docker", False)
        if not use_docker:
            return

        agent_cwd = agent_member_info.cwd
        group_chat_path = self.runtime.project_path

        if self._is_same_path(agent_cwd, group_chat_path):
            raise DockerConfigError(
                agent_name=self.name,
                group_chat_id=self.runtime.group_chat_id,
                reason=(
                    f"Docker 隔离不必要：Agent CWD 与群聊路径相同。\n"
                    f"  Agent CWD: {agent_cwd}\n"
                    f"  GroupChat Path: {group_chat_path}\n"
                    f"建议：建议创建git worktree，分配给Agent"
                ),
            )

    def _is_same_path(self, path1: str, path2: str) -> bool:
        """判断两个路径是否指向同一位置"""
        try:
            return Path(path1).resolve() == Path(path2).resolve()
        except Exception:
            return False

    async def _process_message(self, msg: AgentMessage, prompt: str) -> AgentResult:
        """处理一条入站消息。

        Args:
            msg: 原始 AgentMessage（content 不可变）
            prompt: 已通过 render_for_llm 渲染好的 LLM 输入字符串（保留参数兼容性，但 MAIN 会话使用 build_user_prompt）
        """
        self.logger.debug(
            "_process_message 入口: call_id=%s, from=%s, type=%s, session=%s, content_len=%d",
            msg.call_id,
            msg.send_from,
            msg.message_type,
            msg.session_type,
            len(msg.content) if msg.content else 0,
        )

        # 1. Docker 配置校验（已注释：允许相同路径开启 Docker）
        # self._validate_docker_config()

        # 2. 读取 use_docker 配置
        agent_member_info = self.runtime.get_agent_member_info(self.name)
        use_docker = getattr(agent_member_info, "use_docker", False) if agent_member_info else False

        # 3. system prompt 不再动态生成（保留通道）
        system_prompt = None

        await self.agent_call_manager.update_status(msg.call_id, CallStatus.RUNNING)
        self.logger.debug(
            "状态更新为 RUNNING: call_id=%s, agent=%s",
            msg.call_id,
            self.name,
        )

        # 记录 Git 状态（用于文件变更兜底捕获）
        git_head_before = None
        status_before = None
        if self.agent_cwd:
            try:
                from agents_hub.core.foundation.file_snapshot import (
                    get_git_head,
                    get_working_tree_status,
                )

                git_head_before = get_git_head(self.agent_cwd)
                if git_head_before:
                    self.logger.info(
                        "[Git 兜底] 记录执行前状态: HEAD=%s, agent=%s",
                        git_head_before[:8],
                        self.name,
                    )
                    # 记录完整的工作区状态
                    status_before = get_working_tree_status(self.agent_cwd)
                    if status_before:
                        self.logger.info(
                            "[Git 兜底] 记录 %d 个文件的状态 (agent=%s)",
                            len(status_before),
                            self.name,
                        )
            except Exception as e:
                self.logger.warning("[Git 兜底] 记录执行前状态失败，Git 兜底将不可用: %s", str(e))

        try:
            if msg.session_type == SessionType.MAIN:
                self.logger.debug(
                    "执行 MAIN 会话: agent=%s, call_id=%s, use_docker=%s",
                    self.name,
                    msg.call_id,
                    use_docker,
                )
                # 构建完整 user prompt（runtime + context + incoming_message）
                full_prompt = await self.agent_context.build_user_prompt(
                    msg, self.agent_call_manager, self.task_manager
                )

                result = await self.execute(
                    full_prompt,
                    use_docker=use_docker,
                    group_chat_id=self.runtime.group_chat_id,
                    system_prompt=system_prompt,
                )
            else:
                self.logger.debug(
                    "执行单聊会话: agent=%s, call_id=%s",
                    self.name,
                    msg.call_id,
                )
                result = await self.btw_execute(prompt, system_prompt=system_prompt)

            # 保存 Git 状态到 result（供 fallback 使用）
            if git_head_before:
                result.git_head_before = git_head_before
                result.status_before = status_before
            if msg.message_type != MessageType.TASK:
                await self.agent_call_manager.update_status(msg.call_id, CallStatus.COMPLETED)
            self.logger.debug(
                "执行完成: agent=%s, call_id=%s, result_len=%d",
                self.name,
                msg.call_id,
                len(result.text) if result.text else 0,
            )
            self.logger.info(
                "Agent %s 完成消息处理: call_id=%s, send_from=%s, result_text=%s",
                self.name,
                msg.call_id,
                msg.send_from,
                result.text[:200] if result.text else "",
            )
            return result
        except Exception as e:
            self.logger.error(
                "执行异常: agent=%s, call_id=%s, error=%s",
                self.name,
                msg.call_id,
                str(e),
                exc_info=True,
            )
            await self.agent_call_manager.update_status(msg.call_id, CallStatus.FAILED)
            await self.agent_call_manager.set_error(msg.call_id, str(e), exc=e)

            # 更新 agent 状态为 error 并记录错误信息
            await self._set_error_status(e)

            raise AgentExecutionError(
                agent_name=self.name,
                reason=str(e),
                session_id=self.main_session_id if msg.session_type == SessionType.MAIN else "",
                platform=self.role_config.platform.value,
            ) from e

    async def _update_context_usage(self, result: AgentResult) -> None:
        """根据 LLM 返回的 usage 更新 context_usage。"""
        if not result.usage:
            return
        input_tokens = result.usage.input_tokens
        # claude 输出的 input_token 会小于之前的输出，猜测原因是使用 subagent
        if input_tokens > 0 and input_tokens > self.context_usage * 1000:
            context_usage = input_tokens // 1000
            self.logger.info(
                "Agent %s context_usage 更新: input=%d, context_usage=%dK",
                self.name,
                input_tokens,
                context_usage,
            )
            # 更新 context_usage
            agent_info = self.runtime.get_agent_member_info(self.name)
            if not agent_info:
                self.logger.warning(
                    "Agent %s 的 member info 不存在，无法更新 context_usage", self.name
                )
                return

            agent_info.context_usage = context_usage
            await self.runtime.save_agent_members(
                context=f"Agent {self.name} context_usage → {context_usage}K"
            )

    async def _auto_compact_if_needed(self) -> None:
        """自动上下文压缩：当 context_usage 超过阈值时触发。"""
        from agents_hub.core.foundation.constants import AUTO_COMPACT_THRESHOLD

        if self.context_usage < AUTO_COMPACT_THRESHOLD:
            return

        self.logger.info(
            "Agent %s context_usage=%dK 超过阈值 %dK，触发自动压缩",
            self.name,
            self.context_usage,
            AUTO_COMPACT_THRESHOLD,
        )
        try:
            await self.compress_context()
        except Exception as e:
            # 自动压缩失败不应影响正常消息处理
            self.logger.error("Agent %s 自动压缩失败: %s", self.name, str(e))

    async def compress_context(self):
        """
        压缩 Agent 的 CLI session 上下文

        流程：
        1. 忙碌校验
        2. 发送压缩 prompt 给当前 session，让 Agent 自我总结
        3. 提取摘要
        4. 写入留痕文件
        5. 用摘要新建 session
        6. 更新状态
        7. 广播 refresh

        Returns:
            dict: 包含 old_session_id, new_session_id, context_usage_before, context_usage_after

        Raises:
            AgentBusyError: Agent 正在执行任务
        """
        from datetime import datetime

        from agents_hub.core.foundation.exceptions import AgentBusyError
        from agents_hub.core.foundation.prompt import COMPACT_CONTEXT_PROMPT

        self.logger.info("Agent %s 开始压缩上下文", self.name)

        # 1. 忙碌校验
        agent_member_info = self.runtime.get_agent_member_info(self.name)
        if agent_member_info and agent_member_info.status == "busy":
            raise AgentBusyError(self.name)

        old_session_id = self.main_session_id
        context_usage_before = self.context_usage

        # 2. 发送压缩 prompt 给当前 session
        result = await self.execute(COMPACT_CONTEXT_PROMPT)

        # 3. 提取摘要
        summary = result.text if result.text else ""

        # 4. 写入留痕文件
        # Spec 明确要求：留痕文件写入失败仅 log warning，不影响压缩流程。
        # 这是项目编码规则"中间层不做兜底"的特例，因为留痕是辅助功能而非核心路径。
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
            handoff_dir = Path(self.agent_cwd) / "docs" / "hand-off"
            handoff_dir.mkdir(parents=True, exist_ok=True)
            handoff_file = handoff_dir / f"{timestamp}-{self.name}-compact.md"
            handoff_content = (
                f"# Context Compact - {self.name} - {datetime.now().isoformat()}\n\n"
                f"## 原 Session\n"
                f"- session_id: {old_session_id}\n"
                f"- context_usage: {context_usage_before}K tokens\n\n"
                f"## 摘要\n"
                f"{summary}\n\n"
                f"## 新 Session\n"
                f"- session_id: (待填充)\n"
            )
            handoff_file.write_text(handoff_content, encoding="utf-8")
        except Exception as e:
            self.logger.warning("留痕文件写入失败: %s", str(e))

        # 5. 清空 main_session
        if agent_member_info:
            agent_member_info.main_session = None

        # 6. 用摘要作为首轮 prompt 新建 session（失败时回滚 main_session）
        try:
            new_result = await self.execute(summary)
        except Exception as e:
            # 回滚 main_session 到旧值
            if agent_member_info:
                agent_member_info.main_session = old_session_id
            self.logger.error(
                "Agent %s 新建 session 失败，已回滚 main_session: %s", self.name, str(e)
            )
            raise
        new_session_id = new_result.session_id

        # 7. 更新留痕文件中的新 session_id
        try:
            handoff_content = handoff_content.replace(
                "- session_id: (待填充)", f"- session_id: {new_session_id}"
            )
            handoff_file.write_text(handoff_content, encoding="utf-8")
        except Exception:
            pass

        # 8. 更新 main_session
        if agent_member_info:
            agent_member_info.main_session = new_session_id

        # 9. 重置 context_usage
        agent_info = self.runtime.get_agent_member_info(self.name)
        assert agent_info is not None, f"Agent {self.name} not found"
        agent_info.context_usage = 0
        await self.runtime.save_agent_members()

        # 10. 写入系统消息
        system_msg = (
            f"⚙️ Agent {self.name} 上下文已压缩\n"
            f"   旧 session: {old_session_id} → 新 session: {new_session_id}\n"
            f"   {context_usage_before}K tokens → 0K tokens"
        )
        await self.runtime.add_system_message(system_msg)

        # 11. 广播 refresh（save_agent_members 内部已调用 _notify_change，无需重复调用）

        self.logger.info(
            "Agent %s 上下文已压缩: old_session=%s, new_session=%s, usage_before=%dK",
            self.name,
            old_session_id,
            new_session_id,
            context_usage_before,
        )

        return {
            "old_session_id": old_session_id,
            "new_session_id": new_session_id,
            "context_usage_before": context_usage_before,
            "context_usage_after": 0,
        }

    def _build_system_prompt(self, task_manager=None) -> str | None:
        """构建 system_prompt。

        OpenCode 平台：写入文件，返回文件名（CLI 通过 --agent 注入文件名）。
        其他平台：runtime 信息已移到 user message，返回 None。

        Args:
            task_manager: TaskManager 实例（可选，仅 Manager 需要）

        Returns:
            OpenCode 返回文件名（不含 .md），其他平台返回 None
        """
        from agents_hub.config.types import AgentPlatform

        if self.role_config.platform == AgentPlatform.OPENCODE:
            return self._build_opencode_system_prompt(task_manager)
        return None

    def _build_opencode_system_prompt(self, system_prompt) -> str:
        """为 OpenCode 构建系统提示词，写入文件并返回文件名。

        文件名格式：{agent_name}_{group_chat_id}
        """
        group_chat_id = self.runtime.group_chat_id
        agent_filename = f"{self.name}_{group_chat_id}"

        if not self.role_config.work_root:
            return agent_filename

        work_root = Path(self.role_config.work_root)
        agents_dir = work_root / "agents"
        agents_dir.mkdir(exist_ok=True)

        agent_file = agents_dir / f"{agent_filename}.md"
        agent_file.write_text(system_prompt, encoding="utf-8")

        self.logger.info("OpenCode system_prompt 写入文件: %s", agent_file)
        return agent_filename

    def _enqueue_complete_task_reminder(self, msg: AgentMessage):
        """
        [deprecated] : 已经弃用，但是保留代码
        提醒 Agent 使用 complete_task 显式闭环当前任务调用。
        """
        from agents_hub.config.types import RoleType

        base_content = f"""\
<task_reminder>
你刚处理了来自 [{msg.send_from}] 的任务调用。

<call_info>
call_id: {msg.call_id}
原始请求: {msg.content[:20]}{"..." if len(msg.content) > 20 else ""}
</call_info>

<action>
请调用 complete_task 闭环此任务：
- call_id: {msg.call_id}
- content: 说明任务结果（完成/失败/无法继续）
</action>
</task_reminder>"""

        if self.role_type == RoleType.LEADER:
            base_content += """\

<leader_note>
作为 Manager，你可以在安排完任务后立即闭环，无需等待 Worker 执行结果。
</leader_note>"""
        reminder = AgentMessage(
            call_id=msg.call_id,
            send_from="__SYSTEM__",
            send_to=self.name,
            content=base_content,
            session_type=SessionType.MAIN,
            message_type=MessageType.TASK,
        )
        self.message_queue.put_nowait(reminder)

    async def _needs_complete_task_reminder(self, msg: AgentMessage) -> bool:
        """
        [deprecated] : 已经弃用， 但是保留代码
        判断当前消息处理后是否仍需要显式 complete_task。
        """
        if msg.message_type != MessageType.TASK:
            return False
        call = await self.agent_call_manager.get_call(msg.call_id)
        return call is not None and not call.has_agent_response

    async def _sync_status(self, status: str):
        """
        同步 Agent 状态到 AgentMemberInfo

        如果当前状态是 "stopped" 或 "error"，不允许改为其他状态（防止 stop/error 后被 finally 覆盖）
        """
        # 获取当前状态
        agent_member_info = self.runtime.get_agent_member_info(self.name)
        if not agent_member_info:
            self.logger.warning(
                "Agent %s 的 member info 不存在，无法同步状态: %s", self.name, status
            )
            return

        current_status = agent_member_info.status

        # 如果已经是 stopped 或 error 状态，不允许改为其他状态
        if current_status in ("stopped", "error") and status not in ("stopped", "error"):
            self.logger.debug(
                "Agent %s 已处于 %s 状态，忽略状态更新请求: %s", self.name, current_status, status
            )
            return

        # 更新状态
        agent_member_info.status = status
        # 如果切换到非 error 状态，清空错误信息
        if status != "error":
            agent_member_info.error_info = None
        await self.runtime.save_agent_members(context=f"Agent {self.name} status → {status}")

    async def _set_error_status(self, exc: Exception):
        """
        设置 Agent 错误状态并记录错误信息

        Args:
            exc: 捕获的异常对象
        """
        agent_member_info = self.runtime.get_agent_member_info(self.name)
        if not agent_member_info:
            self.logger.warning("Agent %s 的 member info 不存在，无法设置错误状态", self.name)
            return

        # 构建错误信息
        error_info = {
            "type": exc.__class__.__name__,
            "message": str(exc),
        }

        # 尝试提取额外的错误信息
        if hasattr(exc, "details") and isinstance(exc.details, dict):
            # AgentBridge 异常包含 details
            if "exit_code" in exc.details:
                error_info["exit_code"] = exc.details["exit_code"]
            if "stderr" in exc.details:
                # 截取 stderr 前 500 字符
                stderr = exc.details["stderr"]
                if stderr:
                    error_info["stderr"] = str(stderr)[:500]

        # 更新状态和错误信息
        agent_member_info.status = "error"
        agent_member_info.error_info = error_info

        self.logger.info(
            "Agent %s 状态更新为 error: type=%s, message=%s",
            self.name,
            error_info["type"],
            error_info["message"][:100],
        )

        await self.runtime.save_agent_members(context=f"Agent {self.name} status → error")

    def _parse_changes_xml(self, text: str) -> dict | None:
        """解析 <changes> XML 块，提取变更信息。

        Args:
            text: Agent 输出的文本

        Returns:
            解析结果字典，格式：
            {
                "files": ["file1.py", "file2.py"],
                "diff": "HEAD",
                "preview_url": "http://...",
                "preview_title": "标题"
            }
            如果没有 <changes> 块或解析失败，返回 None
        """
        match = re.search(r"<changes>(.*?)</changes>", text, re.DOTALL)
        if not match:
            return None

        xml_content = match.group(1)

        def extract_tag(tag: str) -> str | None:
            tag_match = re.search(rf"<{tag}>(.*?)</{tag}>", xml_content, re.DOTALL)
            return tag_match.group(1).strip() if tag_match else None

        files_str = extract_tag("files")
        files = [f.strip() for f in files_str.split(",")] if files_str else []

        return {
            "files": files,
            "diff": extract_tag("diff"),
            "preview_url": extract_tag("preview_url"),
            "preview_title": extract_tag("preview_title"),
        }

    def _strip_changes_xml(self, text: str) -> str:
        """从文本中移除 <changes> XML 块（不展示给用户）。"""
        return re.sub(r"<changes>.*?</changes>", "", text, flags=re.DOTALL).strip()

    async def _process_file_changes(
        self,
        result: AgentResult,
        call_id: str,
        files: list[str],
        diff: str | None,
    ) -> None:
        """处理文件变更：创建快照并更新 result。

        Args:
            result: AgentResult 对象
            call_id: AgentCall ID
            files: 修改的文件路径列表
            diff: Git diff 基准（如 "HEAD"）
        """
        from agents_hub.core.foundation.file_snapshot import create_file_snapshot
        from agents_hub.core.foundation.paths import group_chat_paths

        snapshot_dir = group_chat_paths.file_snapshots_dir(
            self.runtime.group_chat_id, self.runtime.project_path
        )

        file_metadata_list = []
        snapshot_failures = []
        for index, file_path in enumerate(files):
            try:
                metadata = create_file_snapshot(
                    snapshot_dir=snapshot_dir,
                    call_id=call_id,
                    file_path=file_path,
                    index=index,
                    cwd=self.agent_cwd,
                    git_diff_range=diff,
                )
                file_metadata_list.append(metadata)
            except Exception as e:
                snapshot_failures.append((file_path, str(e)))

        if snapshot_failures:
            self.logger.warning(
                "文件快照创建失败: %d 个: %s",
                len(snapshot_failures),
                snapshot_failures,
            )

        result.modified_files = file_metadata_list
        result.git_diff_range = diff

    async def _fallback_close_task(self, msg: AgentMessage, result: AgentResult | None) -> None:
        """兜底闭环：未闭环的 TASK 补齐 mark_agent_response + 分流通知（避免 MCP 断连导致群聊无消息）"""
        if msg.message_type != MessageType.TASK:
            self.logger.debug(
                "[fallback_close] 跳过: message_type=%s (非 TASK), call_id=%s",
                msg.message_type,
                msg.call_id,
            )
            return
        call = await self.agent_call_manager.get_call(msg.call_id)
        has_result_text = bool(result and result.text)
        has_call = call is not None
        is_task_call = call is not None and call.message_type == MessageType.TASK
        no_response_yet = call is not None and not call.has_agent_response
        call_status = call.status.value if call else "N/A"
        self.logger.info(
            "[fallback_close] 条件检查: call_id=%s, has_result_text=%s, has_call=%s, "
            "is_task_call=%s, no_response_yet=%s, call_status=%s",
            msg.call_id,
            has_result_text,
            has_call,
            is_task_call,
            no_response_yet,
            call_status,
        )
        if not (
            result
            and result.text
            and call
            and call.message_type == MessageType.TASK
            and not call.has_agent_response
        ):
            self.logger.info(
                "[fallback_close] 退出: 条件不满足, call_id=%s",
                msg.call_id,
            )
            return

        safe_content = redact_token(result.text)

        # 优先级：XML > Git Snapshot 兜底
        changes = self._parse_changes_xml(safe_content)
        if changes:
            # 从展示内容中移除 <changes> 块
            safe_content = self._strip_changes_xml(safe_content)

            # 处理文件快照
            if changes["files"]:
                await self._process_file_changes(
                    result, msg.call_id, changes["files"], changes["diff"]
                )

            # 处理网页预览
            if changes["preview_url"]:
                preview_url = changes["preview_url"]
                # 只对相对路径转换为 file:/// 绝对路径，HTTP/HTTPS URL 保持不变
                if not preview_url.startswith(("file:///", "http://", "https://")):
                    abs_path = Path(self.agent_cwd) / preview_url
                    preview_url = f"file:///{abs_path.as_posix()}"
                result.web_preview = {
                    "url": preview_url,
                    "title": changes["preview_title"] or "",
                }
        elif result.git_head_before and self.agent_cwd:
            # Git Snapshot 兜底：agent 没有通过 XML 报告文件变更
            try:
                self.logger.info(
                    "[Git 兜底] 触发：agent 未输出 XML <changes> (agent=%s, call_id=%s)",
                    self.name,
                    msg.call_id,
                )
                from agents_hub.core.foundation.file_snapshot import get_git_changed_files

                # 使用状态对比模式（推荐）
                status_before = getattr(result, "status_before", None)
                if status_before is not None:
                    self.logger.info("[Git 兜底] 使用状态对比模式")
                    git_files, git_diff_range = get_git_changed_files(
                        self.agent_cwd,
                        base_ref=result.git_head_before,
                        status_before=status_before,
                    )
                else:
                    # 降级：如果 status_before 不存在（旧数据或异常），跳过兜底
                    self.logger.warning("[Git 兜底] status_before 不存在，跳过 Git 兜底")
                    git_files = []
                    git_diff_range = None

                if git_files:
                    self.logger.info(
                        "[Git 兜底] 捕获到 %d 个文件变更 (agent=%s, call_id=%s, diff_range=%s)",
                        len(git_files),
                        self.name,
                        msg.call_id,
                        git_diff_range or "None (工作区变更)",
                    )
                    for f in git_files[:10]:
                        self.logger.info("[Git 兜底]   - %s", Path(f).name)
                    if len(git_files) > 10:
                        self.logger.info("[Git 兜底]   ... 还有 %d 个文件", len(git_files) - 10)
                    await self._process_file_changes(result, msg.call_id, git_files, git_diff_range)
                else:
                    self.logger.info("[Git 兜底] 未检测到文件变更")
            except Exception as e:
                self.logger.error("[Git 兜底] 执行失败，但不影响主流程: %s", str(e), exc_info=True)

        await self.agent_call_manager.mark_agent_response(
            call_id=msg.call_id,
            content=safe_content,
            success=True,
        )

        if config.is_user_name(call.send_from):
            result.text = render_for_chat(self.name, call.send_from, safe_content)
            await self.runtime.add_message(result)
            await self.runtime.update_agent_session(result)
        else:
            # 保存到群聊历史，确保群聊能看到兜底闭环的消息
            result.text = render_for_chat(self.name, call.send_from, safe_content)
            await self.runtime.add_message(result)
            await self.runtime.update_agent_session(result)

            response_call = await self.agent_call_manager.create_call(
                send_from=self.name,
                send_to=call.send_from,
                content=safe_content,
                message_type=MessageType.NOTIFICATION,
            )
            message = AgentMessage(
                call_id=response_call.call_id,
                content=safe_content,
                send_from=self.name,
                send_to=call.send_from,
                message_type=MessageType.NOTIFICATION,
            )
            # 只有这个地方能直接调用message_router，别的地方只能走gourp_chat.send_message_to_agent
            try:
                await self.message_router.send_message(message)
            except Exception as e:
                # 接收者可能已注销/停止，但兜底闭环的主要目标（保存到历史）已完成
                # 通知未送达不影响闭环成功，调用方下次启动后能从历史中看到结果
                self.logger.warning(
                    "兜底闭环通知未送达 %s -> %s: %s（消息已保存到群聊历史）",
                    self.name,
                    call.send_from,
                    str(e),
                )
        # update_agent_session 内部已通过 _save_agent_members() → _notify_change() 触发广播，无需重复调用
        self.logger.info(
            "Agent %s 兜底闭环: call_id=%s, send_from=%s, text_len=%d",
            self.name,
            msg.call_id,
            call.send_from,
            len(safe_content),
        )

    async def _notify_message_completion(
        self,
        msg: AgentMessage,
        result: AgentResult | None,
    ) -> None:
        """通知消息处理完成事件。"""
        loop_id = msg.metadata.get("loop_id") if msg.metadata else None
        if (
            msg.message_type == MessageType.LOOP_MESSAGE
            and loop_id
            and self._loop_completion_queue is not None
            and result is not None
        ):
            await self._loop_completion_queue.put(
                {
                    "loop_id": loop_id,
                    "agent_result": result,
                    "call_id": msg.call_id,
                }
            )

        for handler in self._message_completion_handlers:
            await handler(msg, result)

    # 测试：添加空行，改变 run() 的行号
    async def run(self) -> None:
        """持续监听私有队列，处理收到的消息"""
        self.logger.info("Agent run() 启动: %s, 队列剩余=%d", self.name, self.message_queue.qsize())
        try:
            await self._run_loop()
        except asyncio.CancelledError:
            self.logger.info("Agent run() 被取消: %s", self.name)
            raise
        except Exception as e:
            self.logger.error(
                "Agent run() 异常退出: agent=%s, error=%s, queue_remaining=%d",
                self.name,
                str(e),
                self.message_queue.qsize(),
                exc_info=True,
            )
            raise
        finally:
            self.logger.info(
                "Agent run() 已终止: agent=%s, _run=%s, queue_remaining=%d",
                self.name,
                self._run,
                self.message_queue.qsize(),
            )

    async def _run_loop(self):
        """run() 的实际消息处理循环"""
        while self._run:
            # 1. 从队列中取回消息
            msg: AgentMessage = await self.message_queue.get()

            # 2. 检查是否是停止信号
            if msg.call_id == "__STOP__":
                self.logger.debug("Agent 收到停止信号: %s", self.name)
                break

            # 3. 检查当前状态是否已经是 stopped（防止处理消息时状态被改变）
            agent_member_info = self.runtime.get_agent_member_info(self.name)
            current_status = agent_member_info.status if agent_member_info else None
            if current_status == "stopped":
                self.logger.debug(
                    "Agent %s 已处于 stopped 状态，跳过消息处理: call_id=%s",
                    self.name,
                    msg.call_id,
                )
                continue

            # 4. 检查白名单（循环隔离）
            if not self._should_accept_message(msg):
                # 消息已被拒绝，_should_accept_message 已记录 WARNING 日志
                continue

            # 5. 注入 runtime 和工具使用说明到 CLAUDE.md/AGENTS.md
            # [deprecated]:已弃用，但保留
            # try:
            #     self._inject_runtime_to_files(self.task_manager)
            #     self._inject_tool_usage_to_files()
            # except Exception as e:
            #     # 注入失败不应该影响消息处理
            #     self.logger.debug("Runtime 注入失败: agent=%s, error=%s", self.name, str(e))

            # 6. 渲染 LLM prompt（不写回 msg.content）
            prompt = render_for_llm(msg)
            status = (
                "chatting" if msg.session_type == SessionType.BTW else "busy"
            )  # chatting字段未实装，可以暂时忽略
            await self._sync_status(status)
            self.logger.debug(
                "Agent %s 开始处理消息: call_id=%s, send_from=%s, message_type=%s",
                self.name,
                msg.call_id,
                msg.send_from,
                msg.message_type,
            )
            try:
                result = await self._process_message(msg, prompt)
                await self._update_context_usage(result)
            finally:
                await self._sync_status("idle")

            # 6.5 自动上下文压缩（当 context_usage 超过阈值时）
            await self._auto_compact_if_needed()

            # 7. 兜底闭环（避免 MCP 断连导致群聊无消息）
            await self._notify_message_completion(msg, result)
            await self._fallback_close_task(msg, result)

            # 8. NOTIFICATION 消息保存到群聊历史
            # _fallback_close_task 只处理 TASK 消息，NOTIFICATION 需要单独保存
            if msg.message_type == MessageType.NOTIFICATION and result and result.text:
                call = await self.agent_call_manager.get_call(msg.call_id)
                if call and not call.has_agent_response:
                    result.text = render_for_chat(self.name, msg.send_from, result.text)
                    await self.runtime.add_message(result)

            # 9. TASK 闭环提醒（暂时注释，测试阶段）
            # if self._needs_complete_task_reminder(msg):
            #     self._enqueue_complete_task_reminder(msg)
            #     self._consecutive_no_finish_count += 1
            #     if self._consecutive_no_finish_count >= self.max_consecutive_no_finish:
            #         self.logger.warning(
            #             "Agent %s 连续 %d 次未闭环 TASK，自动停止",
            #             self.name,
            #             self._consecutive_no_finish_count,
            #         )
            #         self._run = False
            # else:
            #     # 成功闭环或非 TASK 消息，重置计数
            #     self._consecutive_no_finish_count = 0
