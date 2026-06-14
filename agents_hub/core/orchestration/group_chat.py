"""
GroupChat 群聊管理

每个 team 可以创建多个群聊，负责：
1. 管理成员的 session_id
2. 初始化各成员状态
3. 管理消息路由和 Agent 生命周期
"""

import asyncio
import contextlib
from uuid import uuid4

from agents_hub.config import config
from agents_hub.config.types import RoleType
from agents_hub.core.agent import Agent, Manager, Worker
from agents_hub.core.communication import AgentCallManager, MessageRouter, TaskManager
from agents_hub.core.context import GroupChatRuntime
from agents_hub.core.foundation import (
    AgentMessage,
    GroupChatType,
    MessageType,
    SessionType,
    StateError,
)
from agents_hub.core.foundation.token import generate_token
from agents_hub.realtime import broadcast_group_chat_refresh
from agents_hub.roles import RoleManager
from agents_hub.utils.logger import get_logger

logger = get_logger(__name__)


class GroupChat:
    """
    群聊管理

    每个 team 可以创建多个群聊，这个群聊管理：
    1. session_id，管理与每个 team member 的 session_id
    2. 初始化各个 member 的状态，在群聊中回复
    3. 管理消息路由和 agent 生命周期

    启动方式：
    - start(): 首次创建群聊（立即激活 agent）
    - load(): 加载已有群聊（只读，不启动 agent）
    - activate(): 激活 agent.run() 任务（发消息前调用）
    """

    def __init__(
        self,
        team_members_name: list[str],
        group_type: GroupChatType,
        project_path: str,
        group_chat_id: str = str(uuid4()),
        group_chat_name: str | None = None,
    ):
        self.group_chat_id = group_chat_id
        self.group_chat_name = group_chat_name or group_chat_id
        self.team_members_name = team_members_name
        self.group_type = group_type
        self.workers: dict[str, Worker] = {}
        self.manager: Manager | None = None
        self.manager_task: asyncio.Task | None = None
        self.worker_tasks: dict[str, asyncio.Task] = {}

        # 依赖组件（按依赖顺序初始化）

        self.runtime = GroupChatRuntime(
            group_chat_id,
            project_path,
            on_change=broadcast_group_chat_refresh,
        )
        self.message_router = MessageRouter()
        self.agent_call_manager = AgentCallManager(self.group_chat_id, project_path)
        self.task_manager = TaskManager(self.group_chat_id, project_path)

        # Heartbeat 定时任务
        self._heartbeat_task: asyncio.Task | None = None
        self._heartbeat_interval: int = 1200  # 20 分钟 = 1200 秒

        # 懒加载标记
        self._activated = False

    async def start(self):
        """
        启动群聊（首次创建）

        1. 加载上下文数据
        2. 立即保存群聊元数据
        3. 初始化 manager 和 workers
        4. 注册所有 agent 到 message_router
        5. 生成并注册 token 到 GroupChatManager
        6. 对第一次进入群聊的成员执行初始化（打招呼）
        7. 启动所有 agent 的 run() 任务
        """
        logger.info(
            "启动群聊: id=%s, name=%s, members=%s",
            self.group_chat_id,
            self.group_chat_name,
            self.team_members_name,
        )

        # 1. 加载上下文数据
        await self.runtime.load()

        # 幂等性检查：如果 metadata 已存在，跳过 initialize_metadata
        if self.runtime.state.metadata is not None:
            logger.debug("群聊 metadata 已存在，跳过初始化: id=%s", self.group_chat_id)
        else:
            # 2. 初始化并保存群聊元数据
            await self.runtime.initialize_metadata(
                group_chat_name=self.group_chat_name,
                group_type=self.group_type,
            )

        # 3-4. 初始化并注册 agents（含 role 验证）
        await self._init_agents()

        # 5. 生成并注册 token
        await self._generate_and_register_tokens()

        # 6. 初始化新成员（第一次会话的成员）
        await self._initialize_new_members()

        # 7. 启动所有 agent 的 run() 任务
        self._start_agent_tasks()

        # 8. 启动 AgentCall 清理循环
        self.agent_call_manager.start_cleanup()

        self._activated = True
        logger.info("群聊启动完成: id=%s", self.group_chat_id)

    async def load(self):
        """
        加载已有的群聊（只读，不启动 agent）

        从 agent_member.json 加载已有 session，恢复 manager 和 workers，
        并验证每个 role 是否存在。恢复并注册 token。对新增成员执行初始化（打招呼）。
        不启动 agent.run() 任务，需要发消息时调用 activate()。
        """
        logger.info("加载群聊: id=%s", self.group_chat_id)

        # 1. 加载上下文数据
        await self.runtime.load()

        # 2. 初始化并注册 agents（含 role 验证）
        await self._init_agents()

        # 3. 恢复并注册 token（必须在 _initialize_new_members 之前）
        await self._restore_and_register_tokens()

        # 4. 初始化新成员（第一次会话的成员）
        await self._initialize_new_members()

        # 5. 启动 AgentCall 清理循环
        self.agent_call_manager.start_cleanup()

        logger.info("群聊加载完成: id=%s", self.group_chat_id)

    async def activate(self):
        """
        激活群聊：启动所有 agent 的 run() 任务

        在 load() 之后调用，用于需要 agent 处理消息的场景（如发送消息）。
        已激活时重复调用无副作用。
        """
        if self._activated:
            return
        logger.info("激活群聊: id=%s", self.group_chat_id)

        # 确保 agents 已注册到 MessageRouter（防止对象重建后注册丢失）
        self._register_agents_to_router()

        self._start_agent_tasks()
        self._activated = True

    def _start_agent_tasks(self):
        """启动所有 agent 的 run() 任务（内部方法）"""
        if self.manager is None:
            logger.error("Manager 未初始化，无法启动 Agent 任务")
            raise StateError("Manager 未初始化，请先调用 _init_agents()")
        self.manager_task = asyncio.create_task(self.manager.run())
        self.manager_task.add_done_callback(
            lambda t: self._on_agent_task_done(self.manager.name, t)
        )
        self.worker_tasks = {}
        for name, w in self.workers.items():
            task = asyncio.create_task(w.run())
            task.add_done_callback(
                lambda t, n=name: self._on_agent_task_done(n, t)
            )
            self.worker_tasks[name] = task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _init_agents(self):
        """
        初始化 manager 和 workers，注册到 message_router

        RoleManager.get_role() 会验证 role 是否存在，不存在则抛出 RoleNotFoundError。
        """
        # 幂等性检查：如果已初始化，直接返回
        if self.manager is not None:
            logger.debug("agents 已初始化，跳过: id=%s", self.group_chat_id)
            return

        logger.debug("初始化 agents: id=%s, members=%s", self.group_chat_id, self.team_members_name)
        role_manager = RoleManager()

        # 初始化 manager
        manager_role = role_manager.get_role(config.default_manager_name)
        self.manager = Manager(
            manager_role,
            self.runtime,
            self.agent_call_manager,
            self.message_router,
            self.task_manager,
        )

        # 初始化 workers
        if not self.team_members_name:
            print("warning : 无团队成员")
            return

        for role_name in self.team_members_name:
            if role_name == config.default_manager_name:
                continue
            role = role_manager.get_role(role_name)
            self.workers[role_name] = Worker(
                role,
                self.runtime,
                self.agent_call_manager,
                self.message_router,
                self.task_manager,
            )

        # 注册所有 agent 到 message_router
        self._register_agents_to_router()

    def _register_agents_to_router(self):
        """注册所有 agents 到 MessageRouter（幂等）

        此方法可以安全地重复调用，MessageRouter.register() 是幂等的。
        """
        if self.manager is None:
            logger.error("Manager 未初始化，无法注册 agents")
            raise StateError("Manager 未初始化，请先调用 _init_agents()")

        # 注册 Manager
        self.message_router.register(self.manager.name, self.manager.message_queue)

        # 注册所有 Workers
        for worker in self.workers.values():
            self.message_router.register(worker.name, worker.message_queue)

        # 注册 user 伪 agent，支持用户通过 API 发送消息
        self.message_router.register(config.default_user_name, asyncio.Queue())

        # 注册 heartbeat 系统身份，用于定时唤醒 manager
        self.message_router.register("__HEARTBEAT__", asyncio.Queue())

        logger.info(
            "agents 注册完成: group=%s, 已注册agents=%s, MessageRouter_id=%s",
            self.group_chat_id,
            list(self.message_router._agents_queue.keys()),
            id(self.message_router),
        )

    async def add_member(self, role_name: str) -> None:
        """增量添加单个成员（热重载安全）

        此方法实现增量式添加：只创建新 Agent，不影响现有 Agent。
        确保运行时状态不丢失，并立即持久化新成员信息。

        Args:
            role_name: 角色名称

        Raises:
            RoleNotFoundError: 角色不存在
        """
        # 1. 验证角色存在
        role_manager = RoleManager()
        role = role_manager.get_role(role_name)  # 不存在会抛出异常

        # 2. 幂等检查
        if role_name in self.workers:
            logger.debug("成员已存在，跳过添加: %s", role_name)
            return

        # 3. 创建新 Worker（共享 runtime）
        new_worker = Worker(
            role,
            self.runtime,  # ⭐ 所有 Agent 共享同一个 runtime
            self.agent_call_manager,
            self.message_router,
            self.task_manager,
        )

        # 4. 注册到 MessageRouter
        self.message_router.register(role_name, new_worker.message_queue)

        # 5. 添加到 workers 字典
        self.workers[role_name] = new_worker

        # 6. ⭐ 关键：立即创建并持久化空条目（防止崩溃后丢失）
        self.runtime.get_or_create_agent_member_info(role_name)
        await self.runtime.save_agent_member_infos()

        # 7. 生成并注册 token
        from .group_chat_manager import group_chat_manager

        token = generate_token()
        group_chat_manager.register_token(token, role_name, self.group_chat_id)
        await self.runtime.set_agent_token_and_default_cwd(role_name, token)

        # 8. 如果群聊已激活，启动新 Worker 的任务
        if self._activated:
            new_task = asyncio.create_task(new_worker.run())
            new_task.add_done_callback(
                lambda t, n=role_name: self._on_agent_task_done(n, t)
            )
            self.worker_tasks[role_name] = new_task
            logger.info("新成员任务已启动: %s", role_name)

        # 9. 更新 team_members_name（运行时使用）
        self.team_members_name.append(role_name)

        # 10. 初始化新成员（打招呼）
        await self._initialize_single_member(new_worker)

        logger.info("成员添加成功: group=%s, member=%s", self.group_chat_id, role_name)

    async def _initialize_single_member(self, agent: Agent) -> None:
        """初始化单个新成员（打招呼）

        Args:
            agent: 要初始化的 Agent
        """
        if agent.role_type == RoleType.LEADER:
            prompt = f"你好，我是这个团队的boss,当前团队成员有{self.team_members_name},你将指挥他们完成我的任务。你使用一句话简单介绍一下自己"
        else:
            other_members = [name for name in self.team_members_name if name != agent.name]
            manager_name = self.manager.name if self.manager else config.default_manager_name
            prompt = f"你好，我是这个团队的boss，当前团队有成员有{other_members},你的直属领导是{manager_name},你使用一句话简单介绍一下自己"

        result = await agent.execute(prompt)
        await self.runtime.update_agent_member_info_from_result(result)
        await self.runtime.add_message(result)

    async def _initialize_new_members(self):
        """
        初始化新成员（第一次进入群聊的成员）

        检查哪些成员没有 session_id，对这些成员执行初始化流程（打招呼）。
        """
        new_members: list[Agent] = []

        # 检查 manager 是否需要初始化
        agent_member_info = (
            self.runtime.get_agent_member_info(self.manager.name)
            if self.manager
            else None
        )
        if self.manager and (not agent_member_info or not agent_member_info.main_session):
            new_members.append(self.manager)

        # 检查 workers 是否需要初始化
        for name, worker in self.workers.items():
            agent_member_info = self.runtime.get_agent_member_info(name)
            if not agent_member_info or not agent_member_info.main_session:
                new_members.append(worker)

        if not new_members:
            return

        logger.info(
            "初始化新成员: id=%s, new_members=%s", self.group_chat_id, [m.name for m in new_members]
        )

        async def start_conversation(agent: Agent):
            if agent.role_type == RoleType.LEADER:
                return await agent.execute(
                    f"你好，我是这个团队的boss,当前团队成员有{self.team_members_name},你将指挥他们完成我的任务。你使用一句话简单介绍一下自己"
                )
            else:
                other_members = [name for name in self.team_members_name if name != agent.name]
                return await agent.execute(
                    f"你好，我是这个团队的boss，当前团队有成员有{other_members},你的直属领导是{self.manager.name},你使用一句话简单介绍一下自己"  # type: ignore[union-attr]
                )

        # 并发执行所有新成员的初始化
        results = await asyncio.gather(*[start_conversation(member) for member in new_members])

        # 保存结果
        for result in results:
            await self.runtime.update_agent_member_info_from_result(result)
            await self.runtime.add_message(result)

    async def compact_history(self):
        """
        压缩群聊历史消息

        将未压缩的消息进行压缩，生成摘要和针对每个 agent 的专门信息
        """
        logger.info("压缩群聊历史: id=%s", self.group_chat_id)
        agent_info = {}

        # 添加 manager 信息
        if self.manager:
            manager_role = RoleManager().get_role(self.manager.name)
            agent_info[self.manager.name] = manager_role.get_role_config().description or "团队领导"

        # 添加 workers 信息
        role_manager = RoleManager()
        for name in self.workers:
            worker_role = role_manager.get_role(name)
            agent_info[name] = worker_role.get_role_config().description or "团队成员"

        await self.runtime.compact_messages(agent_info)

    async def compress_all(self):
        """
        全量压缩所有在线 Agent 的上下文

        逐个处理，忙碌的 Agent 被跳过而非报错。

        Returns:
            list[dict]: 每个 Agent 的压缩结果
        """
        from agents_hub.core.foundation.exceptions import AgentBusyError

        results = []

        # 收集所有 agent（manager + workers）
        all_agents: list[Agent] = []
        if self.manager:
            all_agents.append(self.manager)
        all_agents.extend(self.workers.values())

        for agent in all_agents:
            logger.info("压缩 Agent: %s", agent.name)
            try:
                result = await agent.compress_context()
                results.append(
                    {
                        "agent_name": agent.name,
                        "status": "compressed",
                        "old_session_id": result["old_session_id"],
                        "new_session_id": result["new_session_id"],
                    }
                )
            except AgentBusyError:
                results.append(
                    {
                        "agent_name": agent.name,
                        "status": "skipped",
                        "reason": "busy",
                    }
                )
            except Exception as e:
                logger.warning("Agent %s 压缩失败: %s", agent.name, str(e))
                results.append(
                    {
                        "agent_name": agent.name,
                        "status": "failed",
                        "reason": str(e),
                    }
                )

        return results

    async def send_message_to_agent(self, message: AgentMessage):
        """
        发送消息到目标 Agent 并保存到群聊历史

        包装 MessageRouter.send_message() 和消息保存逻辑，
        确保所有通过控制面投递的消息都被记录。

        Args:
            message: 要发送的消息

        Raises:
            InvalidMessageError: 消息格式错误
            AgentNotFoundError: Agent 不存在
            MessageDeliveryError: 消息投递失败
        """
        from datetime import datetime

        from agents_hub.agent_bridge.models import AgentResult
        from agents_hub.config.types import AgentPlatform
        from agents_hub.core.foundation import render_for_chat

        logger.info(
            "send_message_to_agent 入口: group=%s, call_id=%s, from=%s, to=%s, type=%s",
            self.group_chat_id,
            message.call_id,
            message.send_from,
            message.send_to,
            message.message_type,
        )

        # 0. 确保群聊已激活（懒加载）
        await self.activate()

        # 1. 检查目标 agent 状态
        target_agent_info = self.runtime.state.agent_member_infos.get(message.send_to)
        if target_agent_info and target_agent_info.status == "stopped":
            from agents_hub.exceptions import StateError

            logger.error("无法发送消息给 %s：该 Agent 已停止", message.send_to)
            raise StateError(
                f"无法发送消息给 {message.send_to}：该 Agent 已停止，请先启动",
                details={"agent_name": message.send_to, "status": "stopped"},
            )

        # 2. 投递消息
        await self.message_router.send_message(message)

        # 3. 获取发送方的 platform
        sender_agent = self._find_agent(message.send_from)
        platform = sender_agent.role_config.platform if sender_agent else AgentPlatform.CLAUDE

        # 4. 格式化消息内容（如果还没有 @ 前缀）
        content = message.content
        if not content.startswith(f"@{message.send_to}"):
            content = render_for_chat(message.send_from, message.send_to, content)

        # 5. 构造 AgentResult 并保存（只需要 agent_name, text, timestamp, platform）
        role_type = getattr(sender_agent, "role_type", RoleType.TEAM_MEMBER)
        sender_result = AgentResult(
            text=content,
            session_id="",
            timestamp=datetime.now().isoformat(),
            agent_name=message.send_from,
            platform=platform,
            role_type=role_type,
            files=message.files,
        )
        await self.runtime.add_message(sender_result)

    def _find_agent(self, agent_name: str):
        """查找 agent 实例（manager 或 worker）"""
        if self.manager and self.manager.name == agent_name:
            return self.manager
        return self.workers.get(agent_name)

    async def _cleanup_agent_queue(self, agent_name: str) -> int:
        """
        清空 agent 的消息队列，并闭环所有未完成的 AgentCall

        实现逻辑：
        1. 获取该 agent 的所有 PENDING/RUNNING AgentCall
        2. 对每个 call：
           - 标记为 FAILED（success=False）
           - content = "用户主动停止该 Agent 运行，调用失败，请等待用户下一步指令"
           - 如果调用方不是 user：发送 NOTIFICATION 通知调用方
           - 如果调用方是 user：保存失败消息到群聊历史
        3. 清空消息队列
        4. 返回处理的调用数量

        Args:
            agent_name: Agent 名称

        Returns:
            int: 处理的调用数量
        """
        from datetime import datetime

        from agents_hub.agent_bridge import AgentResult
        from agents_hub.core.foundation.models import CallStatus
        from agents_hub.core.foundation.renderer import render_for_chat

        agent = self._find_agent(agent_name)
        if agent is None:
            return 0

        processed_count = 0

        # 获取该 agent 的所有 PENDING/RUNNING AgentCall
        runtime_calls = self.agent_call_manager.get_runtime_calls_for_agent(agent_name)

        for call in runtime_calls:
            if call.status in (CallStatus.PENDING, CallStatus.RUNNING):
                # 标记为 FAILED
                failure_content = "用户主动停止该 Agent 运行，调用失败，请等待用户下一步指令"
                self.agent_call_manager.mark_agent_response(
                    call_id=call.call_id,
                    content=failure_content,
                    success=False,
                )

                # 如果调用方不是 user，发送 NOTIFICATION 通知
                if not config.is_user_name(call.send_from):
                    notification_call = self.agent_call_manager.create_call(
                        send_from=agent_name,
                        send_to=call.send_from,
                        content=failure_content,
                        message_type=MessageType.NOTIFICATION,
                    )
                    notification_message = AgentMessage(
                        call_id=notification_call.call_id,
                        send_from=agent_name,
                        send_to=call.send_from,
                        content=failure_content,
                        message_type=MessageType.NOTIFICATION,
                    )
                    await self.message_router.send_message(notification_message)
                else:
                    # 如果调用方是 user，保存到群聊历史
                    result = AgentResult(
                        agent_name=agent_name,
                        text=render_for_chat(agent_name, call.send_from, failure_content),
                        session_id="",
                        timestamp=datetime.now().isoformat(),
                        platform=agent.role_config.platform,
                        role_type=agent.role_type,
                    )
                    await self.runtime.add_message(result)

                processed_count += 1

        # 清空队列
        while not agent.message_queue.empty():
            try:
                agent.message_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        return processed_count

    async def stop_member(self, agent_name: str) -> dict:
        """
        停止单个 agent 的运行

        流程：
        1. 验证 agent 存在
        2. 调用 agent.stop() 停止 run() 循环
        3. 强制取消 agent 的 asyncio.Task
        4. 处理消息队列中的所有消息（闭环 AgentCall）
        5. 更新状态为 "stopped"

        Args:
            agent_name: Agent 名称

        Returns:
            dict: {"agent_name": str, "status": "stopped", "processed_calls": int}

        Raises:
            AgentNotFoundError: Agent 不存在
        """
        from agents_hub.core.foundation import AgentNotFoundError

        # 1. 查找 agent
        agent = self._find_agent(agent_name)
        if agent is None:
            raise AgentNotFoundError(agent_name)

        logger.info("停止 Agent: %s", agent_name)

        # 2. 先更新状态为 "stopped"（阻止新消息投递）
        await self.runtime.update_agent_status(agent_name, "stopped")

        # 3. ⭐ 新增：立即终止正在运行的 CLI 进程
        await self._stop_agent_process(agent)

        # 4. 停止 agent.run() 循环（发送哨兵消息并设置 _run=False）
        await agent.stop()

        # 5. 强制取消 agent run 的 asyncio.Task
        if self.manager and agent_name == self.manager.name:
            if self.manager_task and not self.manager_task.done():
                self.manager_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self.manager_task
                self.manager_task = None
        else:
            # 精确取消对应 worker 的 task
            if agent_name in self.worker_tasks:
                task = self.worker_tasks[agent_name]
                if not task.done():
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task
                del self.worker_tasks[agent_name]

        # 5. 清空消息队列并闭环未完成的 AgentCall
        processed_calls = await self._cleanup_agent_queue(agent_name)

        # 6. 从 MessageRouter 注销
        self.message_router.unregister(agent_name)
        logger.debug("Agent %s 已从 MessageRouter 注销", agent_name)

        logger.info("Agent %s 已停止，处理了 %d 个待处理调用", agent_name, processed_calls)

        return {
            "agent_name": agent_name,
            "status": "stopped",
            "processed_calls": processed_calls,
        }

    def _on_agent_task_done(self, agent_name: str, task: asyncio.Task):
        """检测 agent run() 任务异常退出的回调"""
        if task.cancelled():
            logger.debug("Agent %s 的 run() 任务已被取消", agent_name)
            return
        exc = task.exception()
        if exc:
            logger.error(
                "Agent %s 的 run() 任务异常退出: error=%s",
                agent_name,
                str(exc),
                exc_info=(type(exc), exc, exc.__traceback__),
            )
        else:
            logger.info("Agent %s 的 run() 任务正常结束", agent_name)

    async def _stop_agent_process(self, agent):
        """
        终止 Agent 正在运行的 CLI 进程

        Args:
            agent: Agent 实例
        """
        from agents_hub.agent_bridge import agent_platform_client

        session_id = agent.main_session_id
        if not session_id:
            logger.debug("Agent %s 没有活跃 session，跳过进程终止", agent.name)
            return  # 没有活跃 session

        agent_member_info = self.runtime.get_agent_member_info(agent.name)
        use_docker = getattr(agent_member_info, "use_docker", False) if agent_member_info else False

        try:
            await agent_platform_client.stop_session(
                platform=agent.role_config.platform,
                session_id=session_id,
                use_docker=use_docker,
            )
            logger.info("已终止 Agent %s 的 CLI 进程 (session: %s)", agent.name, session_id)
        except Exception as e:
            logger.error("终止 Agent %s 进程失败: %s", agent.name, str(e))

    async def start_member(self, agent_name: str) -> dict:
        """
        重新启动已停止的 agent

        流程：
        1. 验证 agent 存在且状态为 "stopped"
        2. 重置 _run 标志为 True
        3. 重新创建 asyncio.Task 启动 agent.run()
        4. 更新状态为 "idle"

        Args:
            agent_name: Agent 名称

        Returns:
            dict: {"agent_name": str, "status": "idle"}

        Raises:
            AgentNotFoundError: Agent 不存在
            StateError: Agent 未处于 stopped 状态
        """
        from agents_hub.core.foundation import AgentNotFoundError
        from agents_hub.exceptions import StateError

        # 1. 查找 agent
        agent = self._find_agent(agent_name)
        if agent is None:
            raise AgentNotFoundError(agent_name)

        # 2. 获取当前状态
        agent_member_info = self.runtime.state.agent_member_infos.get(agent_name)
        if not agent_member_info or agent_member_info.status != "stopped":
            raise StateError(
                f"Agent {agent_name} 当前状态为 {agent_member_info.status if agent_member_info else 'unknown'}，只能启动 stopped 状态的 Agent",
                details={
                    "agent_name": agent_name,
                    "current_status": agent_member_info.status if agent_member_info else None,
                },
            )

        logger.info("重新启动 Agent: %s", agent_name)

        # 3. 重置 _run 标志
        agent._run = True

        # 4. 创建新任务
        if self.manager and agent_name == self.manager.name:
            self.manager_task = asyncio.create_task(agent.run())
        else:
            new_task = asyncio.create_task(agent.run())
            self.worker_tasks[agent_name] = new_task

        # 5. 重新注册到 MessageRouter
        self.message_router.register(agent_name, agent.message_queue)

        # 6. 添加 task 完成回调（检测 task 异常退出）
        task = self.manager_task if (self.manager and agent_name == self.manager.name) else self.worker_tasks.get(agent_name)
        if task:
            task.add_done_callback(
                lambda t, name=agent_name: self._on_agent_task_done(name, t)
            )

        # 7. 更新状态为 "idle"
        await self.runtime.update_agent_status(agent_name, "idle")

        logger.info("Agent %s 已重新启动", agent_name)

        return {
            "agent_name": agent_name,
            "status": "idle",
        }

    async def reset_member(self, agent_name: str) -> dict:
        """
        重置 agent（清空上下文并重新初始化）

        流程：
        1. 验证 agent 存在
        2. 如果正在运行，先 stop
        3. 清空 main_session 和 btw_sessions
        4. 清空消息队列
        5. 重置 context_usage = 0
        6. 重新执行 _initialize_single_member()（打招呼）
        7. 自动启动（创建 run() 任务）

        Args:
            agent_name: Agent 名称

        Returns:
            dict: {"agent_name": str, "status": "idle", "new_session_id": str}

        Raises:
            AgentNotFoundError: Agent 不存在
        """
        from agents_hub.core.foundation import AgentNotFoundError

        # 1. 查找 agent
        agent = self._find_agent(agent_name)
        if agent is None:
            raise AgentNotFoundError(agent_name)

        logger.info("重置 Agent: %s", agent_name)

        # 2. 如果正在运行，先停止
        agent_member_info = self.runtime.state.agent_member_infos.get(agent_name)
        if agent_member_info and agent_member_info.status != "stopped":
            await self.stop_member(agent_name)

        # 3. 清空 main_session 和 btw_sessions
        if agent_member_info:
            agent_member_info.main_session = None
            agent_member_info.btw_session = []

        # 4. 清空消息队列（stop_member 已经做了，这里确保）
        while not agent.message_queue.empty():
            try:
                agent.message_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        # 5. 重置 context_usage
        await self.runtime.update_agent_context_usage(agent_name, 0)

        # 6. 重新初始化（打招呼）
        await self._initialize_single_member(agent)

        # 7. 自动启动
        agent._run = True
        if self.manager and agent_name == self.manager.name:
            self.manager_task = asyncio.create_task(agent.run())
            self.manager_task.add_done_callback(
                lambda t: self._on_agent_task_done(self.manager.name, t)
            )
        else:
            new_task = asyncio.create_task(agent.run())
            new_task.add_done_callback(
                lambda t, n=agent_name: self._on_agent_task_done(n, t)
            )
            self.worker_tasks[agent_name] = new_task

        # 8. 重新注册到 MessageRouter
        self.message_router.register(agent_name, agent.message_queue)

        # 9. 更新状态为 "idle"
        await self.runtime.update_agent_status(agent_name, "idle")

        # 获取新 session_id
        new_session_id = agent_member_info.main_session if agent_member_info else None

        logger.info("Agent %s 已重置，新 session_id: %s", agent_name, new_session_id)

        return {
            "agent_name": agent_name,
            "status": "idle",
            "new_session_id": new_session_id,
        }

    async def stop(self):
        """停止群聊，停止所有 agent 的 run() 任务。 暂时不要使用这个方法"""
        logger.info("停止群聊: id=%s", self.group_chat_id)
        # 设置所有 agent 停止
        if self.manager:
            self.manager.set_run(False)
        for worker in self.workers.values():
            worker.set_run(False)

        # 等待所有任务完成
        if self.manager_task:
            await self.manager_task
        for task in self.worker_tasks.values():
            await task

    async def cleanup(self, timeout: float = 10.0):
        """
        清理所有资源，确保安全退出

        此方法协调所有组件的清理，确保：
        1. 所有 Agent 任务被停止
        2. AgentCallManager 清理任务被停止
        3. MessageRouter 被清空
        4. GroupChatRuntime 被关闭
        5. 注销所有 token
        6. 所有引用被清空

        Args:
            timeout: 等待任务完成的超时时间（秒），默认 10 秒

        注意：
        - 可以多次调用（幂等性）
        - 超时后会强制取消任务
        - 清理过程中的异常不会阻止其他资源清理
        """
        logger.info("清理群聊资源: id=%s", self.group_chat_id)

        # 1. 停止所有 Agent（发送停止信号）
        if self.manager:
            await self.manager.stop()
        for worker in self.workers.values():
            await worker.stop()

        # 1.5 停止 heartbeat
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task
            self._heartbeat_task = None

        # 2. 等待所有任务完成（设置超时）
        tasks = []
        if self.manager_task and not self.manager_task.done():
            tasks.append(self.manager_task)
        tasks.extend([t for t in self.worker_tasks.values() if not t.done()])

        if tasks:
            try:
                # 等待任务自然退出
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True), timeout=timeout
                )
            except asyncio.TimeoutError:
                # 超时则强制取消
                for task in tasks:
                    if not task.done():
                        task.cancel()
                # 等待取消完成
                await asyncio.gather(*tasks, return_exceptions=True)

        # 3. 停止 AgentCallManager 清理任务
        await self.agent_call_manager.stop_cleanup()

        # 4. 清空 MessageRouter
        self.message_router.clear()

        # 5. 关闭 GroupChatRuntime
        self.runtime.close()

        # 6. 注销所有 token
        from .group_chat_manager import group_chat_manager

        group_chat_manager.unregister_tokens(self.group_chat_id)

        # 7. 清空引用
        self.workers.clear()
        self.manager = None
        self.manager_task = None
        self.worker_tasks.clear()
        logger.info("群聊资源清理完成: id=%s", self.group_chat_id)

    async def _generate_and_register_tokens(self) -> None:
        """
        为所有 agent 生成 token 并注册到 GroupChatManager

        为 manager 和所有 workers 生成唯一的 token，
        并将 token 注册到 GroupChatManager 的索引中。
        同时更新 Runtime 中的 agent_member_info。
        """
        from .group_chat_manager import group_chat_manager

        logger.debug("生成并注册 tokens: id=%s", self.group_chat_id)
        # 为 manager 生成并注册 token
        if self.manager:
            token = generate_token()
            group_chat_manager.register_token(token, self.manager.name, self.group_chat_id)
            await self.runtime.set_agent_token_and_default_cwd(self.manager.name, token)

        # 为 workers 生成并注册 token
        for worker_name in self.workers:
            token = generate_token()
            group_chat_manager.register_token(token, worker_name, self.group_chat_id)
            await self.runtime.set_agent_token_and_default_cwd(worker_name, token)

    async def _restore_and_register_tokens(self) -> None:
        """
        从持久化恢复 token 并注册到 GroupChatManager

        从 Runtime 中读取已保存的 token，
        并将它们注册到 GroupChatManager 的索引中。
        如果某个 agent 没有 token，则生成新的 token。
        """
        from .group_chat_manager import group_chat_manager

        logger.debug("恢复并注册 tokens: id=%s", self.group_chat_id)
        # 恢复 manager 的 token
        if self.manager:
            agent_member_info = self.runtime.state.agent_member_infos.get(self.manager.name)
            if agent_member_info and agent_member_info.token:
                # 恢复已有的 token
                group_chat_manager.register_token(
                    agent_member_info.token, self.manager.name, self.group_chat_id
                )
            else:
                # 生成新的 token
                token = generate_token()
                group_chat_manager.register_token(token, self.manager.name, self.group_chat_id)
                await self.runtime.set_agent_token_and_default_cwd(self.manager.name, token)

        # 恢复 workers 的 token
        for worker_name in self.workers:
            agent_member_info = self.runtime.state.agent_member_infos.get(worker_name)
            if agent_member_info and agent_member_info.token:
                # 恢复已有的 token
                group_chat_manager.register_token(
                    agent_member_info.token, worker_name, self.group_chat_id
                )
            else:
                # 生成新的 token
                token = generate_token()
                group_chat_manager.register_token(token, worker_name, self.group_chat_id)
                await self.runtime.set_agent_token_and_default_cwd(worker_name, token)

    async def _heartbeat_loop(self):
        """定时唤醒 Manager 检查任务进度"""
        heartbeat_logger = get_logger(f"heartbeat.{self.group_chat_id}")
        heartbeat_logger.info("Heartbeat 启动: interval=%ds", self._heartbeat_interval)
        while self._activated:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                if not self._activated or self.manager is None:
                    break
                # 检查 manager task 是否存活
                if self.manager_task and self.manager_task.done():
                    exc = self.manager_task.exception() if not self.manager_task.cancelled() else None
                    heartbeat_logger.error(
                        "Manager run() 任务已退出! cancelled=%s, error=%s",
                        self.manager_task.cancelled(),
                        str(exc) if exc else None,
                    )
                # 检查是否有 worker 连续失败已停止
                stopped_workers = [name for name, w in self.workers.items() if not w._run]
                if stopped_workers:
                    content = (
                        f"[Heartbeat] 以下成员已因连续执行失败自动停止: {', '.join(stopped_workers)}。"
                        "当前没有自动重启机制，请通过 report_progress 向 user 说明情况。"
                    )
                else:
                    content = "[Heartbeat] 定时检查：请查看当前任务进度。"
                heartbeat_msg = AgentMessage(
                    call_id=f"heartbeat_{self.group_chat_id}",
                    send_from="__HEARTBEAT__",
                    send_to=self.manager.name,
                    content=content,
                    session_type=SessionType.MAIN,
                    message_type=MessageType.NOTIFICATION,
                )
                await self.message_router.send_message(heartbeat_msg)
                heartbeat_logger.info("Heartbeat 发送: %s", content[:80])
            except asyncio.CancelledError:
                heartbeat_logger.info("Heartbeat 被取消")
                break
            except Exception as e:
                heartbeat_logger.error("Heartbeat 异常: %s", str(e), exc_info=True)
