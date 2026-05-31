"""TaskManager 测试"""

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


class TestTaskManagerBasics:
    """TaskManager 基础功能测试"""

    def test_get_active_task_list_empty(self, task_manager: TaskManager):
        """测试获取空的 ACTIVE 任务列表"""
        task_list = task_manager.get_active_task_list()
        assert task_list is None

    def test_assign_tasks_create_new(self, task_manager: TaskManager):
        """测试创建新任务列表"""
        tasks = [
            {
                "task_id": "t1",
                "owner": "Worker1",
                "content": "实现模块A",
                "status": "pending",
            },
            {
                "task_id": "t2",
                "owner": "Worker2",
                "content": "编写测试",
                "status": "pending",
            },
        ]

        result = task_manager.assign_tasks(
            group_chat_id="test_gc_123",
            tasks=tasks,
            created_by="Manager",
        )

        assert result["created"] == 2
        assert result["updated"] == 0
        assert result["unchanged"] == 0

        # 验证任务列表已创建
        task_list = task_manager.get_active_task_list()
        assert task_list is not None
        assert task_list.status == TaskListStatus.ACTIVE
        assert len(task_list.tasks) == 2
        assert task_list.tasks[0].task_id == "t1"
        assert task_list.tasks[0].owner == "Worker1"
        assert task_list.tasks[0].content == "实现模块A"
        assert task_list.tasks[0].status == TaskStatus.PENDING

    def test_assign_tasks_update_existing(self, task_manager: TaskManager):
        """测试更新现有任务"""
        # 第一次创建
        tasks_v1 = [
            {
                "task_id": "t1",
                "owner": "Worker1",
                "content": "实现模块A",
                "status": "pending",
            },
            {
                "task_id": "t2",
                "owner": "Worker2",
                "content": "编写测试",
                "status": "pending",
            },
        ]
        task_manager.assign_tasks("test_gc_123", tasks_v1, "Manager")

        # 第二次更新（更新 t1 状态，保持 t2 不变）
        tasks_v2 = [
            {
                "task_id": "t1",
                "owner": "Worker1",
                "content": "实现模块A",
                "status": "completed",
            },
            {
                "task_id": "t2",
                "owner": "Worker2",
                "content": "编写测试",
                "status": "pending",
            },
        ]
        result = task_manager.assign_tasks("test_gc_123", tasks_v2, "Manager")

        assert result["created"] == 0
        assert result["updated"] == 1
        assert result["unchanged"] == 1

        # 验证更新
        task_list = task_manager.get_active_task_list()
        assert task_list is not None
        assert len(task_list.tasks) == 2
        t1 = next(t for t in task_list.tasks if t.task_id == "t1")
        assert t1.status == TaskStatus.COMPLETED

    def test_assign_tasks_mixed_operations(self, task_manager: TaskManager):
        """测试混合操作：创建 + 更新 + 保持不变"""
        # 第一次创建
        tasks_v1 = [
            {
                "task_id": "t1",
                "owner": "Worker1",
                "content": "实现模块A",
                "status": "pending",
            },
            {
                "task_id": "t2",
                "owner": "Worker2",
                "content": "编写测试",
                "status": "pending",
            },
        ]
        task_manager.assign_tasks("test_gc_123", tasks_v1, "Manager")

        # 第二次：更新 t1，保持 t2，新增 t3
        tasks_v2 = [
            {
                "task_id": "t1",
                "owner": "Worker1",
                "content": "实现模块A",
                "status": "running",
            },
            {
                "task_id": "t2",
                "owner": "Worker2",
                "content": "编写测试",
                "status": "pending",
            },
            {
                "task_id": "t3",
                "owner": "Worker3",
                "content": "代码审查",
                "status": "pending",
            },
        ]
        result = task_manager.assign_tasks("test_gc_123", tasks_v2, "Manager")

        assert result["created"] == 1
        assert result["updated"] == 1
        assert result["unchanged"] == 1

        # 验证结果
        task_list = task_manager.get_active_task_list()
        assert task_list is not None
        assert len(task_list.tasks) == 3

    def test_archive_task_list(self, task_manager: TaskManager):
        """测试归档任务列表"""
        # 先创建任务列表
        tasks = [
            {
                "task_id": "t1",
                "owner": "Worker1",
                "content": "实现模块A",
                "status": "completed",
            },
        ]
        task_manager.assign_tasks("test_gc_123", tasks, "Manager")

        # 归档
        result = task_manager.archive_task_list("test_gc_123")

        assert result["archived_count"] == 1
        assert "archived_at" in result

        # 验证归档后没有 ACTIVE 列表
        task_list = task_manager.get_active_task_list()
        assert task_list is None

    def test_archive_empty_list(self, task_manager: TaskManager):
        """测试归档空列表"""
        result = task_manager.archive_task_list("test_gc_123")

        assert result["archived_count"] == 0
        assert "archived_at" in result


