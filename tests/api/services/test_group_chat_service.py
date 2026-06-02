import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime
from pathlib import Path

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


# Task 4: load_group_chat 测试

async def test_load_group_chat_already_in_memory(service, mock_group_chat_manager):
    """测试加载已在内存中的群聊（幂等性）"""
    # Arrange
    group_chat_id = "gc_existing"
    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = AsyncMock(
        return_value=Mock(
            group_chat_id=group_chat_id,
            group_chat_name="Existing Group",
            project_path="/path/to/project",
            created_at=datetime(2026, 6, 3, 10, 0, 0),
            group_type="manager_orchestrate",
        )
    )
    mock_group_chat_manager.get_group_chat.return_value = mock_group_chat

    # Act
    result = await service.load_group_chat(group_chat_id)

    # Assert
    assert isinstance(result, GroupChatInfo)
    assert result.group_chat_id == group_chat_id
    assert result.is_active is True
    mock_group_chat_manager.get_group_chat.assert_called_once_with(group_chat_id)


async def test_load_group_chat_from_disk(service, mock_group_chat_manager):
    """测试从磁盘加载群聊"""
    # Arrange
    group_chat_id = "gc_from_disk"
    mock_group_chat_manager.get_group_chat.return_value = None  # 不在内存

    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = AsyncMock(
        return_value=Mock(
            group_chat_id=group_chat_id,
            group_chat_name="Loaded Group",
            project_path="/path/to/project",
            created_at=datetime(2026, 6, 3, 10, 0, 0),
            group_type="manager_orchestrate",
        )
    )
    mock_group_chat_manager.load_group_chat_from_disk = AsyncMock(return_value=mock_group_chat)

    # Act
    result = await service.load_group_chat(group_chat_id)

    # Assert
    assert isinstance(result, GroupChatInfo)
    assert result.group_chat_id == group_chat_id
    assert result.is_active is True
    mock_group_chat_manager.load_group_chat_from_disk.assert_called_once_with(group_chat_id)


async def test_load_group_chat_not_found_raises_error(service, mock_group_chat_manager):
    """测试加载不存在的群聊抛出异常"""
    # Arrange
    mock_group_chat_manager.get_group_chat.return_value = None
    mock_group_chat_manager.load_group_chat_from_disk = AsyncMock(side_effect=FileNotFoundError("群聊不存在"))

    # Act & Assert
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await service.load_group_chat("gc_nonexistent")
    assert "群聊不存在" in str(exc_info.value)


# Task 5: delete_group_chat 测试

async def test_delete_group_chat_keep_data(service, mock_group_chat_manager):
    """测试删除群聊但保留数据"""
    # Arrange
    group_chat_id = "gc_to_delete"
    mock_group_chat_manager.unregister = AsyncMock()

    # Act
    await service.delete_group_chat(group_chat_id, keep_data=True)

    # Assert
    mock_group_chat_manager.unregister.assert_called_once_with(group_chat_id)


async def test_delete_group_chat_with_data(service, mock_group_chat_manager):
    """测试完全删除群聊（内存+磁盘）"""
    # Arrange
    group_chat_id = "gc_to_delete_full"
    project_path = "/path/to/project"

    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = AsyncMock(
        return_value=Mock(project_path=project_path)
    )
    mock_group_chat_manager.get_group_chat.return_value = mock_group_chat
    mock_group_chat_manager.unregister = AsyncMock()

    with patch("agents_hub.api.services.group_chat_service.group_chat_paths") as mock_paths, \
         patch("agents_hub.api.services.group_chat_service.Path") as MockPath, \
         patch("shutil.rmtree") as mock_rmtree:
        # Mock Path 对象
        mock_dir = Mock()
        mock_dir.exists.return_value = True
        MockPath.return_value = mock_dir

        mock_paths.base_dir.return_value = "/path/to/group_chats/gc_to_delete_full"

        # Act
        await service.delete_group_chat(group_chat_id, keep_data=False)

        # Assert
        mock_group_chat_manager.get_group_chat.assert_called_once()
        mock_group_chat_manager.unregister.assert_called_once_with(group_chat_id)
        mock_paths.base_dir.assert_called_once_with(group_chat_id, project_path)
        mock_rmtree.assert_called_once_with(mock_dir)


async def test_delete_group_chat_from_disk_when_not_in_memory(service, mock_group_chat_manager):
    """测试删除不在内存中的群聊（无法获取 project_path，不删除磁盘）"""
    # Arrange
    group_chat_id = "gc_disk_delete"
    mock_group_chat_manager.get_group_chat.return_value = None  # 不在内存
    mock_group_chat_manager.unregister = AsyncMock()

    # Act
    await service.delete_group_chat(group_chat_id, keep_data=False)

    # Assert
    mock_group_chat_manager.unregister.assert_called_once_with(group_chat_id)


async def test_delete_group_chat_idempotent(service, mock_group_chat_manager):
    """测试删除不存在的群聊是幂等的（不抛异常）"""
    # Arrange
    mock_group_chat_manager.get_group_chat.return_value = None
    mock_group_chat_manager.unregister = AsyncMock()

    # Act & Assert - 不应抛异常
    await service.delete_group_chat("gc_nonexistent", keep_data=False)
    mock_group_chat_manager.unregister.assert_called_once()


