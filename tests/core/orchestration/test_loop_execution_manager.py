"""
LoopExecutionManager 单元测试

测试 LoopExecution 执行实例的 CRUD 操作、状态机校验和持久化。
"""

import pytest
from uuid import uuid4

from agents_hub.core.orchestration.loop_execution_manager import LoopExecutionManager
from agents_hub.core.foundation.exceptions import (
    LoopExecutionNotFoundError,
    LoopExecutionStateError,
)
from agents_hub.core.foundation.models import LoopExecutionStatus
from agents_hub.utils.logger import setup_logging


@pytest.fixture(scope="session", autouse=True)
def setup_test_logging(tmp_path_factory):
    """初始化测试日志系统"""
    log_dir = tmp_path_factory.mktemp("logs")
    setup_logging(log_dir=log_dir)


@pytest.fixture
def temp_project_path(tmp_path):
    """临时项目路径"""
    return str(tmp_path / "test_project")


@pytest.fixture
def execution_manager(temp_project_path):
    """LoopExecutionManager 实例"""
    group_chat_id = f"test_gc_{uuid4().hex[:8]}"
    return LoopExecutionManager(group_chat_id, temp_project_path)


class TestCreateExecution:
    """测试执行实例创建"""

    @pytest.mark.asyncio
    async def test_create_execution_returns_created_status(self, execution_manager):
        """创建的 execution 状态为 CREATED"""
        execution = await execution_manager.create_execution("loop-1", "执行任务")

        assert execution.execution_id is not None
        assert execution.loop_id == "loop-1"
        assert execution.initial_task == "执行任务"
        assert execution.status == LoopExecutionStatus.CREATED.value
        assert execution.current_iteration == 1
        assert execution.current_node_index == 0
        assert execution.error_message is None

    @pytest.mark.asyncio
    async def test_create_execution_stores_in_memory(self, execution_manager):
        """创建后 execution 在内存中可查"""
        execution = await execution_manager.create_execution("loop-1", "任务")

        retrieved = execution_manager.get_execution(execution.execution_id)

        assert retrieved is execution

    @pytest.mark.asyncio
    async def test_create_multiple_executions(self, execution_manager):
        """可以创建多个 execution"""
        exec1 = await execution_manager.create_execution("loop-1", "任务1")
        exec2 = await execution_manager.create_execution("loop-1", "任务2")
        exec3 = await execution_manager.create_execution("loop-2", "任务3")

        assert exec1.execution_id != exec2.execution_id
        assert exec2.execution_id != exec3.execution_id
        assert len(execution_manager._executions) == 3


class TestGetExecution:
    """测试执行实例查询"""

    @pytest.mark.asyncio
    async def test_get_execution_success(self, execution_manager):
        """查询存在的 execution"""
        created = await execution_manager.create_execution("loop-1", "任务")

        retrieved = execution_manager.get_execution(created.execution_id)

        assert retrieved.execution_id == created.execution_id
        assert retrieved.loop_id == "loop-1"

    def test_get_execution_not_found(self, execution_manager):
        """查询不存在的 execution 抛出异常"""
        with pytest.raises(LoopExecutionNotFoundError):
            execution_manager.get_execution("non_existent_id")


class TestGetExecutionWithLazyLoad:
    """测试懒加载查询"""

    @pytest.mark.asyncio
    async def test_lazy_load_from_memory(self, execution_manager):
        """内存中存在时直接返回"""
        created = await execution_manager.create_execution("loop-1", "任务")

        retrieved = execution_manager.get_execution_with_lazy_load(created.execution_id)

        assert retrieved is created

    @pytest.mark.asyncio
    async def test_lazy_load_from_jsonl(self, temp_project_path):
        """内存中不存在时从 JSONL 加载"""
        group_chat_id = f"test_gc_{uuid4().hex[:8]}"

        # 第一个 manager 创建 execution
        manager1 = LoopExecutionManager(group_chat_id, temp_project_path)
        execution = await manager1.create_execution("loop-1", "任务")

        # 第二个 manager（内存为空）通过懒加载查询
        manager2 = LoopExecutionManager(group_chat_id, temp_project_path)
        retrieved = manager2.get_execution_with_lazy_load(execution.execution_id)

        assert retrieved.execution_id == execution.execution_id
        assert retrieved.status == LoopExecutionStatus.CREATED.value
        assert retrieved.initial_task == "任务"

    def test_lazy_load_not_found(self, temp_project_path):
        """JSONL 中也不存在时抛出异常"""
        group_chat_id = f"test_gc_{uuid4().hex[:8]}"
        manager = LoopExecutionManager(group_chat_id, temp_project_path)

        with pytest.raises(LoopExecutionNotFoundError):
            manager.get_execution_with_lazy_load("non_existent_id")


