"""
Agent 循环隔离机制测试

测试 Agent 在 in_loop 状态下的消息白名单过滤逻辑。
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from agents_hub.agent_bridge.models import AgentResult
from agents_hub.config.types import AgentPlatform, RoleType
from agents_hub.core.agent.base_agent import Agent
from agents_hub.core.context.group_chat_session import AgentMemberInfo


class TestAgentMemberInfoLoopSupport:
    """测试 AgentMemberInfo 对循环状态的支持"""

    def test_agent_member_info_can_set_current_loop_id(self):
        """AgentMemberInfo 可以设置 current_loop_id"""
        info = AgentMemberInfo()
        info.current_loop_id = "loop-123"
        assert info.current_loop_id == "loop-123"

    def test_agent_member_info_can_clear_current_loop_id(self):
        """AgentMemberInfo 可以清除 current_loop_id（设为 None）"""
        info = AgentMemberInfo(current_loop_id="loop-123")
        info.current_loop_id = None
        assert info.current_loop_id is None

    def test_agent_member_info_supports_in_loop_status(self):
        """AgentMemberInfo 可以设置 status='in_loop'"""
        info = AgentMemberInfo()
        info.status = "in_loop"
        assert info.status == "in_loop"


class TestAgentMessageCompletionHandlers:
    """测试 Agent 的通用消息完成处理器"""

    @pytest.fixture
    def mock_agent(self):
        """创建 mock Agent 实例"""
        role = Mock()
        role.get_role_config.return_value = Mock(name="test_agent", role_type=Mock())
        runtime = AsyncMock()
        runtime.get_agent_member_info.return_value = AgentMemberInfo()
        agent_call_manager = Mock()
        message_router = Mock()

        agent = Agent(
            role=role,
            runtime=runtime,
            agent_call_manager=agent_call_manager,
            message_router=message_router,
        )
        return agent

    @pytest.mark.asyncio
    async def test_message_completion_handler_receives_message_and_result(self, mock_agent):
        """消息完成后调用已注册的通用 handler"""
        from agents_hub.core.foundation import AgentMessage, MessageType, SessionType

        seen = []

        async def handler(msg, result):
            seen.append((msg, result))

        mock_agent.add_message_completion_handler(handler)
        result = AgentResult(
            text="done",
            session_id="session-1",
            timestamp="2026-06-20T00:00:00",
            agent_name="test_agent",
            platform=AgentPlatform.CLAUDE,
            role_type=RoleType.TEAM_MEMBER,
        )
        msg = AgentMessage(
            call_id="call-1",
            send_from="loop",
            send_to="test_agent",
            content="loop context",
            session_type=SessionType.MAIN,
            message_type=MessageType.LOOP_MESSAGE,
            metadata={"loop_id": "loop-123"},
        )

        await mock_agent._notify_message_completion(msg, result)

        assert seen == [(msg, result)]

    @pytest.mark.asyncio
    async def test_message_completion_handlers_allow_none_result(self, mock_agent):
        """通用 handler 能接收 None result，由 handler 自己判断是否处理"""
        from agents_hub.core.foundation import AgentMessage, MessageType, SessionType

        seen = []

        async def handler(msg, result):
            seen.append((msg.call_id, result))

        mock_agent.add_message_completion_handler(handler)
        msg = AgentMessage(
            call_id="call-1",
            send_from="leader",
            send_to="test_agent",
            content="normal",
            session_type=SessionType.MAIN,
            message_type=MessageType.NOTIFICATION,
        )

        await mock_agent._notify_message_completion(msg, None)

        assert seen == [("call-1", None)]


class TestAgentMessageWhitelist:
    """测试 Agent 的消息白名单过滤逻辑"""

    @pytest.fixture
    def mock_agent(self):
        """创建 mock Agent 实例"""
        role = Mock()
        role.get_role_config.return_value = Mock(name="test_agent", role_type=Mock())
        runtime = Mock()  # 改为同步 Mock
        runtime.get_agent_member_info.return_value = AgentMemberInfo(status="idle")
        agent_call_manager = Mock()
        message_router = Mock()

        agent = Agent(
            role=role,
            runtime=runtime,
            agent_call_manager=agent_call_manager,
            message_router=message_router,
        )
        return agent

    @pytest.fixture
    def sample_message(self):
        """创建示例消息"""
        from agents_hub.core.foundation import AgentMessage, MessageType, SessionType

        return AgentMessage(
            call_id="call-123",
            send_from="sender",
            send_to="test_agent",
            content="test content",
            session_type=SessionType.MAIN,
            message_type=MessageType.TASK,
        )

    def test_idle_status_accepts_all_messages(self, mock_agent, sample_message):
        """status='idle' 状态下接收所有消息（基线行为不变）"""
        # 设置状态为 idle
        mock_agent.runtime.get_agent_member_info.return_value = AgentMemberInfo(status="idle")

        # 应该接收消息
        result = mock_agent._should_accept_message(sample_message)
        assert result is True

    def test_busy_status_accepts_all_messages(self, mock_agent, sample_message):
        """status='busy' 状态下接收所有消息（基线行为不变）"""
        mock_agent.runtime.get_agent_member_info.return_value = AgentMemberInfo(status="busy")

        result = mock_agent._should_accept_message(sample_message)
        assert result is True

    def test_in_loop_status_rejects_external_messages(self, mock_agent, sample_message):
        """status='in_loop' 状态下拒绝循环外的消息"""
        # 设置状态为 in_loop，循环 ID 为 loop-123
        mock_agent.runtime.get_agent_member_info.return_value = AgentMemberInfo(
            status="in_loop", current_loop_id="loop-123"
        )

        # 消息不带 loop_id（循环外消息）
        sample_message.metadata = {}

        # 应该拒绝消息
        result = mock_agent._should_accept_message(sample_message)
        assert result is False

    def test_in_loop_status_accepts_same_loop_messages(self, mock_agent, sample_message):
        """status='in_loop' 状态下接收同一循环的消息"""
        # 设置状态为 in_loop，循环 ID 为 loop-123
        mock_agent.runtime.get_agent_member_info.return_value = AgentMemberInfo(
            status="in_loop", current_loop_id="loop-123"
        )

        # 消息带有相同的 loop_id
        sample_message.metadata = {"loop_id": "loop-123"}

        # 应该接收消息
        result = mock_agent._should_accept_message(sample_message)
        assert result is True

    def test_in_loop_status_rejects_different_loop_messages(self, mock_agent, sample_message):
        """status='in_loop' 状态下拒绝其他循环的消息"""
        # 设置状态为 in_loop，循环 ID 为 loop-123
        mock_agent.runtime.get_agent_member_info.return_value = AgentMemberInfo(
            status="in_loop", current_loop_id="loop-123"
        )

        # 消息带有不同的 loop_id
        sample_message.metadata = {"loop_id": "loop-456"}

        # 应该拒绝消息
        result = mock_agent._should_accept_message(sample_message)
        assert result is False

    def test_in_loop_status_accepts_manager_messages(self, mock_agent, sample_message):
        """status='in_loop' 状态下接收 Manager 的消息"""
        from agents_hub.config import config

        # 设置状态为 in_loop，循环 ID 为 loop-123
        mock_agent.runtime.get_agent_member_info.return_value = AgentMemberInfo(
            status="in_loop", current_loop_id="loop-123"
        )

        # 消息来自 Manager（不带 loop_id）
        sample_message.metadata = {}
        sample_message.send_from = config.default_manager_name

        # 应该接收消息
        result = mock_agent._should_accept_message(sample_message)
        assert result is True


class TestAgentLoopIsolationIntegration:
    """集成测试：验证消息过滤在 run loop 中正常工作"""

    @pytest.mark.asyncio
    async def test_rejected_message_logs_warning_and_skips_processing(self, caplog):
        """拒绝的消息记录 WARNING 日志且不被处理"""
        import logging

        from agents_hub.core.foundation import AgentMessage, MessageType, SessionType

        # 创建 Agent
        role = Mock()
        role.get_role_config.return_value = Mock(name="test_agent", role_type=Mock())
        runtime = Mock()
        runtime.get_agent_member_info.return_value = AgentMemberInfo(
            status="in_loop", current_loop_id="loop-123"
        )
        agent_call_manager = Mock()
        message_router = Mock()

        agent = Agent(
            role=role,
            runtime=runtime,
            agent_call_manager=agent_call_manager,
            message_router=message_router,
        )

        # 创建一个循环外的消息（应该被拒绝）
        external_msg = AgentMessage(
            call_id="call-external",
            send_from="other_agent",
            send_to="test_agent",
            content="external message",
            session_type=SessionType.MAIN,
            message_type=MessageType.TASK,
            metadata={},  # 不带 loop_id
        )

        # 创建停止消息
        stop_msg = AgentMessage(
            call_id="__STOP__",
            send_from="__SYSTEM__",
            send_to="test_agent",
            content="__STOP__",
            session_type=SessionType.MAIN,
            message_type=MessageType.NOTIFICATION,
        )

        # 将消息放入队列
        await agent.message_queue.put(external_msg)
        await agent.message_queue.put(stop_msg)

        # 启动 run loop
        with caplog.at_level(logging.WARNING):
            await agent._run_loop()

        # 验证日志中包含 WARNING
        assert any("消息被白名单拒绝" in record.message for record in caplog.records)
        assert any("loop_id=loop-123" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_whitelist_check_is_called_in_run_loop(self):
        """验证 _should_accept_message 在 run loop 中被调用"""
        from unittest.mock import patch

        from agents_hub.core.foundation import AgentMessage, MessageType, SessionType

        # 创建 Agent
        role = Mock()
        role.get_role_config.return_value = Mock(name="test_agent", role_type=Mock())
        runtime = Mock()
        runtime.get_agent_member_info.return_value = AgentMemberInfo(
            status="in_loop", current_loop_id="loop-123"
        )
        agent_call_manager = Mock()
        message_router = Mock()

        agent = Agent(
            role=role,
            runtime=runtime,
            agent_call_manager=agent_call_manager,
            message_router=message_router,
        )

        # 创建测试消息
        test_msg = AgentMessage(
            call_id="call-test",
            send_from="sender",
            send_to="test_agent",
            content="test",
            session_type=SessionType.MAIN,
            message_type=MessageType.TASK,
            metadata={},
        )

        # 创建停止消息
        stop_msg = AgentMessage(
            call_id="__STOP__",
            send_from="__SYSTEM__",
            send_to="test_agent",
            content="__STOP__",
            session_type=SessionType.MAIN,
            message_type=MessageType.NOTIFICATION,
        )

        await agent.message_queue.put(test_msg)
        await agent.message_queue.put(stop_msg)

        # Mock _should_accept_message 并验证是否被调用
        with patch.object(agent, "_should_accept_message", return_value=False) as mock_check:
            await agent._run_loop()
            # 验证白名单检查被调用
            mock_check.assert_called_once_with(test_msg)


class TestAgentLoopMessageProcessing:
    """测试 Agent 对 LOOP_MESSAGE 的处理差异"""

    @pytest.mark.asyncio
    async def test_run_loop_sends_loop_completion_notification_to_injected_queue(self):
        """LOOP_MESSAGE 完成后向注入的循环完成队列发送完整结果"""
        from datetime import datetime
        from types import SimpleNamespace

        from agents_hub.core.foundation import AgentMessage, MessageType, SessionType

        role = Mock()
        role.get_role_config.return_value = SimpleNamespace(
            name="test_agent",
            role_type=RoleType.TEAM_MEMBER,
            platform=AgentPlatform.CLAUDE,
            work_root=None,
        )
        runtime = Mock()
        runtime.group_chat_id = "group-1"
        agent_info = AgentMemberInfo(main_session="session-1", token="tok_test")
        runtime.state.agent_member_infos = {"test_agent": agent_info}
        runtime.get_agent_member_info.side_effect = runtime.state.agent_member_infos.get
        runtime.repository.group_chat_session_path = "__missing_group_chat_session__"
        runtime.add_message = AsyncMock()
        runtime.save_agent_members = AsyncMock()
        agent_call_manager = Mock()
        agent_call_manager.update_status = AsyncMock()
        agent_call_manager.set_error = AsyncMock()
        message_router = Mock()
        agent = Agent(
            role=role,
            runtime=runtime,
            agent_call_manager=agent_call_manager,
            message_router=message_router,
        )
        completion_queue = asyncio.Queue()
        agent.set_loop_completion_queue(completion_queue)

        result = AgentResult(
            text="loop result",
            session_id="session-1",
            timestamp=datetime.now().isoformat(),
            agent_name="test_agent",
            platform=AgentPlatform.CLAUDE,
            role_type=RoleType.TEAM_MEMBER,
        )

        async def fake_process_message(*args, **kwargs):
            return result

        agent._process_message = fake_process_message
        agent._update_context_usage = AsyncMock()
        agent._auto_compact_if_needed = AsyncMock()

        await agent.message_queue.put(
            AgentMessage(
                call_id="loop-call",
                send_from="loop",
                send_to="test_agent",
                content="loop context",
                session_type=SessionType.MAIN,
                message_type=MessageType.LOOP_MESSAGE,
                metadata={"loop_id": "loop-1"},
            )
        )
        await agent.message_queue.put(
            AgentMessage(
                call_id="__STOP__",
                send_from="__SYSTEM__",
                send_to="test_agent",
                content="__STOP__",
                session_type=SessionType.MAIN,
                message_type=MessageType.NOTIFICATION,
            )
        )

        await agent._run_loop()

        notification = completion_queue.get_nowait()
        assert notification == {
            "loop_id": "loop-1",
            "agent_result": result,
            "call_id": "loop-call",
        }
        runtime.add_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_loop_message_completes_without_group_chat_save(self):
        """LOOP_MESSAGE 完成后不自动保存到群聊历史"""
        from datetime import datetime
        from types import SimpleNamespace

        from agents_hub.core.foundation import AgentMessage, CallStatus, MessageType, SessionType

        role = Mock()
        role.get_role_config.return_value = SimpleNamespace(
            name="test_agent",
            role_type=RoleType.TEAM_MEMBER,
            platform=AgentPlatform.CLAUDE,
            work_root=None,
        )
        runtime = Mock()
        runtime.group_chat_id = "group-1"
        agent_info = AgentMemberInfo(main_session="session-1", token="tok_test")
        runtime.state.agent_member_infos = {"test_agent": agent_info}
        runtime.get_agent_member_info.side_effect = runtime.state.agent_member_infos.get
        runtime.repository.group_chat_session_path = "__missing_group_chat_session__"
        runtime.add_message = AsyncMock()
        runtime.save_agent_members = AsyncMock()
        agent_call_manager = Mock()
        agent_call_manager.update_status = AsyncMock()
        agent_call_manager.set_error = AsyncMock()
        message_router = Mock()
        agent = Agent(
            role=role,
            runtime=runtime,
            agent_call_manager=agent_call_manager,
            message_router=message_router,
        )

        msg = AgentMessage(
            call_id="loop-call",
            send_from="loop",
            send_to="test_agent",
            content="loop context",
            session_type=SessionType.MAIN,
            message_type=MessageType.LOOP_MESSAGE,
            metadata={"loop_id": "loop-1"},
        )

        async def fake_execute(*args, **kwargs):
            return AgentResult(
                text="loop result",
                session_id="session-1",
                timestamp=datetime.now().isoformat(),
                agent_name="test_agent",
                platform=AgentPlatform.CLAUDE,
                role_type=RoleType.TEAM_MEMBER,
            )

        agent.execute = fake_execute

        result = await agent._process_message(msg, "unused prompt")

        assert result.text == "loop result"
        agent_call_manager.update_status.assert_any_await("loop-call", CallStatus.RUNNING)
        agent_call_manager.update_status.assert_any_await("loop-call", CallStatus.COMPLETED)
        runtime.add_message.assert_not_awaited()
