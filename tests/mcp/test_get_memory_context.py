"""get_memory_context MCP 工具测试

测试记忆助手上下文获取工具：
- Token 验证
- 角色权限校验（仅记忆助手可调用）
- history.jsonl 读取
- 新消息获取
- 上下文拼接
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_hub.mcp.errors import (
    INVALID_TOKEN,
    PERMISSION_DENIED,
)


@pytest.fixture
def mock_group_chat_manager():
    with patch("agents_hub.mcp.server.group_chat_manager") as mock:
        mock.load_group_chat = AsyncMock()
        yield mock


@pytest.fixture
def mock_group_chat():
    mock = MagicMock()
    mock.group_chat_id = "group_123"
    return mock


@pytest.fixture
def tmp_memory_path(tmp_path: Path) -> Path:
    return tmp_path / "memory"


class TestGetMemoryContextTokenValidation:
    """Token 验证测试"""

    @pytest.mark.asyncio
    async def test_invalid_token_returns_error(self, mock_group_chat_manager):
        from agents_hub.mcp.server import get_memory_context

        mock_group_chat_manager.resolve_token.return_value = None
        result = await get_memory_context(
            agent_token="bad-token",
            group_chat_id="group_123",
        )
        assert "error" in result
        assert result["error"]["code"] == INVALID_TOKEN

    @pytest.mark.asyncio
    async def test_group_chat_not_found_returns_error(self, mock_group_chat_manager):
        from agents_hub.mcp.server import get_memory_context

        mock_group_chat_manager.resolve_token.return_value = ("agent_1", "group_123")
        mock_group_chat_manager.load_group_chat.side_effect = Exception("not found")
        result = await get_memory_context(
            agent_token="valid-token",
            group_chat_id="group_123",
        )
        assert "error" in result


class TestGetMemoryContextPermission:
    """角色权限校验测试"""

    @pytest.mark.asyncio
    async def test_non_memory_assistant_denied(self, mock_group_chat_manager, mock_group_chat):
        from agents_hub.mcp.server import get_memory_context

        mock_group_chat_manager.resolve_token.return_value = ("some_agent", "group_123")
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat
        with patch("agents_hub.mcp.server.config") as mock_config:
            mock_config.default_memory_assistant_name = "Agents-Hub-Memory-Assistant"
            mock_config.memory_path = Path("/tmp/memory")
            result = await get_memory_context(
                agent_token="valid-token",
                group_chat_id="group_123",
            )
        assert "error" in result
        assert result["error"]["code"] == PERMISSION_DENIED

    @pytest.mark.asyncio
    async def test_memory_assistant_allowed(
        self, mock_group_chat_manager, mock_group_chat, tmp_memory_path
    ):
        from agents_hub.mcp.server import get_memory_context

        mock_group_chat_manager.resolve_token.return_value = (
            "Agents-Hub-Memory-Assistant",
            "group_123",
        )
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        # 创建 history.jsonl
        history_dir = tmp_memory_path / "agents_hub_history"
        history_dir.mkdir(parents=True)
        history_file = history_dir / "history.jsonl"
        history_file.write_text(
            '{"timestamp": "2026-06-24T10:00:00Z", "summary": "测试总结"}\n',
            encoding="utf-8",
        )

        with (
            patch("agents_hub.mcp.server.config") as mock_config,
            patch(
                "agents_hub.mcp.server.get_group_chat_messages",
                return_value="新消息内容",
            ),
        ):
            mock_config.default_memory_assistant_name = "Agents-Hub-Memory-Assistant"
            mock_config.memory_path = tmp_memory_path
            result = await get_memory_context(
                agent_token="valid-token",
                group_chat_id="group_123",
            )

        assert "error" not in result
        assert result["group_chat_id"] == "group_123"
        assert "history_summary" in result
        assert "new_messages" in result
        assert "context" in result


class TestGetMemoryContextData:
    """数据读取和拼接测试"""

    @pytest.mark.asyncio
    async def test_no_history_file_returns_empty_summary(
        self, mock_group_chat_manager, mock_group_chat, tmp_memory_path
    ):
        from agents_hub.mcp.server import get_memory_context

        mock_group_chat_manager.resolve_token.return_value = (
            "Agents-Hub-Memory-Assistant",
            "group_123",
        )
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        with (
            patch("agents_hub.mcp.server.config") as mock_config,
            patch(
                "agents_hub.mcp.server.get_group_chat_messages",
                return_value="新消息",
            ),
        ):
            mock_config.default_memory_assistant_name = "Agents-Hub-Memory-Assistant"
            mock_config.memory_path = tmp_memory_path
            result = await get_memory_context(
                agent_token="valid-token",
                group_chat_id="group_123",
            )

        assert "error" not in result
        assert result["history_summary"] == ""
        assert result["new_messages"] == "新消息"
        assert "新消息" in result["context"]

    @pytest.mark.asyncio
    async def test_with_history_and_messages(
        self, mock_group_chat_manager, mock_group_chat, tmp_memory_path
    ):
        from agents_hub.mcp.server import get_memory_context

        mock_group_chat_manager.resolve_token.return_value = (
            "Agents-Hub-Memory-Assistant",
            "group_123",
        )
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        history_dir = tmp_memory_path / "agents_hub_history"
        history_dir.mkdir(parents=True)
        history_file = history_dir / "history.jsonl"
        history_file.write_text(
            '{"timestamp": "2026-06-24T10:00:00Z", "summary": "历史总结内容"}\n',
            encoding="utf-8",
        )

        with (
            patch("agents_hub.mcp.server.config") as mock_config,
            patch(
                "agents_hub.mcp.server.get_group_chat_messages",
                return_value="新消息内容",
            ),
        ):
            mock_config.default_memory_assistant_name = "Agents-Hub-Memory-Assistant"
            mock_config.memory_path = tmp_memory_path
            result = await get_memory_context(
                agent_token="valid-token",
                group_chat_id="group_123",
                last_updated="2026-06-24T10:00:00Z",
            )

        assert "error" not in result
        assert result["history_summary"] == "历史总结内容"
        assert result["new_messages"] == "新消息内容"
        assert "历史总结内容" in result["context"]
        assert "新消息内容" in result["context"]

    @pytest.mark.asyncio
    async def test_with_last_updated_passes_to_get_messages(
        self, mock_group_chat_manager, mock_group_chat, tmp_memory_path
    ):
        from agents_hub.mcp.server import get_memory_context

        mock_group_chat_manager.resolve_token.return_value = (
            "Agents-Hub-Memory-Assistant",
            "group_123",
        )
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat

        with (
            patch("agents_hub.mcp.server.config") as mock_config,
            patch(
                "agents_hub.mcp.server.get_group_chat_messages",
                return_value="新消息",
            ) as mock_get_messages,
        ):
            mock_config.default_memory_assistant_name = "Agents-Hub-Memory-Assistant"
            mock_config.memory_path = tmp_memory_path
            await get_memory_context(
                agent_token="valid-token",
                group_chat_id="group_123",
                last_updated="2026-06-24T10:00:00Z",
            )

        # 验证 last_updated 被转换为 datetime 传给 get_group_chat_messages
        mock_get_messages.assert_called_once()
        call_args = mock_get_messages.call_args
        assert call_args[0][0] == "group_123"
        assert call_args[1]["after_time"] is not None