class TestListExecutions:
    """测试执行历史查询"""

    @pytest.mark.asyncio
    async def test_list_all_executions(self, execution_manager):
        """查询所有 execution"""
        await execution_manager.create_execution("loop-1", "任务1")
        await execution_manager.create_execution("loop-1", "任务2")
        await execution_manager.create_execution("loop-2", "任务3")

        result = execution_manager.list_executions()

        assert len(result) == 3
        assert all("execution_id" in item for item in result)
        assert all("in_memory" in item for item in result)

    @pytest.mark.asyncio
    async def test_list_executions_filter_by_loop_id(self, execution_manager):
        """按 loop_id 过滤"""
        await execution_manager.create_execution("loop-1", "任务1")
        await execution_manager.create_execution("loop-1", "任务2")
        await execution_manager.create_execution("loop-2", "任务3")

        result = execution_manager.list_executions(loop_id="loop-1")

        assert len(result) == 2
        assert all(item["loop_id"] == "loop-1" for item in result)

    @pytest.mark.asyncio
    async def test_list_executions_filter_by_status(self, execution_manager):
        """按状态过滤"""
        exec1 = await execution_manager.create_execution("loop-1", "任务1")
        await execution_manager.create_execution("loop-1", "任务2")

        # 更新 exec1 为 RUNNING
        await execution_manager.update_execution_status(
            exec1.execution_id, LoopExecutionStatus.RUNNING.value
        )

        running = execution_manager.list_executions(status=LoopExecutionStatus.RUNNING.value)
        created = execution_manager.list_executions(status=LoopExecutionStatus.CREATED.value)

        assert len(running) == 1
        assert running[0]["execution_id"] == exec1.execution_id
        assert len(created) == 1

    @pytest.mark.asyncio
    async def test_list_executions_includes_in_memory_flag(self, execution_manager):
        """结果包含 in_memory 标记"""
        await execution_manager.create_execution("loop-1", "任务")

        result = execution_manager.list_executions()

        assert len(result) == 1
        assert result[0]["in_memory"] is True

    @pytest.mark.asyncio
    async def test_list_executions_from_jsonl_not_in_memory(self, temp_project_path):
        """从 JSONL 读取的 execution in_memory 为 False"""
        group_chat_id = f"test_gc_{uuid4().hex[:8]}"

        manager1 = LoopExecutionManager(group_chat_id, temp_project_path)
        await manager1.create_execution("loop-1", "任务")

        # 新 manager 内存为空
        manager2 = LoopExecutionManager(group_chat_id, temp_project_path)
        result = manager2.list_executions()

        assert len(result) == 1
        assert result[0]["in_memory"] is False


class TestClearOtherExecutions:
    """测试单 execution 保持策略"""

    @pytest.mark.asyncio
    async def test_clear_others_keeps_specified_execution(self, execution_manager):
        """保留指定 execution，清理其他"""
        exec1 = await execution_manager.create_execution("loop-1", "任务1")
        exec2 = await execution_manager.create_execution("loop-1", "任务2")
        exec3 = await execution_manager.create_execution("loop-1", "任务3")

        cleared = execution_manager.clear_other_executions(exec2.execution_id)

        assert cleared == 2
        assert exec2.execution_id in execution_manager._executions
        assert exec1.execution_id not in execution_manager._executions
        assert exec3.execution_id not in execution_manager._executions

    @pytest.mark.asyncio
    async def test_clear_others_with_no_others(self, execution_manager):
        """没有其他 execution 时返回 0"""
        exec1 = await execution_manager.create_execution("loop-1", "任务")

        cleared = execution_manager.clear_other_executions(exec1.execution_id)

        assert cleared == 0
        assert exec1.execution_id in execution_manager._executions

    @pytest.mark.asyncio
    async def test_clear_others_with_empty_memory(self, execution_manager):
        """内存为空时返回 0"""
        cleared = execution_manager.clear_other_executions("any-id")

        assert cleared == 0


