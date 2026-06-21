"""
Loop 循环管理器。

管理 Loop 循环的创建、查询、更新和持久化。LoopManager 是 Loop 功能的
CRUD 入口，负责：
- 创建循环（带校验和并发控制）
- 查询循环（按 loop_id 或 group_chat_id）
- 更新循环状态（带状态机校验）
- 删除循环（只能删除非 RUNNING 状态）
- 持久化到 JSONL（append-only 模式）

设计决策参考：PRD 中的"数据模型"和"持久化"章节。
"""

import asyncio
import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from agents_hub.core.context.loop_models import Loop, LoopNode, LoopNodeType
from agents_hub.core.foundation.exceptions import (
    AgentNotFoundError,
    FileSystemError,
    LoopNotFoundError,
    LoopStateError,
    LoopValidationError,
)
from agents_hub.core.foundation.models import LoopStatus
from agents_hub.core.foundation.paths import group_chat_paths
from agents_hub.roles import RoleManager
from agents_hub.utils.logger import get_specialized_logger


class LoopManager:
    """Loop 循环管理器。

    负责 Loop 循环的 CRUD 操作和持久化管理。每个 GroupChat 实例化一个
    LoopManager，通过 group_chat_id 隔离不同群聊的循环数据。

    状态机转换规则：
    - CREATED -> RUNNING（启动循环）
    - RUNNING -> PAUSED / COMPLETED / FAILED（暂停/正常完成/失败）
    - PAUSED -> RUNNING / FAILED（恢复/失败）
    - COMPLETED / FAILED 是终态，不可转换

    持久化策略：
    - 使用 JSONL 格式，append-only 模式
    - 每次状态变更追加一条记录
    - 同一 loop_id 多条记录取最新（容错）
    - 删除操作使用墓碑记录（_deleted: true）

    Attributes:
        group_chat_id: 所属群聊 ID。
        role_manager: 角色管理器，用于校验 agent_name 是否存在。
        logger: 专用日志器，输出到 loops.log。
    """

    # 合法的状态转换：from_status -> {allowed_to_statuses}
    _VALID_TRANSITIONS: dict[str, set[str]] = {
        LoopStatus.CREATED.value: {LoopStatus.RUNNING.value},
        LoopStatus.RUNNING.value: {
            LoopStatus.PAUSED.value,
            LoopStatus.COMPLETED.value,
            LoopStatus.FAILED.value,
        },
        LoopStatus.PAUSED.value: {LoopStatus.RUNNING.value, LoopStatus.FAILED.value},
        LoopStatus.COMPLETED.value: set(),
        LoopStatus.FAILED.value: set(),
    }

    def __init__(self, group_chat_id: str, project_path: str):
        """初始化 LoopManager。

        Args:
            group_chat_id: 所属群聊 ID，用于隔离不同群聊的循环数据。
            project_path: 项目路径，用于构建持久化文件路径。
        """
        self.group_chat_id = group_chat_id
        self.role_manager = RoleManager()

        # 初始化 logger
        log_dir = group_chat_paths.base_dir(group_chat_id, project_path)
        self.logger = get_specialized_logger(
            name=f"loop_manager.{group_chat_id}",
            log_filename="loops.log",
            also_to_global=True,
            log_dir=log_dir,
        )

        # 初始化持久化路径
        self._persistence_path = group_chat_paths.loops_data(group_chat_id, project_path)
        self._persistence_path.parent.mkdir(parents=True, exist_ok=True)

        # 内存缓存（懒加载，初始为空）
        self._loops: dict[str, Loop] = {}

        # 并发控制锁
        self._lock = asyncio.Lock()

        # 不自动加载历史 Loop，改为懒加载策略（按需加载）

    async def create_loop(
        self,
        nodes: list[dict[str, Any]],
        max_iterations: int,
        initial_task: str,
    ) -> Loop:
        """创建 Loop 循环。

        创建一个新的循环实例，包含节点列表、最大循环次数和初始任务。
        创建过程会进行严格校验，确保循环定义合法。

        创建流程：
        1. 获取并发控制锁，确保线程安全
        2. 将节点字典列表转换为 LoopNode 对象
        3. 调用 _validate_create_request() 执行校验规则
        4. 构造 Loop 对象，设置初始状态为 CREATED
        5. 保存到内存缓存和 JSONL 持久化文件
        6. 记录 INFO 日志并返回 Loop 实例

        Args:
            nodes: 节点列表，每个节点必须包含以下字段：
                - node_type: 节点类型（"normal" 或 "terminator"）
                - agent_name: 执行节点的 Agent 名称
                - role_description: 节点职责描述
                - output_schema_prompt: 输出格式提示词（可选）
                - output_schema_fields: 必需字段列表（可选）
                - max_retries: 最大重试次数（可选，默认 3）
            max_iterations: 最大循环次数，必须大于 0。
            initial_task: 初始任务描述，发送给第一个节点的任务内容。

        Returns:
            创建的 Loop 实例，状态为 CREATED。

        Raises:
            LoopValidationError: 校验失败，包括：
                - 节点数量不足（至少 2 个）
                - TERMINATOR 节点数量不正确（必须恰好 1 个）
                - max_iterations <= 0
                - 该群聊已有 RUNNING 状态的循环
            AgentNotFoundError: 节点中指定的 agent_name 在 RoleManager 中不存在。
        """
        async with self._lock:
            # 构造 LoopNode 对象
            loop_nodes = [LoopNode.from_dict(node) for node in nodes]

            # 校验
            self._validate_create_request(loop_nodes, max_iterations)

            # 清空旧 Loop（单 Loop 保持策略）
            old_loop_count = len(self._loops)
            if old_loop_count > 0:
                self.logger.info(
                    "创建新 Loop 前清空内存: group=%s, 清理数量=%d",
                    self.group_chat_id,
                    old_loop_count,
                )
                self._loops.clear()

            # 创建 Loop
            loop = Loop(
                loop_id=str(uuid4()),
                group_chat_id=self.group_chat_id,
                nodes=loop_nodes,
                status=LoopStatus.CREATED.value,
                max_iterations=max_iterations,
                current_iteration=1,
                current_node_index=0,
                initial_task=initial_task,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            # 保存到内存和持久化
            self._loops[loop.loop_id] = loop
            self._persist_loop(loop)

            self.logger.info(
                "创建 Loop: loop_id=%s, nodes=%d, max_iterations=%d",
                loop.loop_id,
                len(loop.nodes),
                loop.max_iterations,
            )

            return loop

    def get_loop(self, loop_id: str) -> Loop:
        """查询单个 Loop。

        Args:
            loop_id: 循环唯一标识。

        Returns:
            Loop 实例。

        Raises:
            LoopNotFoundError: 循环不存在时抛出。
        """
        if loop_id not in self._loops:
            self.logger.error(
                "Loop 不存在: loop_id=%s, 可用=%s",
                loop_id,
                list(self._loops.keys()),
            )
            raise LoopNotFoundError(loop_id)

        return self._loops[loop_id]

    def _read_jsonl_loops(self) -> dict[str, dict]:
        """从 JSONL 文件读取所有 Loop 记录（内部辅助方法）。

        遍历 JSONL 文件，处理墓碑记录，返回每个 loop_id 的最新记录。
        容错处理：跳过空行和损坏的 JSON 行，记录 WARNING 日志。

        Returns:
            loop_id -> 最新记录的字典。
        """
        if not self._persistence_path.exists():
            return {}

        loop_records: dict[str, dict] = {}
        deleted_ids: set[str] = set()

        try:
            with open(self._persistence_path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        loop_id = data["loop_id"]

                        # 墓碑记录：标记删除
                        if data.get("_deleted"):
                            deleted_ids.add(loop_id)
                            loop_records.pop(loop_id, None)
                            continue

                        # 跳过已删除的 loop_id
                        if loop_id in deleted_ids:
                            continue

                        # 后面的记录覆盖前面的（取最新）
                        loop_records[loop_id] = data
                    except (json.JSONDecodeError, KeyError) as e:
                        self.logger.warning(
                            "跳过损坏的 JSONL 行: 行号=%d, error=%s",
                            line_num,
                            e,
                        )
                        continue

            return loop_records

        except OSError as e:
            raise FileSystemError(
                operation="read",
                path=str(self._persistence_path),
                reason=str(e),
            ) from e

    def get_loop_with_lazy_load(self, loop_id: str) -> Loop:
        """查询单个 Loop，支持懒加载。

        如果 Loop 在内存中，直接返回；如果不在内存中，从 JSONL 加载。
        用于 start_loop() 和 get_loop_status() 等需要懒加载的场景。

        Args:
            loop_id: 循环唯一标识。

        Returns:
            Loop 实例。

        Raises:
            LoopNotFoundError: 循环在 JSONL 中也不存在时抛出。
        """
        # 1. 检查内存
        if loop_id in self._loops:
            self.logger.debug("Loop 命中内存: loop_id=%s", loop_id)
            return self._loops[loop_id]

        # 2. 从 JSONL 加载
        self.logger.info(
            "Loop 未在内存，触发懒加载: loop_id=%s, group=%s",
            loop_id,
            self.group_chat_id,
        )

        loop_records = self._read_jsonl_loops()
        loop_record = loop_records.get(loop_id)

        if loop_record is None:
            self.logger.error(
                "Loop 不存在: loop_id=%s, JSONL 中无有效记录",
                loop_id,
            )
            raise LoopNotFoundError(loop_id)

        # 3. 反序列化并加载到内存
        loop = Loop.from_dict(loop_record)
        self._loops[loop_id] = loop

        self.logger.info(
            "Loop 懒加载成功: loop_id=%s, status=%s",
            loop_id,
            loop.status,
        )

        return loop

    def list_loops(self, status: str | None = None) -> list[dict]:
        """查询群聊的所有历史 Loop（直接读取 JSONL）。

        不依赖内存缓存，直接读取 JSONL 文件并返回摘要信息。
        返回格式包含 `in_memory` 标记，指示该 Loop 是否在内存中。

        Args:
            status: 可选的状态过滤，取值为 "created"/"running"/"paused"/"completed"/"failed"。

        Returns:
            循环摘要列表，每个元素包含：
            - loop_id: 循环 ID
            - status: 循环状态
            - created_at: 创建时间
            - updated_at: 更新时间
            - max_iterations: 最大循环次数
            - current_iteration: 当前轮次
            - in_memory: 是否在内存中（bool）
        """
        loop_records = self._read_jsonl_loops()

        # 构造摘要信息
        result = []
        for loop_id, data in loop_records.items():
            # 状态过滤
            if status and data.get("status") != status:
                continue

            summary = {
                "loop_id": loop_id,
                "status": data.get("status"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "max_iterations": data.get("max_iterations"),
                "current_iteration": data.get("current_iteration"),
                "in_memory": loop_id in self._loops,  # 标记是否在内存
            }
            result.append(summary)

        # 按创建时间排序（最新的在前）
        result.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)

        return result

    def clear_other_loops(self, keep_loop_id: str) -> int:
        """清空内存中除指定 Loop 外的所有 Loop。

        用于启动 Loop 时保持单 Loop 内存策略。

        Args:
            keep_loop_id: 要保留的 Loop ID。

        Returns:
            清理的 Loop 数量。
        """
        other_loops = [lid for lid in self._loops if lid != keep_loop_id]
        if other_loops:
            self.logger.info(
                "清空其他 Loop: group=%s, 清理数量=%d, 保留=%s",
                self.group_chat_id,
                len(other_loops),
                keep_loop_id,
            )
            for lid in other_loops:
                self._loops.pop(lid, None)
        return len(other_loops)

    async def update_loop_status(
        self,
        loop_id: str,
        status: str,
        current_iteration: int | None = None,
        current_node_index: int | None = None,
        error_message: str | None = None,
    ) -> Loop:
        """更新 Loop 状态。

        按照状态机规则更新循环状态，同时可选更新迭代次数、节点索引和错误信息。
        同状态更新（幂等操作）用于持久化迭代/节点等字段变更。

        更新流程：
        1. 调用 get_loop() 获取循环实例（不存在则抛出 LoopNotFoundError）
        2. 检查状态转换合法性：
           - 如果新状态与当前状态相同，视为幂等操作，允许更新其他字段
           - 如果新状态不同，检查 _VALID_TRANSITIONS 字典是否允许该转换
        3. 更新状态和其他可选字段
        4. 调用 _persist_loop() 持久化到 JSONL 文件
        5. 记录 INFO 日志并返回更新后的 Loop 实例

        Args:
            loop_id: 循环唯一标识。
            status: 新状态，取值为 "created"/"running"/"paused"/"completed"/"failed"。
            current_iteration: 当前迭代次数（可选）。
            current_node_index: 当前节点索引（可选）。
            error_message: 错误信息（可选），仅在 FAILED 状态时设置。

        Returns:
            更新后的 Loop 实例。

        Raises:
            LoopNotFoundError: 循环不存在时抛出。
            LoopStateError: 状态转换非法时抛出（如 COMPLETED -> RUNNING）。
        """
        loop = self.get_loop(loop_id)

        # 状态机校验。同状态更新用于持久化迭代/节点等字段，视为幂等操作。
        allowed = self._VALID_TRANSITIONS.get(loop.status, set())
        if status != loop.status and status not in allowed:
            self.logger.error(
                "Loop 状态转换非法: loop_id=%s, %s -> %s, 允许=%s",
                loop_id,
                loop.status,
                status,
                allowed,
            )
            raise LoopStateError(loop_id, loop.status, f"transition to {status}")

        # 更新字段
        loop.status = status
        loop.updated_at = datetime.now()

        if current_iteration is not None:
            loop.current_iteration = current_iteration

        if current_node_index is not None:
            loop.current_node_index = current_node_index

        if error_message is not None:
            loop.error_message = error_message

        # 持久化
        self._persist_loop(loop)

        self.logger.info(
            "更新 Loop 状态: loop_id=%s, status=%s, iteration=%d, node_index=%d",
            loop_id,
            status,
            loop.current_iteration,
            loop.current_node_index,
        )

        return loop

    async def delete_loop(self, loop_id: str) -> None:
        """删除 Loop。

        删除指定的循环，只能删除非 RUNNING 状态的循环。
        删除操作使用墓碑记录（_deleted: true）持久化，确保重启后仍保持删除状态。

        Args:
            loop_id: 循环唯一标识。

        Raises:
            LoopNotFoundError: 循环不存在时抛出。
            LoopStateError: 循环状态为 RUNNING 时抛出，不能删除正在运行的循环。
        """
        loop = self.get_loop(loop_id)

        # 校验状态
        if loop.status == LoopStatus.RUNNING.value:
            self.logger.error(
                "删除 Loop 失败: loop_id=%s, status=%s, 不能删除 RUNNING 状态的 Loop",
                loop_id,
                loop.status,
            )
            raise LoopStateError(loop_id, loop.status, "delete")

        # 从内存删除
        del self._loops[loop_id]

        # 持久化删除标记（墓碑记录）
        self._persist_deletion(loop_id)

        self.logger.info("删除 Loop: loop_id=%s", loop_id)

    def _validate_create_request(self, nodes: list[LoopNode], max_iterations: int) -> None:
        """校验创建 Loop 的请求。

        执行以下校验规则：
        1. max_iterations 必须大于 0
        2. 节点数量至少 2 个
        3. 有且仅有 1 个 TERMINATOR 节点
        4. 所有 agent_name 必须在 RoleManager 中存在
        5. 该群聊没有其他 RUNNING 状态的循环

        校验逻辑详解：
        - 规则 1：防止死循环，max_iterations 必须是正整数
        - 规则 2：循环至少需要 2 个节点（一个执行者 + 一个审查者）
        - 规则 3：TERMINATOR 节点负责判断循环是否继续，必须恰好 1 个
        - 规则 4：确保节点指定的 Agent 在系统中存在
        - 规则 5：一个群聊同时只能有一个 RUNNING 状态的循环，避免资源竞争

        Args:
            nodes: 节点列表，已转换为 LoopNode 对象。
            max_iterations: 最大循环次数。

        Raises:
            LoopValidationError: 校验失败，包括节点数量、TERMINATOR 数量、并发限制等。
            AgentNotFoundError: 节点中指定的 agent_name 不存在。
        """
        # 1. 最大循环次数必须大于 0
        if max_iterations <= 0:
            self.logger.error(
                "Loop 校验失败: max_iterations 必须大于 0, 实际=%d",
                max_iterations,
            )
            raise LoopValidationError(
                reason="max_iterations 必须大于 0",
                details={"max_iterations": max_iterations},
            )

        # 2. 节点数量至少 2 个
        if len(nodes) < 2:
            self.logger.error(
                "Loop 校验失败: 节点数量不足, 需要至少 2 个节点, 实际=%d",
                len(nodes),
            )
            raise LoopValidationError(
                reason="节点数量不足，至少需要 2 个节点",
                details={"node_count": len(nodes)},
            )

        # 3. 有且仅有 1 个 TERMINATOR 节点
        terminator_count = sum(
            1 for node in nodes if node.node_type == LoopNodeType.TERMINATOR.value
        )

        if terminator_count == 0:
            self.logger.error("Loop 校验失败: 缺少 TERMINATOR 节点")
            raise LoopValidationError(
                reason="缺少 TERMINATOR 节点",
                details={"terminator_count": 0},
            )

        if terminator_count > 1:
            self.logger.error(
                "Loop 校验失败: TERMINATOR 节点过多, 只能有 1 个, 实际=%d",
                terminator_count,
            )
            raise LoopValidationError(
                reason="TERMINATOR 节点过多，只能有 1 个",
                details={"terminator_count": terminator_count},
            )

        # 4. 所有 agent_name 必须存在
        available_agents = self.role_manager.list_role_names()
        for node in nodes:
            if node.agent_name not in available_agents:
                self.logger.error(
                    "Loop 校验失败: agent_name=%s 不存在, 可用=%s",
                    node.agent_name,
                    available_agents,
                )
                raise AgentNotFoundError(node.agent_name)

        # 5. 该 group_chat 没有其他 RUNNING 的 Loop
        running_loops = [
            loop for loop in self._loops.values() if loop.status == LoopStatus.RUNNING.value
        ]
        if running_loops:
            running_loop_ids = [loop.loop_id for loop in running_loops]
            self.logger.error(
                "Loop 校验失败: 该群聊已有 RUNNING 状态的 Loop, loop_ids=%s",
                running_loop_ids,
            )
            raise LoopValidationError(
                reason="该群聊已有 RUNNING 状态的 Loop，不能同时创建多个",
                details={"running_loop_ids": running_loop_ids},
            )

    def _load_from_persistence(self) -> None:
        """从 JSONL 文件加载历史 Loop 数据。

        启动时调用，从持久化文件恢复循环状态。采用容错处理策略：
        - 跳过空行
        - 跳过损坏行（记录 WARNING 日志）
        - 同一 loop_id 多条记录取最新（自动去重）
        - 跳过已删除的 Loop（墓碑记录）

        Raises:
            FileSystemError: 文件读取失败时抛出。
        """
        loop_records = self._read_jsonl_loops()

        # 反序列化并加载到内存
        for loop_id, data in loop_records.items():
            loop = Loop.from_dict(data)
            self._loops[loop_id] = loop

        self.logger.info("加载了 %d 个 Loop", len(loop_records))

    def _persist_loop(self, loop: Loop) -> None:
        """持久化单个 Loop（追加模式）。

        将 Loop 序列化为 JSON 并追加到 JSONL 文件。
        每次状态变更都会追加一条新记录，实现 append-only 持久化。

        Args:
            loop: 要持久化的 Loop 实例。

        Raises:
            FileSystemError: 文件写入失败时抛出。
        """
        data = loop.to_dict()

        try:
            with open(self._persistence_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        except OSError as e:
            raise FileSystemError(
                operation="write",
                path=str(self._persistence_path),
                reason=str(e),
            ) from e

    def _persist_deletion(self, loop_id: str) -> None:
        """持久化删除标记（墓碑记录）。

        写入一条包含 _deleted: true 的记录，标记该 loop_id 已被删除。
        重启加载时会跳过墓碑记录对应的 loop_id。

        Args:
            loop_id: 被删除的 Loop ID。

        Raises:
            FileSystemError: 文件写入失败时抛出。
        """
        data = {"loop_id": loop_id, "_deleted": True}

        try:
            with open(self._persistence_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        except OSError as e:
            raise FileSystemError(
                operation="write",
                path=str(self._persistence_path),
                reason=str(e),
            ) from e
