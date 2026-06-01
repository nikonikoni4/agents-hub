"""
TaskManager 测试

契约驱动测试：
- get_active_task_list(): 获取当前 ACTIVE 任务列表
- assign_tasks(): 覆盖式更新（创建/更新/保持不变）
- archive_task_list(): 归档当前 ACTIVE 列表
- 持久化到 tasks.jsonl
"""

import json
from pathlib import Path

import pytest

from agents_hub.core.communication.task_manager import TaskManager
from agents_hub.core.foundation.models import TaskListStatus, TaskStatus
from agents_hub.utils.logger import setup_logging


@pytest.fixture(scope="session", autouse=True)
def setup_test_logging(tmp_path_factory):
    """初始化测试日志系统"""
    log_dir = tmp_path_factory.mktemp("logs")
    setup_logging(log_dir=log_dir)


@pytest.fixture
def temp_project_path(tmp_path: Path) -> Path:
    """创建临时项目路径"""
    project_path = tmp_path / "test_project"
    project_path.mkdir(parents=True, exist_ok=True)
    return project_path


@pytest.fixture
def task_manager(temp_project_path: Path) -> TaskManager:
    """创建 TaskManager 实例"""
    return TaskManager(
        group_chat_id="test_gc_123",
        project_path=str(temp_project_path),
    )


# ============================================================================
# get_active_task_list() 测试
# ============================================================================


def test_get_active_task_list_empty(task_manager: TaskManager) -> None:
    """
    契约：get_active_task_list() 初始返回 None

    验证方式：
    1. 创建新的 TaskManager
    2. 调用 get_active_task_list()
    3. 验证返回 None

    如果失败，说明：初始状态处理错误
    """
    task_list = task_manager.get_active_task_list("test_gc_123")
    assert task_list is None, "初始状态应返回 None"


def test_get_active_task_list_wrong_id(task_manager: TaskManager) -> None:
    """
    契约：group_chat_id 不匹配时抛出 ValueError

    验证方式：
    1. 创建 TaskManager(group_chat_id="test_gc_123")
    2. 调用 get_active_task_list("wrong_id")
    3. 验证抛出 ValueError

    如果失败，说明：group_chat_id 校验缺失
    """
    with pytest.raises(ValueError, match="group_chat_id 不匹配"):
        task_manager.get_active_task_list("wrong_id")


# ============================================================================
# assign_tasks() 测试
# ============================================================================


def test_assign_tasks_create_new(task_manager: TaskManager) -> None:
    """
    契约：assign_tasks() 创建新任务列表

    验证方式：
    1. 调用 assign_tasks() 传入 2 个任务
    2. 验证返回 {created: 2, updated: 0, unchanged: 0}
    3. 验证 get_active_task_list() 返回正确的 TaskList

    如果失败，说明：创建新列表逻辑错误
    """
    tasks = [
        {"task_id": "t1", "owner": "Worker1", "content": "实现模块A", "status": "pending"},
        {"task_id": "t2", "owner": "Worker2", "content": "编写测试", "status": "pending"},
    ]
    result = task_manager.assign_tasks("test_gc_123", tasks, "Manager")
    assert result["created"] == 2
    assert result["updated"] == 0
    assert result["unchanged"] == 0

    task_list = task_manager.get_active_task_list("test_gc_123")
    assert task_list is not None
    assert task_list.status == TaskListStatus.ACTIVE
    assert len(task_list.tasks) == 2
    assert task_list.tasks[0].task_id == "t1"
    assert task_list.tasks[0].owner == "Worker1"
    assert task_list.tasks[0].status == TaskStatus.PENDING


def test_assign_tasks_update_existing(task_manager: TaskManager) -> None:
    """
    契约：assign_tasks() 更新现有任务

    验证方式：
    1. 第一次创建任务 t1(pending), t2(pending)
    2. 第二次更新 t1(completed), t2(pending)
    3. 验证返回 {created: 0, updated: 1, unchanged: 1}
    4. 验证 t1 状态已更新

    如果失败，说明：更新逻辑错误
    """
    tasks_v1 = [
        {"task_id": "t1", "owner": "Worker1", "content": "实现模块A", "status": "pending"},
        {"task_id": "t2", "owner": "Worker2", "content": "编写测试", "status": "pending"},
    ]
    task_manager.assign_tasks("test_gc_123", tasks_v1, "Manager")

    tasks_v2 = [
        {"task_id": "t1", "owner": "Worker1", "content": "实现模块A", "status": "completed"},
        {"task_id": "t2", "owner": "Worker2", "content": "编写测试", "status": "pending"},
    ]
    result = task_manager.assign_tasks("test_gc_123", tasks_v2, "Manager")
    assert result["created"] == 0
    assert result["updated"] == 1
    assert result["unchanged"] == 1

    task_list = task_manager.get_active_task_list("test_gc_123")
    t1 = next(t for t in task_list.tasks if t.task_id == "t1")
    assert t1.status == TaskStatus.COMPLETED


