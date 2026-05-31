"""Task 和 TaskList 数据模型

Task: 单个任务，包含 owner、content、status
TaskList: 任务列表，包含多个 Task，有 ACTIVE/ARCHIVED 状态
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agents_hub.core.foundation.models import TaskListStatus, TaskStatus


@dataclass
class Task:
    """单个任务

    不变量：
    - 每个 Task 有且只有一个 owner（一个 Worker）
    - 多个 Worker 之间的 Task 必须正交（无重叠职责）
    """

    task_id: str  # 唯一标识（UUID）
    owner: str  # worker name（1:1 不变量）
    content: str  # 任务描述
    status: TaskStatus  # PENDING / RUNNING / COMPLETED / FAILED
    group_chat_id: str  # 所属群聊
    created_by: str  # 创建者（必须是 Leader）
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """序列化为 dict（用于持久化）"""
        return {
            "task_id": self.task_id,
            "owner": self.owner,
            "content": self.content,
            "status": self.status.value,
            "group_chat_id": self.group_chat_id,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """从 dict 反序列化"""
        return cls(
            task_id=data["task_id"],
            owner=data["owner"],
            content=data["content"],
            status=TaskStatus(data["status"]),
            group_chat_id=data["group_chat_id"],
            created_by=data["created_by"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


@dataclass
class TaskList:
    """任务列表

    状态机：
    - 每个 GroupChat 同时只有一个 ACTIVE TaskList
    - archive_task_list 将 ACTIVE → ARCHIVED
    - 下次 assign_tasks_to_team 自动创建新 ACTIVE list
    """

    list_id: str  # 唯一标识（UUID）
    group_chat_id: str
    status: TaskListStatus  # ACTIVE / ARCHIVED
    tasks: list[Task]
    created_at: datetime
    archived_at: datetime | None

    def to_dict(self) -> dict[str, Any]:
        """序列化为 dict（用于持久化）"""
        return {
            "list_id": self.list_id,
            "group_chat_id": self.group_chat_id,
            "status": self.status.value,
            "tasks": [task.to_dict() for task in self.tasks],
            "created_at": self.created_at.isoformat(),
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskList":
        """从 dict 反序列化"""
        return cls(
            list_id=data["list_id"],
            group_chat_id=data["group_chat_id"],
            status=TaskListStatus(data["status"]),
            tasks=[Task.from_dict(t) for t in data["tasks"]],
            created_at=datetime.fromisoformat(data["created_at"]),
            archived_at=datetime.fromisoformat(data["archived_at"])
            if data["archived_at"]
            else None,
        )
