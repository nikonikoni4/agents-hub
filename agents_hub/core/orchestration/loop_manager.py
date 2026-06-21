"""
Loop 循环定义管理器。

管理 Loop 循环定义的创建、查询和持久化。LoopManager 是 Loop 定义的
CRUD 入口，负责：
- 创建循环定义（带校验和并发控制）
- 查询循环定义（按 loop_id）
- 删除循环定义（同时级联删除关联的 executions）
- 持久化到 JSONL（append-only 模式）

设计决策：
- Loop 定义与执行实例分离，Loop 作为可复用模板
- 执行状态管理委托给 LoopExecutionManager
- Loop 定义可以长期保留在内存（不再需要单 Loop 保持）
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
    LoopValidationError,
)
from agents_hub.core.foundation.paths import group_chat_paths
from agents_hub.roles import RoleManager
from agents_hub.utils.logger import get_specialized_logger


class LoopManager:
    """Loop 循环定义管理器。

    负责 Loop 循环定义的 CRUD 操作和持久化管理。每个 GroupChat 实例化一个
    LoopManager，通过 group_chat_id 隔离不同群聊的循环定义数据。

    持久化策略：
    - 使用 JSONL 格式，append-only 模式
    - 每次变更追加一条记录
    - 同一 loop_id 多条记录取最新（容错）
    - 删除操作使用墓碑记录（_deleted: true）

    Attributes:
        group_chat_id: 所属群聊 ID。
        role_manager: 角色管理器，用于校验 agent_name 是否存在。
        logger: 专用日志器，输出到 loops.log。
    """

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

        # 内存缓存（Loop 定义可以长期保留）
        self._loops: dict[str, Loop] = {}

        # 并发控制锁
        self._lock = asyncio.Lock()

        # 不自动加载历史 Loop，改为懒加载策略（按需加载）

    async def create_loop(
        self,
        nodes: list[dict[str, Any]],
        max_iterations: int,
    ) -> Loop:
        """创建 Loop 循环定义。

        创建一个新的循环定义，包含节点列表和最大循环次数。
        创建过程会进行严格校验，确保循环定义合法。

        创建流程：
        1. 获取并发控制锁，确保线程安全
        2. 将节点字典列表转换为 LoopNode 对象
        3. 调用 _validate_create_request() 执行校验规则
        4. 构造 Loop 对象
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

        Returns:
            创建的 Loop 实例。

        Raises:
            LoopValidationError: 校验失败，包括：
                - 节点数量不足（至少 2 个）
                - TERMINATOR 节点数量不正确（必须恰好 1 个）
                - max_iterations <= 0
            AgentNotFoundError: 节点中指定的 agent_name 在 RoleManager 中不存在。
        """
        async with self._lock:
            # 构造 LoopNode 对象
            loop_nodes = [LoopNode.from_dict(node) for node in nodes]

            # 校验
            self._validate_create_request(loop_nodes, max_iterations)

            # 创建 Loop 定义
            loop = Loop(
                loop_id=str(uuid4()),
                group_chat_id=self.group_chat_id,
                nodes=loop_nodes,
                max_iterations=max_iterations,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            # 保存到内存和持久化
            self._loops[loop.loop_id] = loop
            self._persist_loop(loop)

            self.logger.info(
                "创建 Loop 定义: loop_id=%s, nodes=%d, max_iterations=%d",
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
            "Loop 懒加载成功: loop_id=%s, max_iterations=%d",
            loop_id,
            loop.max_iterations,
        )

        return loop

    def list_loops(self, status: str | None = None) -> list[dict]:
        """查询群聊的所有历史 Loop 定义（直接读取 JSONL）。

        不依赖内存缓存，直接读取 JSONL 文件并返回摘要信息。
        返回格式包含 `in_memory` 标记，指示该 Loop 是否在内存中。

        注意：status 参数已废弃，Loop 定义本身没有状态。
        保留此参数仅为向后兼容，实际不进行过滤。

        Args:
            status: （已废弃）状态过滤参数，Loop 定义无状态，此参数被忽略。

        Returns:
            循环定义摘要列表，每个元素包含：
            - loop_id: 循环 ID
            - created_at: 创建时间
            - updated_at: 更新时间
            - max_iterations: 最大循环次数
            - nodes_count: 节点数量
            - in_memory: 是否在内存中（bool）
        """
        loop_records = self._read_jsonl_loops()

        # 构造摘要信息
        result = []
        for loop_id, data in loop_records.items():
            summary = {
                "loop_id": loop_id,
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "max_iterations": data.get("max_iterations"),
                "nodes_count": len(data.get("nodes", [])),
                "in_memory": loop_id in self._loops,  # 标记是否在内存
            }
            result.append(summary)

        # 按创建时间排序（最新的在前）
        result.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)

        return result

    async def delete_loop(self, loop_id: str, loop_execution_manager=None) -> None:
        """删除 Loop 定义。

        删除指定的循环定义，同时级联删除所有关联的执行实例。

        Args:
            loop_id: 循环唯一标识。
            loop_execution_manager: LoopExecutionManager 实例，用于级联删除 executions。

        Raises:
            LoopNotFoundError: 循环不存在时抛出。
        """
        # 验证 Loop 存在（不存在则抛出 LoopNotFoundError）
        self.get_loop(loop_id)

        # 级联删除关联的 executions
        if loop_execution_manager:
            deleted_count = await loop_execution_manager.delete_executions_by_loop(loop_id)
            self.logger.info(
                "级联删除 LoopExecution: loop_id=%s, 删除数量=%d",
                loop_id,
                deleted_count,
            )

        # 从内存删除
        del self._loops[loop_id]

        # 持久化删除标记（墓碑记录）
        self._persist_deletion(loop_id)

        self.logger.info("删除 Loop 定义: loop_id=%s", loop_id)

    def _validate_create_request(self, nodes: list[LoopNode], max_iterations: int) -> None:
        """校验创建 Loop 的请求。

        执行以下校验规则：
        1. max_iterations 必须大于 0
        2. 节点数量至少 2 个
        3. 有且仅有 1 个 TERMINATOR 节点
        4. 所有 agent_name 必须在 RoleManager 中存在

        校验逻辑详解：
        - 规则 1：防止死循环，max_iterations 必须是正整数
        - 规则 2：循环至少需要 2 个节点（一个执行者 + 一个审查者）
        - 规则 3：TERMINATOR 节点负责判断循环是否继续，必须恰好 1 个
        - 规则 4：确保节点指定的 Agent 在系统中存在

        Args:
            nodes: 节点列表，已转换为 LoopNode 对象。
            max_iterations: 最大循环次数。

        Raises:
            LoopValidationError: 校验失败，包括节点数量、TERMINATOR 数量等。
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