class TestUpdateExecutionStatus:
    """测试状态更新和状态机"""

    @pytest.mark.asyncio
    async def test_update_status_success(self, execution_manager):
        """正常更新状态"""
        execution = await execution_manager.create_execution("loop-1", "任务")

        updated = await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.RUNNING.value
        )

        assert updated.status == LoopExecutionStatus.RUNNING.value

    @pytest.mark.asyncio
    async def test_update_status_with_iteration_and_node(self, execution_manager):
        """更新状态时同时更新迭代次数和节点索引"""
        execution = await execution_manager.create_execution("loop-1", "任务")
        await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.RUNNING.value
        )

        updated = await execution_manager.update_execution_status(
            execution.execution_id,
            LoopExecutionStatus.RUNNING.value,
            current_iteration=3,
            current_node_index=1,
        )

        assert updated.current_iteration == 3
        assert updated.current_node_index == 1

    @pytest.mark.asyncio
    async def test_update_status_with_error_message(self, execution_manager):
        """更新为 FAILED 时记录错误信息"""
        execution = await execution_manager.create_execution("loop-1", "任务")
        await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.RUNNING.value
        )

        updated = await execution_manager.update_execution_status(
            execution.execution_id,
            LoopExecutionStatus.FAILED.value,
            error_message="节点执行超时",
        )

        assert updated.status == LoopExecutionStatus.FAILED.value
        assert updated.error_message == "节点执行超时"

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, execution_manager):
        """更新不存在的 execution 抛出异常"""
        with pytest.raises(LoopExecutionNotFoundError):
            await execution_manager.update_execution_status(
                "non_existent_id", LoopExecutionStatus.RUNNING.value
            )

    @pytest.mark.asyncio
    async def test_same_status_update_is_idempotent(self, execution_manager):
        """同状态更新是幂等操作（用于持久化迭代/节点字段）"""
        execution = await execution_manager.create_execution("loop-1", "任务")
        await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.RUNNING.value
        )

        updated = await execution_manager.update_execution_status(
            execution.execution_id,
            LoopExecutionStatus.RUNNING.value,
            current_iteration=2,
            current_node_index=1,
        )

        assert updated.status == LoopExecutionStatus.RUNNING.value
        assert updated.current_iteration == 2
        assert updated.current_node_index == 1


class TestStateMachine:
    """测试状态机转换规则"""

    @pytest.mark.asyncio
    async def test_created_to_running(self, execution_manager):
        """CREATED -> RUNNING（合法）"""
        execution = await execution_manager.create_execution("loop-1", "任务")

        updated = await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.RUNNING.value
        )

        assert updated.status == LoopExecutionStatus.RUNNING.value

    @pytest.mark.asyncio
    async def test_running_to_paused(self, execution_manager):
        """RUNNING -> PAUSED（合法）"""
        execution = await execution_manager.create_execution("loop-1", "任务")
        await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.RUNNING.value
        )

        updated = await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.PAUSED.value
        )

        assert updated.status == LoopExecutionStatus.PAUSED.value

    @pytest.mark.asyncio
    async def test_running_to_completed(self, execution_manager):
        """RUNNING -> COMPLETED（合法）"""
        execution = await execution_manager.create_execution("loop-1", "任务")
        await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.RUNNING.value
        )

        updated = await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.COMPLETED.value
        )

        assert updated.status == LoopExecutionStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_running_to_failed(self, execution_manager):
        """RUNNING -> FAILED（合法）"""
        execution = await execution_manager.create_execution("loop-1", "任务")
        await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.RUNNING.value
        )

        updated = await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.FAILED.value
        )

        assert updated.status == LoopExecutionStatus.FAILED.value

    @pytest.mark.asyncio
    async def test_paused_to_running(self, execution_manager):
        """PAUSED -> RUNNING（合法，恢复执行）"""
        execution = await execution_manager.create_execution("loop-1", "任务")
        await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.RUNNING.value
        )
        await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.PAUSED.value
        )

        updated = await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.RUNNING.value
        )

        assert updated.status == LoopExecutionStatus.RUNNING.value

    @pytest.mark.asyncio
    async def test_paused_to_failed(self, execution_manager):
        """PAUSED -> FAILED（合法）"""
        execution = await execution_manager.create_execution("loop-1", "任务")
        await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.RUNNING.value
        )
        await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.PAUSED.value
        )

        updated = await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.FAILED.value
        )

        assert updated.status == LoopExecutionStatus.FAILED.value

    @pytest.mark.asyncio
    async def test_completed_is_terminal(self, execution_manager):
        """COMPLETED 是终态，不能转换"""
        execution = await execution_manager.create_execution("loop-1", "任务")
        await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.RUNNING.value
        )
        await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.COMPLETED.value
        )

        with pytest.raises(LoopExecutionStateError):
            await execution_manager.update_execution_status(
                execution.execution_id, LoopExecutionStatus.RUNNING.value
            )

    @pytest.mark.asyncio
    async def test_failed_is_terminal(self, execution_manager):
        """FAILED 是终态，不能转换"""
        execution = await execution_manager.create_execution("loop-1", "任务")
        await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.RUNNING.value
        )
        await execution_manager.update_execution_status(
            execution.execution_id, LoopExecutionStatus.FAILED.value
        )

        with pytest.raises(LoopExecutionStateError):
            await execution_manager.update_execution_status(
                execution.execution_id, LoopExecutionStatus.RUNNING.value
            )

    @pytest.mark.asyncio
    async def test_created_cannot_go_to_paused(self, execution_manager):
        """CREATED 不能直接转为 PAUSED"""
        execution = await execution_manager.create_execution("loop-1", "任务")

        with pytest.raises(LoopExecutionStateError):
            await execution_manager.update_execution_status(
                execution.execution_id, LoopExecutionStatus.PAUSED.value
            )

    @pytest.mark.asyncio
    async def test_created_cannot_go_to_completed(self, execution_manager):
        """CREATED 不能直接转为 COMPLETED"""
        execution = await execution_manager.create_execution("loop-1", "任务")

        with pytest.raises(LoopExecutionStateError):
            await execution_manager.update_execution_status(
                execution.execution_id, LoopExecutionStatus.COMPLETED.value
            )

    @pytest.mark.asyncio
    async def test_created_cannot_go_to_failed(self, execution_manager):
        """CREATED 不能直接转为 FAILED"""
        execution = await execution_manager.create_execution("loop-1", "任务")

        with pytest.raises(LoopExecutionStateError):
            await execution_manager.update_execution_status(
                execution.execution_id, LoopExecutionStatus.FAILED.value
            )


