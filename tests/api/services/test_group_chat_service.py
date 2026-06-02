import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime

from agents_hub.api.services.group_chat_service import GroupChatService
from agents_hub.api.schemas.group_chats import GroupChatInfo
from agents_hub.exceptions import ValidationError, ResourceNotFoundError, StateError


@pytest.fixture
def mock_group_chat_manager():
    """Mock GroupChatManager"""
    manager = Mock()
    manager.register = Mock()
    return manager


@pytest.fixture
def service(mock_group_chat_manager):
    """创建 GroupChatService 实例"""
    return GroupChatService(mock_group_chat_manager)


async def test_create_group_chat_success(service, mock_group_chat_manager):
    """测试成功创建群聊"""
    # Arrange
    team_members = ["Leader", "Worker1"]
    project_path = "/path/to/project"
    group_chat_name = "Test Group"

    mock_group_chat = Mock()
    mock_group_chat.group_chat_id = "gc_test_123"
    mock_group_chat.start = AsyncMock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = AsyncMock(
        return_value=Mock(
            group_chat_id="gc_test_123",
            group_chat_name="Test Group",
            project_path="/path/to/project",
            created_at=datetime(2026, 6, 3, 10, 0, 0),
            group_type="manager_orchestrate",
        )
    )

    with patch("agents_hub.api.services.group_chat_service.Team") as MockTeam, \
         patch("agents_hub.api.services.group_chat_service.GroupChat") as MockGroupChat, \
         patch("agents_hub.api.services.group_chat_service.generate_group_chat_id", return_value="gc_test_123"):

        MockTeam.return_value = Mock()
        MockGroupChat.return_value = mock_group_chat

        # Act
        result = await service.create_group_chat(team_members, project_path, group_chat_name)

    # Assert
    assert isinstance(result, GroupChatInfo)
    assert result.group_chat_id == "gc_test_123"
    assert result.group_chat_name == "Test Group"
    mock_group_chat.start.assert_called_once()
    mock_group_chat_manager.register.assert_called_once_with("gc_test_123", mock_group_chat)


async def test_create_group_chat_empty_members_raises_validation_error(service):
    """测试空成员列表抛出 ValidationError"""
    with pytest.raises(ValidationError) as exc_info:
        await service.create_group_chat([], "/path/to/project")
    assert "team_members 不能为空" in str(exc_info.value)


async def test_create_group_chat_invalid_role_raises_resource_not_found(service):
    """测试无效角色抛出 ResourceNotFoundError"""
    with patch("agents_hub.api.services.group_chat_service.Team") as MockTeam:
        MockTeam.side_effect = ValueError("错误的role_name InvalidRole")

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.create_group_chat(["InvalidRole"], "/path/to/project")
        assert "InvalidRole" in str(exc_info.value)


async def test_create_group_chat_start_fails_raises_state_error(service, mock_group_chat_manager):
    """测试启动失败抛出 StateError"""
    mock_group_chat = Mock()
    mock_group_chat.start = AsyncMock(side_effect=Exception("启动失败"))

    with patch("agents_hub.api.services.group_chat_service.Team"), \
         patch("agents_hub.api.services.group_chat_service.GroupChat", return_value=mock_group_chat), \
         patch("agents_hub.api.services.group_chat_service.generate_group_chat_id", return_value="gc_test"):

        with pytest.raises(StateError) as exc_info:
            await service.create_group_chat(["Leader"], "/path/to/project")
        assert "群聊启动失败" in str(exc_info.value)
