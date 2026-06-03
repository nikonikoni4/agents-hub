"""
AgentCall 单元测试

契约：
1. 创建时 status 默认 PENDING
2. is_timeout() 已完成状态返回 False
3. is_timeout() 无超时限制返回 False
4. is_timeout() 超时返回 True
5. can_be_deleted() PENDING/RUNNING 返回 False
6. can_be_deleted() 有 business_task_id 返回 False
7. can_be_deleted() NOTIFICATION + COMPLETED + 超过保留时间返回 True
8. can_be_deleted() TASK + COMPLETED + 超过保留时间返回 True
9. can_be_deleted() FAILED/TIMEOUT + 超过保留时间返回 True
"""

from datetime import datetime, timedelta
from unittest.mock import patch

from agents_hub.core.communication.agent_call import AgentCall
from agents_hub.core.foundation import CallStatus, MessageType


def create_call(
    status: CallStatus = CallStatus.PENDING,
    message_type: MessageType = MessageType.NOTIFICATION,
    timeout_seconds: int | None = None,
    business_task_id: str | None = None,
    created_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> AgentCall:
    call = AgentCall(
        send_from="a",
        send_to="b",
        content="test",
        message_type=message_type,
        timeout_seconds=timeout_seconds,
        business_task_id=business_task_id,
    )
    call.status = status
    if created_at:
        call.created_at = created_at
    if completed_at:
        call.completed_at = completed_at
    return call


class TestAgentCallDefaults:
    """测试 AgentCall 默认值"""

    def test_default_status_pending(self):
        """契约：创建时 status 默认 PENDING"""
        call = AgentCall(
            send_from="a", send_to="b", content="c", message_type=MessageType.TASK
        )
        assert call.status == CallStatus.PENDING

    def test_default_call_id_generated(self):
        """契约：call_id 自动生成"""
        call = AgentCall(
            send_from="a", send_to="b", content="c", message_type=MessageType.TASK
        )
        assert call.call_id is not None
        assert len(call.call_id) == 8

    def test_default_timestamps_none(self):
        """契约：started_at 和 completed_at 默认 None"""
        call = AgentCall(
            send_from="a", send_to="b", content="c", message_type=MessageType.TASK
        )
        assert call.started_at is None
        assert call.completed_at is None

    def test_default_has_agent_response_false(self):
        """契约：创建时默认尚未被 Agent 显式回复闭环"""
        call = AgentCall(
            send_from="a", send_to="b", content="c", message_type=MessageType.TASK
        )
        assert call.has_agent_response is False


class TestAgentCallIsTimeout:
    """测试 is_timeout()"""

    def test_completed_returns_false(self):
        """契约：已完成状态不会超时"""
        call = create_call(status=CallStatus.COMPLETED, timeout_seconds=1)
        assert call.is_timeout() is False

    def test_failed_returns_false(self):
        """契约：失败状态不会超时"""
        call = create_call(status=CallStatus.FAILED, timeout_seconds=1)
        assert call.is_timeout() is False

    def test_timeout_status_returns_false(self):
        """契约：已超时状态不再判断超时"""
        call = create_call(status=CallStatus.TIMEOUT, timeout_seconds=1)
        assert call.is_timeout() is False

    def test_no_timeout_limit_returns_false(self):
        """契约：无超时限制返回 False"""
        call = create_call(timeout_seconds=None)
        assert call.is_timeout() is False

    def test_not_expired_returns_false(self):
        """契约：未超时返回 False"""
        now = datetime.now()
        call = create_call(timeout_seconds=60, created_at=now)
        with patch("agents_hub.core.communication.agent_call.datetime") as mock_dt:
            mock_dt.now.return_value = now + timedelta(seconds=30)
            assert call.is_timeout() is False

    def test_expired_returns_true(self):
        """契约：已超时返回 True"""
        now = datetime.now()
        call = create_call(timeout_seconds=60, created_at=now)
        with patch("agents_hub.core.communication.agent_call.datetime") as mock_dt:
            mock_dt.now.return_value = now + timedelta(seconds=61)
            assert call.is_timeout() is True


class TestAgentCallCanBeDeleted:
    """测试 can_be_deleted()"""

    def test_pending_returns_false(self):
        """契约：PENDING 状态不删除"""
        call = create_call(status=CallStatus.PENDING)
        assert call.can_be_deleted() is False

    def test_running_returns_false(self):
        """契约：RUNNING 状态不删除"""
        call = create_call(status=CallStatus.RUNNING)
        assert call.can_be_deleted() is False

    def test_with_business_task_returns_false(self):
        """契约：有业务任务关联不删除"""
        call = create_call(
            status=CallStatus.COMPLETED,
            business_task_id="task_1",
            completed_at=datetime.now() - timedelta(hours=2),
        )
        assert call.can_be_deleted() is False

    def test_notification_completed_within_retention(self):
        """契约：NOTIFICATION 完成但未超过保留时间不删除"""
        now = datetime.now()
        call = create_call(
            status=CallStatus.COMPLETED,
            message_type=MessageType.NOTIFICATION,
            completed_at=now - timedelta(minutes=3),
        )
        with patch("agents_hub.core.communication.agent_call.datetime") as mock_dt:
            mock_dt.now.return_value = now
            assert call.can_be_deleted() is False

    def test_notification_completed_exceeds_retention(self):
        """契约：NOTIFICATION 完成且超过保留时间可删除"""
        now = datetime.now()
        call = create_call(
            status=CallStatus.COMPLETED,
            message_type=MessageType.NOTIFICATION,
            completed_at=now - timedelta(minutes=6),
        )
        with patch("agents_hub.core.communication.agent_call.datetime") as mock_dt:
            mock_dt.now.return_value = now
            assert call.can_be_deleted() is True

    def test_task_completed_within_retention(self):
        """契约：TASK 完成但未超过保留时间不删除"""
        now = datetime.now()
        call = create_call(
            status=CallStatus.COMPLETED,
            message_type=MessageType.TASK,
            completed_at=now - timedelta(minutes=30),
        )
        with patch("agents_hub.core.communication.agent_call.datetime") as mock_dt:
            mock_dt.now.return_value = now
            assert call.can_be_deleted() is False

    def test_task_completed_exceeds_retention(self):
        """契约：TASK 完成且超过保留时间可删除"""
        now = datetime.now()
        call = create_call(
            status=CallStatus.COMPLETED,
            message_type=MessageType.TASK,
            completed_at=now - timedelta(hours=2),
        )
        with patch("agents_hub.core.communication.agent_call.datetime") as mock_dt:
            mock_dt.now.return_value = now
            assert call.can_be_deleted() is True

    def test_failed_within_retention(self):
        """契约：FAILED 未超过保留时间不删除"""
        now = datetime.now()
        call = create_call(
            status=CallStatus.FAILED,
            completed_at=now - timedelta(hours=12),
        )
        with patch("agents_hub.core.communication.agent_call.datetime") as mock_dt:
            mock_dt.now.return_value = now
            assert call.can_be_deleted() is False

    def test_failed_exceeds_retention(self):
        """契约：FAILED 超过保留时间可删除"""
        now = datetime.now()
        call = create_call(
            status=CallStatus.FAILED,
            completed_at=now - timedelta(hours=25),
        )
        with patch("agents_hub.core.communication.agent_call.datetime") as mock_dt:
            mock_dt.now.return_value = now
            assert call.can_be_deleted() is True

    def test_custom_retention_config(self):
        """契约：自定义保留时间配置生效"""
        now = datetime.now()
        call = create_call(
            status=CallStatus.COMPLETED,
            message_type=MessageType.NOTIFICATION,
            completed_at=now - timedelta(seconds=10),
        )
        with patch("agents_hub.core.communication.agent_call.datetime") as mock_dt:
            mock_dt.now.return_value = now
            # 自定义：NOTIFICATION 完成后保留 5 秒
            assert call.can_be_deleted({"notification_completed": 5, "task_completed": 3600, "failed": 86400}) is True
            # 自定义：NOTIFICATION 完成后保留 15 秒
            assert call.can_be_deleted({"notification_completed": 15, "task_completed": 3600, "failed": 86400}) is False
