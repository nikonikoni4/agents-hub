"""
TaskManager - 任务管理器

负责任务的 CRUD 和持久化，实现覆盖式更新语义（参照 Claude Code TodoWrite）。
"""

import json
import uuid
from datetime import datetime

from agents_hub.core.foundation import group_chat_paths
from agents_hub.core.foundation.exceptions import FileSystemError
from agents_hub.core.foundation.models import TaskListStatus, TaskStatus
from agents_hub.utils.logger import get_specialized_logger

from .task import Task, TaskList


class TaskManager:
    """任务管理器

    核心功能：
    - get_active_task_list(): 获取当前 ACTIVE 任务列表
    - assign_tasks(): 覆盖式更新（创建/更新/保持不变）
    - archive_task_list(): 归档当前 ACTIVE 列表
    - 持久化到 tasks.jsonl（每行一个 TaskList JSON）
    """

    def __init__(self, group_chat_id: str, project_path: str):
        """
        初始化 TaskManager

        Args:
            group_chat_id: 群聊 ID
            project_path: 项目路径
        """
        self.group_chat_id = group_chat_id

        # 创建专用 logger
        log_dir = group_chat_paths.base_dir(group_chat_id, project_path)
        self.logger = get_specialized_logger(
            name=f"task_manager.{group_chat_id}",
            log_filename="tasks.log",
            also_to_global=True,
            log_dir=log_dir,
        )

        # 持久化路径
        self._persistence_path = group_chat_paths.tasks_data(group_chat_id, project_path)
        self._persistence_path.parent.mkdir(parents=True, exist_ok=True)

        # 内存中的任务列表（list_id -> TaskList）
        self._task_lists: dict[str, TaskList] = {}

        # 加载历史任务列表
        self._load_from_persistence()

    def get_active_task_list(self, group_chat_id: str) -> TaskList | None:
        """
        获取当前 ACTIVE 任务列表

        Args:
            group_chat_id: 群聊 ID（必须与 self.group_chat_id 一致）

        Returns:
            TaskList | None: 当前 ACTIVE 的任务列表，不存在则返回 None

        Raises:
            ValueError: 如果 group_chat_id 与 self.group_chat_id 不一致
        """
        if group_chat_id != self.group_chat_id:
            raise ValueError(
                f"group_chat_id 不匹配: 期望 {self.group_chat_id}, 实际 {group_chat_id}"
            )

        for task_list in self._task_lists.values():
            if task_list.status == TaskListStatus.ACTIVE:
                return task_list
        return None

    def assign_tasks(
        self,
        group_chat_id: str,
        tasks: list[dict],
        created_by: str,
    ) -> dict:
        """
        为团队分配任务列表（覆盖式更新）

        覆盖式更新语义（参照 Claude Code TodoWrite）：
        - Manager 每次传入完整任务列表（包括已有的和新增的）
        - 系统自动识别哪些是新任务、哪些是更新
        - 旧列表中不在新列表的任务保持不变（不删除）

        Args:
            group_chat_id: 群聊 ID
            tasks: 任务列表（JSON 格式）[{task_id, owner, content, status}]
            created_by: 创建者（必须是 Leader）

        Returns:
            dict: {created: int, updated: int, unchanged: int}
        """
        # 获取当前 ACTIVE 列表
        active_list = self.get_active_task_list(group_chat_id)

        if active_list is None:
            # 创建新列表
            return self._create_new_task_list(group_chat_id, tasks, created_by)
        else:
            # 更新现有列表
            return self._update_existing_task_list(active_list, tasks, created_by)

    def archive_task_list(self, group_chat_id: str) -> dict:
        """
        归档当前 ACTIVE 任务列表

        Args:
            group_chat_id: 群聊 ID

        Returns:
            dict: {archived_count: int, archived_at: str}
        """
        active_list = self.get_active_task_list(group_chat_id)

        if active_list is None:
            self.logger.info("没有 ACTIVE 任务列表，跳过归档")
            return {
                "archived_count": 0,
                "archived_at": datetime.now().isoformat(),
            }

        # 更新状态
        active_list.status = TaskListStatus.ARCHIVED
        active_list.archived_at = datetime.now()

        # 持久化
        self._persist_task_list(active_list)

        self.logger.info(
            f"归档任务列表 {active_list.list_id}，包含 {len(active_list.tasks)} 个任务"
        )

        return {
            "archived_count": len(active_list.tasks),
            "archived_at": active_list.archived_at.isoformat(),
        }

    def _create_new_task_list(
        self,
        group_chat_id: str,
        tasks: list[dict],
        created_by: str,
    ) -> dict:
        """创建新任务列表"""
        list_id = str(uuid.uuid4())
        now = datetime.now()

        # 构造 Task 对象
        task_objects = []
        for task_dict in tasks:
            task = Task(
                task_id=task_dict["task_id"],
                owner=task_dict["owner"],
                content=task_dict["content"],
                status=TaskStatus(task_dict["status"]),
                group_chat_id=group_chat_id,
                created_by=created_by,
                created_at=now,
                updated_at=now,
            )
            task_objects.append(task)

        # 创建 TaskList
        task_list = TaskList(
            list_id=list_id,
            group_chat_id=group_chat_id,
            status=TaskListStatus.ACTIVE,
            tasks=task_objects,
            created_at=now,
            archived_at=None,
        )

        # 保存到内存
        self._task_lists[list_id] = task_list

        # 持久化
        self._persist_task_list(task_list)

        self.logger.info(f"创建新任务列表 {list_id}，包含 {len(task_objects)} 个任务")

        return {
            "created": len(task_objects),
            "updated": 0,
            "unchanged": 0,
        }

    def _update_existing_task_list(
        self,
        active_list: TaskList,
        tasks: list[dict],
        created_by: str,
    ) -> dict:
        """更新现有任务列表（覆盖式更新）"""
        now = datetime.now()

        # 构建现有任务的索引
        existing_tasks = {task.task_id: task for task in active_list.tasks}

        # 统计
        created_count = 0
        updated_count = 0
        unchanged_count = 0

        # 新任务列表
        new_tasks = []

        for task_dict in tasks:
            task_id = task_dict["task_id"]

            if task_id in existing_tasks:
                # 任务已存在，检查是否需要更新
                existing_task = existing_tasks[task_id]
                new_status = TaskStatus(task_dict["status"])
                new_content = task_dict["content"]

                if existing_task.status != new_status or existing_task.content != new_content:
                    # 需要更新
                    existing_task.status = new_status
                    existing_task.content = new_content
                    existing_task.updated_at = now
                    updated_count += 1
                else:
                    # 保持不变
                    unchanged_count += 1

                new_tasks.append(existing_task)
            else:
                # 新任务
                task = Task(
                    task_id=task_id,
                    owner=task_dict["owner"],
                    content=task_dict["content"],
                    status=TaskStatus(task_dict["status"]),
                    group_chat_id=active_list.group_chat_id,
                    created_by=created_by,
                    created_at=now,
                    updated_at=now,
                )
                new_tasks.append(task)
                created_count += 1

        # 保留旧列表中不在新列表的任务（保持不变）
        new_task_ids = {task_dict["task_id"] for task_dict in tasks}
        for task_id, task in existing_tasks.items():
            if task_id not in new_task_ids:
                new_tasks.append(task)
                unchanged_count += 1  # 保留的任务也计入 unchanged

        # 更新任务列表
        active_list.tasks = new_tasks

        # 持久化
        self._persist_task_list(active_list)

        self.logger.info(
            f"更新任务列表 {active_list.list_id}: "
            f"创建 {created_count}, 更新 {updated_count}, 不变 {unchanged_count}"
        )

        return {
            "created": created_count,
            "updated": updated_count,
            "unchanged": unchanged_count,
        }

    def _load_from_persistence(self):
        """从持久化文件加载历史任务列表"""
        if not self._persistence_path.exists():
            self.logger.debug("持久化文件不存在，跳过加载")
            return

        try:
            task_list_records = {}  # list_id -> 最新记录

            with open(self._persistence_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    data = json.loads(line)
                    list_id = data["list_id"]
                    # 后面的记录覆盖前面的（取最新）
                    task_list_records[list_id] = data

            # 反序列化
            for list_id, data in task_list_records.items():
                task_list = TaskList.from_dict(data)
                self._task_lists[list_id] = task_list

            self.logger.info(f"从持久化文件加载了 {len(task_list_records)} 个任务列表")
        except OSError as e:
            raise FileSystemError(
                operation="read",
                path=str(self._persistence_path),
                reason=str(e),
            ) from e

    def _persist_task_list(self, task_list: TaskList):
        """持久化单个任务列表（追加模式）"""
        data = task_list.to_dict()

        try:
            with open(self._persistence_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        except OSError as e:
            raise FileSystemError(
                operation="write",
                path=str(self._persistence_path),
                reason=str(e),
            ) from e
