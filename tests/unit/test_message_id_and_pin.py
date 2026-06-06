"""
消息自增 ID 和 Pin 功能测试

测试契约：
1. GroupChatSession.add_message() - 自增 id 分配
2. GroupChatRepository - 向后兼容性和持久化
3. GroupChatRuntime.get_message_dicts() - 返回 id 字段
4. GroupChatService.pin_message/unpin_message - 使用 message_id
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_hub.api.schemas.group_chats import (
    MessageInfo,
    PinnedMessageInfo,
    PinMessageRequest,
)
from agents_hub.core.context.group_chat_repository import GroupChatRepository
from agents_hub.core.context.group_chat_runtime import GroupChatRuntime
from agents_hub.core.context.group_chat_session import GroupChatSession


# ==================== 辅助类 ====================


class MockAgentResult:
    """模拟 AgentResult"""

    def __init__(self, agent_name: str, text: str, timestamp: str, platform: str):
        self.agent_name = agent_name
        self.text = text
        self.timestamp = timestamp
        self.platform = MagicMock(value=platform)


# ==================== GroupChatSession.add_message() 测试 ====================


class TestGroupChatSessionAddMessage:
    """GroupChatSession.add_message() 契约测试"""

    def test_add_message_assigns_incremental_id(self):
        """
        契约：每条消息自动分配递增的 id（从 1 开始）

        验证方式：
        1. 创建 GroupChatSession
        2. 添加 3 条消息
        3. 验证每条消息的 id 分别为 1, 2, 3
        """
        session = GroupChatSession(group_chat_id="test-chat")

        msg1 = MockAgentResult("agent1", "hello", "2026-01-01T00:00:00", "claude")
        msg2 = MockAgentResult("agent2", "world", "2026-01-01T00:00:01", "codex")
        msg3 = MockAgentResult("agent1", "foo", "2026-01-01T00:00:02", "claude")

        session.add_message(msg1)
        session.add_message(msg2)
        session.add_message(msg3)

        assert session.messages[0]["id"] == 1
        assert session.messages[1]["id"] == 2
        assert session.messages[2]["id"] == 3

    def test_add_message_increments_next_message_id(self):
        """
        契约：添加消息后 next_message_id 自动递增

        验证方式：
        1. 创建 GroupChatSession（初始 next_message_id=1）
        2. 添加 3 条消息
        3. 验证 next_message_id 变为 4
        """
        session = GroupChatSession(group_chat_id="test-chat")

        assert session.next_message_id == 1

        session.add_message(MockAgentResult("agent1", "msg1", "2026-01-01T00:00:00", "claude"))
        assert session.next_message_id == 2

        session.add_message(MockAgentResult("agent1", "msg2", "2026-01-01T00:00:01", "claude"))
        assert session.next_message_id == 3

        session.add_message(MockAgentResult("agent1", "msg3", "2026-01-01T00:00:02", "claude"))
        assert session.next_message_id == 4


# ==================== GroupChatRepository 测试 ====================


class TestGroupChatRepositorySession:
    """GroupChatRepository 会话持久化契约测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def repo(self, temp_dir):
        """创建 GroupChatRepository 实例"""
        with patch("agents_hub.core.context.group_chat_repository.group_chat_paths") as mock_paths:
            base = Path(temp_dir) / "test-chat"
            mock_paths.base_dir.return_value = str(base)
            mock_paths.messages_file.return_value = str(base / "messages.jsonl")
            mock_paths.agent_member_file_path.return_value = str(base / "agent_member.json")
            mock_paths.compact_history_file.return_value = str(base / "compact_history.jsonl")
            mock_paths.metadata_file.return_value = str(base / "group_metadata.json")
            yield GroupChatRepository("test-chat", temp_dir)

    @pytest.mark.asyncio
    async def test_load_session_backfills_ids_for_old_messages(self, repo, temp_dir):
        """
        契约：加载旧数据（无 id 字段）时自动补全 id（从 1 开始）

        验证方式：
        1. 创建没有 id 字段的旧消息文件
        2. 加载会话
        3. 验证每条消息都被补上了 id（从 1 开始）
        """
        # 创建旧格式消息文件（无 id）
        base = Path(temp_dir) / "test-chat"
        base.mkdir(parents=True, exist_ok=True)
        messages_file = base / "messages.jsonl"

        old_messages = [
            {"_type": "meta_data", "last_compact_loc": 0},
            {"agent_name": "agent1", "content": "msg1", "timestamp": "2026-01-01T00:00:00", "platform": "claude"},
            {"agent_name": "agent2", "content": "msg2", "timestamp": "2026-01-01T00:00:01", "platform": "codex"},
        ]

        with open(messages_file, "w", encoding="utf-8") as f:
            for msg in old_messages:
                f.write(json.dumps(msg) + "\n")

        # 加载会话
        session = await repo.load_group_chat_session()

        # 验证 id 被补全
        assert session.messages[0]["id"] == 1
        assert session.messages[1]["id"] == 2

    @pytest.mark.asyncio
    async def test_load_session_preserves_existing_ids(self, repo, temp_dir):
        """
        契约：加载新数据（有 id 字段）时保持原 id

        验证方式：
        1. 创建有 id 字段的新消息文件
        2. 加载会话
        3. 验证消息的 id 保持不变
        """
        base = Path(temp_dir) / "test-chat"
        base.mkdir(parents=True, exist_ok=True)
        messages_file = base / "messages.jsonl"

        new_messages = [
            {"_type": "meta_data", "last_compact_loc": 0, "next_message_id": 10},
            {"id": 5, "agent_name": "agent1", "content": "msg1", "timestamp": "2026-01-01T00:00:00", "platform": "claude"},
            {"id": 8, "agent_name": "agent2", "content": "msg2", "timestamp": "2026-01-01T00:00:01", "platform": "codex"},
        ]

        with open(messages_file, "w", encoding="utf-8") as f:
            for msg in new_messages:
                f.write(json.dumps(msg) + "\n")

        session = await repo.load_group_chat_session()

        assert session.messages[0]["id"] == 5
        assert session.messages[1]["id"] == 8

    @pytest.mark.asyncio
    async def test_load_session_reads_next_message_id_from_meta(self, repo, temp_dir):
        """
        契约：从 meta_data 读取 next_message_id

        验证方式：
        1. 创建包含 next_message_id 的消息文件
        2. 加载会话
        3. 验证 next_message_id 被正确读取
        """
        base = Path(temp_dir) / "test-chat"
        base.mkdir(parents=True, exist_ok=True)
        messages_file = base / "messages.jsonl"

        messages = [
            {"_type": "meta_data", "last_compact_loc": 0, "next_message_id": 100},
            {"id": 1, "agent_name": "agent1", "content": "msg1", "timestamp": "2026-01-01T00:00:00", "platform": "claude"},
        ]

        with open(messages_file, "w", encoding="utf-8") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        session = await repo.load_group_chat_session()

        assert session.next_message_id == 100

    @pytest.mark.asyncio
    async def test_load_session_defaults_next_message_id_for_old_data(self, repo, temp_dir):
        """
        契约：旧数据（无 next_message_id）默认为 len(messages) + 1

        验证方式：
        1. 创建没有 next_message_id 的旧消息文件
        2. 加载会话
        3. 验证 next_message_id 默认为 len(messages) + 1
        """
        base = Path(temp_dir) / "test-chat"
        base.mkdir(parents=True, exist_ok=True)
        messages_file = base / "messages.jsonl"

        old_messages = [
            {"_type": "meta_data", "last_compact_loc": 0},
            {"agent_name": "agent1", "content": "msg1", "timestamp": "2026-01-01T00:00:00", "platform": "claude"},
            {"agent_name": "agent2", "content": "msg2", "timestamp": "2026-01-01T00:00:01", "platform": "codex"},
            {"agent_name": "agent1", "content": "msg3", "timestamp": "2026-01-01T00:00:02", "platform": "claude"},
        ]

        with open(messages_file, "w", encoding="utf-8") as f:
            for msg in old_messages:
                f.write(json.dumps(msg) + "\n")

        session = await repo.load_group_chat_session()

        # 3 条消息，默认 next_message_id = 3 + 1 = 4
        assert session.next_message_id == 4

    @pytest.mark.asyncio
    async def test_save_session_persists_next_message_id(self, repo, temp_dir):
        """
        契约：保存时在 meta_data 中写入 next_message_id

        验证方式：
        1. 创建 GroupChatSession，设置 next_message_id=50
        2. 保存会话
        3. 读取文件，验证 meta_data 包含 next_message_id=50
        """
        session = GroupChatSession(group_chat_id="test-chat")
        session.next_message_id = 50

        await repo.save_group_chat_session(session)

        # 读取文件验证
        messages_file = Path(temp_dir) / "test-chat" / "messages.jsonl"
        with open(messages_file, encoding="utf-8") as f:
            first_line = f.readline()
            meta_data = json.loads(first_line)

        assert meta_data["next_message_id"] == 50

    @pytest.mark.asyncio
    async def test_save_and_load_session_restores_next_message_id(self, repo):
        """
        契约：保存后重新加载能正确恢复 next_message_id

        验证方式：
        1. 创建 GroupChatSession，添加几条消息
        2. 保存会话
        3. 重新加载会话
        4. 验证 next_message_id 保持一致
        """
        session = GroupChatSession(group_chat_id="test-chat")
        session.add_message(MockAgentResult("agent1", "msg1", "2026-01-01T00:00:00", "claude"))
        session.add_message(MockAgentResult("agent2", "msg2", "2026-01-01T00:00:01", "codex"))

        assert session.next_message_id == 3

        await repo.save_group_chat_session(session)

        loaded_session = await repo.load_group_chat_session()

        assert loaded_session.next_message_id == 3


