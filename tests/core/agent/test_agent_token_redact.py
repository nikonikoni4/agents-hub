"""测试公开群聊写入路径的 token 剥离

Agent.run() 的普通执行文本默认私下保留，不再自动写入群聊。
token 剥离应发生在显式公开工具 speak_in_group_chat / finish_agent_call 中。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_hub.config.types import AgentPlatform, RoleType
from agents_hub.core.foundation import CallStatus, MessageType
from agents_hub.core.foundation.token import generate_token


@pytest.mark.asyncio
async def test_speak_in_group_chat_redacts_token():
    """契约：speak_in_group_chat 写群聊前剥离 token"""
    from agents_hub.mcp.server import speak_in_group_chat

    token = generate_token()
    group_chat = MagicMock()
    group_chat.group_chat_context.add_message = AsyncMock()

    with patch("agents_hub.mcp.server.group_chat_manager") as manager:
        manager.resolve_token.return_value = ("worker", "group_1")
        manager.load_group_chat = AsyncMock(return_value=group_chat)

        result = await speak_in_group_chat(
            agent_token="agent_token",
            content=f"公开内容包含 {token}",
            send_to="Leader",
        )

    assert result == {"ok": True}
    group_chat.group_chat_context.add_message.assert_called_once()
    agent_result = group_chat.group_chat_context.add_message.call_args.args[0]
    assert "[REDACTED]" in agent_result.text
    assert token not in agent_result.text
    assert agent_result.text.startswith("@Leader ")


@pytest.mark.asyncio
async def test_finish_agent_call_redacts_token_before_result_and_group_chat():
    """契约：finish_agent_call 写 call result 和群聊前都剥离 token"""
    from agents_hub.mcp.server import finish_agent_call

    token = generate_token()
    group_chat = MagicMock()
    group_chat.group_chat_context.add_message = AsyncMock()
    call = MagicMock()
    call.call_id = "call_1"
    call.send_from = "user"
    call.send_to = "worker"
    call.message_type = MessageType.TASK
    call.has_agent_response = False
    group_chat.agent_call_manager.get_call.return_value = call

    with patch("agents_hub.mcp.server.group_chat_manager") as manager:
        manager.resolve_token.return_value = ("worker", "group_1")
        manager.load_group_chat = AsyncMock(return_value=group_chat)

        result = await finish_agent_call(
            agent_token="agent_token",
            call_id="call_1",
            content=f"任务完成，token={token}",
            success=True,
        )

    assert result == {"call_id": "call_1", "status": CallStatus.COMPLETED.value}
    group_chat.agent_call_manager.mark_agent_response.assert_called_once_with(
        call_id="call_1",
        content="任务完成，token=[REDACTED]",
        success=True,
    )
    group_chat.group_chat_context.add_message.assert_called_once()
    agent_result = group_chat.group_chat_context.add_message.call_args.args[0]
    assert "[REDACTED]" in agent_result.text
    assert token not in agent_result.text
    assert agent_result.text.startswith("@user ")


@pytest.mark.asyncio
async def test_speak_in_group_chat_uses_agent_metadata():
    """契约：群聊消息沿用发言 Agent 的平台和角色元数据"""
    from agents_hub.mcp.server import speak_in_group_chat

    group_chat = MagicMock()
    group_chat.group_chat_context.add_message = AsyncMock()
    worker = MagicMock()
    worker.name = "worker"
    worker.role_type = RoleType.LEADER
    worker.role_config.platform = AgentPlatform.CODEX
    group_chat.manager = None
    group_chat.workers = {"worker": worker}

    with patch("agents_hub.mcp.server.group_chat_manager") as manager:
        manager.resolve_token.return_value = ("worker", "group_1")
        manager.load_group_chat = AsyncMock(return_value=group_chat)

        result = await speak_in_group_chat(
            agent_token="agent_token",
            content="公开内容",
        )

    assert result == {"ok": True}
    agent_result = group_chat.group_chat_context.add_message.call_args.args[0]
    assert agent_result.platform == AgentPlatform.CODEX
    assert agent_result.role_type == RoleType.LEADER