def test_assign_tasks_mixed_operations(task_manager: TaskManager) -> None:
    """
    契约：assign_tasks() 混合操作（创建 + 更新 + 保持不变）

    验证方式：
    1. 第一次创建 t1, t2
    2. 第二次：更新 t1, 保持 t2, 新增 t3
    3. 验证返回 {created: 1, updated: 1, unchanged: 1}

    如果失败，说明：混合操作统计错误
    """
    tasks_v1 = [
        {"task_id": "t1", "owner": "Worker1", "content": "实现模块A", "status": "pending"},
        {"task_id": "t2", "owner": "Worker2", "content": "编写测试", "status": "pending"},
    ]
    task_manager.assign_tasks("test_gc_123", tasks_v1, "Manager")

    tasks_v2 = [
        {"task_id": "t1", "owner": "Worker1", "content": "实现模块A", "status": "running"},
        {"task_id": "t2", "owner": "Worker2", "content": "编写测试", "status": "pending"},
        {"task_id": "t3", "owner": "Worker3", "content": "代码审查", "status": "pending"},
    ]
    result = task_manager.assign_tasks("test_gc_123", tasks_v2, "Manager")
    assert result["created"] == 1
    assert result["updated"] == 1
    assert result["unchanged"] == 1

    task_list = task_manager.get_active_task_list("test_gc_123")
    assert len(task_list.tasks) == 3


def test_coverage_update_semantics(task_manager: TaskManager) -> None:
    """
    契约：覆盖式更新语义（参照 Claude Code TodoWrite）

    验证方式：
    1. 第一次创建 t1, t2
    2. 第二次传入 t1(更新), t2(不变), t3(新增)
    3. 验证统计正确

    如果失败，说明：覆盖式更新逻辑错误
    """
    tasks_v1 = [
        {"task_id": "t1", "owner": "W1", "content": "Task 1", "status": "pending"},
        {"task_id": "t2", "owner": "W2", "content": "Task 2", "status": "pending"},
    ]
    task_manager.assign_tasks("test_gc_123", tasks_v1, "Manager")

    tasks_v2 = [
        {"task_id": "t1", "owner": "W1", "content": "Task 1", "status": "running"},
        {"task_id": "t2", "owner": "W2", "content": "Task 2", "status": "pending"},
        {"task_id": "t3", "owner": "W3", "content": "Task 3", "status": "pending"},
    ]
    result = task_manager.assign_tasks("test_gc_123", tasks_v2, "Manager")
    assert result["created"] == 1
    assert result["updated"] == 1
    assert result["unchanged"] == 1


def test_coverage_update_preserve_old(task_manager: TaskManager) -> None:
    """
    契约：旧列表中不在新列表的任务保持不变（不删除）

    验证方式：
    1. 第一次创建 t1, t2, t3
    2. 第二次只传入 t1, t2（不包含 t3）
    3. 验证 t3 仍然存在（保持不变）
    4. 验证 unchanged 包含保留的 t3

    如果失败，说明：覆盖式更新错误地删除了旧任务
    """
    tasks_v1 = [
        {"task_id": "t1", "owner": "W1", "content": "Task 1", "status": "pending"},
        {"task_id": "t2", "owner": "W2", "content": "Task 2", "status": "pending"},
        {"task_id": "t3", "owner": "W3", "content": "Task 3", "status": "pending"},
    ]
    task_manager.assign_tasks("test_gc_123", tasks_v1, "Manager")

    tasks_v2 = [
        {"task_id": "t1", "owner": "W1", "content": "Task 1", "status": "running"},
        {"task_id": "t2", "owner": "W2", "content": "Task 2", "status": "pending"},
    ]
    result = task_manager.assign_tasks("test_gc_123", tasks_v2, "Manager")
    assert result["created"] == 0
    assert result["updated"] == 1
    assert result["unchanged"] == 2  # t2 + t3（保留）

    task_list = task_manager.get_active_task_list("test_gc_123")
    assert len(task_list.tasks) == 3
    t3 = next(t for t in task_list.tasks if t.task_id == "t3")
    assert t3.status == TaskStatus.PENDING


