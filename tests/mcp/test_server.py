"""
测试 MCP Server 和 4 个工具

测试覆盖：
1. call_agent: 派活给团队成员
2. assign_tasks_to_team: 覆盖式更新任务列表
3. archive_task_list: 归档当前 ACTIVE 列表
4. check_agent_call: 查询 AgentCall 状态

每个工具测试：
- 正常流程
- 错误场景（INVALID_TOKEN, PERMISSION_DENIED, ...）
- 身份解析和权限校验
- 业务逻辑调用
"""

import asyncio
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
# Test call_agent
# ============================================================================


class TestCallAgent:
    """测试 call_agent 工具"""

    def test_call_agent_success(self, mock_group_chat_manager, mock_group_chat):
        """测试正常调用流程"""
        from agents_hub.mcp.server import call_agent

        # 准备数据
        token = "test_token_123"
        agent_name = "worker1"
        group_chat_id = "group_123"
        send_to = "worker2"
        content = "请帮我完成任务 A"

        # Mock resolve_token
        mock_group_chat_manager.resolve_token.return_value = (agent_name, group_chat_id)

        # Mock get_group_chat
        mock_group_chat_manager.get_group_chat.return_value = mock_group_chat

        # Mock message_router.send_message
        mock_group_chat.message_router.send_message = MagicMock()

        # Mock agent_call_manager.create_call
        mock_call = MagicMock()
        mock_call.call_id = "call_456"
        mock_group_chat.agent_call_manager.create_call.return_value = mock_call

        # 调用
        result = call_agent(
            agent_token=token,
            send_to=send_to,
            content=content,
            need_response=True,
            timeout_seconds=300,
        )

        # 验证
        assert result == {"call_id": "call_456"}
        mock_group_chat_manager.resolve_token.assert_called_once_with(token)
        mock_group_chat_manager.get_group_chat.assert_called_once_with(group_chat_id)
        mock_group_chat.agent_call_manager.create_call.assert_called_once()
        mock_group_chat.message_router.send_message.assert_called_once()

    def test_call_agent_invalid_token(self, mock_group_chat_manager):
        """测试无效 token"""
        from agents_hub.mcp.server import call_agent

        # Mock resolve_token 返回 None
        mock_group_chat_manager.resolve_token.return_value = None

        # 调用
        result = call_agent(
            agent_token="invalid_token",
            send_to="worker2",
            content="test",
            need_response=True,
        )

        # 验证错误响应
        assert "error" in result
        assert result["error"]["code"] == INVALID_TOKEN

    def test_call_agent_group_chat_not_found(self, mock_group_chat_manager):
        """测试群聊不存在"""
        from agents_hub.core.foundation import GroupChatNotFoundError
        from agents_hub.mcp.server import call_agent

        # Mock resolve_token
        mock_group_chat_manager.resolve_token.return_value = ("worker1", "group_123")

        # Mock get_group_chat 抛出异常
        mock_group_chat_manager.get_group_chat.side_effect = GroupChatNotFoundError("group_123")

        # 调用
        result = call_agent(
            agent_token="test_token",
            send_to="worker2",
            content="test",
            need_response=True,
        )

        # 验证错误响应
        assert "error" in result
        assert result["error"]["code"] == GROUP_CHAT_NOT_FOUND

    def test_call_agent_agent_not_found(self, mock_group_chat_manager, mock_group_chat):
        """测试目标 Agent 不存在"""
        from agents_hub.core.foundation import AgentNotFoundError
        from agents_hub.mcp.server import call_agent

        # Mock resolve_token
        mock_group_chat_manager.resolve_token.return_value = ("worker1", "group_123")
        mock_group_chat_manager.get_group_chat.return_value = mock_group_chat

        # Mock message_router.send_message 抛出异常
        mock_group_chat.message_router.send_message.side_effect = AgentNotFoundError("worker2")

        # 调用
        result = call_agent(
            agent_token="test_token",
            send_to="worker2",
            content="test",
            need_response=True,
        )

        # 验证错误响应
        assert "error" in result
        assert result["error"]["code"] == AGENT_NOT_FOUND


# ============================================================================
# Test assign_tasks_to_team
# ============================================================================


