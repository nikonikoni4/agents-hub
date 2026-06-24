"""SchedulerService 单元测试

测试调度器基础框架的核心功能：
- 单例行为
- start() / shutdown() 幂等性
- CronTrigger 注册
- 补偿执行逻辑（含任务引用保存和异常监控）
"""

from unittest.mock import MagicMock, patch

import pytest

from agents_hub.scheduler.scheduler_service import SchedulerService


@pytest.fixture(autouse=True)
def _reset_singleton():
    """每个测试前重置单例状态"""
    SchedulerService._instance = None
    yield
    SchedulerService._instance = None


class TestSchedulerServiceSingleton:
    """单例行为测试"""

    def test_multiple_calls_return_same_instance(self):
        s1 = SchedulerService()
        s2 = SchedulerService()
        assert s1 is s2


class TestSchedulerServiceStart:
    """start() 方法测试"""

    @patch("agents_hub.scheduler.scheduler_service.config")
    @patch("agents_hub.scheduler.scheduler_service.StateManager")
    @patch("agents_hub.scheduler.scheduler_service.AsyncIOScheduler")
    def test_start_creates_scheduler_and_starts(self, mock_scheduler_cls, mock_sm_cls, mock_config):
        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        mock_scheduler_cls.return_value = mock_scheduler

        mock_config.memory_task_cron_time = (10, 0)
        mock_config.data_path = "/tmp/data"

        mock_sm = MagicMock()
        mock_sm.should_execute_today.return_value = False
        mock_sm_cls.return_value = mock_sm

        svc = SchedulerService()
        svc.start()

        mock_scheduler.start.assert_called_once()

    @patch("agents_hub.scheduler.scheduler_service.config")
    @patch("agents_hub.scheduler.scheduler_service.StateManager")
    @patch("agents_hub.scheduler.scheduler_service.AsyncIOScheduler")
    def test_start_is_idempotent(self, mock_scheduler_cls, mock_sm_cls, mock_config):
        """已启动时再次调用 start() 应跳过"""
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        mock_scheduler_cls.return_value = mock_scheduler

        mock_config.memory_task_cron_time = (10, 0)
        mock_config.data_path = "/tmp/data"

        mock_sm = MagicMock()
        mock_sm.should_execute_today.return_value = False
        mock_sm_cls.return_value = mock_sm

        svc = SchedulerService()
        svc.start()  # 第一次：启动
        svc.start()  # 第二次：应跳过

        # start 只被调用一次
        mock_scheduler.start.assert_called_once()

    @patch("agents_hub.scheduler.scheduler_service.config")
    @patch("agents_hub.scheduler.scheduler_service.StateManager")
    @patch("agents_hub.scheduler.scheduler_service.AsyncIOScheduler")
    def test_start_registers_cron_trigger(self, mock_scheduler_cls, mock_sm_cls, mock_config):
        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        mock_scheduler_cls.return_value = mock_scheduler

        mock_config.memory_task_cron_time = (10, 0)
        mock_config.data_path = "/tmp/data"

        mock_sm = MagicMock()
        mock_sm.should_execute_today.return_value = False
        mock_sm_cls.return_value = mock_sm

        svc = SchedulerService()
        svc.start()

        mock_scheduler.add_job.assert_called_once()
        call_kwargs = mock_scheduler.add_job.call_args
        # 验证使用了 CronTrigger
        assert "trigger" in call_kwargs.kwargs or "trigger" in call_kwargs[0]


class TestSchedulerServiceShutdown:
    """shutdown() 方法测试"""

    @patch("agents_hub.scheduler.scheduler_service.config")
    @patch("agents_hub.scheduler.scheduler_service.StateManager")
    @patch("agents_hub.scheduler.scheduler_service.AsyncIOScheduler")
    def test_shutdown_after_start(self, mock_scheduler_cls, mock_sm_cls, mock_config):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        mock_scheduler_cls.return_value = mock_scheduler

        mock_config.memory_task_cron_time = (10, 0)
        mock_config.data_path = "/tmp/data"

        mock_sm = MagicMock()
        mock_sm.should_execute_today.return_value = False
        mock_sm_cls.return_value = mock_sm

        svc = SchedulerService()
        svc.start()
        svc.shutdown()

        mock_scheduler.shutdown.assert_called_once()

    @patch("agents_hub.scheduler.scheduler_service.AsyncIOScheduler")
    def test_shutdown_without_start_is_noop(self, mock_scheduler_cls):
        """未启动时调用 shutdown() 应跳过"""
        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        mock_scheduler_cls.return_value = mock_scheduler

        svc = SchedulerService()
        svc.shutdown()

        mock_scheduler.shutdown.assert_not_called()

    @patch("agents_hub.scheduler.scheduler_service.config")
    @patch("agents_hub.scheduler.scheduler_service.StateManager")
    @patch("agents_hub.scheduler.scheduler_service.AsyncIOScheduler")
    def test_shutdown_is_idempotent(self, mock_scheduler_cls, mock_sm_cls, mock_config):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        mock_scheduler_cls.return_value = mock_scheduler

        mock_config.memory_task_cron_time = (10, 0)
        mock_config.data_path = "/tmp/data"

        mock_sm = MagicMock()
        mock_sm.should_execute_today.return_value = False
        mock_sm_cls.return_value = mock_sm

        svc = SchedulerService()
        svc.start()
        svc.shutdown()
        svc.shutdown()  # 第二次：应跳过

        mock_scheduler.shutdown.assert_called_once()


