"""测试 AgentSessionInfo 的 cwd 字段持久化"""

import os
import tempfile

import pytest

from agents_hub.core.context import GroupChatContext
from agents_hub.core.context.group_chat_session import AgentSessionInfo


class TestAgentSessionCwd:
    """测试 AgentSessionInfo 的 cwd 字段"""

    @pytest.mark.asyncio
    async def test_save_and_load_agent_cwd(self):
        """测试保存和加载 agent 的 cwd"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建上下文
            context = GroupChatContext("test-group-1", temp_dir)
            await context.load()

            # 设置 agent session info，包含 cwd
            context.agent_session_id["agent1"] = AgentSessionInfo(
                main_session="session_123",
                token="token_abc",
                cwd="/path/to/project",
            )

            # 保存
            await context.repository.save_agent_session_state(context.agent_session_id)

            # 重新加载
            loaded_state = await context.repository.load_agent_session_state()

            # 验证
            assert "agent1" in loaded_state
            assert loaded_state["agent1"].main_session == "session_123"
            assert loaded_state["agent1"].token == "token_abc"
            assert loaded_state["agent1"].cwd == "/path/to/project"

    @pytest.mark.asyncio
    async def test_backward_compatibility_no_cwd_field(self):
        """测试向后兼容：旧数据没有 cwd 字段"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建上下文
            context = GroupChatContext("test-group-2", temp_dir)
            await context.load()

            # 手动创建旧格式的 JSON 文件（没有 cwd 字段）
            import json

            session_file = context.repository.session_file
            os.makedirs(os.path.dirname(session_file), exist_ok=True)

            old_format_data = {
                "agent1": {
                    "main_session": "session_456",
                    "btw_session": [],
                    "context_state": {
                        "last_loaded_compact_index": 0,
                        "last_loaded_message_index": 0,
                    },
                    "token": "token_xyz",
                    # 注意：没有 cwd 字段
                }
            }

            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(old_format_data, f)

            # 加载
            loaded_state = await context.repository.load_agent_session_state()

            # 验证：cwd 字段应该有默认值 ""
            assert "agent1" in loaded_state
            assert loaded_state["agent1"].main_session == "session_456"
            assert loaded_state["agent1"].token == "token_xyz"
            assert loaded_state["agent1"].cwd == ""  # 默认值

    @pytest.mark.asyncio
    async def test_save_multiple_agents_with_different_cwd(self):
        """测试保存多个 agent，每个有不同的 cwd"""
        with tempfile.TemporaryDirectory() as temp_dir:
            context = GroupChatContext("test-group-3", temp_dir)
            await context.load()

            # 设置多个 agent，每个有不同的 cwd
            context.agent_session_id["agent1"] = AgentSessionInfo(
                main_session="session_1",
                token="token_1",
                cwd="/project/agent1",
            )
            context.agent_session_id["agent2"] = AgentSessionInfo(
                main_session="session_2",
                token="token_2",
                cwd="/project/agent2",
            )
            context.agent_session_id["agent3"] = AgentSessionInfo(
                main_session="session_3",
                token="token_3",
                cwd="",  # 空 cwd
            )

            # 保存
            await context.repository.save_agent_session_state(context.agent_session_id)

            # 重新加载
            loaded_state = await context.repository.load_agent_session_state()

            # 验证
            assert loaded_state["agent1"].cwd == "/project/agent1"
            assert loaded_state["agent2"].cwd == "/project/agent2"
            assert loaded_state["agent3"].cwd == ""

    @pytest.mark.asyncio
    async def test_update_cwd_after_load(self):
        """测试加载后更新 cwd"""
        with tempfile.TemporaryDirectory() as temp_dir:
            context = GroupChatContext("test-group-4", temp_dir)
            await context.load()

            # 初始保存
            context.agent_session_id["agent1"] = AgentSessionInfo(
                main_session="session_abc",
                token="token_def",
                cwd="/original/path",
            )
            await context.repository.save_agent_session_state(context.agent_session_id)

            # 重新加载
            loaded_state = await context.repository.load_agent_session_state()
            assert loaded_state["agent1"].cwd == "/original/path"

            # 更新 cwd
            loaded_state["agent1"].cwd = "/updated/path"
            await context.repository.save_agent_session_state(loaded_state)

            # 再次加载验证
            final_state = await context.repository.load_agent_session_state()
            assert final_state["agent1"].cwd == "/updated/path"
