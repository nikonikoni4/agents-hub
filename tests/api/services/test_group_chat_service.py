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
    mock_group_chat._activated = True
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
         patch("agents_hub.api.services.group_chat_service.uuid4", return_value="gc_test_123"):

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
         patch("agents_hub.api.services.group_chat_service.uuid4", return_value="gc_test"):

        with pytest.raises(StateError) as exc_info:
            await service.create_group_chat(["Leader"], "/path/to/project")
        assert "群聊启动失败" in str(exc_info.value)


# Task 4: load_group_chat 测试

async def test_load_group_chat_already_in_memory(service, mock_group_chat_manager):
    """测试加载已在内存中的群聊（幂等性）"""
    # Arrange
    group_chat_id = "gc_existing"
    mock_group_chat = Mock()
    mock_group_chat._activated = True
    mock_group_chat.group_chat_context.repository.load_group_metadata = AsyncMock(
        return_value=Mock(
            group_chat_id=group_chat_id,
            group_chat_name="Existing Group",
            project_path="/path/to/project",
            created_at=datetime(2026, 6, 3, 10, 0, 0),
            group_type="manager_orchestrate",
        )
    )
    mock_group_chat_manager.load_group_chat = AsyncMock(return_value=mock_group_chat)

    # Act
    result = await service.load_group_chat(group_chat_id)

    # Assert
    assert isinstance(result, GroupChatInfo)
    assert result.group_chat_id == group_chat_id
    assert result.is_active is True
    mock_group_chat_manager.load_group_chat.assert_called_once_with(group_chat_id)


async def test_load_group_chat_from_disk(service, mock_group_chat_manager):
    """测试从磁盘加载群聊"""
    # Arrange
    group_chat_id = "gc_from_disk"

    mock_group_chat = Mock()
    mock_group_chat._activated = True
    mock_group_chat.group_chat_context.repository.load_group_metadata = AsyncMock(
        return_value=Mock(
            group_chat_id=group_chat_id,
            group_chat_name="Loaded Group",
            project_path="/path/to/project",
            created_at=datetime(2026, 6, 3, 10, 0, 0),
            group_type="manager_orchestrate",
        )
    )
    mock_group_chat_manager.load_group_chat = AsyncMock(return_value=mock_group_chat)

    # Act
    result = await service.load_group_chat(group_chat_id)

    # Assert
    assert isinstance(result, GroupChatInfo)
    assert result.group_chat_id == group_chat_id
    assert result.is_active is True
    mock_group_chat_manager.load_group_chat.assert_called_once_with(group_chat_id)


async def test_load_group_chat_not_found_raises_error(service, mock_group_chat_manager):
    """测试加载不存在的群聊抛出异常"""
    # Arrange
    from agents_hub.core.foundation import GroupChatNotFoundError
    mock_group_chat_manager.load_group_chat = AsyncMock(
        side_effect=GroupChatNotFoundError("群聊不存在")
    )

    # Act & Assert
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await service.load_group_chat("gc_nonexistent")
    assert "gc_nonexistent" in str(exc_info.value)


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
    mock_group_chat_manager._group_chats = {group_chat_id: mock_group_chat}
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
        mock_group_chat_manager.unregister.assert_called_once_with(group_chat_id)
        mock_paths.base_dir.assert_called_once_with(group_chat_id, project_path)
        mock_rmtree.assert_called_once_with(mock_dir)


async def test_delete_group_chat_from_disk_when_not_in_memory(service, mock_group_chat_manager):
    """测试删除不在内存中的群聊（从 list_all_group_chats 获取 project_path）"""
    # Arrange
    group_chat_id = "gc_disk_delete"
    project_path = "/path/to/disk/project"

    mock_group_chat_manager._group_chats = {}  # 不在内存
    mock_group_chat_manager.unregister = AsyncMock()

    # Mock list_all_group_chats 返回包含目标群聊的元数据
    mock_group_chat_manager.list_all_group_chats.return_value = [
        {
            "group_chat_id": "gc_other",
            "group_chat_name": "Other Group",
            "project_path": "/path/to/other",
            "created_at": datetime(2026, 6, 1, 10, 0, 0),
            "group_type": "manager_orchestrate",
        },
        {
            "group_chat_id": group_chat_id,
            "group_chat_name": "Disk Group",
            "project_path": project_path,
            "created_at": datetime(2026, 6, 2, 10, 0, 0),
            "group_type": "manager_orchestrate",
        },
    ]

    with patch("agents_hub.api.services.group_chat_service.group_chat_paths") as mock_paths, \
         patch("agents_hub.api.services.group_chat_service.Path") as MockPath, \
         patch("shutil.rmtree") as mock_rmtree:
        # Mock Path 对象
        mock_dir = Mock()
        mock_dir.exists.return_value = True
        MockPath.return_value = mock_dir

        mock_paths.base_dir.return_value = f"/path/to/group_chats/{group_chat_id}"

        # Act
        await service.delete_group_chat(group_chat_id, keep_data=False)

        # Assert
        mock_group_chat_manager.list_all_group_chats.assert_called_once()
        mock_group_chat_manager.unregister.assert_called_once_with(group_chat_id)
        mock_paths.base_dir.assert_called_once_with(group_chat_id, project_path)
        mock_rmtree.assert_called_once_with(mock_dir)


