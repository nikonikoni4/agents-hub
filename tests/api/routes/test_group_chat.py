"""测试文件快照 API 端点"""

from unittest.mock import AsyncMock, Mock

import pytest

from agents_hub.api.routes.group_chat import get_file_snapshot_content, get_file_snapshot_diff
from agents_hub.exceptions import ResourceNotFoundError


@pytest.fixture
def mock_service():
    """Mock GroupChatService"""
    service = Mock()
    service.get_file_snapshot_content = AsyncMock()
    service.get_file_snapshot_diff = AsyncMock()
    return service


# ==================== GET /files/{snapshot_id}/content ====================


async def test_get_file_snapshot_content_success(mock_service):
    """测试成功获取快照内容"""
    # Arrange
    group_chat_id = "gc_test_123"
    snapshot_id = "call_001_0"
    expected_content = "def hello():\n    print('Hello, World!')"

    mock_service.get_file_snapshot_content.return_value = expected_content

    # Act
    result = await get_file_snapshot_content(group_chat_id, snapshot_id, mock_service)

    # Assert
    assert result == {"content": expected_content}
    mock_service.get_file_snapshot_content.assert_called_once_with(group_chat_id, snapshot_id)


async def test_get_file_snapshot_content_not_found(mock_service):
    """测试获取不存在的快照内容（404）"""
    # Arrange
    group_chat_id = "gc_test_123"
    snapshot_id = "nonexistent_snapshot"

    mock_service.get_file_snapshot_content.side_effect = ResourceNotFoundError(
        "快照不存在",
        details={"snapshot_id": snapshot_id}
    )

    # Act & Assert
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await get_file_snapshot_content(group_chat_id, snapshot_id, mock_service)

    assert "快照不存在" in str(exc_info.value)


async def test_get_file_snapshot_content_group_chat_not_found(mock_service):
    """测试群聊不存在时获取快照内容（404）"""
    # Arrange
    group_chat_id = "nonexistent_group_chat"
    snapshot_id = "call_001_0"

    mock_service.get_file_snapshot_content.side_effect = ResourceNotFoundError(
        "群聊不存在",
        details={"group_chat_id": group_chat_id}
    )

    # Act & Assert
    with pytest.raises(ResourceNotFoundError):
        await get_file_snapshot_content(group_chat_id, snapshot_id, mock_service)


# ==================== GET /files/{snapshot_id}/diff ====================


async def test_get_file_snapshot_diff_success(mock_service):
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

    mock_service.get_file_snapshot_diff.return_value = expected_diff

    # Act
    result = await get_file_snapshot_diff(group_chat_id, snapshot_id, mock_service)

    # Assert
    assert result == {"diff": expected_diff}
    mock_service.get_file_snapshot_diff.assert_called_once_with(group_chat_id, snapshot_id)


async def test_get_file_snapshot_diff_not_found(mock_service):
    """测试获取不存在的快照 diff（404）"""
    # Arrange
    group_chat_id = "gc_test_123"
    snapshot_id = "nonexistent_snapshot"

    mock_service.get_file_snapshot_diff.side_effect = ResourceNotFoundError(
        "快照不存在",
        details={"snapshot_id": snapshot_id}
    )

    # Act & Assert
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await get_file_snapshot_diff(group_chat_id, snapshot_id, mock_service)

    assert "快照不存在" in str(exc_info.value)


async def test_get_file_snapshot_diff_empty_diff(mock_service):
    """测试获取空 diff"""
    # Arrange
    group_chat_id = "gc_test_123"
    snapshot_id = "call_001_0"
    empty_diff = ""

    mock_service.get_file_snapshot_diff.return_value = empty_diff

    # Act
    result = await get_file_snapshot_diff(group_chat_id, snapshot_id, mock_service)

    # Assert
    assert result == {"diff": empty_diff}
    mock_service.get_file_snapshot_diff.assert_called_once_with(group_chat_id, snapshot_id)