class TestDeleteExecution:
    """测试执行实例删除"""

    @pytest.mark.asyncio
    async def test_delete_execution_success(self, execution_manager):
        """删除存在的 execution"""
        execution = await execution_manager.create_execution("loop-1", "任务")

        await execution_manager.delete_execution(execution.execution_id)

        with pytest.raises(LoopExecutionNotFoundError):
            execution_manager.get_execution(execution.execution_id)

    @pytest.mark.asyncio
    async def test_delete_execution_not_found(self, execution_manager):
        """删除不存在的 execution 抛出异常"""
        with pytest.raises(LoopExecutionNotFoundError):
            await execution_manager.delete_execution("non_existent_id")

    @pytest.mark.asyncio
    async def test_delete_persists_across_restart(self, temp_project_path):
        """删除后重启 manager，execution 不可见（墓碑记录）"""
        group_chat_id = f"test_gc_{uuid4().hex[:8]}"

        manager1 = LoopExecutionManager(group_chat_id, temp_project_path)
        execution = await manager1.create_execution("loop-1", "任务")
        await manager1.delete_execution(execution.execution_id)

        # 重启 manager
        manager2 = LoopExecutionManager(group_chat_id, temp_project_path)

        # get_execution_with_lazy_load 应该找不到（墓碑记录生效）
        with pytest.raises(LoopExecutionNotFoundError):
            manager2.get_execution_with_lazy_load(execution.execution_id)

        # list_executions 也应该为空
        result = manager2.list_executions()
        assert len(result) == 0


class TestDeleteExecutionsByLoop:
    """测试按 Loop ID 级联删除"""

    @pytest.mark.asyncio
    async def test_delete_executions_by_loop(self, execution_manager):
        """删除特定 Loop 的所有 execution"""
        await execution_manager.create_execution("loop-1", "任务1")
        await execution_manager.create_execution("loop-1", "任务2")
        await execution_manager.create_execution("loop-2", "任务3")

        deleted = await execution_manager.delete_executions_by_loop("loop-1")

        assert deleted == 2
        result = execution_manager.list_executions()
        assert len(result) == 1
        assert result[0]["loop_id"] == "loop-2"

    @pytest.mark.asyncio
    async def test_delete_executions_by_loop_none_exist(self, execution_manager):
        """没有关联 execution 时返回 0"""
        await execution_manager.create_execution("loop-1", "任务")

        deleted = await execution_manager.delete_executions_by_loop("loop-999")

        assert deleted == 0


