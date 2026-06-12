"""
Agent 基类

所有 Agent 的基类，包含消息处理、执行逻辑。

渲染分工（参见 foundation/renderer.py）：
- 入站 LLM prompt：render_for_llm（msg.content 始终为原始内容，不被改写）
- 对外公开发言：通过 MCP 工具显式写入群聊
- 任务闭环回复：通过 complete_task 显式完成调用
"""

import asyncio
from pathlib import Path

from agents_hub.agent_bridge import AgentResult, agent_platform_client
from agents_hub.config import config
from agents_hub.core.communication import AgentCallManager, MessageRouter
from agents_hub.core.context import AgentContext, GroupChatContext
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

1. **report_progress**：所有 agent 都会看到，但只有被调用和激活时才会传给它。当你接受到一个任务的时候必须使用report_progress发送"收到任务，我将xx"
2. **complete_task**：会显示在群聊中，并激活目标 agent
3. **不要同时调用 report_progress 和 complete_task**
4. **任务结束时使用 complete_task，不要使用 report_progress**
"""

    def __init__(
        self,
        role: Role,
        group_chat_context: GroupChatContext,
        agent_call_manager: AgentCallManager,
        message_router: MessageRouter,
        task_manager=None,
    ):
        self.role_config: RoleConfig = role.get_role_config()
        self.name = self.role_config.name
        self.role_type = self.role_config.role_type
        self.message_queue: asyncio.Queue[AgentMessage] = asyncio.Queue()  # 私有队列
        self.group_chat_context = group_chat_context
        self.agent_context = AgentContext(self.name, group_chat_context, self.role_type)
        self.message_router = message_router
        self.agent_call_manager = agent_call_manager
        self.task_manager = task_manager
        self._run = True
        self._consecutive_no_finish_count: int = 0  # 连续未闭环计数
        self.max_consecutive_no_finish: int = 30  # 阈值
        self.logger = get_logger(f"agent.{self.name}")

    @property
    def agent_token(self) -> str:
        info = self.group_chat_context.agent_member_info.get(self.name)
        return info.token if info else ""

    @property
    def agent_cwd(self) -> str:
        info = self.group_chat_context.agent_member_info.get(self.name)
        return info.cwd if info else ""

    @property
    def context_usage(self) -> int:
        info = self.group_chat_context.agent_member_info.get(self.name)
        return info.context_usage if info else 0

    def set_run(self, run: bool):
        """设置该agent是否工作"""
        # TODO 后续使用，暂时占位
        self._run = run

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
    ) -> AgentResult:
        """执行主会话（群聊）

        Args:
            prompt: 渲染好的 LLM prompt 字符串
            use_docker: 是否使用 Docker 沙箱执行
            group_chat_id: 群聊 ID（Docker 模式下必填）
            system_prompt: 系统提示词（可选，通过 CLI 参数注入）
        """
        cwd = self.agent_cwd if self.agent_cwd else None
        return await agent_platform_client.execute(
            prompt,
            self.role_config,
            self.main_session_id,
            cwd,
            use_docker=use_docker,
            group_chat_id=group_chat_id,
            system_prompt=system_prompt,
        )

    async def btw_execute(
        self, prompt, session: str | None = None, system_prompt: str | None = None
    ) -> AgentResult:
        """执行单聊（by the way）"""
        print(f"Info : {self.name} 执行单聊 content:{prompt[:20]}")
        cwd = self.agent_cwd if self.agent_cwd else None
        return await agent_platform_client.execute(
            prompt, self.role_config, session, cwd, system_prompt=system_prompt
        )

    @property
    def main_session_id(self):
        if self.group_chat_context.agent_member_info.get(self.name):
            if self.group_chat_context.agent_member_info[self.name].main_session:
                return self.group_chat_context.agent_member_info[self.name].main_session
            else:
                print(f"warning : {self.name}在当前群聊中无历史记录")  # TODO 替换为 logger
        else:
            print(
                f"warning : 当前群聊无{self.name}的main session记录 [ 如果是初始化会话 忽略该警告]"
            )
        return None

    def _validate_docker_config(self):
        """校验 Docker 配置（在 _process_message 中调用）"""
        agent_member_info = self.group_chat_context.agent_member_info.get(self.name)
        if not agent_member_info:
            return

        use_docker = getattr(agent_member_info, "use_docker", False)
        if not use_docker:
            return

        agent_cwd = agent_member_info.cwd
        group_chat_path = self.group_chat_context.get_project_path()

        if self._is_same_path(agent_cwd, group_chat_path):
            raise DockerConfigError(
                agent_name=self.name,
                group_chat_id=self.group_chat_context.group_chat_id,
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
        agent_member_info = self.group_chat_context.agent_member_info.get(self.name)
        use_docker = getattr(agent_member_info, "use_docker", False) if agent_member_info else False

        # 3. system prompt 不再动态生成（保留通道）
        system_prompt = None

        self.agent_call_manager.update_status(msg.call_id, CallStatus.RUNNING)
        self.logger.debug(
            "状态更新为 RUNNING: call_id=%s, agent=%s",
            msg.call_id,
            self.name,
        )
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
                    group_chat_id=self.group_chat_context.group_chat_id,
                    system_prompt=system_prompt,
                )
            else:
                self.logger.debug(
                    "执行单聊会话: agent=%s, call_id=%s",
                    self.name,
                    msg.call_id,
                )
                result = await self.btw_execute(prompt, system_prompt=system_prompt)
            if msg.message_type != MessageType.TASK:
                self.agent_call_manager.update_status(msg.call_id, CallStatus.COMPLETED)
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
            self.logger.debug(
                "执行异常: agent=%s, call_id=%s, error=%s",
                self.name,
                msg.call_id,
                str(e),
            )
            self.agent_call_manager.update_status(msg.call_id, CallStatus.FAILED)
            self.agent_call_manager.set_error(msg.call_id, str(e), exc=e)
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
            await self.group_chat_context.runtime.update_agent_context_usage(
                self.name, context_usage
            )

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
        agent_member_info = self.group_chat_context.agent_member_info.get(self.name)
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
        await self.group_chat_context.runtime.update_agent_context_usage(self.name, 0)

        # 10. 写入系统消息
        system_msg = (
            f"⚙️ Agent {self.name} 上下文已压缩\n"
            f"   旧 session: {old_session_id} → 新 session: {new_session_id}\n"
            f"   {context_usage_before}K tokens → 0K tokens"
        )
        await self.group_chat_context.runtime.add_system_message(system_msg)

        # 11. 广播 refresh（update_agent_context_usage 内部已调用 _notify_change，无需重复调用）

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
        group_chat_id = self.group_chat_context.group_chat_id
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

    def _needs_complete_task_reminder(self, msg: AgentMessage) -> bool:
        """
        [deprecated] : 已经弃用， 但是保留代码
        判断当前消息处理后是否仍需要显式 complete_task。
        """
        if msg.message_type != MessageType.TASK:
            return False
        call = self.agent_call_manager.get_call(msg.call_id)
        return call is not None and not call.has_agent_response

    async def _sync_status(self, status: str):
        """同步 Agent 状态到 AgentMemberInfo"""
        await self.group_chat_context.runtime.update_agent_status(self.name, status)

    async def _fallback_close_task(self, msg: AgentMessage, result: AgentResult | None) -> None:
        """兜底闭环：未闭环的 TASK 补齐 mark_agent_response + 分流通知（避免 MCP 断连导致群聊无消息）"""
        call = self.agent_call_manager.get_call(msg.call_id)
        if not (
            result
            and result.text
            and call
            and call.message_type == MessageType.TASK
            and not call.has_agent_response
        ):
            return

        safe_content = redact_token(result.text)
        self.agent_call_manager.mark_agent_response(
            call_id=msg.call_id,
            content=safe_content,
            success=True,
        )

        if config.is_user_name(call.send_from):
            result.text = render_for_chat(self.name, call.send_from, safe_content)
            await self.group_chat_context.add_message(result)
            await self.group_chat_context.update_agent_member_info(result)
        else:
            # 保存到群聊历史，确保群聊能看到兜底闭环的消息
            result.text = render_for_chat(self.name, call.send_from, safe_content)
            await self.group_chat_context.add_message(result)
            await self.group_chat_context.update_agent_member_info(result)

            response_call = self.agent_call_manager.create_call(
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
            await self.message_router.send_message(message)
        await self.group_chat_context.runtime._notify_change()
        self.logger.info(
            "Agent %s 兜底闭环: call_id=%s, send_from=%s, text_len=%d",
            self.name,
            msg.call_id,
            call.send_from,
            len(safe_content),
        )

    async def run(self):
        """持续监听私有队列，处理收到的消息"""
        self.logger.debug(
            "Agent run() 启动: %s, 队列剩余=%d", self.name, self.message_queue.qsize()
        )
        while self._run:
            # 1. 从队列中取回消息
            msg: AgentMessage = await self.message_queue.get()
            # 2. 检查是否是停止信号
            if msg.call_id == "__STOP__":
                self.logger.debug("Agent 收到停止信号: %s", self.name)
                break
            self.logger.debug(
                "Agent 收到消息: agent=%s, call_id=%s, from=%s, type=%s, content_preview=%s",
                self.name,
                msg.call_id,
                msg.send_from,
                msg.message_type,
                msg.content[:50] if msg.content else "",
            )

            # 3. 注入 runtime 和工具使用说明到 CLAUDE.md/AGENTS.md
            # [deprecated]:已弃用，但保留
            # try:
            #     self._inject_runtime_to_files(self.task_manager)
            #     self._inject_tool_usage_to_files()
            # except Exception as e:
            #     # 注入失败不应该影响消息处理
            #     self.logger.debug("Runtime 注入失败: agent=%s, error=%s", self.name, str(e))

            # 4. 渲染 LLM prompt（不写回 msg.content）
            prompt = render_for_llm(msg)
            status = "chatting" if msg.session_type == SessionType.BTW else "busy"
            await self._sync_status(status)
            self.logger.info(
                "Agent %s 开始处理消息: call_id=%s, send_from=%s, message_type=%s, content=%s",
                self.name,
                msg.call_id,
                msg.send_from,
                msg.message_type,
                msg.content[:100] if msg.content else "",
            )
            try:
                result = await self._process_message(msg, prompt)
                await self._update_context_usage(result)
            finally:
                await self._sync_status("idle")
            # 5. 兜底闭环（避免 MCP 断连导致群聊无消息）
            await self._fallback_close_task(msg, result)

            # 6. TASK 闭环提醒（暂时注释，测试阶段）
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