# ============================================================================
# archive_task_list() 测试
# ============================================================================


def test_archive_task_list(task_manager: TaskManager) -> None:
    """
    契约：archive_task_list() 归档当前 ACTIVE 列表

    验证方式：
    1. 创建任务列表
    2. 调用 archive_task_list()
    3. 验证返回 archived_count=1
    4. 验证 get_active_task_list() 返回 None

    如果失败，说明：归档逻辑错误
    """
    tasks = [
        {"task_id": "t1", "owner": "Worker1", "content": "实现模块A", "status": "completed"},
    ]
    task_manager.assign_tasks("test_gc_123", tasks, "Manager")

    result = task_manager.archive_task_list("test_gc_123")
    assert result["archived_count"] == 1
    assert "archived_at" in result

    task_list = task_manager.get_active_task_list("test_gc_123")
    assert task_list is None, "归档后应没有 ACTIVE 列表"


def test_archive_empty_list(task_manager: TaskManager) -> None:
    """
    契约：archive_task_list() 空列表时返回 archived_count=0

    验证方式：
    1. 不创建任何任务
    2. 调用 archive_task_list()
    3. 验证返回 archived_count=0

    如果失败，说明：空列表边界处理错误
    """
    result = task_manager.archive_task_list("test_gc_123")
    assert result["archived_count"] == 0
    assert "archived_at" in result


# ============================================================================
# 持久化测试
# ============================================================================


def test_persistence_create(task_manager: TaskManager) -> None:
    """
    契约：创建任务后 tasks.jsonl 存在

    验证方式：
    1. 创建任务
    2. 验证 tasks.jsonl 文件存在
    3. 验证文件内容正确

    如果失败，说明：持久化写入逻辑错误
    """
    tasks = [
        {"task_id": "t1", "owner": "Worker1", "content": "实现模块A", "status": "pending"},
    ]
    task_manager.assign_tasks("test_gc_123", tasks, "Manager")

    # 使用 TaskManager 内部的持久化路径（由 group_chat_paths 管理）
    persistence_path = task_manager._persistence_path
    assert persistence_path.exists(), "tasks.jsonl 应存在"

    with open(persistence_path, encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["status"] == "active"
        assert len(data["tasks"]) == 1


def test_persistence_load(temp_project_path: Path) -> None:
    """
    契约：新 TaskManager 实例能加载历史数据

    验证方式：
    1. 第一个 TaskManager 创建任务
    2. 创建第二个 TaskManager（同一路径）
    3. 验证第二个实例能加载历史数据

    如果失败，说明：持久化加载逻辑错误
    """
    tm1 = TaskManager("test_gc_123", str(temp_project_path))
    tasks = [
        {"task_id": "t1", "owner": "Worker1", "content": "实现模块A", "status": "pending"},
    ]
    tm1.assign_tasks("test_gc_123", tasks, "Manager")

    tm2 = TaskManager("test_gc_123", str(temp_project_path))
    task_list = tm2.get_active_task_list("test_gc_123")

    assert task_list is not None
    assert len(task_list.tasks) == 1
    assert task_list.tasks[0].task_id == "t1"


def test_persistence_archive(task_manager: TaskManager) -> None:
    """
    契约：归档后 tasks.jsonl 包含两行（ACTIVE + ARCHIVED）

    验证方式：
    1. 创建任务
    2. 归档
    3. 验证 tasks.jsonl 有两行
    4. 验证第一行 status=active，第二行 status=archived

    如果失败，说明：归档持久化逻辑错误
    """
    tasks = [
        {"task_id": "t1", "owner": "Worker1", "content": "实现模块A", "status": "completed"},
    ]
    task_manager.assign_tasks("test_gc_123", tasks, "Manager")
    task_manager.archive_task_list("test_gc_123")

    # 使用 TaskManager 内部的持久化路径（由 group_chat_paths 管理）
    persistence_path = task_manager._persistence_path
    with open(persistence_path, encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 2
        data1 = json.loads(lines[0])
        data2 = json.loads(lines[1])
        assert data1["status"] == "active"
        assert data2["status"] == "archived"
        assert data2["archived_at"] is not None