class TestPersistence:
    """测试 JSONL 持久化"""

    @pytest.mark.asyncio
    async def test_persistence_creates_jsonl_file(self, temp_project_path):
        """创建 execution 后 JSONL 文件存在"""
        group_chat_id = f"test_gc_{uuid4().hex[:8]}"
        manager = LoopExecutionManager(group_chat_id, temp_project_path)

        await manager.create_execution("loop-1", "任务")

        assert manager._persistence_path.exists()

    @pytest.mark.asyncio
    async def test_persistence_and_recovery(self, temp_project_path):
        """创建后可以从 JSONL 恢复"""
        group_chat_id = f"test_gc_{uuid4().hex[:8]}"

        manager1 = LoopExecutionManager(group_chat_id, temp_project_path)
        execution = await manager1.create_execution("loop-1", "初始任务")

        # 更新状态
        await manager1.update_execution_status(
            execution.execution_id, LoopExecutionStatus.RUNNING.value
        )

        # 新 manager 从 JSONL 恢复
        manager2 = LoopExecutionManager(group_chat_id, temp_project_path)
        recovered = manager2.get_execution_with_lazy_load(execution.execution_id)

        assert recovered.execution_id == execution.execution_id
        assert recovered.status == LoopExecutionStatus.RUNNING.value
        assert recovered.initial_task == "初始任务"

    @pytest.mark.asyncio
    async def test_persistence_same_id_takes_latest(self, temp_project_path):
        """同一 execution_id 多条记录取最新"""
        group_chat_id = f"test_gc_{uuid4().hex[:8]}"

        manager1 = LoopExecutionManager(group_chat_id, temp_project_path)
        execution = await manager1.create_execution("loop-1", "任务")

        # 多次更新（追加新记录）
        await manager1.update_execution_status(
            execution.execution_id, LoopExecutionStatus.RUNNING.value
        )
        await manager1.update_execution_status(
            execution.execution_id,
            LoopExecutionStatus.RUNNING.value,
            current_iteration=2,
        )
        await manager1.update_execution_status(
            execution.execution_id,
            LoopExecutionStatus.RUNNING.value,
            current_iteration=3,
            current_node_index=1,
        )

        # 新 manager 取最新记录
        manager2 = LoopExecutionManager(group_chat_id, temp_project_path)
        recovered = manager2.get_execution_with_lazy_load(execution.execution_id)

        assert recovered.current_iteration == 3
        assert recovered.current_node_index == 1

    @pytest.mark.asyncio
    async def test_tombstone_prevents_recovery(self, temp_project_path):
        """墓碑记录阻止恢复"""
        group_chat_id = f"test_gc_{uuid4().hex[:8]}"

        manager1 = LoopExecutionManager(group_chat_id, temp_project_path)
        execution = await manager1.create_execution("loop-1", "任务")
        await manager1.delete_execution(execution.execution_id)

        # 新 manager 加载时应该跳过墓碑记录
        manager2 = LoopExecutionManager(group_chat_id, temp_project_path)

        # list_executions 应该为空
        result = manager2.list_executions()
        assert len(result) == 0

        # get_execution_with_lazy_load 应该抛出异常
        with pytest.raises(LoopExecutionNotFoundError):
            manager2.get_execution_with_lazy_load(execution.execution_id)

    @pytest.mark.asyncio
    async def test_jsonl_handles_corrupted_lines(self, temp_project_path):
        """JSONL 中的损坏行被跳过"""
        group_chat_id = f"test_gc_{uuid4().hex[:8]}"
        manager = LoopExecutionManager(group_chat_id, temp_project_path)

        # 创建一个有效的 execution
        execution = await manager.create_execution("loop-1", "任务")

        # 手动写入损坏的行
        with open(manager._persistence_path, "a", encoding="utf-8") as f:
            f.write("not valid json\n")
            f.write("{}\n")  # 缺少 execution_id
            f.write('{"execution_id": "orphan", "_deleted": true}\n')

        # 新 manager 应该能正常加载（跳过损坏行）
        manager2 = LoopExecutionManager(group_chat_id, temp_project_path)
        recovered = manager2.get_execution_with_lazy_load(execution.execution_id)

        assert recovered.execution_id == execution.execution_id

    @pytest.mark.asyncio
    async def test_jsonl_empty_file_returns_empty(self, temp_project_path):
        """空 JSONL 文件返回空结果"""
        group_chat_id = f"test_gc_{uuid4().hex[:8]}"
        manager = LoopExecutionManager(group_chat_id, temp_project_path)

        # 确保文件不存在时 list_executions 不报错
        result = manager.list_executions()
        assert result == []
