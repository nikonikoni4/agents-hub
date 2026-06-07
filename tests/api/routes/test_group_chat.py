"""测试文件快照 API 端点"""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

from agents_hub.api.routes.group_chat import router
from agents_hub.exceptions import ResourceNotFoundError


@pytest.fixture
def mock_group_chat_manager():
    """Mock GroupChatManager"""
    manager = Mock()
    manager.load_group_chat = AsyncMock()
    return manager


@pytest.fixture
def mock_service():
    """Mock GroupChatService"""
    service = Mock()
    service.group_chat_manager = Mock()
    service.group_chat_manager.load_group_chat = AsyncMock()
    return service


@pytest.fixture
def mock_group_chat():
    """Mock GroupChat 实例"""
    gc = Mock()
    gc.runtime = Mock()
    gc.runtime.get_project_path.return_value = "project1"
    return gc


# ==================== GET /files/{snapshot_id}/content ====================


async def test_get_file_snapshot_content_success(mock_service, mock_group_chat):
    """测试成功获取快照内容"""
    # Arrange
    group_chat_id = "gc_test_123"
    snapshot_id = "call_001_0"
    expected_content = "def hello():\n    print('Hello, World!')"

    mock_service.group_chat_manager.load_group_chat.return_value = mock_group_chat

    with patch("agents_hub.api.routes.group_chat.get_snapshot_content") as mock_get_content:
        mock_get_content.return_value = expected_content

        # Act - 直接调用路由处理函数
        from agents_hub.api.routes.group_chat import get_file_snapshot_content
        result = await get_file_snapshot_content(group_chat_id, snapshot_id, mock_service)

    # Assert
    assert result == {"content": expected_content}
    mock_service.group_chat_manager.load_group_chat.assert_called()


async def test_get_file_snapshot_content_not_found(mock_service, mock_group_chat):
    """测试获取不存在的快照内容（404）"""
    # Arrange
    group_chat_id = "gc_test_123"
    snapshot_id = "nonexistent_snapshot"

    mock_service.group_chat_manager.load_group_chat.return_value = mock_group_chat

    with patch("agents_hub.api.routes.group_chat.get_snapshot_content") as mock_get_content:
        mock_get_content.side_effect = ValueError("Failed to read snapshot content: [Errno 2] No such file or directory")

        # Act & Assert
        from agents_hub.api.routes.group_chat import get_file_snapshot_content
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await get_file_snapshot_content(group_chat_id, snapshot_id, mock_service)

        assert "快照不存在" in str(exc_info.value)
        assert snapshot_id in str(exc_info.value)


async def test_get_file_snapshot_content_group_chat_not_found(mock_service):
    """测试群聊不存在时获取快照内容（404）"""
    # Arrange
    group_chat_id = "nonexistent_group_chat"
    snapshot_id = "call_001_0"

    mock_service.group_chat_manager.load_group_chat.side_effect = Exception("群聊不存在")

    # Act & Assert
    from agents_hub.api.routes.group_chat import get_file_snapshot_content
    with pytest.raises(Exception):
        await get_file_snapshot_content(group_chat_id, snapshot_id, mock_service)


# ==================== GET /files/{snapshot_id}/diff ====================


async def test_get_file_snapshot_diff_success(mock_service, mock_group_chat):
    """测试成功获取快照 diff"""
    # Arrange
    group_chat_id = "gc_test_123"
    snapshot_id = "call_001_0"
    expected_diff = """diff --git a/test.py b/test.py
index 1234567..abcdefg 100644
--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 def hello():
+    print('Hello, World!')
     pass"""

    mock_service.group_chat_manager.load_group_chat.return_value = mock_group_chat

    with patch("agents_hub.api.routes.group_chat.get_snapshot_diff") as mock_get_diff:
        mock_get_diff.return_value = expected_diff

        # Act
        from agents_hub.api.routes.group_chat import get_file_snapshot_diff
        result = await get_file_snapshot_diff(group_chat_id, snapshot_id, mock_service)

    # Assert
    assert result == {"diff": expected_diff}
    mock_service.group_chat_manager.load_group_chat.assert_called()


async def test_get_file_snapshot_diff_not_found(mock_service, mock_group_chat):
    """测试获取不存在的快照 diff（404）"""
    # Arrange
    group_chat_id = "gc_test_123"
    snapshot_id = "nonexistent_snapshot"

    mock_service.group_chat_manager.load_group_chat.return_value = mock_group_chat

    with patch("agents_hub.api.routes.group_chat.get_snapshot_diff") as mock_get_diff:
        mock_get_diff.side_effect = ValueError("Failed to read snapshot diff: [Errno 2] No such file or directory")

        # Act & Assert
        from agents_hub.api.routes.group_chat import get_file_snapshot_diff
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await get_file_snapshot_diff(group_chat_id, snapshot_id, mock_service)

        assert "快照不存在" in str(exc_info.value)
        assert snapshot_id in str(exc_info.value)


async def test_get_file_snapshot_diff_empty_diff(mock_service, mock_group_chat):
    """测试获取快照 diff 为空（新增文件或无变化）"""
    # Arrange
    group_chat_id = "gc_test_123"
    snapshot_id = "call_001_0"
    expected_diff = ""  # 无 diff

    mock_service.group_chat_manager.load_group_chat.return_value = mock_group_chat

    with patch("agents_hub.api.routes.group_chat.get_snapshot_diff") as mock_get_diff:
        mock_get_diff.return_value = expected_diff

        # Act
        from agents_hub.api.routes.group_chat import get_file_snapshot_diff
        result = await get_file_snapshot_diff(group_chat_id, snapshot_id, mock_service)

    # Assert
    assert result == {"diff": ""}
