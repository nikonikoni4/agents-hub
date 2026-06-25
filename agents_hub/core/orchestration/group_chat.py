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
from agents_hub.core.foundation.constants import HEARTBEAT_INTERVAL_SECONDS
from agents_hub.core.foundation.models import (
    LoopExecutionStatus,
    SystemRoles,
)
from agents_hub.core.foundation.token import generate_token
from agents_hub.core.orchestration.loop_execution_manager import LoopExecutionManager
from agents_hub.core.orchestration.loop_executor import LoopExecutor
from agents_hub.core.orchestration.loop_manager import LoopManager
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
        fork_from_sessions: dict[str, str] | None = None,
    ):
        """初始化群聊编排实例。

        Args:
            team_members_name: 群聊成员名称列表。
            group_type: 群聊类型。
            project_path: 项目路径。
            group_chat_id: 群聊 ID。
            group_chat_name: 群聊展示名称。
            fork_from_sessions: fork 模式下的源 session 映射。
        """
        self.group_chat_id = group_chat_id
        self.group_chat_name = group_chat_name or group_chat_id
        self.team_members_name = team_members_name
        self.group_type = group_type
        self.workers: dict[str, Worker] = {}
        self.manager: Manager | None = None
        self.manager_task: asyncio.Task | None = None
        self.worker_tasks: dict[str, asyncio.Task] = {}
        self._member_lifecycle_locks: dict[str, asyncio.Lock] = {}

        # fork 模式：agent_name → source_session_id
        self.fork_from_sessions = fork_from_sessions

        # 依赖组件（按依赖顺序初始化）

        self.runtime = GroupChatRuntime(
            group_chat_id,
            project_path,
            on_change=broadcast_group_chat_refresh,
        )
        self.message_router = MessageRouter()
        self.agent_call_manager = AgentCallManager(self.group_chat_id, project_path)
        self.task_manager = TaskManager(self.group_chat_id, project_path)

        # Loop 相关组件
        self.loop_manager: LoopManager | None = None  # Loop 定义 CRUD 管理器（懒加载）
        self.loop_execution_manager: LoopExecutionManager | None = (
            None  # Loop 执行实例管理器（懒加载）
        )
        self.active_loops: dict[
            str, LoopExecutor
        ] = {}  # 活跃的 LoopExecutor 实例映射 {execution_id: executor}
        self._loop_tasks: dict[
            str, asyncio.Task
        ] = {}  # LoopExecutor 后台任务映射 {execution_id: task}
        self._loop_queues: dict[
            str, asyncio.Queue
        ] = {}  # Loop 完成通知队列映射 {execution_id: queue}
        self._loop_completion_queue: asyncio.Queue | None = (
            asyncio.Queue()
        )  # 全局完成通知队列（用于 Agent 注入）

        # Heartbeat 定时任务
        self._heartbeat_task: asyncio.Task | None = None
        self._heartbeat_interval: int = HEARTBEAT_INTERVAL_SECONDS

        # 懒加载标记
        self._activated = False

    def _get_loop_manager(self) -> LoopManager:
        """获取 LoopManager 实例（懒加载）。

        LoopManager 负责 Loop 定义的 CRUD 操作和持久化管理。
        首次调用时创建实例，后续调用返回缓存的实例。

        Returns:
            LoopManager 实例
        """
        # 懒加载：首次调用时创建 LoopManager
        if self.loop_manager is None:
            self.loop_manager = LoopManager(self.group_chat_id, self.runtime.project_path)
        return self.loop_manager

    def _get_loop_execution_manager(self) -> LoopExecutionManager:
        """获取 LoopExecutionManager 实例（懒加载）。

        LoopExecutionManager 负责 LoopExecution 执行实例的 CRUD 操作和持久化管理。
        首次调用时创建实例，后续调用返回缓存的实例。

        Returns:
            LoopExecutionManager 实例
        """
        # 懒加载：首次调用时创建 LoopExecutionManager
        if self.loop_execution_manager is None:
            self.loop_execution_manager = LoopExecutionManager(
                self.group_chat_id, self.runtime.project_path
            )
        return self.loop_execution_manager

    def _get_member_lifecycle_lock(self, agent_name: str) -> asyncio.Lock:
        """获取单个成员 stop/start 生命周期锁。"""
        if agent_name not in self._member_lifecycle_locks:
            self._member_lifecycle_locks[agent_name] = asyncio.Lock()
        return self._member_lifecycle_locks[agent_name]

    async def start(self):
        """
        启动群聊（首次创建）

        1. 加载上下文数据
        2. 初始化 agents
        3. 确保 tokens
        4. 初始化新成员（打招呼）
        5. 初始化 metadata
        6. 启动 agent 任务
        """
        # 幂等性检查提前到入口
        if self._activated:
            logger.warning("群聊已启动，跳过: id=%s", self.group_chat_id)
            return

        logger.info(
            "启动群聊: id=%s, name=%s, members=%s",
            self.group_chat_id,
            self.group_chat_name,
            self.team_members_name,
        )

        # 加载上下文数据
        await self.runtime.load()

        # 初始化 agents
        await self._init_agents()

        # 确保所有 agent 都有 token
        await self._ensure_tokens()

        # 初始化新成员（首次创建时所有成员都是新的）
        await self._initialize_new_members()

        # start() 特有：初始化 metadata
        if self.runtime.state.metadata is None:
            await self.runtime.initialize_metadata(
                group_chat_name=self.group_chat_name,
                group_type=self.group_type,
            )

        # start() 特有：立即启动 agent 任务
        self._start_agent_tasks()
        self._activated = True

        logger.info("群聊启动完成: id=%s", self.group_chat_id)

    async def load(self):
        """
        加载已有群聊（不启动 agent）

        只读操作：
        1. 加载上下文数据
        2. 初始化 agents
        3. 确保 tokens
        4. 启动清理循环

        注意：不会初始化新成员（无 LLM 调用），等待后续 activate() 时处理
        """
        logger.info("加载群聊: id=%s", self.group_chat_id)

        # 加载上下文数据
        await self.runtime.load()

        # 初始化 agents
        await self._init_agents()

        # 确保所有 agent 都有 token
        await self._ensure_tokens()

        # load() 不设置 _activated，等待 activate()
        logger.info("群聊加载完成: id=%s", self.group_chat_id)

    async def activate(self):
        """
        激活群聊：启动所有 agent 的 run() 任务

        在 load() 之后调用，用于需要 agent 处理消息的场景（如发送消息）。
        已激活时重复调用无副作用。

        流程：
        1. 注册 agents 到 MessageRouter
        2. 初始化新成员（如果有无 session 的成员）
        3. 启动所有 agent 的 run() 任务
        """
        if self._activated:
            return
        logger.info("激活群聊: id=%s", self.group_chat_id)

        # 确保 agents 已注册到 MessageRouter（防止对象重建后注册丢失）
        self._register_agents_to_router()

        # 初始化新成员（获取 session）
        await self._initialize_new_members()

        self._start_agent_tasks()
        self._activated = True

    def _start_agent_tasks(self):
        """启动所有 agent 的 run() 任务和事件循环（内部方法）"""
        if self.manager is None:
            logger.error("Manager 未初始化，无法启动 Agent 任务")
            raise StateError("Manager 未初始化，请先调用 _init_agents()")
        self.manager_task = asyncio.create_task(self.manager.run())
        manager_name = self.manager.name
        self.manager_task.add_done_callback(lambda t: self._on_agent_task_done(manager_name, t))
        self.worker_tasks = {}
        for name, w in self.workers.items():
            task = asyncio.create_task(w.run())
            task.add_done_callback(lambda t, n=name: self._on_agent_task_done(n, t))  # type: ignore[misc]
            self.worker_tasks[name] = task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # 启动清理循环（生命周期与 agent.run() 一致）
        self.agent_call_manager.start_cleanup()

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
        self.manager.set_loop_completion_queue(self._loop_completion_queue)

        # 初始化 workers
        if not self.team_members_name:
            logger.warning("无团队成员")
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
            self.workers[role_name].set_loop_completion_queue(self._loop_completion_queue)

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
        self.message_router.register(SystemRoles.HEARTBEAT, asyncio.Queue())

        # 注意：loop 系统身份在循环开始时动态注册（create_and_start_loop），
        # 循环结束时自动注销（_on_loop_task_done），不在这里静态注册

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
        new_worker.set_loop_completion_queue(self._loop_completion_queue)

        # 4. 注册到 MessageRouter
        self.message_router.register(role_name, new_worker.message_queue)

        # 5. 添加到 workers 字典
        self.workers[role_name] = new_worker

        # 6. ⭐ 关键：立即创建并持久化空条目（防止崩溃后丢失）
        worker_info = self.runtime.get_or_create_agent_member_info(role_name)

        # 7. 生成并注册 token
        from .group_chat_manager import group_chat_manager

        token = generate_token()
        worker_info.token = token
        worker_info.cwd = self.runtime.project_path
        group_chat_manager.register_token(token, role_name, self.group_chat_id)
        await self.runtime.save_agent_members(context=f"Add member {role_name}")

        # 8. 如果群聊已激活，启动新 Worker 的任务
        if self._activated:
            new_task = asyncio.create_task(new_worker.run())
            new_task.add_done_callback(lambda t, n=role_name: self._on_agent_task_done(n, t))  # type: ignore[misc]
            self.worker_tasks[role_name] = new_task
            logger.info("新成员任务已启动: %s", role_name)

        # 9. 更新 team_members_name（运行时使用）
        self.team_members_name.append(role_name)

        # 10. 初始化新成员（打招呼）
        await self._initialize_single_member(new_worker)

        logger.info("成员添加成功: group=%s, member=%s", self.group_chat_id, role_name)

    async def create_loop(
        self,
        nodes: list[dict],
        max_iterations: int,
        name: str | None = None,
    ):
        """创建 Loop 定义（可复用模板）。

        创建一个 Loop 定义，包含节点列表和最大循环次数。
        Loop 定义可以多次启动，每次启动时传入不同的 initial_task。

        Args:
            nodes: 节点定义列表，每个节点包含:
                - node_id: 节点唯一标识
                - node_type: 节点类型 ("normal" / "terminator")
                - agent_name: 执行该节点的 Agent 名称
                - role_description: 节点职责描述
                - output_schema_prompt: 输出格式提示词
                - output_schema_fields: 必需字段列表
                - max_retries: 输出校验失败的最大重试次数（默认 3）
            max_iterations: 最大循环次数，防止死循环
            name: 循环名称（可选），用于识别和管理

        Returns:
            Loop: 创建的 Loop 定义对象

        Raises:
            LoopValidationError: 节点校验失败（少于 2 个节点、无 TERMINATOR 节点等）
            AgentNotFoundError: 节点引用的 Agent 不存在
        """
        logger.info(
            "创建 Loop 定义: group=%s, name=%s, nodes=%d, max_iterations=%d",
            self.group_chat_id,
            name,
            len(nodes) if nodes else 0,
            max_iterations,
        )
        return await self._get_loop_manager().create_loop(
            nodes=nodes,
            max_iterations=max_iterations,
            name=name,
        )

    async def create_and_start_loop(self, loop_id: str, initial_task: str):
        """启动已创建的 Loop 定义，创建执行实例并在后台运行。

        执行流程：
        1. 懒加载目标 Loop 定义（如果不在内存）
        2. 创建 LoopExecution 执行实例（关联 Loop 定义）
        3. 清空其他 execution（单 execution 保持策略）
        4. 创建完成通知队列（completion_queue）
        5. 将参与的 Agent 状态设置为 IN_LOOP（隔离外部消息）
        6. 为参与的 Agent 注入完成通知队列
        7. 更新 execution 状态为 RUNNING
        8. 创建 LoopExecutor 并在后台启动执行

        Args:
            loop_id: 要启动的 Loop 定义 ID
            initial_task: 本次执行的初始任务描述，发送给第一个节点

        Returns:
            dict: 包含 execution_id 和 loop_id 的字典

        Raises:
            LoopNotFoundError: Loop 定义不存在
        """
        loop_manager = self._get_loop_manager()
        loop_execution_manager = self._get_loop_execution_manager()

        # 懒加载目标 Loop 定义（如果不在内存，从 JSONL 加载）
        loop = loop_manager.get_loop_with_lazy_load(loop_id)

        # 创建 LoopExecution 执行实例
        execution = await loop_execution_manager.create_execution(
            loop_id=loop_id,
            initial_task=initial_task,
        )

        # 清空其他 execution（单 execution 保持策略）
        loop_execution_manager.clear_other_executions(execution.execution_id)

        logger.info(
            "启动 Loop: loop_id=%s, execution_id=%s, group=%s, nodes=%d",
            loop_id,
            execution.execution_id,
            self.group_chat_id,
            len(loop.nodes),
        )

        # 创建完成通知队列：Agent 处理完循环消息后向此队列发送通知
        completion_queue: asyncio.Queue = asyncio.Queue()

        # 获取循环中所有 Agent 实例
        agents = self._loop_agents(loop)

        # 设置参与 Agent 的状态为 IN_LOOP，实现消息隔离
        for node in loop.nodes:
            agent_info = self.runtime.get_or_create_agent_member_info(node.agent_name)
            agent_info.status = "in_loop"
            agent_info.current_loop_id = loop.loop_id
            # 注入完成通知队列到 Agent
            agent = agents.get(node.agent_name)
            if agent is not None:
                agent.set_loop_completion_queue(completion_queue)

        # 持久化 Agent 状态变更
        await self.runtime.save_agent_members(
            context=f"Start loop {loop.loop_id}, execution {execution.execution_id}"
        )

        # 更新 execution 状态为 RUNNING
        await loop_execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.RUNNING.value
        )

        # 注册 "loop" 系统身份到 MessageRouter，用于 LoopExecutor 发送循环消息
        # 一个群聊同时只能有一个 RUNNING 状态的 execution，所以不会有冲突
        self.message_router.register(SystemRoles.LOOP, asyncio.Queue())

        # 创建 on_state_change 回调：Loop 状态变化时通知前端刷新
        def _on_loop_state_change(loop_id: str) -> None:
            """Loop 状态变化时发送 WebSocket 通知。"""
            import asyncio

            asyncio.get_running_loop().create_task(broadcast_group_chat_refresh(self.group_chat_id))

        # 创建 LoopExecutor：循环执行引擎，负责节点调度、输出校验、退出判断
        executor = LoopExecutor(
            loop=loop,
            execution=execution,
            runtime=self.runtime,
            completion_queue=completion_queue,
            send_message_callback=self.send_message_to_agent,
            agent_call_manager=self.agent_call_manager,
            loop_execution_manager=loop_execution_manager,
            agents=agents,
            manager_name=self.manager.name if self.manager else None,
            on_state_change=_on_loop_state_change,
        )

        # 在后台启动 LoopExecutor
        task = asyncio.create_task(executor.run())

        # 注册完成回调：Loop 结束时清理运行时索引
        def _on_done(t: asyncio.Task, eid: str = execution.execution_id) -> None:
            """在 Loop 任务完成后转交统一清理逻辑。

            Args:
                t: 已完成的后台任务。
                eid: 对应的 execution ID。
            """
            self._on_loop_task_done(eid, t)

        task.add_done_callback(_on_done)

        # 记录运行时引用（使用 execution_id 作为 key）
        self.active_loops[execution.execution_id] = executor
        self._loop_tasks[execution.execution_id] = task
        self._loop_queues[execution.execution_id] = completion_queue

        return {
            "execution_id": execution.execution_id,
            "loop_id": loop_id,
            "status": execution.status,
        }

    def _on_loop_task_done(self, execution_id: str, task: asyncio.Task) -> None:
        """LoopExecutor 后台任务结束后清理运行时索引。

        此方法作为 asyncio.Task 的 done_callback 被调用，
        负责清理 GroupChat 中维护的 Loop 运行时引用。

        清理内容：
        1. 从 MessageRouter 注销 "loop" 系统身份
        2. 清理 active_loops、_loop_tasks、_loop_queues 字典

        Args:
            execution_id: 完成的 execution ID
            task: 完成的 asyncio.Task 对象
        """
        # 安全检查：确保要清理的是同一个 task（防止并发场景下的误删）
        if self._loop_tasks.get(execution_id) is task:
            # 从 MessageRouter 注销 "loop" 系统身份
            self.message_router.unregister(SystemRoles.LOOP)

            # 清理运行时引用
            self._loop_tasks.pop(execution_id, None)
            self.active_loops.pop(execution_id, None)
            self._loop_queues.pop(execution_id, None)

    def _loop_agents(self, loop) -> dict[str, Agent]:
        """获取循环中所有 Agent 实例的映射。

        遍历 Loop 的所有节点，查找对应的 Agent 实例（Manager 或 Worker），
        返回 agent_name -> Agent 的映射字典。

        Args:
            loop: Loop 对象，包含节点列表

        Returns:
            dict[str, Agent]: agent_name 到 Agent 实例的映射
        """
        agents: dict[str, Agent] = {}
        for node in loop.nodes:
            agent = self._find_agent(node.agent_name)
            if agent is not None:
                agents[node.agent_name] = agent
        return agents

    async def stop_loop(self, execution_id: str):
        """停止 RUNNING 的 Loop 执行实例，并恢复参与 Agent。

        执行流程：
        1. 验证 execution 状态必须为 RUNNING
        2. 向完成通知队列发送终止信号
        3. 取消 LoopExecutor 的后台任务
        4. 恢复参与 Agent 的状态（IN_LOOP → idle）
        5. 更新 execution 状态为 PAUSED

        Args:
            execution_id: 要停止的 execution ID

        Returns:
            LoopExecution: 更新后的执行实例

        Raises:
            LoopExecutionNotFoundError: execution 不存在
            LoopExecutionStateError: execution 状态不是 RUNNING
        """
        loop_execution_manager = self._get_loop_execution_manager()
        loop_manager = self._get_loop_manager()

        # 获取 execution 和 loop 定义
        execution = loop_execution_manager.get_execution(execution_id)
        # 使用 get_loop_with_lazy_load 而非 get_loop，避免单例模式下 Loop 被驱逐后找不到
        loop = loop_manager.get_loop_with_lazy_load(execution.loop_id)

        # 状态校验：只能停止 RUNNING 状态的 execution
        if execution.status != LoopExecutionStatus.RUNNING.value:
            from agents_hub.core.foundation.exceptions import LoopExecutionStateError

            raise LoopExecutionStateError(execution_id, execution.status, "stop")

        logger.info(
            "停止 Loop: execution_id=%s, loop_id=%s, group=%s",
            execution_id,
            execution.loop_id,
            self.group_chat_id,
        )

        # 取消 LoopExecutor 的后台任务
        task = self._loop_tasks.get(execution_id)
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        # 恢复参与 Agent 的状态（IN_LOOP → idle）
        seen_agents: set[str] = set()
        for node in loop.nodes:
            if node.agent_name in seen_agents:
                continue
            seen_agents.add(node.agent_name)

            # 清除 Agent 的完成通知队列引用
            agent = self._find_agent(node.agent_name)
            if agent is not None:
                agent.set_loop_completion_queue(None)

            # 恢复 Agent 状态：IN_LOOP → stopped → idle
            # 先 stop 再 start，确保 Agent 重新进入正常运行状态
            agent_info = self.runtime.get_agent_member_info(node.agent_name)
            if agent_info is not None:
                if agent_info.status != "stopped":
                    await self.stop_member(node.agent_name)
                await self.start_member(node.agent_name)
                # 更新状态为 idle，清除循环 ID
                agent_info = self.runtime.get_agent_member_info(node.agent_name)
                if agent_info is not None:
                    agent_info.status = "idle"
                    agent_info.current_loop_id = None

        # 持久化 Agent 状态变更
        await self.runtime.save_agent_members(context=f"Stop loop execution {execution_id}")

        # 清理运行时引用
        self.active_loops.pop(execution_id, None)
        self._loop_queues.pop(execution_id, None)

        # 更新 execution 状态为 PAUSED
        return await loop_execution_manager.update_execution_status(
            execution_id, LoopExecutionStatus.PAUSED.value
        )

    async def cleanup_loop(self, execution_id: str) -> None:
        """清理已结束 Loop 执行实例的运行时引用。

        此方法清理 GroupChat 中维护的 Loop 运行时索引，
        包括活跃执行器、完成通知队列和后台任务。

        通常在 Loop 执行完成（COMPLETED/FAILED）后调用。

        Args:
            execution_id: 要清理的 execution ID
        """
        # 清理活跃执行器引用
        self.active_loops.pop(execution_id, None)

        # 清理完成通知队列
        self._loop_queues.pop(execution_id, None)

        # 取消并清理后台任务（如果仍在运行）
        task = self._loop_tasks.pop(execution_id, None)
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        # 注销 "loop" 系统身份（与 stop_loop 同理，显式注销防止泄露）
        self.message_router.unregister(SystemRoles.LOOP)

    async def delete_loop(self, loop_id: str) -> None:
        """删除 Loop 定义及其所有关联的执行实例。

        删除 Loop 定义时会级联删除所有关联的 execution。
        如果有 RUNNING 状态的 execution，需要先停止。

        Args:
            loop_id: 要删除的 Loop 定义 ID

        Raises:
            LoopNotFoundError: Loop 定义不存在
        """
        logger.info(
            "删除 Loop 定义: loop_id=%s, group=%s",
            loop_id,
            self.group_chat_id,
        )

        loop_execution_manager = self._get_loop_execution_manager()

        # 查找该 Loop 的所有 RUNNING 状态的 execution
        running_executions = [
            ex
            for ex in loop_execution_manager.list_executions(loop_id=loop_id)
            if ex.get("status") == LoopExecutionStatus.RUNNING.value
        ]

        # 停止所有 RUNNING 的 execution
        for ex in running_executions:
            execution_id = ex.get("execution_id")
            if execution_id:
                try:
                    await self.stop_loop(execution_id)
                except Exception as e:
                    logger.warning(
                        "停止 execution 失败: execution_id=%s, error=%s",
                        execution_id,
                        e,
                    )

        # 从 LoopManager 删除 Loop 定义（会级联删除所有 executions）
        await self._get_loop_manager().delete_loop(
            loop_id, loop_execution_manager=loop_execution_manager
        )

    def get_loop_status(self, execution_id: str) -> dict:
        """查询 Loop 执行状态。

        获取 Loop 执行实例的当前状态，包括循环轮次、当前节点、错误信息等。

        Args:
            execution_id: 要查询的 execution ID

        Returns:
            dict: Loop 执行状态信息，包含以下字段:
                - execution_id: 执行实例唯一标识
                - loop_id: Loop 定义唯一标识
                - status: 执行状态 ("created"/"running"/"paused"/"completed"/"failed")
                - current_iteration: 当前循环轮次
                - max_iterations: 最大循环次数
                - current_node: 当前执行节点的 Agent 名称（可能为 None）
                - error: 错误信息（失败时有值，否则为 None）

        Raises:
            LoopExecutionNotFoundError: execution 不存在
        """
        loop_execution_manager = self._get_loop_execution_manager()
        loop_manager = self._get_loop_manager()

        execution = loop_execution_manager.get_execution_with_lazy_load(execution_id)
        # 使用 get_loop_with_lazy_load 而非 get_loop，避免单例模式下 Loop 被驱逐后找不到
        loop = loop_manager.get_loop_with_lazy_load(execution.loop_id)

        # 获取当前执行节点的 Agent 名称
        current_node = None
        if 0 <= execution.current_node_index < len(loop.nodes):
            current_node = loop.nodes[execution.current_node_index].agent_name

        return {
            "execution_id": execution.execution_id,
            "loop_id": execution.loop_id,
            "status": execution.status,
            "current_iteration": execution.current_iteration,
            "max_iterations": loop.max_iterations,
            "current_node": current_node,
            "error": execution.error_message,
        }

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
        await self.runtime.update_agent_session(result)
        await self.runtime.add_message(result)

    async def _initialize_new_members(self):
        """
        初始化新成员（第一次进入群聊的成员）

        检查哪些成员没有 session_id，对这些成员执行初始化流程（打招呼）。
        fork 模式下，使用 fork_from 源 session 创建新会话。
        """
        from agents_hub.config.types import AgentPlatform

        new_members: list[Agent] = []

        # 检查 manager 是否需要初始化
        agent_member_info = (
            self.runtime.get_agent_member_info(self.manager.name) if self.manager else None
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

        is_fork = bool(self.fork_from_sessions)
        logger.info(
            "初始化新成员: id=%s, new_members=%s, is_fork=%s",
            self.group_chat_id,
            [m.name for m in new_members],
            is_fork,
        )

        async def start_conversation(agent: Agent):
            """初始化单个新成员的主会话。

            Args:
                agent: 需要初始化的 Agent。

            Returns:
                Agent 执行或 fork 初始化后的结果。
            """
            # 构建提示词
            if agent.role_type == RoleType.LEADER:
                prompt = f"你好，我是这个团队的boss,当前团队成员有{self.team_members_name},你将指挥他们完成我的任务。你使用一句话简单介绍一下自己"
            else:
                other_members = [name for name in self.team_members_name if name != agent.name]
                manager_name = self.manager.name if self.manager else config.default_manager_name
                prompt = f"你好，我是这个团队的boss，当前团队有成员有{other_members},你的直属领导是{manager_name},你使用一句话简单介绍一下自己"

            # fork 模式：尝试使用 fork_from 创建新会话
            if is_fork and self.fork_from_sessions:
                source_session = self.fork_from_sessions.get(agent.name)
                if source_session:
                    if agent.role_config.platform == AgentPlatform.CODEX:
                        # Codex: 通过 fork_codex_session 复制会话文件，直接构造结果
                        from datetime import datetime, timezone

                        from agents_hub.agent_bridge.models import AgentResult
                        from agents_hub.core.foundation.exceptions import ForkError
                        from agents_hub.core.utils.session_fork import fork_codex_session
                        from agents_hub.utils.session_parser import resolve_session_path

                        session_path = resolve_session_path(
                            source_session, agent.role_config.platform, agent.role_config.work_root
                        )
                        if not session_path:
                            logger.error(
                                "Codex fork 失败: 无法解析源会话路径, agent=%s, session=%s",
                                agent.name,
                                source_session,
                            )
                            raise ForkError(
                                agent_name=agent.name,
                                platform="codex",
                                source_session=source_session,
                                reason=f"无法解析源会话路径: session_id={source_session}",
                            )
                        try:
                            new_session_id = fork_codex_session(source_session, session_path)
                        except FileNotFoundError as e:
                            logger.error(
                                "Codex fork 失败: 源会话文件不存在, agent=%s, path=%s",
                                agent.name,
                                session_path,
                            )
                            raise ForkError(
                                agent_name=agent.name,
                                platform="codex",
                                source_session=source_session,
                                reason=f"源会话文件不存在: {session_path}",
                            ) from e
                        logger.info(
                            "Codex fork 初始化: agent=%s, source=%s, new_session=%s, group=%s",
                            agent.name,
                            source_session,
                            new_session_id,
                            self.group_chat_id,
                        )
                        return AgentResult(
                            text="fork成功",
                            session_id=new_session_id,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            agent_name=agent.name,
                            platform=AgentPlatform.CODEX,
                            role_type=agent.role_type,
                        )
                    elif agent.role_config.platform == AgentPlatform.OPENCODE:
                        # OpenCode 不支持 fork，降级为普通初始化
                        logger.warning(
                            "OpenCode 平台不支持 fork，降级为普通初始化: agent=%s, group=%s",
                            agent.name,
                            self.group_chat_id,
                        )
                        return await agent.execute(prompt)
                    else:
                        # Claude: 使用 --fork-session --resume
                        logger.info(
                            "Fork 模式初始化: agent=%s, source_session=%s, group=%s",
                            agent.name,
                            source_session,
                            self.group_chat_id,
                        )
                        return await agent.execute(
                            "你只需要回复：fork成功", fork_from=source_session
                        )

            # 普通初始化
            return await agent.execute(prompt)

        # 并发执行所有新成员的初始化
        results = await asyncio.gather(*[start_conversation(member) for member in new_members])

        # 保存结果
        for result in results:
            await self.runtime.update_agent_session(result)
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
            logger.debug("压缩 Agent: %s", agent.name)
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

        if message.message_type == MessageType.LOOP_MESSAGE:
            logger.info(
                "循环内部消息已投递，不自动保存: group=%s, call_id=%s, loop_id=%s",
                self.group_chat_id,
                message.call_id,
                message.metadata.get("loop_id") if message.metadata else None,
            )
            return

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
        runtime_calls = await self.agent_call_manager.get_runtime_calls_for_agent(agent_name)

        for call in runtime_calls:
            if call.status in (CallStatus.PENDING, CallStatus.RUNNING):
                # 标记为 FAILED
                failure_content = "用户主动停止该 Agent 运行，调用失败，请等待用户下一步指令"
                await self.agent_call_manager.mark_agent_response(
                    call_id=call.call_id,
                    content=failure_content,
                    success=False,
                )

                # 如果调用方不是 user，发送 NOTIFICATION 通知
                if not config.is_user_name(call.send_from):
                    notification_call = await self.agent_call_manager.create_call(
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
                    # 使用 GroupChat 包装层，处理接收者已停止的情况
                    try:
                        await self.send_message_to_agent(notification_message)
                    except Exception as e:
                        # 接收者可能已停止或注销，记录警告但不阻断清理流程
                        logger.warning(
                            "无法发送停止通知 %s -> %s: %s（接收者可能已停止）",
                            agent_name,
                            call.send_from,
                            str(e),
                        )
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
        async with self._get_member_lifecycle_lock(agent_name):
            return await self._stop_member_locked(agent_name)

    async def _stop_member_locked(self, agent_name: str) -> dict:
        """在成员生命周期锁内停止单个 agent。"""
        from agents_hub.core.foundation import AgentNotFoundError

        # 1. 查找 agent
        agent = self._find_agent(agent_name)
        if agent is None:
            logger.error("停止 Agent 失败: name=%s, 原因=未找到", agent_name)
            raise AgentNotFoundError(agent_name)

        logger.info("停止 Agent: %s", agent_name)

        # 2. 先更新状态为 "stopped"（阻止新消息投递）
        try:
            agent_info = self.runtime.get_agent_member_info(agent_name)
        except KeyError:
            agent_info = None
        if agent_info is None:
            logger.warning(
                "停止 Agent 时发现运行态存在但成员状态缺失，自动恢复: group=%s, agent=%s",
                self.group_chat_id,
                agent_name,
            )
            agent_info = self.runtime.get_or_create_agent_member_info(agent_name)
            agent_info.cwd = agent_info.cwd or self.runtime.project_path
        agent_info.status = "stopped"
        await self.runtime.save_agent_members(context=f"Stop agent {agent_name}")

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
            # 降级处理：进程停止失败不阻止后续清理（队列清空、MessageRouter 注销）
            # 避免因外部服务异常导致 Agent 状态不一致
            logger.error("终止 Agent %s 进程失败（降级继续）: %s", agent.name, str(e))

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
        async with self._get_member_lifecycle_lock(agent_name):
            return await self._start_member_locked(agent_name)

    async def _start_member_locked(self, agent_name: str) -> dict:
        """在成员生命周期锁内重新启动单个 agent。"""
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
        task = (
            self.manager_task
            if (self.manager and agent_name == self.manager.name)
            else self.worker_tasks.get(agent_name)
        )
        if task:
            task.add_done_callback(lambda t, name=agent_name: self._on_agent_task_done(name, t))  # type: ignore[misc]

        # 7. 更新状态为 "idle"
        agent_info = self.runtime.get_agent_member_info(agent_name)
        assert agent_info is not None, f"Agent {agent_name} not found"
        agent_info.status = "idle"
        await self.runtime.save_agent_members(context=f"Start agent {agent_name}")

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
        async with self._get_member_lifecycle_lock(agent_name):
            return await self._reset_member_locked(agent_name)

    async def _reset_member_locked(self, agent_name: str) -> dict:
        """在成员生命周期锁内重置单个 agent。"""
        from agents_hub.core.foundation import AgentNotFoundError

        # 1. 查找 agent
        agent = self._find_agent(agent_name)
        if agent is None:
            logger.error("重置 Agent 失败: name=%s, 原因=未找到", agent_name)
            raise AgentNotFoundError(agent_name)

        logger.info("重置 Agent: %s", agent_name)

        # 2. 如果正在运行，先停止
        agent_member_info = self.runtime.state.agent_member_infos.get(agent_name)
        if agent_member_info and agent_member_info.status != "stopped":
            await self._stop_member_locked(agent_name)

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
        agent_info = self.runtime.get_agent_member_info(agent_name)
        assert agent_info is not None, f"Agent {agent_name} not found"
        agent_info.context_usage = 0
        await self.runtime.save_agent_members(context=f"Reset agent {agent_name}")

        # 6. 重新初始化（打招呼）
        await self._initialize_single_member(agent)

        # 7. 自动启动
        agent._run = True
        if self.manager and agent_name == self.manager.name:
            self.manager_task = asyncio.create_task(agent.run())
            mgr_name = self.manager.name
            self.manager_task.add_done_callback(lambda t: self._on_agent_task_done(mgr_name, t))
        else:
            new_task = asyncio.create_task(agent.run())
            new_task.add_done_callback(lambda t, n=agent_name: self._on_agent_task_done(n, t))  # type: ignore[misc]
            self.worker_tasks[agent_name] = new_task

        # 8. 重新注册到 MessageRouter
        self.message_router.register(agent_name, agent.message_queue)

        # 9. 更新状态为 "idle"
        agent_info.status = "idle"
        await self.runtime.save_agent_members(context=f"Reset agent {agent_name} complete")

        # 获取新 session_id
        new_session_id = agent_member_info.main_session if agent_member_info else None

        logger.info("Agent %s 已重置，新 session_id: %s", agent_name, new_session_id)

        return {
            "agent_name": agent_name,
            "status": "idle",
            "new_session_id": new_session_id,
        }

    async def start_private_chat(self, agent_name: str) -> dict:
        """
        将 Agent 状态设置为 in_private_chat，允许前端私聊。

        前置条件：Agent 必须处于 idle 状态。
        Manager 角色禁止私聊。

        Args:
            agent_name: Agent 名称

        Returns:
            dict: {"agent_name": str, "status": "in_private_chat", "main_session_id": str | None}

        Raises:
            AgentNotFoundError: Agent 不存在
            StateError: Agent 非 idle 状态
            PermissionError: Agent 是 Manager
        """
        from agents_hub.core.foundation import AgentNotFoundError
        from agents_hub.exceptions import StateError

        # 检查是否为 Manager
        if agent_name == self.manager.name if self.manager else False:
            logger.warning("禁止与 Manager 私聊: agent=%s", agent_name)
            raise PermissionError("Manager 不允许进入私聊")

        # 获取 Agent 状态
        agent_info = self.runtime.state.agent_member_infos.get(agent_name)
        if not agent_info:
            raise AgentNotFoundError(agent_name)

        # 检查状态是否为 idle
        if agent_info.status != "idle":
            raise StateError(
                f"Agent {agent_name} 当前状态为 {agent_info.status}，只有 idle 状态才能进入私聊",
                details={"agent_name": agent_name, "current_status": agent_info.status},
            )

        # 更新状态
        agent_info.status = "in_private_chat"
        await self.runtime.save_agent_members(context=f"Start private chat: {agent_name}")

        logger.info("Agent %s 已进入私聊", agent_name)

        return {
            "agent_name": agent_name,
            "status": "in_private_chat",
            "main_session_id": agent_info.main_session,
        }

    async def stop_private_chat(self, agent_name: str) -> dict:
        """
        将 Agent 状态从 in_private_chat 恢复为 idle。

        前置条件：Agent 必须处于 in_private_chat 状态。

        Args:
            agent_name: Agent 名称

        Returns:
            dict: {"agent_name": str, "status": "idle"}

        Raises:
            AgentNotFoundError: Agent 不存在
            StateError: Agent 非 in_private_chat 状态
        """
        from agents_hub.core.foundation import AgentNotFoundError
        from agents_hub.exceptions import StateError

        # 获取 Agent 状态
        agent_info = self.runtime.state.agent_member_infos.get(agent_name)
        if not agent_info:
            raise AgentNotFoundError(agent_name)

        # 检查状态是否为 in_private_chat
        if agent_info.status != "in_private_chat":
            raise StateError(
                f"Agent {agent_name} 当前状态为 {agent_info.status}，只有 in_private_chat 状态才能退出私聊",
                details={"agent_name": agent_name, "current_status": agent_info.status},
            )

        # 更新状态
        agent_info.status = "idle"
        await self.runtime.save_agent_members(context=f"Stop private chat: {agent_name}")

        logger.info("Agent %s 已退出私聊", agent_name)

        return {
            "agent_name": agent_name,
            "status": "idle",
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

        if self.manager:
            self.manager.set_loop_completion_queue(None)
        for worker in self.workers.values():
            worker.set_loop_completion_queue(None)

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

        # 3.5 关闭 AgentCallManager，释放文件句柄
        self.agent_call_manager.close()

        # 3.6 关闭 TaskManager，释放文件句柄
        self.task_manager.close()

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

    async def _ensure_tokens(self) -> None:
        """
        确保所有 agent 都有 token（生成或恢复）并注册到 GroupChatManager

        策略：
        - 如果 agent 已有 token → 使用已有的（load 场景）
        - 如果 agent 没有 token → 生成新的（start 场景或新增成员）
        """
        from .group_chat_manager import group_chat_manager

        logger.debug("确保所有 agent 都有 token: id=%s", self.group_chat_id)

        # Manager token
        if self.manager:
            manager_info = self.runtime.get_or_create_agent_member_info(self.manager.name)
            if not manager_info.token:
                token = generate_token()
                manager_info.token = token
                manager_info.cwd = self.runtime.project_path
            else:
                token = manager_info.token

            group_chat_manager.register_token(token, self.manager.name, self.group_chat_id)

        # Worker tokens
        for worker_name, _worker in self.workers.items():
            worker_info = self.runtime.get_or_create_agent_member_info(worker_name)
            if not worker_info.token:
                token = generate_token()
                worker_info.token = token
                worker_info.cwd = self.runtime.project_path
            else:
                token = worker_info.token

            group_chat_manager.register_token(token, worker_name, self.group_chat_id)

        # 统一保存
        await self.runtime.save_agent_members()

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
                    exc = (
                        self.manager_task.exception() if not self.manager_task.cancelled() else None
                    )
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
                    send_from=SystemRoles.HEARTBEAT,
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