# ==================== GroupChatRuntime.get_message_dicts() 测试 ====================


class TestGroupChatRuntimeGetMessageDicts:
    """GroupChatRuntime.get_message_dicts() 契约测试"""

    def test_get_message_dicts_includes_id(self):
        """
        契约：返回的每条消息包含 id 字段

        验证方式：
        1. 创建 GroupChatSession，添加几条消息
        2. 创建 GroupChatRuntime 并设置 session
        3. 调用 get_message_dicts()
        4. 验证返回的消息包含 id 字段
        """
        session = GroupChatSession(group_chat_id="test-chat")
        session.add_message(MockAgentResult("agent1", "msg1", "2026-01-01T00:00:00", "claude"))
        session.add_message(MockAgentResult("agent2", "msg2", "2026-01-01T00:00:01", "codex"))

        # 创建 runtime 并设置 state
        state = MagicMock()
        state.group_chat_session = session
        state.require_session.return_value = session

        runtime = GroupChatRuntime(
            group_chat_id="test-chat",
            project_path="/tmp/test",
            repository=MagicMock(),
            state=state,
        )

        messages = runtime.get_message_dicts()

        assert len(messages) == 2
        assert messages[0]["id"] == 1
        assert messages[1]["id"] == 2
        assert messages[0]["speaker"] == "agent1"
        assert messages[1]["speaker"] == "agent2"