class TestTaskManagerPersistence:
    """TaskManager 持久化测试"""

    def test_persistence_create(self, task_manager: TaskManager, temp_project_path: Path):
        """测试创建任务后持久化"""
        tasks = [
            {
                "task_id": "t1",
                "owner": "Worker1",
                "content": "实现模块A",
                "status": "pending",
            },
        ]
        task_manager.assign_tasks("test_gc_123", tasks, "Manager")

        # 验证持久化文件存在
        persistence_path = temp_project_path / "test_gc_123" / "tasks.jsonl"
        assert persistence_path.exists()

        # 验证文件内容
        with open(persistence_path, encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["status"] == "active"
            assert len(data["tasks"]) == 1

    def test_persistence_load(self, temp_project_path: Path):
        """测试从持久化文件加载"""
        # 第一个 TaskManager 创建任务
        tm1 = TaskManager("test_gc_123", str(temp_project_path))
        tasks = [
            {
                "task_id": "t1",
                "owner": "Worker1",
                "content": "实现模块A",
                "status": "pending",
            },
        ]
        tm1.assign_tasks("test_gc_123", tasks, "Manager")

        # 第二个 TaskManager 加载
        tm2 = TaskManager("test_gc_123", str(temp_project_path))
        task_list = tm2.get_active_task_list()

        assert task_list is not None
        assert len(task_list.tasks) == 1
        assert task_list.tasks[0].task_id == "t1"

    def test_persistence_archive(self, task_manager: TaskManager, temp_project_path: Path):
        """测试归档后持久化"""
        # 创建任务
        tasks = [
            {
                "task_id": "t1",
                "owner": "Worker1",
                "content": "实现模块A",
                "status": "completed",
            },
        ]
        task_manager.assign_tasks("test_gc_123", tasks, "Manager")

        # 归档
        task_manager.archive_task_list("test_gc_123")

        # 验证持久化文件
        persistence_path = temp_project_path / "test_gc_123" / "tasks.jsonl"
        with open(persistence_path, encoding="utf-8") as f:
            lines = f.readlines()
            # 应该有两行：第一行 ACTIVE，第二行 ARCHIVED
            assert len(lines) == 2
            data1 = json.loads(lines[0])
            data2 = json.loads(lines[1])
            assert data1["status"] == "active"
            assert data2["status"] == "archived"
            assert data2["archived_at"] is not None


class TestTaskManagerCoverageUpdate:
    """测试覆盖式更新语义"""

    def test_coverage_update_semantics(self, task_manager: TaskManager):
        """测试覆盖式更新语义：Manager 传入完整列表，系统自动识别"""
        # 第一次：创建 t1, t2
        tasks_v1 = [
            {"task_id": "t1", "owner": "W1", "content": "Task 1", "status": "pending"},
            {"task_id": "t2", "owner": "W2", "content": "Task 2", "status": "pending"},
        ]
        task_manager.assign_tasks("test_gc_123", tasks_v1, "Manager")

        # 第二次：传入 t1(更新), t2(不变), t3(新增)
        tasks_v2 = [
            {"task_id": "t1", "owner": "W1", "content": "Task 1", "status": "running"},
            {"task_id": "t2", "owner": "W2", "content": "Task 2", "status": "pending"},
            {"task_id": "t3", "owner": "W3", "content": "Task 3", "status": "pending"},
        ]
        result = task_manager.assign_tasks("test_gc_123", tasks_v2, "Manager")

        # 验证统计
        assert result["created"] == 1  # t3
        assert result["updated"] == 1  # t1
        assert result["unchanged"] == 1  # t2

        # 验证最终状态
        task_list = task_manager.get_active_task_list()
        assert task_list is not None
        assert len(task_list.tasks) == 3

    def test_coverage_update_remove_task(self, task_manager: TaskManager):
        """测试覆盖式更新：旧列表中不在新列表的任务保持不变（不删除）"""
        # 第一次：创建 t1, t2, t3
        tasks_v1 = [
            {"task_id": "t1", "owner": "W1", "content": "Task 1", "status": "pending"},
            {"task_id": "t2", "owner": "W2", "content": "Task 2", "status": "pending"},
            {"task_id": "t3", "owner": "W3", "content": "Task 3", "status": "pending"},
        ]
        task_manager.assign_tasks("test_gc_123", tasks_v1, "Manager")

        # 第二次：只传入 t1, t2（不包含 t3）
        tasks_v2 = [
            {"task_id": "t1", "owner": "W1", "content": "Task 1", "status": "running"},
            {"task_id": "t2", "owner": "W2", "content": "Task 2", "status": "pending"},
        ]
        result = task_manager.assign_tasks("test_gc_123", tasks_v2, "Manager")

        # 验证统计
        assert result["created"] == 0
        assert result["updated"] == 1  # t1
        assert result["unchanged"] == 1  # t2

        # 验证 t3 仍然存在（保持不变）
        task_list = task_manager.get_active_task_list()
        assert task_list is not None
        assert len(task_list.tasks) == 3
        t3 = next(t for t in task_list.tasks if t.task_id == "t3")
        assert t3.status == TaskStatus.PENDING
