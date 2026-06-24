"""StateManager 单元测试

测试状态文件管理的核心功能：
- JSON 文件读写
- should_execute_today 判断
- append_result 保留最近 10 条
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from agents_hub.scheduler.state_manager import StateManager


@pytest.fixture
def tmp_data_path(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def state_manager(tmp_data_path: Path) -> StateManager:
    return StateManager(tmp_data_path)


class TestScheduleState:
    """调度状态读写测试"""

    def test_load_nonexistent_returns_empty(self, state_manager: StateManager):
        assert state_manager.load_schedule_state() == {}

    def test_save_and_load_roundtrip(self, state_manager: StateManager):
        state = {"memory_task": "2026-06-24T10:00:00+00:00"}
        state_manager.save_schedule_state(state)
        assert state_manager.load_schedule_state() == state

    def test_should_execute_today_no_state(self, state_manager: StateManager):
        assert state_manager.should_execute_today() is True

    def test_should_execute_today_same_date(self, state_manager: StateManager):
        today = datetime.now(timezone.utc).isoformat()
        state_manager.save_schedule_state({"memory_task": today})
        assert state_manager.should_execute_today() is False

    def test_should_execute_today_different_date(self, state_manager: StateManager):
        yesterday = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        state_manager.save_schedule_state({"memory_task": yesterday})
        assert state_manager.should_execute_today() is True


class TestMemoryIndex:
    """记忆索引读写测试"""

    def test_load_nonexistent_returns_empty(self, state_manager: StateManager):
        assert state_manager.load_memory_index() == {}

    def test_save_and_load_roundtrip(self, state_manager: StateManager):
        index = {"chat-1": {"last_updated": "2026-06-24T10:00:00Z"}}
        state_manager.save_memory_index(index)
        assert state_manager.load_memory_index() == index


class TestAppendResult:
    """执行结果追加测试"""

    def test_append_creates_file(self, state_manager: StateManager):
        state_manager.append_result("chat-1", "成功", True)
        results = state_manager._read_json(state_manager._result_path)
        assert len(results) == 1
        assert results[0]["group_chat_id"] == "chat-1"
        assert results[0]["success"] is True

    def test_append_keeps_max_10(self, state_manager: StateManager):
        for i in range(15):
            state_manager.append_result(f"chat-{i}", f"结果{i}", True)
        results = state_manager._read_json(state_manager._result_path)
        assert len(results) == 10
        assert results[0]["group_chat_id"] == "chat-5"
        assert results[-1]["group_chat_id"] == "chat-14"
