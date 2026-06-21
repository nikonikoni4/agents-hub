from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_hub.core.foundation.models import LoopStatus
from agents_hub.mcp import INVALID_TOKEN, PERMISSION_DENIED


@pytest.mark.asyncio
async def test_loop_tools_expose_complete_docstrings():
    """契约：MCP 客户端能从工具元数据读取 Loop 工具参数和返回说明。"""
    from agents_hub.mcp.server import mcp

    expected_terms = {
        "create_loop": [
            "Args:",
            "agent_token:",
            "nodes:",
            "max_iterations:",
            "initial_task:",
            "Returns:",
            "loop_id",
        ],
        "start_loop": ["Args:", "agent_token:", "loop_id:", "Returns:", "status"],
        "stop_loop": ["Args:", "agent_token:", "loop_id:", "Returns:", "PAUSED"],
        "delete_loop": ["Args:", "agent_token:", "loop_id:", "Returns:", "success"],
        "get_loop_status": [
            "Args:",
            "agent_token:",
            "loop_id:",
            "Returns:",
            "current_iteration",
        ],
    }

    for tool_name, terms in expected_terms.items():
        tool = await mcp.get_tool(tool_name)
        description = tool.description or ""
        for term in terms:
            assert term in description, f"{tool_name} description missing {term!r}"


@pytest.fixture
def mock_group_chat_manager():
    with patch("agents_hub.mcp.server.group_chat_manager") as mock:
        mock.load_group_chat = AsyncMock()
        yield mock


@pytest.fixture
def mock_group_chat():
    mock = MagicMock()
    mock.create_loop = AsyncMock()
    mock.create_and_start_loop = AsyncMock()
    mock.stop_loop = AsyncMock()
    mock.delete_loop = AsyncMock()
    mock.get_loop_status = MagicMock()
    return mock


def _loop_nodes() -> list[dict]:
    return [
        {
            "node_type": "normal",
            "agent_name": "executor",
            "role_description": "实现代码",
            "output_schema_prompt": "必须包含执行结果",
            "output_schema_fields": ["# 执行结果"],
        },
        {
            "node_type": "terminator",
            "agent_name": "reviewer",
            "role_description": "审查代码",
            "output_schema_prompt": "必须包含审查结论",
            "output_schema_fields": ["# 审查结论"],
        },
    ]


class TestCreateLoopTool:
    @pytest.mark.asyncio
    async def test_create_loop_leader_creates_loop(
        self, mock_group_chat_manager, mock_group_chat
    ):
        from agents_hub.mcp.server import create_loop

        mock_group_chat_manager.resolve_token.return_value = ("manager", "group-1")
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat
        mock_group_chat.manager.name = "manager"

        loop = MagicMock()
        loop.loop_id = "loop-1"
        loop.status = LoopStatus.CREATED.value
        mock_group_chat.create_loop.return_value = loop

        result = await create_loop(
            agent_token="leader-token",
            nodes=_loop_nodes(),
            max_iterations=3,
            initial_task="修复 bug",
        )

        assert result == {"loop_id": "loop-1", "status": LoopStatus.CREATED.value}
        mock_group_chat.create_loop.assert_awaited_once_with(
            nodes=_loop_nodes(),
            max_iterations=3,
            initial_task="修复 bug",
        )

    @pytest.mark.asyncio
    async def test_create_loop_rejects_invalid_token(self, mock_group_chat_manager):
        from agents_hub.mcp.server import create_loop

        mock_group_chat_manager.resolve_token.return_value = None

        result = await create_loop(
            agent_token="bad-token",
            nodes=_loop_nodes(),
            max_iterations=3,
            initial_task="修复 bug",
        )

        assert result["error"]["code"] == INVALID_TOKEN

    @pytest.mark.asyncio
    async def test_create_loop_rejects_non_leader(
        self, mock_group_chat_manager, mock_group_chat
    ):
        from agents_hub.mcp.server import create_loop

        mock_group_chat_manager.resolve_token.return_value = ("worker", "group-1")
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat
        mock_group_chat.manager.name = "manager"

        result = await create_loop(
            agent_token="worker-token",
            nodes=_loop_nodes(),
            max_iterations=3,
            initial_task="修复 bug",
        )

        assert result["error"]["code"] == PERMISSION_DENIED
        mock_group_chat.create_loop.assert_not_called()


