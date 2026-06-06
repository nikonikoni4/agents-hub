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
from agents_hub.core.context import GroupChatContext, GroupChatRuntime
from agents_hub.core.foundation import (
    AgentMessage,
    GroupChatType,
    MessageType,
    SessionType,
    StateError,
)
from agents_hub.core.foundation.token import generate_token
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
        self.worker_tasks: list[asyncio.Task] = []

        # 依赖组件（按依赖顺序初始化）

        self.runtime = GroupChatRuntime(group_chat_id, project_path)
        self.group_chat_context = GroupChatContext(self.runtime)
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
        await self.group_chat_context.load()

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
        await self.group_chat_context.load()

        # 2. 初始化并注册 agents（含 role 验证）
        await self._init_agents()

        # 3. 恢复并注册 token（必须在 _initialize_new_members 之前）
        await self._restore_and_register_tokens()

        # 4. 初始化新成员（第一次会话的成员）
        await self._initialize_new_members()
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
        self._start_agent_tasks()
        self._activated = True

    def _start_agent_tasks(self):
        """启动所有 agent 的 run() 任务（内部方法）"""
        if self.manager is None:
            raise StateError("Manager 未初始化，请先调用 _init_agents()")
        self.manager_task = asyncio.create_task(self.manager.run())
        self.worker_tasks = [asyncio.create_task(w.run()) for w in self.workers.values()]
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _init_agents(self):
        """
        初始化 manager 和 workers，注册到 message_router

        RoleManager.get_role() 会验证 role 是否存在，不存在则抛出 RoleNotFoundError。
        """
        logger.debug("初始化 agents: id=%s, members=%s", self.group_chat_id, self.team_members_name)
        role_manager = RoleManager()

        # 初始化 manager
        manager_role = role_manager.get_role(config.default_manager_name)
        self.manager = Manager(
            manager_role,
            self.group_chat_context,
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
                self.group_chat_context,
                self.agent_call_manager,
                self.message_router,
                self.task_manager,
            )

        # 注册所有 agent 到 message_router
        self.message_router.register(self.manager.name, self.manager.message_queue)
        for worker in self.workers.values():
            self.message_router.register(worker.name, worker.message_queue)
        # 注册 user 伪 agent，支持用户通过 API 发送消息
        self.message_router.register(config.default_user_name, asyncio.Queue())
        # 注册 heartbeat 系统身份，用于定时唤醒 manager
        self.message_router.register("__HEARTBEAT__", asyncio.Queue())

    async def _initialize_new_members(self):
        """
        初始化新成员（第一次进入群聊的成员）

        检查哪些成员没有 session_id，对这些成员执行初始化流程（打招呼）。
        """
        new_members: list[Agent] = []

        # 检查 manager 是否需要初始化
        agent_member_info = (
            self.group_chat_context.agent_member_info.get(self.manager.name)
            if self.manager
            else None
        )
        if self.manager and (not agent_member_info or not agent_member_info.main_session):
            new_members.append(self.manager)

        # 检查 workers 是否需要初始化
        for name, worker in self.workers.items():
            agent_member_info = self.group_chat_context.agent_member_info.get(name)
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
            await self.group_chat_context.update_agent_member_info(result)
            await self.group_chat_context.add_message(result)

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

        await self.group_chat_context.compact_messages(agent_info)

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

        # 1. 投递消息
        await self.message_router.send_message(message)

        # 2. 获取发送方的 platform
        sender_agent = self._find_agent(message.send_from)
        platform = sender_agent.role_config.platform if sender_agent else AgentPlatform.CLAUDE

        # 3. 格式化消息内容（如果还没有 @ 前缀）
        content = message.content
        if not content.startswith(f"@{message.send_to}"):
            content = render_for_chat(message.send_from, message.send_to, content)

        # 4. 构造 AgentResult 并保存（只需要 agent_name, text, timestamp, platform）
        role_type = getattr(sender_agent, "role_type", RoleType.TEAM_MEMBER)
        sender_result = AgentResult(
            text=content,
            session_id="",
            timestamp=datetime.now().isoformat(),
            agent_name=message.send_from,
            platform=platform,
            role_type=role_type,
        )
        await self.group_chat_context.add_message(sender_result)

    def _find_agent(self, agent_name: str):
        """查找 agent 实例（manager 或 worker）"""
        if self.manager and self.manager.name == agent_name:
            return self.manager
        return self.workers.get(agent_name)

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
        for task in self.worker_tasks:
            await task

    async def cleanup(self, timeout: float = 10.0):
        """
        清理所有资源，确保安全退出

        此方法协调所有组件的清理，确保：
        1. 所有 Agent 任务被停止
        2. AgentCallManager 清理任务被停止
        3. MessageRouter 被清空
        4. GroupChatContext 被关闭
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
        tasks.extend([t for t in self.worker_tasks if not t.done()])

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

        # 5. 关闭 GroupChatContext
        self.group_chat_context.close()

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
                # 检查是否有 worker 连续失败已停止
                stopped_workers = [name for name, w in self.workers.items() if not w._run]
                if stopped_workers:
                    content = (
                        f"[Heartbeat] 以下成员已因连续执行失败自动停止: {', '.join(stopped_workers)}。"
                        "当前没有自动重启机制，请通过 speak_in_group_chat 向 user 说明情况。"
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
