"""
Task 和 TaskList 数据模型测试

契约驱动测试：
- Task: 单个任务，支持 to_dict/from_dict 序列化
- TaskList: 任务列表，支持 to_dict/from_dict 序列化
"""

from datetime import datetime

from agents_hub.core.communication.task import Task, TaskList
from agents_hub.core.foundation.models import TaskListStatus, TaskStatus


# ============================================================================
# Task 测试
# ============================================================================


def test_task_creation() -> None:
    """
    契约：Task 应该正确创建，所有字段赋值正确

    验证方式：
    1. 创建 Task 实例
    2. 验证每个字段的值

    如果失败，说明：构造函数或字段定义错误
    """
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
    assert task.task_id == "t1"
    assert task.owner == "Worker1"
    assert task.content == "实现功能A"
    assert task.status == TaskStatus.PENDING
    assert task.group_chat_id == "gc_123"
    assert task.created_by == "Manager"
    assert task.created_at == now
    assert task.updated_at == now


def test_task_to_dict() -> None:
    """
    契约：Task.to_dict() 序列化正确

    验证方式：
    1. 创建 Task 实例
    2. 调用 to_dict()
    3. 验证 status 转为 value（"pending"）
    4. 验证 datetime 转为 isoformat 字符串

    如果失败，说明：序列化逻辑错误
    """
    now = datetime(2026, 5, 31, 10, 0, 0)
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
    assert data["owner"] == "Worker1"
    assert data["content"] == "实现功能A"
    assert data["status"] == "pending", "status 应转为 value"
    assert data["group_chat_id"] == "gc_123"
    assert data["created_by"] == "Manager"
    assert data["created_at"] == "2026-05-31T10:00:00", "datetime 应转为 isoformat"
    assert data["updated_at"] == "2026-05-31T10:00:00"


def test_task_from_dict() -> None:
    """
    契约：Task.from_dict() 反序列化正确

    验证方式：
    1. 准备 dict 数据
    2. 调用 Task.from_dict()
    3. 验证 status 转回 TaskStatus 枚举
    4. 验证 datetime 转回 datetime 对象

    如果失败，说明：反序列化逻辑错误
    """
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
    assert task.owner == "Worker1"
    assert task.status == TaskStatus.PENDING, "status 应转回枚举"
    assert isinstance(task.created_at, datetime), "应转回 datetime 对象"
    assert task.created_at.year == 2026


def test_task_roundtrip() -> None:
    """
    契约：序列化后反序列化应得到等价对象

    验证方式：
    1. 创建 Task 实例
    2. to_dict() 序列化
    3. from_dict() 反序列化
    4. 验证所有字段相等

    如果失败，说明：序列化/反序列化不对称
    """
    now = datetime(2026, 5, 31, 10, 0, 0)
    original = Task(
        task_id="t1",
        owner="Worker1",
        content="实现功能A",
        status=TaskStatus.PENDING,
        group_chat_id="gc_123",
        created_by="Manager",
        created_at=now,
        updated_at=now,
    )
    data = original.to_dict()
    restored = Task.from_dict(data)
    assert restored.task_id == original.task_id
    assert restored.owner == original.owner
    assert restored.content == original.content
    assert restored.status == original.status
    assert restored.group_chat_id == original.group_chat_id
    assert restored.created_by == original.created_by
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at


# ============================================================================
# TaskList 测试
# ============================================================================


def test_task_list_creation() -> None:
    """
    契约：TaskList 应该正确创建

    验证方式：
    1. 创建 TaskList 实例
    2. 验证每个字段的值

    如果失败，说明：构造函数或字段定义错误
    """
    now = datetime.now()
    task_list = TaskList(
        list_id="list_1",
        group_chat_id="gc_123",
        status=TaskListStatus.ACTIVE,
        tasks=[],
        created_at=now,
        archived_at=None,
    )
    assert task_list.list_id == "list_1"
    assert task_list.group_chat_id == "gc_123"
    assert task_list.status == TaskListStatus.ACTIVE
    assert len(task_list.tasks) == 0
    assert task_list.archived_at is None


