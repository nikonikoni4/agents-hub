"""定时调度服务

封装 APScheduler AsyncIOScheduler，提供定时记忆任务调度能力。
单例模式，模块级变量 scheduler_service 确保全局唯一。
启动时检查补偿执行：如果今天已过配置时间且未执行，则异步补偿一次。
"""

import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from agents_hub.config.config import config
from agents_hub.scheduler.state_manager import StateManager
from agents_hub.scheduler.task.memory_task import MemoryTask

logger = logging.getLogger(__name__)


class SchedulerService:
    """定时任务调度服务（单例）

    封装 APScheduler AsyncIOScheduler，支持 start() / shutdown() 幂等调用。
    在 FastAPI lifespan 中集成：startup 调用 start()，shutdown 调用 shutdown()。
    """

    _instance: "SchedulerService | None" = None
    _scheduler: AsyncIOScheduler | None = None
    _running: bool = False

    def __new__(cls) -> "SchedulerService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._scheduler = None
            cls._instance._running = False
        return cls._instance

    def start(self) -> None:
        """启动调度器，已在运行时跳过（幂等）

        启动时检查补偿执行：如果今天已过配置时间且未执行，则异步补偿一次。
        """
        if self._scheduler is not None and self._scheduler.running:
            logger.warning("调度器已在运行，跳过重复启动")
            return

        self._scheduler = AsyncIOScheduler()

        hour, minute = config.memory_task_cron_time
        self._scheduler.add_job(
            self._execute_memory_task,
            trigger=CronTrigger(hour=hour, minute=minute),
            id="memory_task",
            name="记忆助手定时任务",
            replace_existing=True,
        )

        self._scheduler.start()
        logger.info("调度器已启动，CronTrigger 时间: %02d:%02d", hour, minute)

        # 补偿执行检查：如果今天已过配置时间且未执行，异步补偿一次
        self._check_compensation()

    def _check_compensation(self) -> None:
        """检查是否需要补偿执行

        如果今天已过配置的执行时间且未执行，则异步补偿执行一次。
        """
        now = datetime.now()
        target_hour, target_minute = config.memory_task_cron_time

        if now.hour > target_hour or (now.hour == target_hour and now.minute >= target_minute):
            state_manager = StateManager(config.data_path)
            if state_manager.should_execute_today():
                logger.info(
                    "已过今日 %02d:%02d，异步补偿执行 memory_task",
                    target_hour,
                    target_minute,
                )
                asyncio.create_task(self._execute_memory_task())

    def shutdown(self) -> None:
        """关闭调度器，未启动时跳过（幂等）"""
        if self._scheduler is None or not self._scheduler.running:
            logger.warning("调度器未运行，跳过关闭")
            return

        self._scheduler.shutdown()
        self._scheduler = None
        logger.info("调度器已关闭")

    async def _execute_memory_task(self) -> None:
        """执行记忆更新任务（内部方法）

        遍历 index.json 中的群聊列表，对需要更新的群聊执行记忆收集。
        单群聊失败时跳过并记录，继续处理下一个群聊。
        """
        # 防止重入
        if self._running:
            logger.warning("记忆任务正在执行，跳过本次调度")
            return

        self._running = True
        logger.info("开始执行记忆更新任务")

        try:
            state_manager = StateManager(config.data_path)

            # 检查今天是否需要执行
            if not state_manager.should_execute_today():
                logger.info("今天已执行过记忆任务，跳过")
                return

            # 加载群聊索引
            index = state_manager.load_memory_index()
            if not index:
                logger.info("群聊索引为空，跳过执行")
                state_manager.save_schedule_state(
                    {"memory_task": datetime.now(timezone.utc).isoformat()}
                )
                return

            memory_task = MemoryTask()
            success_count = 0
            fail_count = 0

            # 遍历群聊列表
            for group_chat_id, group_info in index.items():
                last_updated = group_info.get("last_updated")
                result_text = await memory_task.execute(group_chat_id, last_updated)

                is_success = not result_text.startswith("执行失败:")
                if is_success:
                    success_count += 1
                    # 成功时更新 index 的 last_updated
                    index[group_chat_id]["last_updated"] = datetime.now(timezone.utc).isoformat()
                else:
                    fail_count += 1

                # 记录执行结果
                state_manager.append_result(group_chat_id, result_text, is_success)

            # 保存更新后的 index
            state_manager.save_memory_index(index)

            # 更新调度状态
            state_manager.save_schedule_state(
                {"memory_task": datetime.now(timezone.utc).isoformat()}
            )

            logger.info("记忆更新任务完成: 成功=%d, 失败=%d", success_count, fail_count)

        except Exception as e:
            logger.error("记忆更新任务异常: %s", str(e), exc_info=True)
        finally:
            self._running = False


# 模块级单例
scheduler_service = SchedulerService()
