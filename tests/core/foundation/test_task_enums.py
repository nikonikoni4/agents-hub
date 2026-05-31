from agents_hub.core.foundation.models import TaskListStatus, TaskStatus


def test_task_status_values():
    """TaskStatus 应包含 4 个状态"""
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.RUNNING.value == "running"
    assert TaskStatus.COMPLETED.value == "completed"
    assert TaskStatus.FAILED.value == "failed"


def test_task_list_status_values():
    """TaskListStatus 应包含 2 个状态"""
    assert TaskListStatus.ACTIVE.value == "active"
    assert TaskListStatus.ARCHIVED.value == "archived"
