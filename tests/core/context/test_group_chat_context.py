"""
测试 GroupChatContext 的 agent_member.json 持久化功能
"""

import tempfile

import pytest

from agents_hub.config.types import AgentPlatform
from agents_hub.core.context.group_chat_context import GroupChatContext
from agents_hub.core.context.group_chat_runtime import GroupChatRuntime


class MockAgentResult:
    """模拟 AgentResult"""

    def __init__(
        self,
        agent_name: str,
        session_id: str,
        text: str = "test message",
        timestamp: str = "2024-01-01T00:00:00",
        platform: AgentPlatform = AgentPlatform.CLAUDE,
    ):
        self.agent_name = agent_name
        self.session_id = session_id
        self.text = text
        self.timestamp = timestamp
        self.platform = platform


class TestGroupChatContextTokenPersistence:
    """测试 agent_member.json 的 token 持久化功能"""

    @pytest.mark.asyncio
    async def test_save_and_load_agent_token(self):
        """测试保存和加载 agent token"""
        with tempfile.TemporaryDirectory() as tmpdir:
            group_chat_id = "test_chat_001"
            runtime = GroupChatRuntime(group_chat_id, tmpdir)
            context = GroupChatContext(runtime)
            await context.load()

            # 创建 AgentSessionInfo 并设置 token
            agent_name = "agent_a"
            session_id = "session_123"
            agent_token = "tok_a1b2c3d4e5f6"

            # 模拟 update_agent_session_id
            agent_result = MockAgentResult(agent_name, session_id)
            await context.update_agent_session_id(agent_result)

            # 手动设置 token
            context.agent_session_id[agent_name].token = agent_token
            await runtime.repository.save_agent_member(context.agent_session_id)

            # 创建新的 context 并加载
            runtime2 = GroupChatRuntime(group_chat_id, tmpdir)
            context2 = GroupChatContext(runtime2)
            await context2.load()

            # 验证 token 被正确加载
            assert agent_name in context2.agent_session_id
            assert context2.agent_session_id[agent_name].token == agent_token
            assert context2.agent_session_id[agent_name].main_session == session_id

            context.close()
            context2.close()

    @pytest.mark.asyncio
    async def test_save_multiple_agent_tokens(self):
        """测试保存多个 agent 的 token"""
        with tempfile.TemporaryDirectory() as tmpdir:
            group_chat_id = "test_chat_002"
            runtime = GroupChatRuntime(group_chat_id, tmpdir)
            context = GroupChatContext(runtime)
            await context.load()

            # 创建多个 agent 的 session info
            agents = [
                ("agent_a", "session_a", "tok_aaa"),
                ("agent_b", "session_b", "tok_bbb"),
                ("agent_c", "session_c", "tok_ccc"),
            ]

            for agent_name, session_id, token in agents:
                agent_result = MockAgentResult(agent_name, session_id)
                await context.update_agent_session_id(agent_result)
                context.agent_session_id[agent_name].token = token

            await runtime.repository.save_agent_member(context.agent_session_id)

            # 创建新的 context 并加载
            runtime2 = GroupChatRuntime(group_chat_id, tmpdir)
            context2 = GroupChatContext(runtime2)
            await context2.load()

            # 验证所有 token 都被正确加载
            for agent_name, session_id, token in agents:
                assert agent_name in context2.agent_session_id
                assert context2.agent_session_id[agent_name].token == token
                assert context2.agent_session_id[agent_name].main_session == session_id

            context.close()
            context2.close()

    @pytest.mark.asyncio
    async def test_backward_compatibility_no_token_field(self):
        """测试向后兼容：旧文件没有 token 字段时不报错"""
        with tempfile.TemporaryDirectory() as tmpdir:
            group_chat_id = "test_chat_003"
            runtime = GroupChatRuntime(group_chat_id, tmpdir)
            context = GroupChatContext(runtime)
            await context.load()

            # 创建一个没有 token 字段的旧格式文件
            agent_name = "agent_a"
            session_id = "session_123"
            agent_result = MockAgentResult(agent_name, session_id)
            await context.update_agent_session_id(agent_result)

            # 手动修改文件，移除 token 字段（模拟旧文件）
            import json

            agent_member_file = runtime.repository.agent_member_file
            with open(agent_member_file, encoding="utf-8") as f:
                data = json.load(f)

            # 移除 token 字段
            if "token" in data[agent_name]:
                del data[agent_name]["token"]

            with open(agent_member_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 创建新的 context 并加载（应该不报错）
            runtime2 = GroupChatRuntime(group_chat_id, tmpdir)
            context2 = GroupChatContext(runtime2)
            await context2.load()

            # 验证加载成功，token 为空字符串（默认值）
            assert agent_name in context2.agent_session_id
            assert context2.agent_session_id[agent_name].token == ""
            assert context2.agent_session_id[agent_name].main_session == session_id

            context.close()
            context2.close()

    @pytest.mark.asyncio
    async def test_empty_token_field(self):
        """测试 token 字段为空字符串"""
        with tempfile.TemporaryDirectory() as tmpdir:
            group_chat_id = "test_chat_004"
            runtime = GroupChatRuntime(group_chat_id, tmpdir)
            context = GroupChatContext(runtime)
            await context.load()

            # 创建 AgentSessionInfo，token 为空
            agent_name = "agent_a"
            session_id = "session_123"
            agent_result = MockAgentResult(agent_name, session_id)
            await context.update_agent_session_id(agent_result)

            # token 默认为空字符串
            await runtime.repository.save_agent_member(context.agent_session_id)

            # 创建新的 context 并加载
            runtime2 = GroupChatRuntime(group_chat_id, tmpdir)
            context2 = GroupChatContext(runtime2)
            await context2.load()

            # 验证 token 为空字符串
            assert agent_name in context2.agent_session_id
            assert context2.agent_session_id[agent_name].token == ""

            context.close()
            context2.close()

    @pytest.mark.asyncio
    async def test_update_token_after_load(self):
        """测试加载后更新 token"""
        with tempfile.TemporaryDirectory() as tmpdir:
            group_chat_id = "test_chat_005"
            runtime = GroupChatRuntime(group_chat_id, tmpdir)
            context = GroupChatContext(runtime)
            await context.load()

            # 创建 agent session
            agent_name = "agent_a"
            session_id = "session_123"
            agent_result = MockAgentResult(agent_name, session_id)
            await context.update_agent_session_id(agent_result)

            # 第一次保存，token 为空
            await runtime.repository.save_agent_member(context.agent_session_id)

            # 更新 token
            new_token = "tok_new_token"
            context.agent_session_id[agent_name].token = new_token
            await runtime.repository.save_agent_member(context.agent_session_id)

            # 创建新的 context 并加载
            runtime2 = GroupChatRuntime(group_chat_id, tmpdir)
            context2 = GroupChatContext(runtime2)
            await context2.load()

            # 验证 token 被更新
            assert context2.agent_session_id[agent_name].token == new_token

            context.close()
            context2.close()

    @pytest.mark.asyncio
    async def test_token_persistence_with_context_state(self):
        """测试 token 与 context_state 一起持久化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            group_chat_id = "test_chat_006"
            runtime = GroupChatRuntime(group_chat_id, tmpdir)
            context = GroupChatContext(runtime)
            await context.load()

            # 创建 agent session
            agent_name = "agent_a"
            session_id = "session_123"
            agent_result = MockAgentResult(agent_name, session_id)
            await context.update_agent_session_id(agent_result)

            # 设置 token 和 context_state
            context.agent_session_id[agent_name].token = "tok_test"
            context.agent_session_id[agent_name].context_state.last_loaded_compact_index = 5
            context.agent_session_id[agent_name].context_state.last_loaded_message_index = 10
            await runtime.repository.save_agent_member(context.agent_session_id)

            # 创建新的 context 并加载
            runtime2 = GroupChatRuntime(group_chat_id, tmpdir)
            context2 = GroupChatContext(runtime2)
            await context2.load()

            # 验证所有字段都被正确加载
            assert context2.agent_session_id[agent_name].token == "tok_test"
            assert context2.agent_session_id[agent_name].context_state.last_loaded_compact_index == 5
            assert context2.agent_session_id[agent_name].context_state.last_loaded_message_index == 10

            context.close()
            context2.close()