# ==================== Schema 测试 ====================


class TestMessageSchemas:
    """消息相关 Schema 契约测试"""

    def test_message_info_requires_id(self):
        """
        契约：MessageInfo 必须包含 id 字段

        验证方式：
        1. 创建包含 id 的 MessageInfo
        2. 验证创建成功
        """
        msg = MessageInfo(
            id=1,
            speaker="agent1",
            content="hello",
            timestamp="2026-01-01T00:00:00",
            platform="claude",
        )
        assert msg.id == 1
        assert msg.speaker == "agent1"

    def test_message_info_missing_id_raises(self):
        """
        契约：MessageInfo 缺少 id 字段时抛出异常

        验证方式：
        1. 尝试创建缺少 id 的 MessageInfo
        2. 验证抛出 ValidationError
        """
        with pytest.raises(Exception):  # Pydantic ValidationError
            MessageInfo(
                speaker="agent1",
                content="hello",
                timestamp="2026-01-01T00:00:00",
                platform="claude",
            )

    def test_pin_message_request_requires_message_id(self):
        """
        契约：PinMessageRequest 必须包含 message_id 字段

        验证方式：
        1. 创建包含 message_id 的 PinMessageRequest
        2. 验证创建成功
        """
        req = PinMessageRequest(message_id=42)
        assert req.message_id == 42

    def test_pinned_message_info_requires_message_id(self):
        """
        契约：PinnedMessageInfo 必须包含 message_id 字段

        验证方式：
        1. 创建包含 message_id 的 PinnedMessageInfo
        2. 验证创建成功
        """
        info = PinnedMessageInfo(
            message_id=42,
            speaker="agent1",
            content="hello",
            timestamp="2026-01-01T00:00:00",
            platform="claude",
            pinned_at="2026-01-01T00:01:00",
        )
        assert info.message_id == 42


