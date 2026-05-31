"""
GroupChat 群聊管理

每个 team 可以创建多个群聊，负责：
1. 管理成员的 session_id
2. 初始化各成员状态
3. 管理消息路由和 Agent 生命周期
"""

import asyncio
from uuid import uuid4

from agents_hub.config.types import RoleType
from agents_hub.core.agent import Agent, Manager, Worker
from agents_hub.core.communication import AgentCallManager, MessageRouter
from agents_hub.core.context import GroupChatContext
from agents_hub.core.foundation import GroupChatType, StateError
from agents_hub.roles import RoleManager

from .team import Team


class GroupChat:
    """
    群聊管理

    每个 team 可以创建多个群聊，这个群聊管理：
    1. session_id，管理与每个 team member 的 session_id
    2. 初始化各个 member 的状态，在群聊中回复
    3. 管理消息路由和 agent 生命周期

    启动方式：
    - start(): 首次创建群聊
    - load(): 加载已有群聊，验证 role 有效性
    """

    def __init__(
        self,
        team: Team,
        group_type: GroupChatType,
        project_path: str,
        group_chat_id: str = str(uuid4()),
    ):
        self.group_chat_id = group_chat_id
        self.team_members_name = team.team_members_name
        self.group_type = group_type
        self.workers: dict[str, Worker] = {}
        self.manager: Manager | None = None
        self.manager_task: asyncio.Task | None = None
        self.worker_tasks: list[asyncio.Task] = []

        # 依赖组件
        self.group_chat_context = GroupChatContext(group_chat_id, project_path)
        self.message_router = MessageRouter()
        self.agent_call_manager = AgentCallManager(self.group_chat_id, project_path)

    async def start(self):
        """
        启动群聊（首次创建）

        1. 加载上下文数据
        2. 初始化 manager 和 workers
        3. 注册所有 agent 到 message_router
        4. 对第一次进入群聊的成员执行初始化（打招呼）
        5. 启动所有 agent 的 run() 任务
        """
        # 1. 加载上下文数据
        await self.group_chat_context.load()

        # 2-4. 初始化并注册 agents（含 role 验证）
        await self._init_agents()

        # 5. 初始化新成员（第一次会话的成员）
        await self._initialize_new_members()

        # 6. 启动所有 agent 的 run() 任务
        if self.manager is None:
            raise StateError("Manager 未初始化，请先调用 _init_agents()")
        self.manager_task = asyncio.create_task(self.manager.run())
        self.worker_tasks = [asyncio.create_task(w.run()) for w in self.workers.values()]

    async def load(self):
        """
        加载已有的群聊

        从 agent_session_id.json 加载已有 session，恢复 manager 和 workers，
        并验证每个 role 是否存在。对新增成员执行初始化（打招呼）。
        """
        # 1. 加载上下文数据
        await self.group_chat_context.load()

        # 2. 初始化并注册 agents（含 role 验证）
        await self._init_agents()

        # 3. 初始化新成员（第一次会话的成员）
        await self._initialize_new_members()

        # 4. 启动所有 agent 的 run() 任务
        if self.manager is None:
            raise StateError("Manager 未初始化，请先调用 _init_agents()")
        self.manager_task = asyncio.create_task(self.manager.run())
        self.worker_tasks = [asyncio.create_task(w.run()) for w in self.workers.values()]

    async def _init_agents(self):
        """
        初始化 manager 和 workers，注册到 message_router

        RoleManager.get_role() 会验证 role 是否存在，不存在则抛出 RoleNotFoundError。
        """
        role_manager = RoleManager()

        # 初始化 manager
        manager_role = role_manager.get_role("Leader")
        self.manager = Manager(
            manager_role, self.group_chat_context, self.agent_call_manager, self.message_router
        )

        # 初始化 workers
        if not self.team_members_name:
            print("warning : 无团队成员")
            return

        for role_name in self.team_members_name:
            role = role_manager.get_role(role_name)
            self.workers[role_name] = Worker(
                role, self.group_chat_context, self.agent_call_manager, self.message_router
            )

        # 注册所有 agent 到 message_router
        self.message_router.register(self.manager.name, self.manager.message_queue)
        for worker in self.workers.values():
            self.message_router.register(worker.name, worker.message_queue)

    async def _initialize_new_members(self):
        """
        初始化新成员（第一次进入群聊的成员）

        检查哪些成员没有 session_id，对这些成员执行初始化流程（打招呼）。
        """
        new_members: list[Agent] = []

        # 检查 manager 是否需要初始化
        if self.manager and self.manager.name not in self.group_chat_context.agent_session_id:
            new_members.append(self.manager)

        # 检查 workers 是否需要初始化
        for name, worker in self.workers.items():
            if name not in self.group_chat_context.agent_session_id:
                new_members.append(worker)

        if not new_members:
            return

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
            await self.group_chat_context.update_agent_session_id(result)
            await self.group_chat_context.add_message(result)

    async def compact_history(self):
        """
        压缩群聊历史消息

        将未压缩的消息进行压缩，生成摘要和针对每个 agent 的专门信息
        """
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

    async def stop(self):
        """停止群聊，停止所有 agent 的 run() 任务。 暂时不要使用这个方法"""
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
        5. 所有引用被清空

        Args:
            timeout: 等待任务完成的超时时间（秒），默认 10 秒

        注意：
        - 可以多次调用（幂等性）
        - 超时后会强制取消任务
        - 清理过程中的异常不会阻止其他资源清理
        """
        # 1. 停止所有 Agent（发送停止信号）
        if self.manager:
            await self.manager.stop()
        for worker in self.workers.values():
            await worker.stop()

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

        # 6. 清空引用
        self.workers.clear()
        self.manager = None
        self.manager_task = None
        self.worker_tasks.clear()