def test_task_list_to_dict() -> None:
    """
    契约：TaskList.to_dict() 序列化正确（包括嵌套 Task 列表）

    验证方式：
    1. 创建包含 Task 的 TaskList
    2. 调用 to_dict()
    3. 验证 tasks 列表正确序列化

    如果失败，说明：嵌套序列化逻辑错误
    """
    now = datetime(2026, 5, 31, 10, 0, 0)
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
    assert data["archived_at"] is None


def test_task_list_from_dict() -> None:
    """
    契约：TaskList.from_dict() 反序列化正确（包括嵌套 Task 列表）

    验证方式：
    1. 准备 dict 数据（包含嵌套 tasks）
    2. 调用 TaskList.from_dict()
    3. 验证 tasks 列表正确反序列化

    如果失败，说明：嵌套反序列化逻辑错误
    """
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
    assert task_list.archived_at is None


def test_task_list_roundtrip() -> None:
    """
    契约：序列化后反序列化应得到等价对象

    验证方式：
    1. 创建 TaskList 实例
    2. to_dict() 序列化
    3. from_dict() 反序列化
    4. 验证所有字段相等（包括嵌套 tasks）

    如果失败，说明：序列化/反序列化不对称
    """
    now = datetime(2026, 5, 31, 10, 0, 0)
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
    original = TaskList(
        list_id="list_1",
        group_chat_id="gc_123",
        status=TaskListStatus.ACTIVE,
        tasks=[task],
        created_at=now,
        archived_at=None,
    )
    data = original.to_dict()
    restored = TaskList.from_dict(data)
    assert restored.list_id == original.list_id
    assert restored.group_chat_id == original.group_chat_id
    assert restored.status == original.status
    assert len(restored.tasks) == len(original.tasks)
    assert restored.tasks[0].task_id == original.tasks[0].task_id
    assert restored.created_at == original.created_at
    assert restored.archived_at == original.archived_at


def test_task_list_empty_tasks() -> None:
    """
    契约：空 tasks 列表正确处理

    验证方式：
    1. 创建空 tasks 的 TaskList
    2. to_dict() 序列化
    3. from_dict() 反序列化
    4. 验证 tasks 仍为空列表

    如果失败，说明：空列表边界处理错误
    """
    now = datetime(2026, 5, 31, 10, 0, 0)
    original = TaskList(
        list_id="list_1",
        group_chat_id="gc_123",
        status=TaskListStatus.ACTIVE,
        tasks=[],
        created_at=now,
        archived_at=None,
    )
    data = original.to_dict()
    assert data["tasks"] == [], "空 tasks 序列化应为空列表"
    restored = TaskList.from_dict(data)
    assert len(restored.tasks) == 0, "反序列化后 tasks 应为空列表"


def test_task_list_with_archived_at() -> None:
    """
    契约：archived_at 非 None 时正确序列化/反序列化

    验证方式：
    1. 创建 archived_at 非 None 的 TaskList
    2. to_dict() 序列化
    3. from_dict() 反序列化
    4. 验证 archived_at 正确转换

    如果失败，说明：archived_at 处理逻辑错误
    """
    now = datetime(2026, 5, 31, 10, 0, 0)
    archived_at = datetime(2026, 5, 31, 12, 0, 0)
    original = TaskList(
        list_id="list_1",
        group_chat_id="gc_123",
        status=TaskListStatus.ARCHIVED,
        tasks=[],
        created_at=now,
        archived_at=archived_at,
    )
    data = original.to_dict()
    assert data["archived_at"] == "2026-05-31T12:00:00", "archived_at 应转为 isoformat"
    restored = TaskList.from_dict(data)
    assert restored.archived_at == archived_at, "反序列化后 archived_at 应恢复"