async def test_delete_group_chat_idempotent(service, mock_group_chat_manager):
    """测试删除不存在的群聊是幂等的（不抛异常）"""
    # Arrange
    mock_group_chat_manager._group_chats = {}
    mock_group_chat_manager.list_all_group_chats.return_value = []  # 不存在于索引中
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
    mock_group_chat_manager._group_chats = {group_chat_id: mock_group_chat}
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
    mock_metadata_list = [
        {
            "group_chat_id": "gc_1",
            "group_chat_name": "Group 1",
            "project_path": "/path/1",
            "created_at": datetime(2026, 6, 1, 10, 0, 0),
            "group_type": "manager_orchestrate",
        },
        {
            "group_chat_id": "gc_2",
            "group_chat_name": "Group 2",
            "project_path": "/path/2",
            "created_at": datetime(2026, 6, 2, 10, 0, 0),
            "group_type": "manager_orchestrate",
        },
    ]
    mock_group_chat_manager.list_all_group_chats.return_value = mock_metadata_list
    mock_group_chat_manager.is_active_group.side_effect = lambda cid: cid == "gc_1"

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
    mock_metadata_list = [
        {
            "group_chat_id": "gc_active",
            "group_chat_name": "Active Group",
            "project_path": "/path/active",
            "created_at": datetime(2026, 6, 1, 10, 0, 0),
            "group_type": "manager_orchestrate",
        },
        {
            "group_chat_id": "gc_inactive",
            "group_chat_name": "Inactive Group",
            "project_path": "/path/inactive",
            "created_at": datetime(2026, 6, 2, 10, 0, 0),
            "group_type": "manager_orchestrate",
        },
    ]
    mock_group_chat_manager.list_all_group_chats.return_value = mock_metadata_list
    mock_group_chat_manager.is_active_group.side_effect = lambda cid: cid == "gc_active"

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
    mock_group_chat._activated = True
    mock_group_chat.group_chat_context.repository.load_group_metadata = AsyncMock(
        return_value=Mock(
            group_chat_id=group_chat_id,
            group_chat_name="Memory Group",
            project_path="/path/to/project",
            created_at=datetime(2026, 6, 3, 10, 0, 0),
            group_type="manager_orchestrate",
        )
    )
    mock_group_chat_manager.load_group_chat = AsyncMock(return_value=mock_group_chat)
    mock_group_chat_manager.is_active_group.return_value = True

    # Act
    result = await service.get_group_chat_info(group_chat_id)

    # Assert
    assert result.group_chat_id == group_chat_id
    assert result.is_active is True
    mock_group_chat_manager.load_group_chat.assert_called_once_with(group_chat_id)


async def test_get_group_chat_info_from_disk(service, mock_group_chat_manager):
    """测试从磁盘获取群聊信息"""
    # Arrange
    group_chat_id = "gc_disk"

    mock_group_chat = Mock()
    mock_group_chat._activated = False
    mock_group_chat.group_chat_context.repository.load_group_metadata = AsyncMock(
        return_value=Mock(
            group_chat_id=group_chat_id,
            group_chat_name="Disk Group",
            project_path="/path/to/project",
            created_at=datetime(2026, 6, 3, 10, 0, 0),
            group_type="manager_orchestrate",
        )
    )
    mock_group_chat_manager.load_group_chat = AsyncMock(return_value=mock_group_chat)
    mock_group_chat_manager.is_active_group.return_value = False

    # Act
    result = await service.get_group_chat_info(group_chat_id)

    # Assert
    assert result.group_chat_id == group_chat_id
    assert result.is_active is False  # 从磁盘加载，非活跃
    mock_group_chat_manager.load_group_chat.assert_called_once_with(group_chat_id)


async def test_get_group_chat_info_not_found(service, mock_group_chat_manager):
    """测试获取不存在的群聊信息"""
    # Arrange
    from agents_hub.core.foundation import GroupChatNotFoundError
    mock_group_chat_manager.load_group_chat = AsyncMock(
        side_effect=GroupChatNotFoundError("不存在")
    )

    # Act & Assert
    with pytest.raises(ResourceNotFoundError):
        await service.get_group_chat_info("gc_nonexistent")


# Task 8: get_group_chat_members 测试

