"""
测试 user_send_message 端点

测试 User 通过前端发送消息给 Agent（不走 MCP）的功能。
"""

import pytest
from fastapi.testclient import TestClient

from agents_hub.api.app import app
from agents_hub.core.orchestration.group_chat_manager import group_chat_manager


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_group_chat(mocker):
    """模拟 GroupChat 实例"""
    mock_gc = mocker.MagicMock()
    mock_gc.message_router = mocker.MagicMock()
    mock_gc.agent_call_manager = mocker.MagicMock()

    # 模拟 create_call 返回一个 call_id
    mock_call = mocker.MagicMock()
    mock_call.call_id = "test-call-id-123"
    mock_call.send_from = "user"
    mock_call.send_to = "TestAgent"
    mock_call.content = "test message"
    mock_call.message_type = mocker.ANY
    mock_gc.agent_call_manager.create_call.return_value = mock_call

    return mock_gc


@pytest.fixture
def setup_group_chat(mock_group_chat):
    """注册测试用的 GroupChat"""
    group_chat_id = "test-group-chat-id"
    # 直接设置到内部字典，绕过类型检查
    group_chat_manager._group_chats[group_chat_id] = mock_group_chat
    yield group_chat_id
    # 清理
    group_chat_manager._group_chats.pop(group_chat_id, None)


class TestUserSendMessage:
    """测试 user_send_message 端点"""

    def test_send_message_success(self, client, setup_group_chat, mock_group_chat):
        """测试正常发送消息"""
        group_chat_id = setup_group_chat

        response = client.post(
            f"/group_chats/{group_chat_id}/send_message",
            json={
                "send_to": "TestAgent",
                "content": "Hello, agent!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "call_id" in data
        assert data["call_id"] == "test-call-id-123"

        # 验证调用了正确的方法
        mock_group_chat.agent_call_manager.create_call.assert_called_once()
        mock_group_chat.message_router.send_message.assert_called_once()

    def test_send_message_group_chat_not_found(self, client):
        """测试 group_chat_id 不存在时返回错误"""
        response = client.post(
            "/group_chats/non-existent-id/send_message",
            json={
                "send_to": "TestAgent",
                "content": "Hello, agent!",
            },
        )

        assert response.status_code == 404
        data = response.json()
        # FastAPI 将错误信息包装在 detail 字段中
        detail = data["detail"]
        assert detail["success"] is False
        assert detail["error_code"] == "GROUP_CHAT_NOT_FOUND"
        assert "non-existent-id" in detail["message"]

    def test_send_message_agent_not_found(self, client, setup_group_chat, mock_group_chat, mocker):
        """测试 send_to agent 不存在时返回错误"""
        from agents_hub.core.foundation import AgentNotFoundError

        group_chat_id = setup_group_chat

        # 模拟 MessageRouter 抛出 AgentNotFoundError
        mock_group_chat.message_router.send_message.side_effect = AgentNotFoundError("NonExistentAgent")

        response = client.post(
            f"/group_chats/{group_chat_id}/send_message",
            json={
                "send_to": "NonExistentAgent",
                "content": "Hello, agent!",
            },
        )

        assert response.status_code == 404
        data = response.json()
        detail = data["detail"]
        assert detail["success"] is False
        assert detail["error_code"] == "AGENT_NOT_FOUND"
        assert "NonExistentAgent" in detail["message"]

    def test_send_message_empty_content(self, client, setup_group_chat, mock_group_chat, mocker):
        """测试空消息内容时返回错误"""
        from agents_hub.core.foundation import InvalidMessageError

        group_chat_id = setup_group_chat

        # 模拟 MessageRouter 抛出 InvalidMessageError
        mock_group_chat.message_router.send_message.side_effect = InvalidMessageError("消息内容不能为空")

        response = client.post(
            f"/group_chats/{group_chat_id}/send_message",
            json={
                "send_to": "TestAgent",
                "content": "",
            },
        )

        assert response.status_code == 400
        data = response.json()
        detail = data["detail"]
        assert detail["success"] is False
        assert detail["error_code"] == "INVALID_MESSAGE"

    def test_send_message_validates_call_creation(self, client, setup_group_chat, mock_group_chat):
        """测试验证 AgentCall 创建时的参数"""
        from agents_hub.core.foundation import MessageType

        group_chat_id = setup_group_chat

        response = client.post(
            f"/group_chats/{group_chat_id}/send_message",
            json={
                "send_to": "TestAgent",
                "content": "Test message",
            },
        )

        assert response.status_code == 200

        # 验证 create_call 的参数
        call_args = mock_group_chat.agent_call_manager.create_call.call_args
        assert call_args.kwargs["send_from"] == "user"
        assert call_args.kwargs["send_to"] == "TestAgent"
        assert call_args.kwargs["content"] == "Test message"
        assert call_args.kwargs["message_type"] == MessageType.TASK

    def test_send_message_validates_message_router_call(self, client, setup_group_chat, mock_group_chat):
        """测试验证 MessageRouter.send_message 的调用"""
        group_chat_id = setup_group_chat

        response = client.post(
            f"/group_chats/{group_chat_id}/send_message",
            json={
                "send_to": "TestAgent",
                "content": "Test message",
            },
        )

        assert response.status_code == 200

        # 验证 send_message 的参数
        call_args = mock_group_chat.message_router.send_message.call_args
        message = call_args.args[0]
        assert message.call_id == "test-call-id-123"
        assert message.send_from == "user"
        assert message.send_to == "TestAgent"
        assert message.content == "test message"
