"""
Loop 循环管理器

管理 Loop 循环的创建、查询、更新和持久化。
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
    """Loop 循环管理器

    职责：
    - 创建循环（带校验和并发控制）
    - 查询循环（按 loop_id 或 group_chat_id）
    - 更新循环状态（带状态机校验）
    - 删除循环（只能删除非 RUNNING 状态）
    - 持久化到 JSONL（append-only 模式）
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

        # 内存缓存
        self._loops: dict[str, Loop] = {}

        # 并发控制锁
        self._lock = asyncio.Lock()

        # 从持久化恢复
        self._load_from_persistence()

    async def create_loop(
        self,
        nodes: list[dict[str, Any]],
        max_iterations: int,
        initial_task: str,
    ) -> Loop:
        """创建 Loop 循环

        Args:
            nodes: 节点列表，每个节点包含 node_type, agent_name, role_description, output_schema_prompt, output_schema_fields, max_retries
            max_iterations: 最大循环次数
            initial_task: 初始任务描述

        Returns:
            Loop: 创建的循环对象

        Raises:
            LoopValidationError: 校验失败（节点数量、TERMINATOR、agent_name、并发限制）
            AgentNotFoundError: Agent 不存在
        """
        async with self._lock:
            # 构造 LoopNode 对象
            loop_nodes = [LoopNode.from_dict(node) for node in nodes]

            # 校验
            self._validate_create_request(loop_nodes, max_iterations)

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
        """查询单个 Loop

        Args:
            loop_id: Loop ID

        Returns:
            Loop: 循环对象

        Raises:
            LoopNotFoundError: Loop 不存在
        """
        if loop_id not in self._loops:
            self.logger.error(
                "Loop 不存在: loop_id=%s, 可用=%s",
                loop_id,
                list(self._loops.keys()),
            )
            raise LoopNotFoundError(loop_id)

        return self._loops[loop_id]

    def list_loops(self, status: str | None = None) -> list[Loop]:
        """查询群聊的所有 Loop

        Args:
            status: 可选的状态过滤（"created"/"running"/"paused"/"completed"/"failed"）

        Returns:
            list[Loop]: 循环列表
        """
        loops = list(self._loops.values())

        if status:
            loops = [loop for loop in loops if loop.status == status]

        return loops

    async def update_loop_status(
        self,
        loop_id: str,
        status: str,
        current_iteration: int | None = None,
        current_node_index: int | None = None,
        error_message: str | None = None,
    ) -> Loop:
        """更新 Loop 状态

        Args:
            loop_id: Loop ID
            status: 新状态
            current_iteration: 当前迭代次数（可选）
            current_node_index: 当前节点索引（可选）
            error_message: 错误信息（可选）

        Returns:
            Loop: 更新后的循环对象

        Raises:
            LoopNotFoundError: Loop 不存在
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
        """删除 Loop

        Args:
            loop_id: Loop ID

        Raises:
            LoopNotFoundError: Loop 不存在
            LoopStateError: Loop 状态为 RUNNING，不能删除
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
        """校验创建 Loop 的请求

        Args:
            nodes: 节点列表

        Raises:
            LoopValidationError: 校验失败
            AgentNotFoundError: Agent 不存在
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
        """从 JSONL 加载历史 Loop

        容错处理：
        - 跳过空行
        - 跳过损坏行（记录 WARNING）
        - 同一 loop_id 多条记录取最新
        - 跳过已删除的 Loop（墓碑记录）
        """
        if not self._persistence_path.exists():
            self.logger.debug("持久化文件不存在，跳过加载")
            return

        try:
            loop_records: dict[str, dict[str, Any]] = {}  # loop_id -> 最新记录（去重）
            deleted_ids: set[str] = set()  # 已删除的 loop_id

            with open(self._persistence_path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue  # 跳过空行

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

                        # 后面的记录覆盖前面的（取最新，自动去重）
                        loop_records[loop_id] = data
                    except (json.JSONDecodeError, KeyError) as e:
                        self.logger.warning(
                            "跳过损坏的 JSONL 行: 行号=%d, error=%s",
                            line_num,
                            e,
                        )
                        continue

            # 反序列化
            for loop_id, data in loop_records.items():
                loop = Loop.from_dict(data)
                self._loops[loop_id] = loop

            self.logger.info("加载了 %d 个 Loop", len(loop_records))

        except OSError as e:
            raise FileSystemError(
                operation="read",
                path=str(self._persistence_path),
                reason=str(e),
            ) from e

    def _persist_loop(self, loop: Loop) -> None:
        """持久化单个 Loop（追加模式）

        Args:
            loop: Loop 对象

        Raises:
            FileSystemError: 文件操作失败
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
        """持久化删除标记（墓碑记录）

        Args:
            loop_id: 被删除的 Loop ID

        Raises:
            FileSystemError: 文件操作失败
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