async def test_get_group_chat_members_success(service, mock_group_chat_manager):
    """测试成功获取群聊成员"""
    # Arrange
    import json

    group_chat_id = "gc_members"
    project_path = "/path/to/project"

    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = AsyncMock(
        return_value=Mock(project_path=project_path)
    )
    mock_group_chat_manager.load_group_chat_from_disk = AsyncMock(return_value=mock_group_chat)

    session_state_data = {
        "Leader": {
            "main_session": "session_123",
            "btw_session": ["btw_1", "btw_2"],
            "cwd": "/path/to/project",
            "use_docker": False,
        },
        "Worker1": {
            "main_session": None,
            "btw_session": [],
            "cwd": "/path/to/project",
        },
    }

    with patch("agents_hub.api.services.group_chat_service.group_chat_paths") as mock_paths, \
         patch("json.load", return_value=session_state_data), \
         patch("builtins.open", MagicMock()):
        mock_paths.base_dir.return_value = "/path/to/group_chats/gc_members"

        mock_session_file = MagicMock()
        mock_session_file.exists.return_value = True
        # Mock Path 的 __truediv__ 操作
        with patch("agents_hub.api.services.group_chat_service.Path", return_value=mock_session_file):
            # Act
            result = await service.get_group_chat_members(group_chat_id)

    # Assert
    assert len(result) == 2
    assert result[0].name == "Leader"
    assert result[0].main_session == "session_123"
    assert len(result[0].btw_session) == 2
    assert result[0].use_docker is False
    assert result[1].name == "Worker1"
    assert result[1].main_session is None


async def test_get_group_chat_members_file_not_found(service, mock_group_chat_manager):
    """测试 session_state 文件不存在"""
    # Arrange
    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = AsyncMock(
        return_value=Mock(project_path="/path")
    )
    mock_group_chat_manager.load_group_chat_from_disk = AsyncMock(return_value=mock_group_chat)

    with patch("agents_hub.api.services.group_chat_service.group_chat_paths") as mock_paths:
        mock_paths.base_dir.return_value = "/path/to/group_chats/gc_no_file"

        # Mock Path 的 / 操作和 exists
        mock_path_obj = MagicMock()
        mock_session_file = MagicMock()
        mock_session_file.exists.return_value = False
        mock_path_obj.__truediv__ = MagicMock(return_value=mock_session_file)

        with patch("agents_hub.api.services.group_chat_service.Path", return_value=mock_path_obj):
            # Act & Assert
            with pytest.raises(ResourceNotFoundError) as exc_info:
                await service.get_group_chat_members("gc_no_file")
            assert "session_state 文件不存在" in str(exc_info.value)


async def test_get_group_chat_members_json_decode_error(service, mock_group_chat_manager):
    """测试 JSON 格式错误转换为 StateError"""
    # Arrange
    import json
    from agents_hub.exceptions import StateError

    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = AsyncMock(
        return_value=Mock(project_path="/path")
    )
    mock_group_chat_manager.load_group_chat_from_disk = AsyncMock(return_value=mock_group_chat)

    with patch("agents_hub.api.services.group_chat_service.group_chat_paths") as mock_paths, \
         patch("builtins.open", MagicMock()), \
         patch("json.load", side_effect=json.JSONDecodeError("Invalid JSON", "", 0)):
        mock_paths.base_dir.return_value = "/path/to/group_chats/gc_bad_json"

        mock_file = MagicMock()
        mock_file.exists.return_value = True

        with patch("agents_hub.api.services.group_chat_service.Path", return_value=mock_file):
            # Act & Assert
            with pytest.raises(StateError) as exc_info:
                await service.get_group_chat_members("gc_bad_json")
            assert "JSON 格式错误" in str(exc_info.value)


async def test_get_group_chat_members_missing_fields_use_defaults(service, mock_group_chat_manager):
    """测试缺失字段使用默认值"""
    # Arrange
    import json

    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = AsyncMock(
        return_value=Mock(project_path="/path")
    )
    mock_group_chat_manager.load_group_chat_from_disk = AsyncMock(return_value=mock_group_chat)

    # 缺少某些字段
    session_state_data = {
        "Leader": {
            "main_session": "session_123",
            # 缺少 btw_session, cwd, use_docker
        },
    }

    with patch("agents_hub.api.services.group_chat_service.group_chat_paths") as mock_paths, \
         patch("json.load", return_value=session_state_data), \
         patch("builtins.open", MagicMock()):
        mock_paths.base_dir.return_value = "/path/to/group_chats/gc_partial"

        mock_session_file = MagicMock()
        mock_session_file.exists.return_value = True

        with patch("agents_hub.api.services.group_chat_service.Path", return_value=mock_session_file):
            # Act
            result = await service.get_group_chat_members("gc_partial")

    # Assert
    assert len(result) == 1
    assert result[0].name == "Leader"
    assert result[0].btw_session == []  # 默认空列表
    assert result[0].cwd is None
    assert result[0].use_docker is False  # 默认 False
