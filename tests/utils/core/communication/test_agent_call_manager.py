"""
AgentCallManager 单元测试

契约：
1. create_call() 创建并返回 AgentCall
2. get_call() 存在时返回 AgentCall
3. get_call() 不存在时返回 None
4. update_status() 更新状态并设置 started_at/completed_at
5. set_result() 设置结果并标记 COMPLETED
6. set_error() 设置错误并标记 FAILED
7. get_stats() 返回正确统计
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from agents_hub.core.communication.agent_call_manager import AgentCallManager
from agents_hub.core.foundation import CallStatus, MessageType


@pytest.fixture
def tmp_project(tmp_path):
    """提供临时项目路径，避免污染真实数据目录"""
    return str(tmp_path / "test_project")


@pytest.fixture
def manager(tmp_project):
    """创建 AgentCallManager 实例，使用临时路径"""
    with patch("agents_hub.core.communication.agent_call_manager.get_specialized_logger") as mock_logger:
        mock_logger.return_value = MagicMock(spec=logging.Logger)
        mgr = AgentCallManager(
            group_chat_id="gc_test",
            project_path=tmp_project,
            cleanup_interval=60,
        )
        return mgr


class TestAgentCallManagerCreate:
    """测试 create_call()"""

    def test_create_call_returns_agent_call(self, manager):
        """契约：create_call() 创建并返回 AgentCall"""
        call = manager.create_call(
            send_from="a",
            send_to="b",
            content="hello",
            message_type=MessageType.TASK,
            timeout_seconds=30,
        )
        assert call.send_from == "a"
        assert call.send_to == "b"
        assert call.content == "hello"
        assert call.message_type == MessageType.TASK
        assert call.timeout_seconds == 30
        assert call.status == CallStatus.PENDING

    def test_create_call_stored_internally(self, manager):
        """契约：创建的调用可通过 get_call() 获取"""
        call = manager.create_call(
            send_from="a", send_to="b", content="hi", message_type=MessageType.NOTIFICATION
        )
        retrieved = manager.get_call(call.call_id)
        assert retrieved is call


class TestAgentCallManagerGet:
    """测试 get_call()"""

    def test_get_call_exists(self, manager):
        """契约：获取已存在的调用返回正确对象"""
        call = manager.create_call(
            send_from="a", send_to="b", content="hi", message_type=MessageType.TASK
        )
        result = manager.get_call(call.call_id)
        assert result is call

    def test_get_call_not_exists(self, manager):
        """契约：获取不存在的调用返回 None"""
        result = manager.get_call("nonexistent_id")
        assert result is None


class TestAgentCallManagerUpdateStatus:
    """测试 update_status()"""

    def test_update_to_running_sets_started_at(self, manager):
        """契约：更新为 RUNNING 时设置 started_at"""
        call = manager.create_call(
            send_from="a", send_to="b", content="hi", message_type=MessageType.TASK
        )
        assert call.started_at is None

        manager.update_status(call.call_id, CallStatus.RUNNING)

        assert call.status == CallStatus.RUNNING
        assert call.started_at is not None

    def test_update_to_completed_sets_completed_at(self, manager):
        """契约：更新为 COMPLETED 时设置 completed_at"""
        call = manager.create_call(
            send_from="a", send_to="b", content="hi", message_type=MessageType.TASK
        )
        manager.update_status(call.call_id, CallStatus.COMPLETED)

        assert call.status == CallStatus.COMPLETED
        assert call.completed_at is not None

    def test_update_to_failed_sets_completed_at(self, manager):
        """契约：更新为 FAILED 时设置 completed_at"""
        call = manager.create_call(
            send_from="a", send_to="b", content="hi", message_type=MessageType.TASK
        )
        manager.update_status(call.call_id, CallStatus.FAILED)

        assert call.status == CallStatus.FAILED
        assert call.completed_at is not None

    def test_update_nonexistent_silent(self, manager):
        """契约：更新不存在的调用静默处理"""
        manager.update_status("nonexistent", CallStatus.RUNNING)  # 不应报错


class TestAgentCallManagerResultSet:
    """测试 set_result() 和 set_error()"""

    def test_set_result_marks_completed(self, manager):
        """契约：set_result() 设置结果并标记 COMPLETED"""
        call = manager.create_call(
            send_from="a", send_to="b", content="hi", message_type=MessageType.TASK
        )
        manager.set_result(call.call_id, {"answer": "42"})

        assert call.result == {"answer": "42"}
        assert call.status == CallStatus.COMPLETED
        assert call.completed_at is not None

    def test_set_error_marks_failed(self, manager):
        """契约：set_error() 设置错误并标记 FAILED"""
        call = manager.create_call(
            send_from="a", send_to="b", content="hi", message_type=MessageType.TASK
        )
        manager.set_error(call.call_id, "something broke")

        assert call.error == "something broke"
        assert call.status == CallStatus.FAILED
        assert call.completed_at is not None


class TestAgentCallManagerStats:
    """测试 get_stats()"""

    def test_get_stats_empty(self, manager):
        """契约：无调用时统计为空"""
        stats = manager.get_stats()
        assert stats["total"] == 0
        assert stats["by_status"] == {}
        assert stats["by_message_type"] == {}

    def test_get_stats_returns_correct_counts(self, manager):
        """契约：统计反映实际调用状态分布"""
        manager.create_call(send_from="a", send_to="b", content="1", message_type=MessageType.TASK)
        c2 = manager.create_call(
            send_from="a", send_to="b", content="2", message_type=MessageType.NOTIFICATION
        )
        manager.update_status(c2.call_id, CallStatus.RUNNING)

        stats = manager.get_stats()
        assert stats["total"] == 2
        assert stats["by_status"]["pending"] == 1
        assert stats["by_status"]["running"] == 1
        assert stats["by_message_type"]["task"] == 1
        assert stats["by_message_type"]["notification"] == 1
