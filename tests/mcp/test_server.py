"""
MCP Server 和 4 个工具测试

契约驱动测试：
- call_agent(): 派活给团队成员
- assign_tasks_to_team(): 覆盖式更新任务列表
- archive_task_list(): 归档当前 ACTIVE 列表
- check_agent_call(): 查询 AgentCall 状态

每个工具测试：
- 正常流程
- 错误场景（INVALID_TOKEN, PERMISSION_DENIED, ...）
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_hub.core.foundation import CallStatus, MessageType
from agents_hub.mcp import (
    AGENT_CALL_NOT_FOUND,
    AGENT_NOT_FOUND,
    GROUP_CHAT_NOT_FOUND,
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
    mock.task_manager = MagicMock()
    mock.agent_call_manager = MagicMock()
    mock.team = MagicMock()
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
        mock_group_chat.message_router.send_message.assert_called_once()

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
        mock_group_chat.message_router.send_message.side_effect = AgentNotFoundError("worker2")

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
    async def test_archive_task_list_permission_denied(self, mock_group_chat_manager, mock_group_chat):
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
        mock_call.result = MagicMock()
        mock_call.result.content = "result content"
        mock_call.error = None
        mock_group_chat.agent_call_manager.get_call.return_value = mock_call

        result = await check_agent_call(agent_token=token, call_id=call_id)

        assert result["call_id"] == call_id
        assert result["status"] == CallStatus.COMPLETED.value
        assert result["send_from"] == "worker1"
        assert result["send_to"] == "worker2"
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
