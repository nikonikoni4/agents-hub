"""
MCP Server 和 6 个工具测试

契约驱动测试：
- call_agent(): 派活给团队成员
- assign_tasks_to_team(): 覆盖式更新任务列表
- archive_task_list(): 归档当前 ACTIVE 列表
- check_agent_call(): 查询 AgentCall 状态
- report_progress(): 在群聊中公开发言
- complete_task(): 结束需要回复的 AgentCall

每个工具测试：
- 正常流程
- 错误场景（INVALID_TOKEN, PERMISSION_DENIED, ...）
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_hub.core.foundation import AgentMessage, CallStatus, MessageType
from agents_hub.mcp import (
    AGENT_CALL_NOT_FOUND,
    AGENT_NOT_FOUND,
    GROUP_CHAT_NOT_FOUND,
    INVALID_AGENT_CALL_STATE,
    INVALID_TOKEN,
    PERMISSION_DENIED,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_group_chat_manager():
    """Mock GroupChatManager"""
    with patch("agents_hub.mcp.server.group_chat_manager") as mock:
        mock.load_group_chat = AsyncMock()
        yield mock


@pytest.fixture
def mock_group_chat():
    """Mock GroupChat 实例"""
    mock = MagicMock()
    mock.message_router = MagicMock()
    mock.send_message_to_agent = AsyncMock()
    mock.task_manager = MagicMock()
    mock.agent_call_manager = MagicMock()
    mock.team = MagicMock()
    mock.group_chat_context.add_message = AsyncMock()
    return mock


# ============================================================================
# call_agent() 测试
# ============================================================================


class TestCallAgent:
    """测试 call_agent 工具"""

    @pytest.mark.asyncio
    async def test_call_agent_success(self, mock_group_chat_manager, mock_group_chat):
        """
        契约：正常调用返回 {"call_id": "..."}

        验证方式：
        1. Mock resolve_token 返回有效身份
        2. Mock load_group_chat 返回 GroupChat
        3. Mock create_call 返回 call_id
        4. 调用 call_agent()
        5. 验证返回 {"call_id": "call_456"}

        如果失败，说明：正常流程逻辑错误
        """
        from agents_hub.mcp.server import call_agent

        token = "test_token_123"
        agent_name = "worker1"
        group_chat_id = "group_123"
        send_to = "worker2"
        content = "请帮我完成任务 A"

        mock_group_chat_manager.resolve_token.return_value = (agent_name, group_chat_id)
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        mock_call = MagicMock()
        mock_call.call_id = "call_456"
        mock_group_chat.agent_call_manager.create_call.return_value = mock_call

        result = await call_agent(
            agent_token=token,
            send_to=send_to,
            content=content,
            need_response=True,
            timeout_seconds=300,
        )

        assert result == {"call_id": "call_456"}
        mock_group_chat_manager.resolve_token.assert_called_once_with(token)
        mock_group_chat_manager.load_group_chat.assert_called_once_with(group_chat_id)
        mock_group_chat.agent_call_manager.create_call.assert_called_once()
        mock_group_chat.send_message_to_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_agent_invalid_token(self, mock_group_chat_manager):
        """
        契约：无效 token 返回 INVALID_TOKEN 错误

        验证方式：
        1. Mock resolve_token 返回 None
        2. 调用 call_agent()
        3. 验证返回 {"error": {"code": "INVALID_TOKEN", ...}}

        如果失败，说明：token 校验逻辑错误
        """
        from agents_hub.mcp.server import call_agent

        mock_group_chat_manager.resolve_token.return_value = None

        result = await call_agent(
            agent_token="invalid_token",
            send_to="worker2",
            content="test",
            need_response=True,
        )

        assert "error" in result
        assert result["error"]["code"] == INVALID_TOKEN

    @pytest.mark.asyncio
    async def test_call_agent_group_chat_not_found(self, mock_group_chat_manager):
        """
        契约：群聊不存在返回 GROUP_CHAT_NOT_FOUND 错误

        验证方式：
        1. Mock resolve_token 返回有效身份
        2. Mock load_group_chat 抛出 GroupChatNotFoundError
        3. 调用 call_agent()
        4. 验证返回 {"error": {"code": "GROUP_CHAT_NOT_FOUND", ...}}

        如果失败，说明：群聊校验逻辑错误
        """
        from agents_hub.core.foundation import GroupChatNotFoundError
        from agents_hub.mcp.server import call_agent

        mock_group_chat_manager.resolve_token.return_value = ("worker1", "group_123")
        mock_group_chat_manager.load_group_chat.side_effect = GroupChatNotFoundError("group_123")

        result = await call_agent(
            agent_token="test_token",
            send_to="worker2",
            content="test",
            need_response=True,
        )

        assert "error" in result
        assert result["error"]["code"] == GROUP_CHAT_NOT_FOUND

    @pytest.mark.asyncio
    async def test_call_agent_agent_not_found(self, mock_group_chat_manager, mock_group_chat):
        """
        契约：Agent 不存在返回 AGENT_NOT_FOUND 错误

        验证方式：
        1. Mock resolve_token 返回有效身份
        2. Mock send_message 抛出 AgentNotFoundError
        3. 调用 call_agent()
        4. 验证返回 {"error": {"code": "AGENT_NOT_FOUND", ...}}

        如果失败，说明：Agent 校验逻辑错误
        """
        from agents_hub.core.foundation import AgentNotFoundError
        from agents_hub.mcp.server import call_agent

        mock_group_chat_manager.resolve_token.return_value = ("worker1", "group_123")
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat
        mock_group_chat.send_message_to_agent.side_effect = AgentNotFoundError("worker2")

        result = await call_agent(
            agent_token="test_token",
            send_to="worker2",
            content="test",
            need_response=True,
        )

        assert "error" in result
        assert result["error"]["code"] == AGENT_NOT_FOUND

    @pytest.mark.asyncio
    async def test_call_agent_notification_type(self, mock_group_chat_manager, mock_group_chat):
        """
        契约：need_response=False 时使用 NOTIFICATION 类型

        验证方式：
        1. Mock resolve_token 返回有效身份
        2. 调用 call_agent(need_response=False)
        3. 验证 create_call 使用 MessageType.NOTIFICATION

        如果失败，说明：消息类型判断逻辑错误
        """
        from agents_hub.mcp.server import call_agent

        mock_group_chat_manager.resolve_token.return_value = ("worker1", "group_123")
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        mock_call = MagicMock()
        mock_call.call_id = "call_789"
        mock_group_chat.agent_call_manager.create_call.return_value = mock_call

        result = await call_agent(
            agent_token="test_token",
            send_to="worker2",
            content="test",
            need_response=False,
        )

        assert result == {"call_id": "call_789"}
        call_args = mock_group_chat.agent_call_manager.create_call.call_args
        assert call_args.kwargs["message_type"] == MessageType.NOTIFICATION


# ============================================================================
# assign_tasks_to_team() 测试
# ============================================================================


class TestAssignTasksToTeam:
    """测试 assign_tasks_to_team 工具"""

    @pytest.mark.asyncio
    async def test_assign_tasks_success(self, mock_group_chat_manager, mock_group_chat):
        """
        契约：Leader 调用返回 {created, updated, unchanged}

        验证方式：
        1. Mock resolve_token 返回 Leader 身份
        2. Mock manager.name 匹配 agent_name
        3. Mock assign_tasks 返回统计结果
        4. 调用 assign_tasks_to_team()
        5. 验证返回正确的统计

        如果失败，说明：Leader 权限校验或任务分配逻辑错误
        """
        from agents_hub.mcp.server import assign_tasks_to_team

        token = "leader_token_123"
        agent_name = "leader"
        group_chat_id = "group_123"
        tasks = [
            {"task_id": "task_1", "owner": "worker1", "content": "任务 1", "status": "pending"},
            {"task_id": "task_2", "owner": "worker2", "content": "任务 2", "status": "pending"},
        ]

        mock_group_chat_manager.resolve_token.return_value = (agent_name, group_chat_id)
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        mock_manager = MagicMock()
        mock_manager.name = agent_name
        mock_group_chat.manager = mock_manager

        mock_group_chat.task_manager.assign_tasks.return_value = {
            "created": 2,
            "updated": 0,
            "unchanged": 0,
        }

        result = await assign_tasks_to_team(agent_token=token, tasks=tasks)

        assert result == {"created": 2, "updated": 0, "unchanged": 0}
        mock_group_chat.task_manager.assign_tasks.assert_called_once_with(
            group_chat_id=group_chat_id,
            tasks=tasks,
            created_by=agent_name,
        )

    @pytest.mark.asyncio
    async def test_assign_tasks_invalid_token(self, mock_group_chat_manager):
        """
        契约：无效 token 返回 INVALID_TOKEN 错误
        """
        from agents_hub.mcp.server import assign_tasks_to_team

        mock_group_chat_manager.resolve_token.return_value = None

        result = await assign_tasks_to_team(agent_token="invalid_token", tasks=[])

        assert "error" in result
        assert result["error"]["code"] == INVALID_TOKEN

    @pytest.mark.asyncio
    async def test_assign_tasks_permission_denied(self, mock_group_chat_manager, mock_group_chat):
        """
        契约：非 Leader 调用返回 PERMISSION_DENIED 错误
        """
        from agents_hub.mcp.server import assign_tasks_to_team

        mock_group_chat_manager.resolve_token.return_value = ("worker1", "group_123")
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        mock_manager = MagicMock()
        mock_manager.name = "leader"
        mock_group_chat.manager = mock_manager

        result = await assign_tasks_to_team(agent_token="worker_token", tasks=[])

        assert "error" in result
        assert result["error"]["code"] == PERMISSION_DENIED


# ============================================================================
# archive_task_list() 测试
# ============================================================================


class TestArchiveTaskList:
    """测试 archive_task_list 工具"""

    @pytest.mark.asyncio
    async def test_archive_task_list_success(self, mock_group_chat_manager, mock_group_chat):
        """
        契约：Leader 调用返回归档结果
        """
        from agents_hub.mcp.server import archive_task_list

        token = "leader_token_123"
        agent_name = "leader"
        group_chat_id = "group_123"

        mock_group_chat_manager.resolve_token.return_value = (agent_name, group_chat_id)
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        mock_manager = MagicMock()
        mock_manager.name = agent_name
        mock_group_chat.manager = mock_manager

        mock_group_chat.task_manager.archive_task_list.return_value = {
            "archived_list_id": "list_123",
            "archived_tasks_count": 5,
        }

        result = await archive_task_list(agent_token=token)

        assert result == {"archived_list_id": "list_123", "archived_tasks_count": 5}
        mock_group_chat.task_manager.archive_task_list.assert_called_once_with(
            group_chat_id=group_chat_id,
        )

    @pytest.mark.asyncio
    async def test_archive_task_list_invalid_token(self, mock_group_chat_manager):
        """
        契约：无效 token 返回 INVALID_TOKEN 错误
        """
        from agents_hub.mcp.server import archive_task_list

        mock_group_chat_manager.resolve_token.return_value = None

        result = await archive_task_list(agent_token="invalid_token")

        assert "error" in result
        assert result["error"]["code"] == INVALID_TOKEN

    @pytest.mark.asyncio
    async def test_archive_task_list_permission_denied(
        self, mock_group_chat_manager, mock_group_chat
    ):
        """
        契约：非 Leader 调用返回 PERMISSION_DENIED 错误
        """
        from agents_hub.mcp.server import archive_task_list

        mock_group_chat_manager.resolve_token.return_value = ("worker1", "group_123")
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        mock_manager = MagicMock()
        mock_manager.name = "leader"
        mock_group_chat.manager = mock_manager

        result = await archive_task_list(agent_token="worker_token")

        assert "error" in result
        assert result["error"]["code"] == PERMISSION_DENIED


# ============================================================================
# check_agent_call() 测试
# ============================================================================


class TestCheckAgentCall:
    """测试 check_agent_call 工具"""

    @pytest.mark.asyncio
    async def test_check_agent_call_success(self, mock_group_chat_manager, mock_group_chat):
        """
        契约：正常查询返回 call 状态信息
        """
        from agents_hub.mcp.server import check_agent_call

        token = "test_token_123"
        agent_name = "worker1"
        group_chat_id = "group_123"
        call_id = "call_456"

        mock_group_chat_manager.resolve_token.return_value = (agent_name, group_chat_id)
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        mock_call = MagicMock()
        mock_call.call_id = call_id
        mock_call.status = CallStatus.COMPLETED
        mock_call.send_from = "worker1"
        mock_call.send_to = "worker2"
        mock_call.content = "test content"
        mock_call.message_type = MessageType.TASK
        mock_call.has_agent_response = True
        mock_call.result = MagicMock()
        mock_call.result.content = "result content"
        mock_call.error = None
        mock_group_chat.agent_call_manager.get_call.return_value = mock_call

        result = await check_agent_call(agent_token=token, call_id=call_id)

        assert result["call_id"] == call_id
        assert result["status"] == CallStatus.COMPLETED.value
        assert result["send_from"] == "worker1"
        assert result["send_to"] == "worker2"
        assert result["has_agent_response"] is True
        mock_group_chat.agent_call_manager.get_call.assert_called_once_with(call_id)

    @pytest.mark.asyncio
    async def test_check_agent_call_invalid_token(self, mock_group_chat_manager):
        """
        契约：无效 token 返回 INVALID_TOKEN 错误
        """
        from agents_hub.mcp.server import check_agent_call

        mock_group_chat_manager.resolve_token.return_value = None

        result = await check_agent_call(agent_token="invalid_token", call_id="call_456")

        assert "error" in result
        assert result["error"]["code"] == INVALID_TOKEN

    @pytest.mark.asyncio
    async def test_check_agent_call_not_found(self, mock_group_chat_manager, mock_group_chat):
        """
        契约：call 不存在返回 AGENT_CALL_NOT_FOUND 错误
        """
        from agents_hub.mcp.server import check_agent_call

        mock_group_chat_manager.resolve_token.return_value = ("worker1", "group_123")
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat
        mock_group_chat.agent_call_manager.get_call.return_value = None

        result = await check_agent_call(agent_token="test_token", call_id="call_456")

        assert "error" in result
        assert result["error"]["code"] == AGENT_CALL_NOT_FOUND


# ============================================================================
# report_progress() 测试
# ============================================================================


class TestSpeakInGroupChat:
    """测试 report_progress 工具"""

    @pytest.mark.asyncio
    async def test_report_progress_broadcasts_refresh(
        self, mock_group_chat_manager, mock_group_chat
    ):
        """契约：公开发言写入群聊后广播 refresh 信号"""
        from agents_hub.mcp.server import report_progress

        token = "worker_token"
        worker_name = "worker1"
        group_chat_id = "group_123"

        mock_group_chat_manager.resolve_token.return_value = (worker_name, group_chat_id)
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        with patch(
            "agents_hub.mcp.server.broadcast_group_chat_refresh",
            new=AsyncMock(),
            create=True,
        ) as mock_broadcast:
            result = await report_progress(
                agent_token=token,
                content="我完成了一部分",
            )

        assert result == {"ok": True}
        mock_group_chat.group_chat_context.add_message.assert_called_once()
        mock_broadcast.assert_awaited_once_with(group_chat_id)


# ============================================================================
# complete_task() 测试
# ============================================================================


class TestFinishAgentCall:
    """测试 complete_task 工具"""

    @pytest.mark.asyncio
    async def test_complete_task_success(self, mock_group_chat_manager, mock_group_chat):
        """契约：TASK 接收者结束调用后，系统向原调用方投递完成通知"""
        from agents_hub.mcp.server import complete_task

        token = "worker_token"
        worker_name = "worker1"
        group_chat_id = "group_123"
        call_id = "call_456"
        response_call_id = "call_response"

        mock_group_chat_manager.resolve_token.return_value = (worker_name, group_chat_id)
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        mock_call = MagicMock()
        mock_call.call_id = call_id
        mock_call.send_from = "Leader"
        mock_call.send_to = worker_name
        mock_call.message_type = MessageType.TASK
        mock_call.has_agent_response = False
        mock_group_chat.agent_call_manager.get_call.return_value = mock_call
        mock_response_call = MagicMock()
        mock_response_call.call_id = response_call_id
        mock_group_chat.agent_call_manager.create_call.return_value = mock_response_call

        with patch(
            "agents_hub.mcp.server.broadcast_group_chat_refresh",
            new=AsyncMock(),
            create=True,
        ) as mock_broadcast:
            result = await complete_task(
                agent_token=token,
                call_id=call_id,
                content="任务已完成",
                success=True,
            )

        assert result == {"call_id": call_id, "status": CallStatus.COMPLETED.value}
        mock_group_chat.agent_call_manager.mark_agent_response.assert_called_once_with(
            call_id=call_id,
            content="任务已完成",
            success=True,
        )
        mock_group_chat.agent_call_manager.create_call.assert_called_once_with(
            send_from=worker_name,
            send_to="Leader",
            content="任务已完成",
            message_type=MessageType.NOTIFICATION,
            timeout_seconds=None,
        )
        mock_group_chat.send_message_to_agent.assert_called_once()
        sent_message = mock_group_chat.send_message_to_agent.call_args.args[0]
        assert isinstance(sent_message, AgentMessage)
        assert sent_message.call_id == response_call_id
        assert sent_message.send_from == worker_name
        assert sent_message.send_to == "Leader"
        assert sent_message.content == "任务已完成"
        assert sent_message.message_type == MessageType.NOTIFICATION
        mock_group_chat.group_chat_context.add_message.assert_not_called()
        mock_broadcast.assert_awaited_once_with(group_chat_id)

    @pytest.mark.asyncio
    async def test_complete_task_redacts_completion_notification(
        self, mock_group_chat_manager, mock_group_chat
    ):
        """契约：完成通知和原调用结果都使用脱敏后的内容"""
        from agents_hub.mcp.server import complete_task

        token = "worker_token"
        worker_name = "worker1"
        group_chat_id = "group_123"

        mock_group_chat_manager.resolve_token.return_value = (worker_name, group_chat_id)
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        mock_call = MagicMock()
        mock_call.call_id = "call_456"
        mock_call.send_from = "worker2"
        mock_call.send_to = worker_name
        mock_call.message_type = MessageType.TASK
        mock_call.has_agent_response = False
        mock_group_chat.agent_call_manager.get_call.return_value = mock_call

        mock_response_call = MagicMock()
        mock_response_call.call_id = "call_response"
        mock_group_chat.agent_call_manager.create_call.return_value = mock_response_call

        await complete_task(
            agent_token=token,
            call_id="call_456",
            content="完成了，token=tok_0123456789abcdef0123456789abcdef",
            success=True,
        )

        mock_group_chat.agent_call_manager.mark_agent_response.assert_called_once()
        safe_content = mock_group_chat.agent_call_manager.mark_agent_response.call_args.kwargs[
            "content"
        ]
        assert "tok_0123456789abcdef0123456789abcdef" not in safe_content
        assert "[REDACTED]" in safe_content

        mock_group_chat.agent_call_manager.create_call.assert_called_once()
        assert (
            mock_group_chat.agent_call_manager.create_call.call_args.kwargs["content"]
            == safe_content
        )
        sent_message = mock_group_chat.send_message_to_agent.call_args.args[0]
        assert sent_message.send_from == worker_name
        assert sent_message.send_to == "worker2"
        assert sent_message.content == safe_content

    @pytest.mark.asyncio
    async def test_complete_task_to_user_writes_group_chat_message(
        self, mock_group_chat_manager, mock_group_chat
    ):
        """契约：原调用方是 user 时，完成结果写入群聊并由 refresh 暴露给前端"""
        from agents_hub.mcp.server import complete_task

        worker_name = "worker1"
        group_chat_id = "group_123"
        mock_group_chat_manager.resolve_token.return_value = (worker_name, group_chat_id)
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        mock_call = MagicMock()
        mock_call.call_id = "call_456"
        mock_call.send_from = "Alice"
        mock_call.send_to = worker_name
        mock_call.message_type = MessageType.TASK
        mock_call.has_agent_response = False
        mock_group_chat.agent_call_manager.get_call.return_value = mock_call

        with (
            patch("agents_hub.mcp.server.config") as mock_config,
            patch(
                "agents_hub.mcp.server.broadcast_group_chat_refresh",
                new=AsyncMock(),
                create=True,
            ) as mock_broadcast,
        ):
            mock_config.is_user_name.return_value = True
            result = await complete_task(
                agent_token="worker_token",
                call_id="call_456",
                content="用户任务完成，token=tok_0123456789abcdef0123456789abcdef",
                success=True,
            )

        mock_config.is_user_name.assert_called_once_with("Alice")
        assert result == {"call_id": "call_456", "status": CallStatus.COMPLETED.value}
        mock_group_chat.agent_call_manager.mark_agent_response.assert_called_once()
        mock_group_chat.agent_call_manager.create_call.assert_not_called()
        mock_group_chat.send_message_to_agent.assert_not_called()
        mock_group_chat.group_chat_context.add_message.assert_awaited_once()
        agent_result = mock_group_chat.group_chat_context.add_message.call_args.args[0]
        assert agent_result.agent_name == worker_name
        assert agent_result.text == "@Alice 用户任务完成，token=[REDACTED]"
        mock_broadcast.assert_awaited_once_with(group_chat_id)

    @pytest.mark.asyncio
    async def test_complete_task_rejects_notification(
        self, mock_group_chat_manager, mock_group_chat
    ):
        """契约：NOTIFICATION 不需要回复，调用 complete_task 返回状态错误"""
        from agents_hub.mcp.server import complete_task

        mock_group_chat_manager.resolve_token.return_value = ("worker1", "group_123")
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        mock_call = MagicMock()
        mock_call.call_id = "call_456"
        mock_call.send_from = "Leader"
        mock_call.send_to = "worker1"
        mock_call.message_type = MessageType.NOTIFICATION
        mock_call.has_agent_response = False
        mock_group_chat.agent_call_manager.get_call.return_value = mock_call

        result = await complete_task(
            agent_token="worker_token",
            call_id="call_456",
            content="不应该回复",
            success=True,
        )

        assert "error" in result
        assert result["error"]["code"] == INVALID_AGENT_CALL_STATE
        mock_group_chat.agent_call_manager.mark_agent_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_complete_task_rejects_non_receiver(
        self, mock_group_chat_manager, mock_group_chat
    ):
        """契约：只有 call 的接收者可以结束该调用"""
        from agents_hub.mcp.server import complete_task

        mock_group_chat_manager.resolve_token.return_value = ("other_worker", "group_123")
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        mock_call = MagicMock()
        mock_call.call_id = "call_456"
        mock_call.send_from = "Leader"
        mock_call.send_to = "worker1"
        mock_call.message_type = MessageType.TASK
        mock_call.has_agent_response = False
        mock_group_chat.agent_call_manager.get_call.return_value = mock_call

        result = await complete_task(
            agent_token="other_token",
            call_id="call_456",
            content="越权回复",
            success=True,
        )

        assert "error" in result
        assert result["error"]["code"] == PERMISSION_DENIED
        mock_group_chat.agent_call_manager.mark_agent_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_complete_task_rejects_already_finished(
        self, mock_group_chat_manager, mock_group_chat
    ):
        """契约：已经显式回复闭环的 call 不能重复 finish"""
        from agents_hub.mcp.server import complete_task

        mock_group_chat_manager.resolve_token.return_value = ("worker1", "group_123")
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        mock_call = MagicMock()
        mock_call.call_id = "call_456"
        mock_call.send_from = "Leader"
        mock_call.send_to = "worker1"
        mock_call.message_type = MessageType.TASK
        mock_call.has_agent_response = True
        mock_group_chat.agent_call_manager.get_call.return_value = mock_call

        result = await complete_task(
            agent_token="worker_token",
            call_id="call_456",
            content="重复回复",
            success=True,
        )

        assert "error" in result
        assert result["error"]["code"] == INVALID_AGENT_CALL_STATE
        mock_group_chat.agent_call_manager.mark_agent_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_complete_task_with_web_preview(self, mock_group_chat_manager, mock_group_chat):
        """
        契约：传入 web_preview_url 时，写入群聊的消息包含 web_preview 字段

        验证方式：
        1. Mock user 调用方的 complete_task
        2. 传入 web_preview_url 和 web_preview_title
        3. 验证 AgentResult 包含 web_preview dict

        如果失败，说明：complete_task 未将 web_preview 传递到 AgentResult
        """
        from agents_hub.mcp.server import complete_task

        worker_name = "worker1"
        group_chat_id = "group_123"
        mock_group_chat_manager.resolve_token.return_value = (worker_name, group_chat_id)
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        mock_call = MagicMock()
        mock_call.call_id = "call_456"
        mock_call.send_from = "Alice"
        mock_call.send_to = worker_name
        mock_call.message_type = MessageType.TASK
        mock_call.has_agent_response = False
        mock_group_chat.agent_call_manager.get_call.return_value = mock_call

        with (
            patch("agents_hub.mcp.server.config") as mock_config,
            patch(
                "agents_hub.mcp.server.broadcast_group_chat_refresh",
                new=AsyncMock(),
                create=True,
            ),
        ):
            mock_config.is_user_name.return_value = True
            result = await complete_task(
                agent_token="worker_token",
                call_id="call_456",
                content="网页已生成",
                success=True,
                web_preview_url="http://localhost:3000",
                web_preview_title="我的网页",
            )

        assert result == {"call_id": "call_456", "status": CallStatus.COMPLETED.value}
        mock_group_chat.group_chat_context.add_message.assert_awaited_once()
        agent_result = mock_group_chat.group_chat_context.add_message.call_args.args[0]
        assert agent_result.web_preview is not None
        assert agent_result.web_preview["url"] == "http://localhost:3000"
        assert agent_result.web_preview["title"] == "我的网页"

    @pytest.mark.asyncio
    async def test_complete_task_without_web_preview(
        self, mock_group_chat_manager, mock_group_chat
    ):
        """
        契约：不传 web_preview_url 时，AgentResult.web_preview 为 None

        验证方式：
        1. Mock user 调用方的 complete_task
        2. 不传 web_preview 参数
        3. 验证 AgentResult.web_preview 为 None

        如果失败，说明：web_preview 在未传入时未正确设为 None
        """
        from agents_hub.mcp.server import complete_task

        worker_name = "worker1"
        group_chat_id = "group_123"
        mock_group_chat_manager.resolve_token.return_value = (worker_name, group_chat_id)
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        mock_call = MagicMock()
        mock_call.call_id = "call_456"
        mock_call.send_from = "Alice"
        mock_call.send_to = worker_name
        mock_call.message_type = MessageType.TASK
        mock_call.has_agent_response = False
        mock_group_chat.agent_call_manager.get_call.return_value = mock_call

        with (
            patch("agents_hub.mcp.server.config") as mock_config,
            patch(
                "agents_hub.mcp.server.broadcast_group_chat_refresh",
                new=AsyncMock(),
                create=True,
            ),
        ):
            mock_config.is_user_name.return_value = True
            result = await complete_task(
                agent_token="worker_token",
                call_id="call_456",
                content="任务完成",
                success=True,
            )

        assert result == {"call_id": "call_456", "status": CallStatus.COMPLETED.value}
        agent_result = mock_group_chat.group_chat_context.add_message.call_args.args[0]
        assert agent_result.web_preview is None
