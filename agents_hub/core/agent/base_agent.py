"""
Agent 基类

所有 Agent 的基类，包含消息处理、执行逻辑。

渲染分工（参见 foundation/renderer.py）：
- 入站 LLM prompt：render_for_llm（msg.content 始终为原始内容，不被改写）
- 对外公开发言：通过 MCP 工具显式写入群聊
- 任务闭环回复：通过 finish_agent_call 显式完成调用
"""

import asyncio
from pathlib import Path

from agents_hub.agent_bridge import agent_platform_client
from agents_hub.core.communication import AgentCallManager, MessageRouter
from agents_hub.core.context import AgentContext, GroupChatContext
from agents_hub.core.foundation import (
    AgentExecutionError,
    AgentMessage,
    AgentResult,
    CallStatus,
    MessageType,
    Role,
    RoleConfig,
    SessionType,
    render_for_llm,
)
from agents_hub.core.foundation.exceptions import DockerConfigError
from agents_hub.utils.logger import get_logger


class Agent:
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
        self.agent_context = AgentContext(self.name, group_chat_context)
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
        self, prompt, use_docker: bool = False, group_chat_id: str | None = None
    ) -> AgentResult:
        """执行主会话（群聊）

        Args:
            prompt: 渲染好的 LLM prompt 字符串
            use_docker: 是否使用 Docker 沙箱执行
            group_chat_id: 群聊 ID（Docker 模式下必填）
        """
        cwd = self.agent_cwd if self.agent_cwd else None
        return await agent_platform_client.execute(
            prompt,
            self.role_config,
            self.main_session_id,
            cwd,
            use_docker=use_docker,
            group_chat_id=group_chat_id,
        )

    async def btw_execute(self, prompt, session: str | None = None) -> AgentResult:
        """执行单聊（by the way）"""
        print(f"Info : {self.name} 执行单聊 content:{prompt[:20]}")
        cwd = self.agent_cwd if self.agent_cwd else None
        return await agent_platform_client.execute(prompt, self.role_config, session, cwd)

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
            prompt: 已通过 render_for_llm 渲染好的 LLM 输入字符串
        """
        self.logger.debug(
            "_process_message 入口: call_id=%s, from=%s, type=%s, session=%s, content_len=%d",
            msg.call_id,
            msg.send_from,
            msg.message_type,
            msg.session_type,
            len(msg.content) if msg.content else 0,
        )

        # 1. Docker 配置校验
        self._validate_docker_config()

        # 2. 读取 use_docker 配置
        agent_member_info = self.group_chat_context.agent_member_info.get(self.name)
        use_docker = getattr(agent_member_info, "use_docker", False) if agent_member_info else False

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
                history = await self.agent_context.get_context()
                full_prompt = f"{history}\n{prompt}" if history else prompt
                result = await self.execute(
                    full_prompt,
                    use_docker=use_docker,
                    group_chat_id=self.group_chat_context.group_chat_id,
                )
            else:
                self.logger.debug(
                    "执行单聊会话: agent=%s, call_id=%s",
                    self.name,
                    msg.call_id,
                )
                result = await self.btw_execute(prompt)
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

    def _generate_runtime_content(self, task_manager=None) -> str:
        """生成 XML 格式的 runtime 内容。

        Args:
            task_manager: TaskManager 实例（可选，仅 Manager 需要）

        Returns:
            XML 格式的 runtime 内容字符串
        """
        from agents_hub.config import config
        from agents_hub.config.types import RoleType

        # 获取团队成员列表（排除自己）
        team_members = [
            name for name in self.group_chat_context.agent_member_info if name != self.name
        ]
        team_members_str = ", ".join(team_members)

        # 构建基础内容（不含外层 <AGENT_RUNTIME> 标签，由 replace_marked_section 包裹）
        content_parts = [
            "<identity>",
            f"你的名字：{self.name}",
            f"群聊ID：{self.group_chat_context.group_chat_id}",
            f"身份令牌：{self.agent_token}",
            "</identity>",
            "",
            "<team>",
            f"团队成员：{team_members_str}",
            f"前端用户身份名：{config.default_user_name}",
            "带有 user 标记的前端用户不是可调用 Agent；不要对它使用 call_agent。",
            "</team>",
        ]

        # 如果是 Manager，添加 team_workboard
        if self.role_type == RoleType.LEADER and task_manager is not None:
            task_list = task_manager.get_active_task_list(self.group_chat_context.group_chat_id)
            if task_list and task_list.tasks:
                content_parts.extend(
                    [
                        "",
                        "<team_workboard>",
                        "当前任务列表：",
                    ]
                )
                for task in task_list.tasks:
                    status_str = task.status.value.upper()
                    content_parts.append(
                        f"- [{status_str}] {task.task_id}: {task.content} (owner: {task.owner})"
                    )
                content_parts.append("</team_workboard>")

        runtime_calls = self.agent_call_manager.get_runtime_calls_for_agent(self.name)
        if runtime_calls:
            content_parts.extend(
                [
                    "",
                    "<active_agent_calls>",
                    "当前需要你处理的 AgentCall：",
                ]
            )
            from itertools import groupby

            sorted_calls = sorted(runtime_calls, key=lambda c: c.message_type.value)
            for msg_type, group in groupby(sorted_calls, key=lambda c: c.message_type):
                content_parts.append(self._format_runtime_call_instruction(msg_type))
                for call in group:
                    content_parts.append(
                        f"- call_id={call.call_id}; from={call.send_from}; "
                        f"type={call.message_type.value}; status={call.status.value}; "
                        f"request={call.content}"
                    )
            content_parts.append("</active_agent_calls>")

        return "\n".join(content_parts)

    def _generate_tool_usage_content(self) -> str:
        """生成工具使用说明内容。

        根据角色类型生成不同的工具使用说明：
        - Manager/Leader：说明所有工具
        - Worker/Team Member：只说明 speak_in_group_chat 和 finish_agent_call

        Returns:
            XML 格式的工具使用说明字符串
        """
        from agents_hub.config.types import RoleType

        content_parts = [
            "<tool_usage>",
            "## 工具使用说明",
            "",
        ]

        if self.role_type == RoleType.LEADER:
            # Manager 需要了解所有工具
            content_parts.extend(
                [
                    "### 作为 Manager，你可以使用以下工具：",
                    "",
                    "#### 1. call_agent - 派活给团队成员",
                    "当你需要分配任务给团队成员时使用。",
                    "参数：send_to（目标 Agent 名称）、content（任务内容）",
                    "返回：call_id（用于后续查询状态）",
                    "",
                    "#### 2. assign_tasks_to_team - 更新任务列表",
                    "覆盖式更新任务列表，用于管理团队任务。",
                    "参数：tasks（任务列表）",
                    "",
                    "#### 3. archive_task_list - 归档任务列表",
                    "归档当前 ACTIVE 任务列表。",
                    "",
                    "#### 4. check_agent_call - 查询调用状态",
                    "查询 AgentCall 的状态，了解任务执行进度。",
                    "参数：call_id（AgentCall ID）",
                    "",
                    "#### 5. speak_in_group_chat - 群聊公开发言",
                    "在群聊中公开发言，所有 agent 都会看到。",
                    "使用场景：汇报状态、宣布决定、与团队沟通",
                    "参数：content（发言内容）、send_to（可选，@ 某个 agent）",
                    "注意：不要在任务结束时使用此工具，任务结束应使用 finish_agent_call",
                    "",
                    "#### 6. finish_agent_call - 完成任务调用",
                    "当你完成任务分派或做出决策后，立即调用此工具闭环。",
                    "参数：call_id（AgentCall ID）、content（完成说明）、success（是否成功）",
                    "重要：",
                    "- 安排完任务后即可闭环，无需等待 Worker 执行结果。Worker 完成后会通过新的 AgentCall 重新激活你。",
                    "- 如果你在上一次输出时忘记调用，需要立即补一个 finish_agent_call。",
                    "- 忘记闭环会导致系统判定你连续出错而自动停止。",
                    "",
                ]
            )
        else:
            # Worker 只需要了解 speak_in_group_chat 和 finish_agent_call
            content_parts.extend(
                [
                    "### 作为 Worker，你可以使用以下工具：",
                    "",
                    "#### 1. speak_in_group_chat - 群聊公开发言",
                    "在群聊中公开发言，所有 agent 都会看到。",
                    "使用场景：",
                    "- 收到任务时，汇报'收到任务，开始执行'",
                    "- 执行过程中，汇报进度或遇到的问题",
                    "参数：content（发言内容）、send_to（可选，@ 某个 agent）",
                    "注意：不要在任务结束时使用此工具，任务结束应使用 finish_agent_call",
                    "",
                    "#### 2. finish_agent_call - 完成任务调用",
                    "完成实际工作后调用此工具闭环。",
                    "参数：call_id（AgentCall ID）、content（完成说明）、success（是否成功）",
                    "重要：",
                    "- 必须在完成实际工作后才能调用，不要提前闭环。",
                    "- 如果你在上一次输出时忘记调用，需要立即补一个 finish_agent_call。",
                    "- 忘记闭环会导致系统判定你连续出错而自动停止。",
                    "",
                ]
            )

        content_parts.extend(
            [
                "## 群聊消息显示规则",
                "",
                "1. **speak_in_group_chat**：所有 agent 都会看到，但只有被调用和激活时才会传给它",
                "2. **finish_agent_call**：会显示在群聊中，并激活目标 agent",
                "3. **不要同时调用 speak_in_group_chat 和 finish_agent_call**",
                "4. **任务结束时使用 finish_agent_call，不要使用 speak_in_group_chat**",
                "",
                "</tool_usage>",
            ]
        )

        return "\n".join(content_parts)

    def _format_runtime_call_instruction(self, message_type: MessageType) -> str:
        """生成 runtime 中针对不同 AgentCall 类型的操作提示。"""
        if message_type == MessageType.TASK:
            return "- 需要回复：请在完成时调用 finish_agent_call。"
        return "- 无需使用 finish_agent_call；"

    def _inject_runtime_to_files(self, task_manager=None):
        """注入 runtime 内容到 CLAUDE.md 和 AGENTS.md。

        Args:
            task_manager: TaskManager 实例（可选，仅 Manager 需要）
        """
        from pathlib import Path

        from agents_hub.core.utils.markdown_injector import replace_marked_section

        # 生成 runtime 内容
        runtime_content = self._generate_runtime_content(task_manager)

        # 获取 work_root
        if not self.role_config.work_root:
            return
        work_root = Path(self.role_config.work_root)

        # 注入到 CLAUDE.md
        claude_md = work_root / "CLAUDE.md"
        if claude_md.exists():
            replace_marked_section(claude_md, "AGENT_RUNTIME", runtime_content)

        # 注入到 AGENTS.md
        agents_md = work_root / "AGENTS.md"
        if agents_md.exists():
            replace_marked_section(agents_md, "AGENT_RUNTIME", runtime_content)

    def _inject_tool_usage_to_files(self):
        """注入工具使用说明到 CLAUDE.md 和 AGENTS.md。

        根据角色类型生成不同的工具使用说明，注入到 TOOL_USAGE 标记中。
        """
        from pathlib import Path

        from agents_hub.core.utils.markdown_injector import replace_marked_section

        # 生成工具使用说明内容
        tool_usage_content = self._generate_tool_usage_content()

        # 获取 work_root
        if not self.role_config.work_root:
            return
        work_root = Path(self.role_config.work_root)

        # 注入到 CLAUDE.md
        claude_md = work_root / "CLAUDE.md"
        if claude_md.exists():
            replace_marked_section(claude_md, "TOOL_USAGE", tool_usage_content)

        # 注入到 AGENTS.md
        agents_md = work_root / "AGENTS.md"
        if agents_md.exists():
            replace_marked_section(agents_md, "TOOL_USAGE", tool_usage_content)

    def _enqueue_finish_agent_call_reminder(self, msg: AgentMessage):
        """提醒 Agent 使用 finish_agent_call 显式闭环当前任务调用。"""
        from agents_hub.config.types import RoleType

        base_content = (
            f"系统提醒：你刚刚处理了来自 [{msg.send_from}] 的 TASK 调用（call_id={msg.call_id}），"
            f"原始请求：{msg.content[:100]}{'...' if len(msg.content) > 100 else ''}。"
            "该调用尚未闭环，请调用 finish_agent_call，传入对应的 call_id，"
            "并用 content 说明任务完成、失败或无法继续的结果。"
        )
        if self.role_type == RoleType.LEADER:
            base_content += (
                " 你可以在安排完任务后立即闭环，无需等待 Worker 执行结果。"
                "如果忘记调用，请立即补一个。连续未闭环会被系统自动停止。"
            )
        reminder = AgentMessage(
            call_id=msg.call_id,
            send_from="__SYSTEM__",
            send_to=self.name,
            content=base_content,
            session_type=SessionType.MAIN,
            message_type=MessageType.TASK,
        )
        self.message_queue.put_nowait(reminder)

    def _needs_finish_agent_call_reminder(self, msg: AgentMessage) -> bool:
        """判断当前消息处理后是否仍需要显式 finish_agent_call。"""
        if msg.message_type != MessageType.TASK:
            return False
        call = self.agent_call_manager.get_call(msg.call_id)
        return call is not None and not call.has_agent_response

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
            try:
                self._inject_runtime_to_files(self.task_manager)
                self._inject_tool_usage_to_files()
            except Exception as e:
                # 注入失败不应该影响消息处理
                self.logger.debug("Runtime 注入失败: agent=%s, error=%s", self.name, str(e))

            # 4. 渲染 LLM prompt（不写回 msg.content）
            prompt = render_for_llm(msg)
            await self._process_message(msg, prompt)
            # 5. TASK 必须由 finish_agent_call 显式闭环；普通执行文本默认私下保留。
            if self._needs_finish_agent_call_reminder(msg):
                self._enqueue_finish_agent_call_reminder(msg)
                self._consecutive_no_finish_count += 1
                if self._consecutive_no_finish_count >= self.max_consecutive_no_finish:
                    self.logger.warning(
                        "Agent %s 连续 %d 次未闭环 TASK，自动停止",
                        self.name,
                        self._consecutive_no_finish_count,
                    )
                    self._run = False
            else:
                # 成功闭环或非 TASK 消息，重置计数
                self._consecutive_no_finish_count = 0