class TestStartLoopTool:
    @pytest.mark.asyncio
    async def test_start_loop_leader_starts_loop(
        self, mock_group_chat_manager, mock_group_chat
    ):
        from agents_hub.mcp.server import start_loop

        mock_group_chat_manager.resolve_token.return_value = ("manager", "group-1")
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat
        mock_group_chat.manager.name = "manager"

        loop = MagicMock()
        loop.loop_id = "loop-1"
        loop.status = LoopStatus.RUNNING.value
        mock_group_chat.create_and_start_loop.return_value = loop

        result = await start_loop(agent_token="leader-token", loop_id="loop-1")

        assert result == {"loop_id": "loop-1", "status": LoopStatus.RUNNING.value}
        mock_group_chat.create_and_start_loop.assert_awaited_once_with("loop-1")

    @pytest.mark.asyncio
    async def test_start_loop_rejects_non_leader(
        self, mock_group_chat_manager, mock_group_chat
    ):
        from agents_hub.mcp.server import start_loop

        mock_group_chat_manager.resolve_token.return_value = ("worker", "group-1")
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat
        mock_group_chat.manager.name = "manager"

        result = await start_loop(agent_token="worker-token", loop_id="loop-1")

        assert result["error"]["code"] == PERMISSION_DENIED
        mock_group_chat.create_and_start_loop.assert_not_called()


class TestStopDeleteStatusLoopTools:
    @pytest.mark.asyncio
    async def test_get_loop_status_allows_any_agent(
        self, mock_group_chat_manager, mock_group_chat
    ):
        from agents_hub.mcp.server import get_loop_status

        mock_group_chat_manager.resolve_token.return_value = ("worker", "group-1")
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat
        mock_group_chat.get_loop_status.return_value = {
            "loop_id": "loop-1",
            "status": LoopStatus.RUNNING.value,
            "current_iteration": 2,
            "max_iterations": 3,
            "current_node": "reviewer",
            "error": None,
        }

        result = await get_loop_status(agent_token="worker-token", loop_id="loop-1")

        assert result["status"] == LoopStatus.RUNNING.value
        assert result["current_node"] == "reviewer"
        mock_group_chat.get_loop_status.assert_called_once_with("loop-1")

    @pytest.mark.asyncio
    async def test_stop_loop_leader_pauses_running_loop(
        self, mock_group_chat_manager, mock_group_chat
    ):
        from agents_hub.mcp.server import stop_loop

        mock_group_chat_manager.resolve_token.return_value = ("manager", "group-1")
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat
        mock_group_chat.manager.name = "manager"

        loop = MagicMock()
        loop.loop_id = "loop-1"
        loop.status = LoopStatus.PAUSED.value
        mock_group_chat.stop_loop.return_value = loop

        result = await stop_loop(agent_token="leader-token", loop_id="loop-1")

        assert result == {"loop_id": "loop-1", "status": LoopStatus.PAUSED.value}
        mock_group_chat.stop_loop.assert_awaited_once_with("loop-1")

    @pytest.mark.asyncio
    async def test_delete_loop_leader_deletes_non_running_loop(
        self, mock_group_chat_manager, mock_group_chat
    ):
        from agents_hub.mcp.server import delete_loop

        mock_group_chat_manager.resolve_token.return_value = ("manager", "group-1")
        mock_group_chat_manager.load_group_chat.return_value = mock_group_chat
        mock_group_chat.manager.name = "manager"

        result = await delete_loop(agent_token="leader-token", loop_id="loop-1")

        assert result == {"success": True}
        mock_group_chat.delete_loop.assert_awaited_once_with("loop-1")