# ==================== GroupChatService pin/unpin 测试 ====================


class TestGroupChatServicePin:
    """GroupChatService pin/unpin 契约测试"""

    @pytest.fixture
    def mock_service(self):
        """创建 mock 的 GroupChatService"""
        from agents_hub.api.services.group_chat_service import GroupChatService

        mock_manager = MagicMock()
        service = GroupChatService(group_chat_manager=mock_manager)
        return service, mock_manager

    @pytest.mark.asyncio
    async def test_pin_message_by_id(self, mock_service):
        """
        契约：通过 message_id 置顶消息

        验证方式：
        1. 创建 mock 群聊，包含消息
        2. 调用 pin_message(message_id=1)
        3. 验证 pins 文件包含该消息
        """
        service, mock_manager = mock_service

        # 创建 mock 群聊
        mock_group_chat = MagicMock()
        mock_group_chat.runtime.get_message_dicts.return_value = [
            {"id": 1, "speaker": "agent1", "content": "msg1", "timestamp": "2026-01-01T00:00:00", "platform": "claude"},
            {"id": 2, "speaker": "agent2", "content": "msg2", "timestamp": "2026-01-01T00:00:01", "platform": "codex"},
        ]
        mock_group_chat.runtime.repository.group_chat_session_path = "/tmp/test"
        mock_manager.load_group_chat = AsyncMock(return_value=mock_group_chat)

        # Mock _get_pins_path 和 _read_pins/_write_pins
        with patch.object(service, "_get_pins_path", return_value=Path("/tmp/pins.json")), \
             patch.object(service, "_get_pins_lock", return_value=AsyncMock()), \
             patch.object(service, "_read_pins", new_callable=AsyncMock, return_value=[]), \
             patch.object(service, "_write_pins", new_callable=AsyncMock) as mock_write:

            await service.pin_message("test-chat", 1)

            # 验证 _write_pins 被调用
            mock_write.assert_called_once()
            written_pins = mock_write.call_args[0][1]
            assert len(written_pins) == 1
            assert written_pins[0]["message_id"] == 1
            assert written_pins[0]["speaker"] == "agent1"

    @pytest.mark.asyncio
    async def test_pin_message_idempotent(self, mock_service):
        """
        契约：重复 pin 是幂等的

        验证方式：
        1. 创建 mock 群聊，消息已 pin
        2. 再次调用 pin_message
        3. 验证 _write_pins 未被调用（跳过）
        """
        service, mock_manager = mock_service

        mock_group_chat = MagicMock()
        mock_group_chat.runtime.get_message_dicts.return_value = [
            {"id": 1, "speaker": "agent1", "content": "msg1", "timestamp": "2026-01-01T00:00:00", "platform": "claude"},
        ]
        mock_manager.load_group_chat = AsyncMock(return_value=mock_group_chat)

        existing_pins = [
            {"message_id": 1, "speaker": "agent1", "content": "msg1", "timestamp": "2026-01-01T00:00:00", "platform": "claude", "pinned_at": "2026-01-01T00:01:00"},
        ]

        with patch.object(service, "_get_pins_path", return_value=Path("/tmp/pins.json")), \
             patch.object(service, "_get_pins_lock", return_value=AsyncMock()), \
             patch.object(service, "_read_pins", new_callable=AsyncMock, return_value=existing_pins), \
             patch.object(service, "_write_pins", new_callable=AsyncMock) as mock_write:

            await service.pin_message("test-chat", 1)

            # 幂等：_write_pins 不应被调用
            mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_pin_message_not_found_raises(self, mock_service):
        """
        契约：消息不存在时抛出 MessageNotFoundError

        验证方式：
        1. 创建 mock 群聊，不包含 message_id=999
        2. 调用 pin_message(message_id=999)
        3. 验证抛出 MessageNotFoundError
        """
        from agents_hub.exceptions import MessageNotFoundError

        service, mock_manager = mock_service

        mock_group_chat = MagicMock()
        mock_group_chat.runtime.get_message_dicts.return_value = [
            {"id": 1, "speaker": "agent1", "content": "msg1", "timestamp": "2026-01-01T00:00:00", "platform": "claude"},
        ]
        mock_manager.load_group_chat = AsyncMock(return_value=mock_group_chat)

        with pytest.raises(MessageNotFoundError):
            await service.pin_message("test-chat", 999)

    @pytest.mark.asyncio
    async def test_unpin_message_by_id(self, mock_service):
        """
        契约：通过 message_id 取消置顶

        验证方式：
        1. 创建 mock 群聊，已有 pins
        2. 调用 unpin_message(message_id=1)
        3. 验证 pins 文件不包含该消息
        """
        service, mock_manager = mock_service

        mock_group_chat = MagicMock()
        mock_manager.load_group_chat = AsyncMock(return_value=mock_group_chat)

        existing_pins = [
            {"message_id": 1, "speaker": "agent1", "content": "msg1"},
            {"message_id": 2, "speaker": "agent2", "content": "msg2"},
        ]

        with patch.object(service, "_get_pins_path", return_value=Path("/tmp/pins.json")), \
             patch.object(service, "_get_pins_lock", return_value=AsyncMock()), \
             patch.object(service, "_read_pins", new_callable=AsyncMock, return_value=existing_pins), \
             patch.object(service, "_write_pins", new_callable=AsyncMock) as mock_write:

            await service.unpin_message("test-chat", 1)

            mock_write.assert_called_once()
            written_pins = mock_write.call_args[0][1]
            assert len(written_pins) == 1
            assert written_pins[0]["message_id"] == 2

    @pytest.mark.asyncio
    async def test_unpin_message_idempotent(self, mock_service):
        """
        契约：重复 unpin 是幂等的

        验证方式：
        1. 创建 mock 群聊，pins 中不包含 message_id=999
        2. 调用 unpin_message(message_id=999)
        3. 验证 _write_pins 未被调用（跳过）
        """
        service, mock_manager = mock_service

        mock_group_chat = MagicMock()
        mock_manager.load_group_chat = AsyncMock(return_value=mock_group_chat)

        existing_pins = [
            {"message_id": 1, "speaker": "agent1", "content": "msg1"},
        ]

        with patch.object(service, "_get_pins_path", return_value=Path("/tmp/pins.json")), \
             patch.object(service, "_get_pins_lock", return_value=AsyncMock()), \
             patch.object(service, "_read_pins", new_callable=AsyncMock, return_value=existing_pins), \
             patch.object(service, "_write_pins", new_callable=AsyncMock) as mock_write:

            await service.unpin_message("test-chat", 999)

            # 幂等：_write_pins 不应被调用
            mock_write.assert_not_called()