async def test_delete_group_chat_file_deletion_fails(service, mock_group_chat_manager):
    """测试文件删除失败抛出 ExternalServiceError"""
    # Arrange
    from agents_hub.exceptions import ExternalServiceError

    group_chat_id = "gc_delete_fail"
    project_path = "/path"

    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = AsyncMock(
        return_value=Mock(project_path=project_path)
    )
    mock_group_chat_manager.get_group_chat.return_value = mock_group_chat
    mock_group_chat_manager.unregister = AsyncMock()

    with patch("agents_hub.api.services.group_chat_service.group_chat_paths") as mock_paths, \
         patch("agents_hub.api.services.group_chat_service.Path") as MockPath, \
         patch("shutil.rmtree", side_effect=PermissionError("权限不足")):
        # Mock Path 对象
        mock_dir = Mock()
        mock_dir.exists.return_value = True
        MockPath.return_value = mock_dir

        mock_paths.base_dir.return_value = "/path/to/group_chats/gc_delete_fail"

        # Act & Assert
        with pytest.raises(ExternalServiceError) as exc_info:
            await service.delete_group_chat(group_chat_id, keep_data=False)
        assert "文件删除失败" in str(exc_info.value)


# Task 6: list_group_chats 测试

async def test_list_group_chats_returns_all(service, mock_group_chat_manager):
    """测试列出所有群聊"""
    # Arrange
    from agents_hub.core.context.group_metadata import GroupMetadata
    from agents_hub.api.schemas.group_chats import GroupChatSummary

    mock_metadata_list = [
        GroupMetadata(
            group_chat_id="gc_1",
            group_chat_name="Group 1",
            project_path="/path/1",
            created_at=datetime(2026, 6, 1, 10, 0, 0),
            group_type="manager_orchestrate",
        ),
        GroupMetadata(
            group_chat_id="gc_2",
            group_chat_name="Group 2",
            project_path="/path/2",
            created_at=datetime(2026, 6, 2, 10, 0, 0),
            group_type="manager_orchestrate",
        ),
    ]
    mock_group_chat_manager.list_all_group_chats.return_value = mock_metadata_list
    mock_group_chat_manager.get_group_chat.side_effect = [Mock(), None]  # gc_1 活跃，gc_2 非活跃

    # Act
    result = await service.list_group_chats(is_active_only=False)

    # Assert
    assert len(result) == 2
    assert result[0].group_chat_id == "gc_1"
    assert result[0].is_active is True
    assert result[1].group_chat_id == "gc_2"
    assert result[1].is_active is False


async def test_list_group_chats_active_only(service, mock_group_chat_manager):
    """测试只列出活跃群聊"""
    # Arrange
    from agents_hub.core.context.group_metadata import GroupMetadata

    mock_metadata_list = [
        GroupMetadata(
            group_chat_id="gc_active",
            group_chat_name="Active Group",
            project_path="/path/active",
            created_at=datetime(2026, 6, 1, 10, 0, 0),
            group_type="manager_orchestrate",
        ),
        GroupMetadata(
            group_chat_id="gc_inactive",
            group_chat_name="Inactive Group",
            project_path="/path/inactive",
            created_at=datetime(2026, 6, 2, 10, 0, 0),
            group_type="manager_orchestrate",
        ),
    ]
    mock_group_chat_manager.list_all_group_chats.return_value = mock_metadata_list
    mock_group_chat_manager.get_group_chat.side_effect = [Mock(), None]

    # Act
    result = await service.list_group_chats(is_active_only=True)

    # Assert
    assert len(result) == 1
    assert result[0].group_chat_id == "gc_active"
    assert result[0].is_active is True


async def test_list_group_chats_empty(service, mock_group_chat_manager):
    """测试没有群聊时返回空列表"""
    # Arrange
    mock_group_chat_manager.list_all_group_chats.return_value = []

    # Act
    result = await service.list_group_chats()

    # Assert
    assert result == []


# Task 7: get_group_chat_info 测试

async def test_get_group_chat_info_from_memory(service, mock_group_chat_manager):
    """测试从内存获取群聊信息"""
    # Arrange
    group_chat_id = "gc_memory"
    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = AsyncMock(
        return_value=Mock(
            group_chat_id=group_chat_id,
            group_chat_name="Memory Group",
            project_path="/path/to/project",
            created_at=datetime(2026, 6, 3, 10, 0, 0),
            group_type="manager_orchestrate",
        )
    )
    mock_group_chat_manager.get_group_chat.return_value = mock_group_chat

    # Act
    result = await service.get_group_chat_info(group_chat_id)

    # Assert
    assert result.group_chat_id == group_chat_id
    assert result.is_active is True
    mock_group_chat_manager.get_group_chat.assert_called_once_with(group_chat_id)


async def test_get_group_chat_info_from_disk(service, mock_group_chat_manager):
    """测试从磁盘获取群聊信息"""
    # Arrange
    group_chat_id = "gc_disk"
    mock_group_chat_manager.get_group_chat.return_value = None  # 不在内存

    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = AsyncMock(
        return_value=Mock(
            group_chat_id=group_chat_id,
            group_chat_name="Disk Group",
            project_path="/path/to/project",
            created_at=datetime(2026, 6, 3, 10, 0, 0),
            group_type="manager_orchestrate",
        )
    )
    mock_group_chat_manager.load_group_chat_from_disk = AsyncMock(return_value=mock_group_chat)

    # Act
    result = await service.get_group_chat_info(group_chat_id)

    # Assert
    assert result.group_chat_id == group_chat_id
    assert result.is_active is False  # 从磁盘加载，非活跃
    mock_group_chat_manager.load_group_chat_from_disk.assert_called_once_with(group_chat_id)


async def test_get_group_chat_info_not_found(service, mock_group_chat_manager):
    """测试获取不存在的群聊信息"""
    # Arrange
    mock_group_chat_manager.get_group_chat.return_value = None
    mock_group_chat_manager.load_group_chat_from_disk = AsyncMock(side_effect=FileNotFoundError("不存在"))

    # Act & Assert
    with pytest.raises(ResourceNotFoundError):
        await service.get_group_chat_info("gc_nonexistent")
