"""
TaskStatus 和 TaskListStatus 枚举测试

契约驱动测试：
- TaskStatus: PENDING / RUNNING / COMPLETED / FAILED
- TaskListStatus: ACTIVE / ARCHIVED
"""

from agents_hub.core.foundation.models import TaskListStatus, TaskStatus


def test_task_status_values() -> None:
    """
    契约：TaskStatus 应包含 4 个状态，值正确

    验证方式：
    1. 验证 PENDING.value == "pending"
    2. 验证 RUNNING.value == "running"
    3. 验证 COMPLETED.value == "completed"
    4. 验证 FAILED.value == "failed"

    如果失败，说明：枚举定义错误或值变更
    """
    assert TaskStatus.PENDING.value == "pending", "PENDING 值应为 'pending'"
    assert TaskStatus.RUNNING.value == "running", "RUNNING 值应为 'running'"
    assert TaskStatus.COMPLETED.value == "completed", "COMPLETED 值应为 'completed'"
    assert TaskStatus.FAILED.value == "failed", "FAILED 值应为 'failed'"


def test_task_status_count() -> None:
    """
    契约：TaskStatus 应恰好有 4 个成员

    验证方式：
    1. 验证 len(TaskStatus) == 4

    如果失败，说明：枚举成员数量变更
    """
    assert len(TaskStatus) == 4, f"TaskStatus 应有 4 个成员，实际: {len(TaskStatus)}"


def test_task_list_status_values() -> None:
    """
    契约：TaskListStatus 应包含 2 个状态，值正确

    验证方式：
    1. 验证 ACTIVE.value == "active"
    2. 验证 ARCHIVED.value == "archived"

    如果失败，说明：枚举定义错误或值变更
    """
    assert TaskListStatus.ACTIVE.value == "active", "ACTIVE 值应为 'active'"
    assert TaskListStatus.ARCHIVED.value == "archived", "ARCHIVED 值应为 'archived'"


def test_task_list_status_count() -> None:
    """
    契约：TaskListStatus 应恰好有 2 个成员

    验证方式：
    1. 验证 len(TaskListStatus) == 2

    如果失败，说明：枚举成员数量变更
    """
    assert len(TaskListStatus) == 2, f"TaskListStatus 应有 2 个成员，实际: {len(TaskListStatus)}"


def test_task_status_from_value() -> None:
    """
    契约：TaskStatus 可以从字符串值构造

    验证方式：
    1. 使用 TaskStatus("pending") 构造
    2. 验证结果为 TaskStatus.PENDING

    如果失败，说明：枚举构造方式不支持从值构造
    """
    assert TaskStatus("pending") == TaskStatus.PENDING
    assert TaskStatus("running") == TaskStatus.RUNNING
    assert TaskStatus("completed") == TaskStatus.COMPLETED
    assert TaskStatus("failed") == TaskStatus.FAILED


def test_task_list_status_from_value() -> None:
    """
    契约：TaskListStatus 可以从字符串值构造

    验证方式：
    1. 使用 TaskListStatus("active") 构造
    2. 验证结果为 TaskListStatus.ACTIVE

    如果失败，说明：枚举构造方式不支持从值构造
    """
    assert TaskListStatus("active") == TaskListStatus.ACTIVE
    assert TaskListStatus("archived") == TaskListStatus.ARCHIVED