class TestCompensationExecution:
    """补偿执行逻辑测试"""

    @patch("agents_hub.scheduler.scheduler_service.asyncio")
    @patch("agents_hub.scheduler.scheduler_service.AsyncIOScheduler")
    @patch("agents_hub.scheduler.scheduler_service.StateManager")
    @patch("agents_hub.scheduler.scheduler_service.config")
    def test_compensation_when_past_time_and_not_executed(
        self, mock_config, mock_sm_cls, mock_scheduler_cls, mock_asyncio
    ):
        """已过执行时间且今天未执行时，触发补偿并保存任务引用"""
        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        mock_scheduler_cls.return_value = mock_scheduler

        mock_sm = MagicMock()
        mock_sm.should_execute_today.return_value = True
        mock_sm_cls.return_value = mock_sm

        mock_config.memory_task_cron_time = (10, 0)
        mock_config.data_path = "/tmp/data"

        # 模拟 create_task 返回带 add_done_callback 的 task
        mock_task = MagicMock()
        mock_asyncio.create_task.return_value = mock_task

        fake_now = MagicMock()
        fake_now.hour = 11
        fake_now.minute = 0

        with patch("agents_hub.scheduler.scheduler_service.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now

            svc = SchedulerService()
            svc.start()

        # 应该触发了补偿执行
        mock_asyncio.create_task.assert_called_once()
        # 任务引用被保存
        assert svc._compensation_task is mock_task
        # 添加了异常监控回调
        mock_task.add_done_callback.assert_called_once()

    @patch("agents_hub.scheduler.scheduler_service.asyncio")
    @patch("agents_hub.scheduler.scheduler_service.AsyncIOScheduler")
    @patch("agents_hub.scheduler.scheduler_service.StateManager")
    @patch("agents_hub.scheduler.scheduler_service.config")
    def test_no_compensation_when_before_time(
        self, mock_config, mock_sm_cls, mock_scheduler_cls, mock_asyncio
    ):
        """未到执行时间时不触发补偿"""
        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        mock_scheduler_cls.return_value = mock_scheduler

        mock_sm = MagicMock()
        mock_sm.should_execute_today.return_value = True
        mock_sm_cls.return_value = mock_sm

        mock_config.memory_task_cron_time = (10, 0)
        mock_config.data_path = "/tmp/data"

        fake_now = MagicMock()
        fake_now.hour = 9
        fake_now.minute = 0

        with patch("agents_hub.scheduler.scheduler_service.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now

            svc = SchedulerService()
            svc.start()

        # 不触发补偿
        mock_asyncio.create_task.assert_not_called()
        assert svc._compensation_task is None

    @patch("agents_hub.scheduler.scheduler_service.asyncio")
    @patch("agents_hub.scheduler.scheduler_service.AsyncIOScheduler")
    @patch("agents_hub.scheduler.scheduler_service.StateManager")
    @patch("agents_hub.scheduler.scheduler_service.config")
    def test_no_compensation_when_already_executed(
        self, mock_config, mock_sm_cls, mock_scheduler_cls, mock_asyncio
    ):
        """今天已执行过时不触发补偿"""
        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        mock_scheduler_cls.return_value = mock_scheduler

        mock_sm = MagicMock()
        mock_sm.should_execute_today.return_value = False  # 今天已执行
        mock_sm_cls.return_value = mock_sm

        mock_config.memory_task_cron_time = (10, 0)
        mock_config.data_path = "/tmp/data"

        fake_now = MagicMock()
        fake_now.hour = 11
        fake_now.minute = 0

        with patch("agents_hub.scheduler.scheduler_service.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now

            svc = SchedulerService()
            svc.start()

        # 不触发补偿
        mock_asyncio.create_task.assert_not_called()


class TestOnTaskDone:
    """_on_task_done 异常监控测试"""

    def test_logs_exception_on_failure(self):
        """任务异常时记录 ERROR 日志"""
        mock_task = MagicMock()
        mock_task.cancelled.return_value = False
        mock_task.exception.return_value = RuntimeError("测试异常")

        with patch("agents_hub.scheduler.scheduler_service.logger") as mock_logger:
            SchedulerService._on_task_done(mock_task)

        mock_logger.error.assert_called_once()
        assert "补偿执行任务异常退出" in mock_logger.error.call_args[0][0]

    def test_no_log_on_cancelled(self):
        """任务取消时不记录"""
        mock_task = MagicMock()
        mock_task.cancelled.return_value = True

        with patch("agents_hub.scheduler.scheduler_service.logger") as mock_logger:
            SchedulerService._on_task_done(mock_task)

        mock_logger.error.assert_not_called()

    def test_no_log_on_success(self):
        """任务成功时不记录"""
        mock_task = MagicMock()
        mock_task.cancelled.return_value = False
        mock_task.exception.return_value = None

        with patch("agents_hub.scheduler.scheduler_service.logger") as mock_logger:
            SchedulerService._on_task_done(mock_task)

        mock_logger.error.assert_not_called()
