"""
Loop 执行实例管理器。

管理 LoopExecution 执行实例的创建、查询、更新和持久化。LoopExecutionManager
负责执行实例的 CRUD 操作，与 LoopManager 平级。

职责：
- 创建执行实例（关联 Loop 定义）
- 查询执行实例（按 execution_id）
- 更新执行状态（带状态机校验）
- 删除执行实例（写墓碑记录）
- 持久化到 JSONL（append-only 模式）
- 支持懒加载和单 execution 保持策略

设计决策：
- LoopExecution 是一次性执行实例，完成后成为历史记录
- 内存中同时只保持一个活跃的 execution（单 execution 保持策略）
- 支持查询特定 Loop 的所有执行历史
"""

import asyncio
import json
from datetime import datetime
from uuid import uuid4

from agents_hub.core.context.loop_models import LoopExecution
from agents_hub.core.foundation.exceptions import (
    FileSystemError,
    LoopExecutionNotFoundError,
    LoopExecutionStateError,
)
from agents_hub.core.foundation.models import LoopExecutionStatus
from agents_hub.core.foundation.paths import group_chat_paths
from agents_hub.utils.logger import get_specialized_logger


class LoopExecutionManager:
    """Loop 执行实例管理器。

    负责 LoopExecution 执行实例的 CRUD 操作和持久化管理。每个 GroupChat
    实例化一个 LoopExecutionManager，通过 group_chat_id 隔离不同群聊的执行数据。

    状态机转换规则：
    - CREATED -> RUNNING（启动执行）
    - RUNNING -> PAUSED / COMPLETED / FAILED（暂停/正常完成/失败）
    - PAUSED -> RUNNING / FAILED（恢复/失败）
    - COMPLETED / FAILED 是终态，不可转换

    持久化策略：
    - 使用 JSONL 格式，append-only 模式
    - 每次状态变更追加一条记录
    - 同一 execution_id 多条记录取最新（容错）
    - 删除操作使用墓碑记录（_deleted: true）

    内存管理策略：
    - 初始化时内存为空，不自动加载历史
    - 单 execution 保持策略：启动时清空其他 execution
    - COMPLETED/FAILED/PAUSED 状态保留在内存，方便查询
    - 懒加载：查询时如果不在内存则从 JSONL 加载

    Attributes:
        group_chat_id: 所属群聊 ID。
        logger: 专用日志器，输出到 loops.log。
    """

    # 合法的状态转换：from_status -> {allowed_to_statuses}
    _VALID_TRANSITIONS: dict[str, set[str]] = {
        LoopExecutionStatus.CREATED.value: {LoopExecutionStatus.RUNNING.value},
        LoopExecutionStatus.RUNNING.value: {
            LoopExecutionStatus.PAUSED.value,
            LoopExecutionStatus.COMPLETED.value,
            LoopExecutionStatus.FAILED.value,
        },
        LoopExecutionStatus.PAUSED.value: {
            LoopExecutionStatus.RUNNING.value,
            LoopExecutionStatus.FAILED.value,
        },
        LoopExecutionStatus.COMPLETED.value: set(),
        LoopExecutionStatus.FAILED.value: set(),
    }

    def __init__(self, group_chat_id: str, project_path: str):
        """初始化 LoopExecutionManager。

        Args:
            group_chat_id: 所属群聊 ID，用于隔离不同群聊的执行数据。
            project_path: 项目路径，用于构建持久化文件路径。
        """
        self.group_chat_id = group_chat_id

        # 初始化 logger（复用 loops.log）
        log_dir = group_chat_paths.base_dir(group_chat_id, project_path)
        self.logger = get_specialized_logger(
            name=f"loop_execution_manager.{group_chat_id}",
            log_filename="loops.log",
            also_to_global=True,
            log_dir=log_dir,
        )

        # 初始化持久化路径
        self._persistence_path = group_chat_paths.loop_executions_data(group_chat_id, project_path)
        self._persistence_path.parent.mkdir(parents=True, exist_ok=True)

        # 内存缓存（懒加载，初始为空）
        self._executions: dict[str, LoopExecution] = {}

        # 并发控制锁
        self._lock = asyncio.Lock()

        # 不自动加载历史 LoopExecution，改为懒加载策略（按需加载）

    async def create_execution(
        self,
        loop_id: str,
        initial_task: str,
    ) -> LoopExecution:
        """创建 LoopExecution 执行实例。

        创建一个新的执行实例，关联到指定的 Loop 定义。

        创建流程：
        1. 获取并发控制锁，确保线程安全
        2. 构造 LoopExecution 对象，设置初始状态为 CREATED
        3. 保存到内存缓存和 JSONL 持久化文件
        4. 记录 INFO 日志并返回 LoopExecution 实例

        Args:
            loop_id: 关联的 Loop 定义 ID。
            initial_task: 本次执行的初始任务描述，发送给第一个节点。

        Returns:
            创建的 LoopExecution 实例，状态为 CREATED。
        """
        async with self._lock:
            # 创建 LoopExecution
            execution = LoopExecution(
                execution_id=str(uuid4()),
                loop_id=loop_id,
                initial_task=initial_task,
                status=LoopExecutionStatus.CREATED.value,
                current_iteration=1,
                current_node_index=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            # 保存到内存和持久化
            self._executions[execution.execution_id] = execution
            self._persist_execution(execution)

            self.logger.info(
                "创建 LoopExecution: execution_id=%s, loop_id=%s",
                execution.execution_id,
                execution.loop_id,
            )

            return execution

    def get_execution(self, execution_id: str) -> LoopExecution:
        """查询单个 LoopExecution。

        Args:
            execution_id: 执行实例唯一标识。

        Returns:
            LoopExecution 实例。

        Raises:
            LoopExecutionNotFoundError: 执行实例不存在时抛出。
        """
        if execution_id not in self._executions:
            self.logger.error(
                "LoopExecution 不存在: execution_id=%s, 可用=%s",
                execution_id,
                list(self._executions.keys()),
            )
            raise LoopExecutionNotFoundError(execution_id)

        return self._executions[execution_id]

    def _read_jsonl_executions(self) -> dict[str, dict]:
        """从 JSONL 文件读取所有 LoopExecution 记录（内部辅助方法）。

        遍历 JSONL 文件，处理墓碑记录，返回每个 execution_id 的最新记录。
        容错处理：跳过空行和损坏的 JSON 行，记录 WARNING 日志。

        Returns:
            execution_id -> 最新记录的字典。
        """
        if not self._persistence_path.exists():
            return {}

        execution_records: dict[str, dict] = {}
        deleted_ids: set[str] = set()

        try:
            with open(self._persistence_path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        execution_id = data["execution_id"]

                        # 墓碑记录：标记删除
                        if data.get("_deleted"):
                            deleted_ids.add(execution_id)
                            execution_records.pop(execution_id, None)
                            continue

                        # 跳过已删除的 execution_id
                        if execution_id in deleted_ids:
                            continue

                        # 后面的记录覆盖前面的（取最新）
                        execution_records[execution_id] = data
                    except (json.JSONDecodeError, KeyError) as e:
                        self.logger.warning(
                            "跳过损坏的 JSONL 行: 行号=%d, error=%s",
                            line_num,
                            e,
                        )
                        continue

            return execution_records

        except OSError as e:
            raise FileSystemError(
                operation="read",
                path=str(self._persistence_path),
                reason=str(e),
            ) from e

    def get_execution_with_lazy_load(self, execution_id: str) -> LoopExecution:
        """查询单个 LoopExecution，支持懒加载。

        如果 LoopExecution 在内存中，直接返回；如果不在内存中，从 JSONL 加载。
        用于 get_loop_status() 等需要懒加载的场景。

        Args:
            execution_id: 执行实例唯一标识。

        Returns:
            LoopExecution 实例。

        Raises:
            LoopExecutionNotFoundError: 执行实例在 JSONL 中也不存在时抛出。
        """
        # 1. 检查内存
        if execution_id in self._executions:
            self.logger.debug("LoopExecution 命中内存: execution_id=%s", execution_id)
            return self._executions[execution_id]

        # 2. 从 JSONL 加载
        self.logger.info(
            "LoopExecution 未在内存，触发懒加载: execution_id=%s, group=%s",
            execution_id,
            self.group_chat_id,
        )

        execution_records = self._read_jsonl_executions()
        execution_record = execution_records.get(execution_id)

        if execution_record is None:
            self.logger.error(
                "LoopExecution 不存在: execution_id=%s, JSONL 中无有效记录",
                execution_id,
            )
            raise LoopExecutionNotFoundError(execution_id)

        # 3. 反序列化并加载到内存
        execution = LoopExecution.from_dict(execution_record)
        self._executions[execution_id] = execution

        self.logger.info(
            "LoopExecution 懒加载成功: execution_id=%s, status=%s",
            execution_id,
            execution.status,
        )

        return execution

    def list_executions(self, loop_id: str | None = None, status: str | None = None) -> list[dict]:
        """查询执行历史（直接读取 JSONL）。

        不依赖内存缓存，直接读取 JSONL 文件并返回摘要信息。
        返回格式包含 `in_memory` 标记，指示该 execution 是否在内存中。

        Args:
            loop_id: 可选的 Loop ID 过滤，只返回该 Loop 的执行历史。
            status: 可选的状态过滤，取值为 "created"/"running"/"paused"/"completed"/"failed"。

        Returns:
            执行实例摘要列表，每个元素包含：
            - execution_id: 执行实例 ID
            - loop_id: 关联的 Loop ID
            - initial_task: 初始任务
            - status: 执行状态
            - created_at: 创建时间
            - updated_at: 更新时间
            - current_iteration: 当前轮次
            - in_memory: 是否在内存中（bool）
        """
        execution_records = self._read_jsonl_executions()

        # 构造摘要信息
        result = []
        for execution_id, data in execution_records.items():
            # Loop ID 过滤
            if loop_id and data.get("loop_id") != loop_id:
                continue

            # 状态过滤
            if status and data.get("status") != status:
                continue

            summary = {
                "execution_id": execution_id,
                "loop_id": data.get("loop_id"),
                "initial_task": data.get("initial_task"),
                "status": data.get("status"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "current_iteration": data.get("current_iteration"),
                "in_memory": execution_id in self._executions,  # 标记是否在内存
            }
            result.append(summary)

        # 按创建时间排序（最新的在前）
        result.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)

        return result

    def clear_other_executions(self, keep_execution_id: str) -> int:
        """清空内存中除指定 execution 外的所有 execution。

        用于启动 execution 时保持单 execution 内存策略。

        Args:
            keep_execution_id: 要保留的 execution ID。

        Returns:
            清理的 execution 数量。
        """
        other_executions = [eid for eid in self._executions if eid != keep_execution_id]
        if other_executions:
            self.logger.info(
                "清空其他 LoopExecution: group=%s, 清理数量=%d, 保留=%s",
                self.group_chat_id,
                len(other_executions),
                keep_execution_id,
            )
            for eid in other_executions:
                self._executions.pop(eid, None)
        return len(other_executions)

    async def update_execution_status(
        self,
        execution_id: str,
        status: str,
        current_iteration: int | None = None,
        current_node_index: int | None = None,
        error_message: str | None = None,
    ) -> LoopExecution:
        """更新 LoopExecution 状态。

        按照状态机规则更新执行状态，同时可选更新迭代次数、节点索引和错误信息。
        同状态更新（幂等操作）用于持久化迭代/节点等字段变更。

        更新流程：
        1. 调用 get_execution() 获取执行实例（不存在则抛出 LoopExecutionNotFoundError）
        2. 检查状态转换合法性：
           - 如果新状态与当前状态相同，视为幂等操作，允许更新其他字段
           - 如果新状态不同，检查 _VALID_TRANSITIONS 字典是否允许该转换
        3. 更新状态和其他可选字段
        4. 调用 _persist_execution() 持久化到 JSONL 文件
        5. 记录 INFO 日志并返回更新后的 LoopExecution 实例

        Args:
            execution_id: 执行实例唯一标识。
            status: 新状态，取值为 "created"/"running"/"paused"/"completed"/"failed"。
            current_iteration: 当前迭代次数（可选）。
            current_node_index: 当前节点索引（可选）。
            error_message: 错误信息（可选），仅在 FAILED 状态时设置。

        Returns:
            更新后的 LoopExecution 实例。

        Raises:
            LoopExecutionNotFoundError: 执行实例不存在时抛出。
            LoopExecutionStateError: 状态转换非法时抛出（如 COMPLETED -> RUNNING）。
        """
        execution = self.get_execution(execution_id)

        # 状态机校验。同状态更新用于持久化迭代/节点等字段，视为幂等操作。
        allowed = self._VALID_TRANSITIONS.get(execution.status, set())
        if status != execution.status and status not in allowed:
            self.logger.error(
                "LoopExecution 状态转换非法: execution_id=%s, %s -> %s, 允许=%s",
                execution_id,
                execution.status,
                status,
                allowed,
            )
            raise LoopExecutionStateError(execution_id, execution.status, status)

        # 更新字段
        execution.status = status
        execution.updated_at = datetime.now()

        if current_iteration is not None:
            execution.current_iteration = current_iteration

        if current_node_index is not None:
            execution.current_node_index = current_node_index

        if error_message is not None:
            execution.error_message = error_message

        # 持久化
        self._persist_execution(execution)

        self.logger.info(
            "更新 LoopExecution 状态: execution_id=%s, status=%s, iteration=%d, node_index=%d",
            execution_id,
            status,
            execution.current_iteration,
            execution.current_node_index,
        )

        return execution

    async def delete_execution(self, execution_id: str) -> None:
        """删除 LoopExecution。

        删除指定的执行实例。
        删除操作使用墓碑记录（_deleted: true）持久化，确保重启后仍保持删除状态。

        Args:
            execution_id: 执行实例唯一标识。

        Raises:
            LoopExecutionNotFoundError: 执行实例不存在时抛出。
        """
        # 验证 execution 存在（不存在则抛出 LoopExecutionNotFoundError）
        self.get_execution(execution_id)

        # 从内存删除
        del self._executions[execution_id]

        # 持久化删除标记（墓碑记录）
        self._persist_deletion(execution_id)

        self.logger.info("删除 LoopExecution: execution_id=%s", execution_id)

    async def delete_executions_by_loop(self, loop_id: str) -> int:
        """删除特定 Loop 的所有执行实例。

        当删除 Loop 定义时，级联删除所有关联的 execution。

        Args:
            loop_id: Loop 定义 ID。

        Returns:
            删除的 execution 数量。
        """
        # 从 JSONL 读取所有 execution
        execution_records = self._read_jsonl_executions()

        # 找到所有关联的 execution_id
        target_ids = [
            eid for eid, data in execution_records.items() if data.get("loop_id") == loop_id
        ]

        # 删除
        for eid in target_ids:
            # 从内存删除
            self._executions.pop(eid, None)
            # 持久化删除标记
            self._persist_deletion(eid)

        self.logger.info(
            "级联删除 LoopExecution: loop_id=%s, 删除数量=%d",
            loop_id,
            len(target_ids),
        )

        return len(target_ids)

    def _persist_execution(self, execution: LoopExecution) -> None:
        """持久化单个 LoopExecution（追加模式）。

        将 LoopExecution 序列化为 JSON 并追加到 JSONL 文件。
        每次状态变更都会追加一条新记录，实现 append-only 持久化。

        Args:
            execution: 要持久化的 LoopExecution 实例。

        Raises:
            FileSystemError: 文件写入失败时抛出。
        """
        data = execution.to_dict()

        try:
            with open(self._persistence_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        except OSError as e:
            raise FileSystemError(
                operation="write",
                path=str(self._persistence_path),
                reason=str(e),
            ) from e

    def _persist_deletion(self, execution_id: str) -> None:
        """持久化删除标记（墓碑记录）。

        写入一条包含 _deleted: true 的记录，标记该 execution_id 已被删除。
        重启加载时会跳过墓碑记录对应的 execution_id。

        Args:
            execution_id: 被删除的 execution ID。

        Raises:
            FileSystemError: 文件写入失败时抛出。
        """
        data = {"execution_id": execution_id, "_deleted": True}

        try:
            with open(self._persistence_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        except OSError as e:
            raise FileSystemError(
                operation="write",
                path=str(self._persistence_path),
                reason=str(e),
            ) from e
