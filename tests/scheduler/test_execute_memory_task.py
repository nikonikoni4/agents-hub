"""SchedulerService._execute_memory_task 单元测试

测试调度器的主执行流程：
- 遍历 index.json 中的群聊列表
- 对需要更新的群聊执行记忆收集
- 更新 index.json 和 result.json
- 单群聊失败时跳过继续
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_hub.scheduler.scheduler_service import SchedulerService


@pytest.fixture(autouse=True)
def _reset_singleton():
    SchedulerService._instance = None
    yield
    SchedulerService._instance = None


class TestExecuteMemoryTask:
    """_execute_memory_task 测试"""

    @pytest.mark.asyncio
    async def test_executes_for_group_chats_needing_update(self):
        """对需要更新的群聊执行记忆收集"""
        with (
            patch("agents_hub.scheduler.scheduler_service.StateManager") as mock_sm_cls,
            patch("agents_hub.scheduler.scheduler_service.MemoryTask") as mock_mt_cls,
        ):
            mock_sm = MagicMock()
            mock_sm.load_memory_index.return_value = {
                "chat-1": {"last_updated": "2020-01-01T00:00:00Z"},
            }
            mock_sm.should_execute_today.return_value = True
            mock_sm_cls.return_value = mock_sm

            mock_mt = MagicMock()
            mock_mt.execute = AsyncMock(return_value="记忆收集完成")
            mock_mt_cls.return_value = mock_mt

            svc = SchedulerService()
            await svc._execute_memory_task()

            mock_mt.execute.assert_awaited_once_with("chat-1", "2020-01-01T00:00:00Z")
            mock_sm.save_memory_index.assert_called_once()
            mock_sm.save_schedule_state.assert_called_once()
            # 验证使用批量写入
            mock_sm.append_results.assert_called_once()
            results_arg = mock_sm.append_results.call_args[0][0]
            assert len(results_arg) == 1
            assert results_arg[0]["success"] is True

    @pytest.mark.asyncio
    async def test_skips_when_should_not_execute(self):
        """今天已执行时跳过"""
        with patch("agents_hub.scheduler.scheduler_service.StateManager") as mock_sm_cls:
            mock_sm = MagicMock()
            mock_sm.should_execute_today.return_value = False
            mock_sm_cls.return_value = mock_sm

            svc = SchedulerService()
            await svc._execute_memory_task()

            mock_sm.load_memory_index.assert_not_called()

    @pytest.mark.asyncio
    async def test_single_failure_continues_others(self):
        """单群聊失败时继续处理其他群聊"""
        with (
            patch("agents_hub.scheduler.scheduler_service.StateManager") as mock_sm_cls,
            patch("agents_hub.scheduler.scheduler_service.MemoryTask") as mock_mt_cls,
        ):
            mock_sm = MagicMock()
            mock_sm.load_memory_index.return_value = {
                "chat-1": {"last_updated": "2020-01-01T00:00:00Z"},
                "chat-2": {"last_updated": "2020-01-01T00:00:00Z"},
            }
            mock_sm.should_execute_today.return_value = True
            mock_sm_cls.return_value = mock_sm

            mock_mt = MagicMock()
            # 第一个失败，第二个成功
            mock_mt.execute = AsyncMock(side_effect=["执行失败: CLI 超时", "记忆收集完成"])
            mock_mt_cls.return_value = mock_mt

            svc = SchedulerService()
            await svc._execute_memory_task()

            assert mock_mt.execute.await_count == 2
            # 批量写入，只调用一次
            mock_sm.append_results.assert_called_once()
            results_arg = mock_sm.append_results.call_args[0][0]
            assert len(results_arg) == 2
            assert results_arg[0]["success"] is False
            assert results_arg[1]["success"] is True
            # 只有成功的群聊更新了 index
            mock_sm.save_memory_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_index_does_nothing(self):
        """index.json 为空时不做任何操作"""
        with (
            patch("agents_hub.scheduler.scheduler_service.StateManager") as mock_sm_cls,
            patch("agents_hub.scheduler.scheduler_service.MemoryTask") as mock_mt_cls,
        ):
            mock_sm = MagicMock()
            mock_sm.load_memory_index.return_value = {}
            mock_sm.should_execute_today.return_value = True
            mock_sm_cls.return_value = mock_sm

            mock_mt = MagicMock()
            mock_mt_cls.return_value = mock_mt

            svc = SchedulerService()
            await svc._execute_memory_task()

            mock_mt.execute.assert_not_called()
            mock_sm.save_schedule_state.assert_called_once()
