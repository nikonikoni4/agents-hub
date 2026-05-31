"""Task 和 TaskList 数据模型测试"""

from datetime import datetime

from agents_hub.core.communication.task import Task, TaskList
from agents_hub.core.foundation.models import TaskListStatus, TaskStatus


def test_task_creation():
    """Task 应该正确创建"""
    task = Task(
        task_id="t1",
        owner="Worker1",
        content="实现功能A",
        status=TaskStatus.PENDING,
        group_chat_id="gc_123",
        created_by="Manager",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    assert task.task_id == "t1"
    assert task.owner == "Worker1"
    assert task.status == TaskStatus.PENDING


def test_task_to_dict():
    """Task 应该能序列化为 dict"""
    now = datetime.now()
    task = Task(
        task_id="t1",
        owner="Worker1",
        content="实现功能A",
        status=TaskStatus.PENDING,
        group_chat_id="gc_123",
        created_by="Manager",
        created_at=now,
        updated_at=now,
    )
    data = task.to_dict()
    assert data["task_id"] == "t1"
    assert data["status"] == "pending"
    assert isinstance(data["created_at"], str)


def test_task_from_dict():
    """Task 应该能从 dict 反序列化"""
    data = {
        "task_id": "t1",
        "owner": "Worker1",
        "content": "实现功能A",
        "status": "pending",
        "group_chat_id": "gc_123",
        "created_by": "Manager",
        "created_at": "2026-05-31T10:00:00",
        "updated_at": "2026-05-31T10:00:00",
    }
    task = Task.from_dict(data)
    assert task.task_id == "t1"
    assert task.status == TaskStatus.PENDING


def test_task_list_creation():
    """TaskList 应该正确创建"""
    task_list = TaskList(
        list_id="list_1",
        group_chat_id="gc_123",
        status=TaskListStatus.ACTIVE,
        tasks=[],
        created_at=datetime.now(),
        archived_at=None,
    )
    assert task_list.list_id == "list_1"
    assert task_list.status == TaskListStatus.ACTIVE
    assert len(task_list.tasks) == 0


def test_task_list_to_dict():
    """TaskList 应该能序列化为 dict"""
    now = datetime.now()
    task = Task(
        task_id="t1",
        owner="Worker1",
        content="实现功能A",
        status=TaskStatus.PENDING,
        group_chat_id="gc_123",
        created_by="Manager",
        created_at=now,
        updated_at=now,
    )
    task_list = TaskList(
        list_id="list_1",
        group_chat_id="gc_123",
        status=TaskListStatus.ACTIVE,
        tasks=[task],
        created_at=now,
        archived_at=None,
    )
    data = task_list.to_dict()
    assert data["list_id"] == "list_1"
    assert data["status"] == "active"
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["task_id"] == "t1"


def test_task_list_from_dict():
    """TaskList 应该能从 dict 反序列化"""
    data = {
        "list_id": "list_1",
        "group_chat_id": "gc_123",
        "status": "active",
        "tasks": [
            {
                "task_id": "t1",
                "owner": "Worker1",
                "content": "实现功能A",
                "status": "pending",
                "group_chat_id": "gc_123",
                "created_by": "Manager",
                "created_at": "2026-05-31T10:00:00",
                "updated_at": "2026-05-31T10:00:00",
            }
        ],
        "created_at": "2026-05-31T10:00:00",
        "archived_at": None,
    }
    task_list = TaskList.from_dict(data)
    assert task_list.list_id == "list_1"
    assert task_list.status == TaskListStatus.ACTIVE
    assert len(task_list.tasks) == 1
    assert task_list.tasks[0].task_id == "t1"