class TestAssignTasksToTeam:
    """测试 assign_tasks_to_team 工具"""

    def test_assign_tasks_success(self, mock_group_chat_manager, mock_group_chat):
        """测试正常分配任务"""
        from agents_hub.mcp.server import assign_tasks_to_team

        # 准备数据
        token = "leader_token_123"
        agent_name = "leader"
        group_chat_id = "group_123"
        tasks = [
            {"task_id": "task_1", "owner": "worker1", "content": "任务 1", "status": "pending"},
            {"task_id": "task_2", "owner": "worker2", "content": "任务 2", "status": "pending"},
        ]

        # Mock resolve_token
        mock_group_chat_manager.resolve_token.return_value = (agent_name, group_chat_id)
        mock_group_chat_manager.get_group_chat.return_value = mock_group_chat

        # Mock manager
        mock_manager = MagicMock()
        mock_manager.name = agent_name
        mock_group_chat.manager = mock_manager

        # Mock task_manager.assign_tasks
        mock_group_chat.task_manager.assign_tasks.return_value = {
            "created": 2,
            "updated": 0,
            "unchanged": 0,
        }

        # 调用
        result = assign_tasks_to_team(agent_token=token, tasks=tasks)

        # 验证
        assert result == {"created": 2, "updated": 0, "unchanged": 0}
        mock_group_chat.task_manager.assign_tasks.assert_called_once_with(
            group_chat_id=group_chat_id,
            tasks=tasks,
            created_by=agent_name,
        )

    def test_assign_tasks_invalid_token(self, mock_group_chat_manager):
        """测试无效 token"""
        from agents_hub.mcp.server import assign_tasks_to_team

        # Mock resolve_token 返回 None
        mock_group_chat_manager.resolve_token.return_value = None

        # 调用
        result = assign_tasks_to_team(agent_token="invalid_token", tasks=[])

        # 验证错误响应
        assert "error" in result
        assert result["error"]["code"] == INVALID_TOKEN

    def test_assign_tasks_permission_denied(self, mock_group_chat_manager, mock_group_chat):
        """测试非 Leader 调用"""
        from agents_hub.mcp.server import assign_tasks_to_team

        # Mock resolve_token
        mock_group_chat_manager.resolve_token.return_value = ("worker1", "group_123")
        mock_group_chat_manager.get_group_chat.return_value = mock_group_chat

        # Mock manager (worker1 不是 manager)
        mock_manager = MagicMock()
        mock_manager.name = "leader"
        mock_group_chat.manager = mock_manager

        # 调用
        result = assign_tasks_to_team(agent_token="worker_token", tasks=[])

        # 验证错误响应
        assert "error" in result
        assert result["error"]["code"] == PERMISSION_DENIED


# ============================================================================
# Test archive_task_list
# ============================================================================


class TestArchiveTaskList:
    """测试 archive_task_list 工具"""

    def test_archive_task_list_success(self, mock_group_chat_manager, mock_group_chat):
        """测试正常归档"""
        from agents_hub.mcp.server import archive_task_list

        # 准备数据
        token = "leader_token_123"
        agent_name = "leader"
        group_chat_id = "group_123"

        # Mock resolve_token
        mock_group_chat_manager.resolve_token.return_value = (agent_name, group_chat_id)
        mock_group_chat_manager.get_group_chat.return_value = mock_group_chat

        # Mock manager
        mock_manager = MagicMock()
        mock_manager.name = agent_name
        mock_group_chat.manager = mock_manager

        # Mock task_manager.archive_task_list
        mock_group_chat.task_manager.archive_task_list.return_value = {
            "archived_list_id": "list_123",
            "archived_tasks_count": 5,
        }

        # 调用
        result = archive_task_list(agent_token=token)

        # 验证
        assert result == {"archived_list_id": "list_123", "archived_tasks_count": 5}
        mock_group_chat.task_manager.archive_task_list.assert_called_once_with(
            group_chat_id=group_chat_id,
        )

    def test_archive_task_list_permission_denied(self, mock_group_chat_manager, mock_group_chat):
        """测试非 Leader 调用"""
        from agents_hub.mcp.server import archive_task_list

        # Mock resolve_token
        mock_group_chat_manager.resolve_token.return_value = ("worker1", "group_123")
        mock_group_chat_manager.get_group_chat.return_value = mock_group_chat

        # Mock manager (worker1 不是 manager)
        mock_manager = MagicMock()
        mock_manager.name = "leader"
        mock_group_chat.manager = mock_manager

        # 调用
        result = archive_task_list(agent_token="worker_token")

        # 验证错误响应
        assert "error" in result
        assert result["error"]["code"] == PERMISSION_DENIED


# ============================================================================
# Test check_agent_call
# ============================================================================


class TestCheckAgentCall:
    """测试 check_agent_call 工具"""

    def test_check_agent_call_success(self, mock_group_chat_manager, mock_group_chat):
        """测试正常查询"""
        from agents_hub.mcp.server import check_agent_call

        # 准备数据
        token = "test_token_123"
        agent_name = "worker1"
        group_chat_id = "group_123"
        call_id = "call_456"

        # Mock resolve_token
        mock_group_chat_manager.resolve_token.return_value = (agent_name, group_chat_id)
        mock_group_chat_manager.get_group_chat.return_value = mock_group_chat

        # Mock agent_call_manager.get_call
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

        # 调用
        result = check_agent_call(agent_token=token, call_id=call_id)

        # 验证
        assert result["call_id"] == call_id
        assert result["status"] == CallStatus.COMPLETED.value
        assert result["send_from"] == "worker1"
        assert result["send_to"] == "worker2"
        mock_group_chat.agent_call_manager.get_call.assert_called_once_with(call_id)

    def test_check_agent_call_not_found(self, mock_group_chat_manager, mock_group_chat):
        """测试 AgentCall 不存在"""
        from agents_hub.mcp.server import check_agent_call

        # Mock resolve_token
        mock_group_chat_manager.resolve_token.return_value = ("worker1", "group_123")
        mock_group_chat_manager.get_group_chat.return_value = mock_group_chat

        # Mock agent_call_manager.get_call 返回 None
        mock_group_chat.agent_call_manager.get_call.return_value = None

        # 调用
        result = check_agent_call(agent_token="test_token", call_id="call_456")

        # 验证错误响应
        assert "error" in result
        assert result["error"]["code"] == AGENT_CALL_NOT_FOUND
