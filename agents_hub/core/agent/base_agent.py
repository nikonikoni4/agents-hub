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
from pathlib import Path

from agents_hub.agent_bridge import AgentResult, agent_platform_client
from agents_hub.core.communication import AgentCallManager, MessageRouter
from agents_hub.core.context import AgentContext, GroupChatContext
from agents_hub.core.foundation import (
    AgentExecutionError,
    AgentMessage,
    CallStatus,
    MessageType,
    Role,
    RoleConfig,
    SessionType,
    render_for_llm,
)
from agents_hub.core.foundation.exceptions import DockerConfigError
from agents_hub.utils.logger import get_logger


def _parse_output_fields(text: str) -> dict:
    """从 Agent 回复文本中解析 markdown 格式的结构化字段。

    支持的格式：
    - **Modified files:** 后跟 "- path" 列表
    - **Git diff:** `range`
    - **Web preview:** [title](url)

    Returns:
        dict: {
            "cleaned_text": str,
            "modified_files": list[str] | None,
            "git_diff_range": str | None,
            "web_preview_url": str | None,
            "web_preview_title": str | None,
        }
    """
    result = {
        "cleaned_text": text,
        "modified_files": None,
        "git_diff_range": None,
        "web_preview_url": None,
        "web_preview_title": None,
    }

    # Modified files: **Modified files:** 后跟 "- path" 行
    m = re.search(
        r"\*\*Modified files:\*\*\s*\n((?:\s*-\s+.+\n?)+)", text, re.IGNORECASE
    )
    if m:
        files = re.findall(r"-\s+(.+)", m.group(1))
        files = [f.strip() for f in files if f.strip()]
        if files:
            result["modified_files"] = files
        result["cleaned_text"] = result["cleaned_text"].replace(m.group(0), "").strip()

    # Git diff: **Git diff:** `range`
    m = re.search(r"\*\*Git diff:\*\*\s*`([^`]+)`", text, re.IGNORECASE)
    if m:
        val = m.group(1).strip()
        if val:
            result["git_diff_range"] = val
        result["cleaned_text"] = result["cleaned_text"].replace(m.group(0), "").strip()

    # Web preview: **Web preview:** [title](url)
    m = re.search(r"\*\*Web preview:\*\*\s*\[([^\]]*)\]\(([^)]+)\)", text, re.IGNORECASE)
    if m:
        title = m.group(1).strip()
        url = m.group(2).strip()
        if url:
            result["web_preview_url"] = url
            result["web_preview_title"] = title
        result["cleaned_text"] = result["cleaned_text"].replace(m.group(0), "").strip()

    return result


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
        self._is_processing: bool = False  # 是否正在处理消息
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
    def is_processing(self) -> bool:
        return self._is_processing

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
        """提醒 Agent 使用 complete_task 显式闭环当前任务调用。"""
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
        """判断当前消息处理后是否仍需要显式 complete_task。"""
        if msg.message_type != MessageType.TASK:
            return False
        call = self.agent_call_manager.get_call(msg.call_id)
        return call is not None and not call.has_agent_response

    async def _sync_status(self, status: str):
        """同步 Agent 状态到 AgentMemberInfo"""
        try:
            await self.group_chat_context.runtime.update_agent_status(self.name, status)
        except Exception as e:
            self.logger.warning(
                "同步状态失败: agent=%s, status=%s, error=%s", self.name, status, str(e)
            )

    async def run(self):
        """持续监听私有队列，处理收到的消息"""
        self.logger.debug(
            "Agent run() 启动: %s, 队列剩余=%d", self.name, self.message_queue.qsize()
        )
        while self._run:
            # 1. 从队列中取回消息
            # TODO 当前调用agent的call id 没有发送给send_to 端
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
            # try:
            #     self._inject_runtime_to_files(self.task_manager)
            #     self._inject_tool_usage_to_files()
            # except Exception as e:
            #     # 注入失败不应该影响消息处理
            #     self.logger.debug("Runtime 注入失败: agent=%s, error=%s", self.name, str(e))

            # 4. 渲染 LLM prompt（不写回 msg.content）
            prompt = render_for_llm(msg)
            self._is_processing = True
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

                # 更新 context_window
                if result.usage:
                    input_tokens = result.usage.input_tokens
                    if input_tokens > 0:
                        context_window = input_tokens // 1000
                        self.logger.info(
                            "Agent %s context_window 更新: input=%d, context_window=%dK",
                            self.name,
                            input_tokens,
                            context_window,
                        )
                        try:
                            await self.group_chat_context.runtime.update_agent_context_window(
                                self.name, context_window
                            )
                        except Exception as e:  # TODO 这里不能使用Exception
                            self.logger.warning("更新 context_window 失败: %s", str(e))
                    else:
                        self.logger.warning(
                            "Agent %s context_window 未更新: input_tokens=0, cache_read=0",
                            self.name,
                        )
                else:
                    self.logger.warning(
                        "Agent %s context_window 未更新: usage=None",
                        self.name,
                        result.usage.input_tokens if result.usage else None,
                    )

                self.logger.info(
                    "Agent %s 完成消息处理: call_id=%s, send_from=%s, result_text=%s",
                    self.name,
                    msg.call_id,
                    msg.send_from,
                    result.text[:200] if result.text else "",
                )
            finally:
                self._is_processing = False
                await self._sync_status("idle")
            # 5. 未闭环时把 Agent 回复写入群聊消息（避免 MCP 断连导致群聊无消息）
            call = self.agent_call_manager.get_call(msg.call_id)
            already_closed = call is not None and call.has_agent_response
            if result and result.text and not already_closed:
                try:
                    # 从文本中解析 XML 标签字段
                    parsed = _parse_output_fields(result.text)
                    result.text = parsed["cleaned_text"]
                    if parsed["modified_files"]:
                        result.modified_files = parsed["modified_files"]
                    if parsed["git_diff_range"]:
                        result.git_diff_range = parsed["git_diff_range"]
                    if parsed["web_preview_url"]:
                        result.web_preview = {
                            "url": parsed["web_preview_url"],
                            "title": parsed["web_preview_title"] or "",
                        }
                    await self.group_chat_context.add_message(result)
                    await self.group_chat_context.update_agent_member_info(result)
                    await self.group_chat_context.runtime._notify_change()
                    self.logger.info(
                        "Agent %s 回复已写入群聊: call_id=%s, text_len=%d",
                        self.name,
                        msg.call_id,
                        len(result.text),
                    )
                except Exception as e:
                    self.logger.warning("写入群聊消息失败: %s", str(e))

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
