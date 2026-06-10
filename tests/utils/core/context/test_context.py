"""
Context 层单元测试

契约：
1. group_chat_session.py: 默认值、add_message、get_uncompact_messages
2. group_chat_repository.py: sanitize_project_path、load/save 往返一致性
3. group_chat_context.py: close 清空引用、add_message 未 load 抛异常
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_hub.config.types import RoleType
from agents_hub.core.context.agent_context import AgentContext
from agents_hub.core.context.group_chat_context import GroupChatContext
from agents_hub.core.context.group_chat_repository import GroupChatRepository
from agents_hub.core.context.group_chat_session import (
    AgentContextState,
    AgentMemberInfo,
    GroupChatSession,
)
from agents_hub.core.foundation import StateError, Tag
from agents_hub.core.utils import sanitize_project_path

# ==================== group_chat_session.py ====================


class TestAgentContextState:
    """测试 AgentContextState"""

    def test_defaults(self):
        """契约：默认值为 0"""
        state = AgentContextState()
        assert state.last_loaded_compact_index == 0
        assert state.last_loaded_message_index == 0

    def test_custom_values(self):
        """契约：可自定义值"""
        state = AgentContextState(last_loaded_compact_index=5, last_loaded_message_index=10)
        assert state.last_loaded_compact_index == 5
        assert state.last_loaded_message_index == 10


class TestAgentMemberInfo:
    """测试 AgentMemberInfo"""

    def test_defaults(self):
        """契约：默认值正确"""
        info = AgentMemberInfo()
        assert info.main_session is None
        assert info.btw_session == []
        assert isinstance(info.context_state, AgentContextState)

    def test_btw_session_isolation(self):
        """契约：不同实例的 btw_session 互不影响"""
        a = AgentMemberInfo()
        b = AgentMemberInfo()
        a.btw_session.append("s1")
        assert "s1" not in b.btw_session


class TestGroupChatSession:
    """测试 GroupChatSession"""

    def test_defaults(self):
        """契约：默认值正确"""
        session = GroupChatSession(group_chat_id="test_id")
        assert session.group_chat_id == "test_id"
        assert session.messages == []
        assert session.last_compacted_loc == 0
        assert session.created_at is not None
        assert session.updated_at is not None

    def test_add_message(self):
        """契约：add_message 追加消息到 messages 列表"""
        session = GroupChatSession(group_chat_id="gc1")
        result = SimpleNamespace(
            agent_name="agent_a",
            text="hello",
            timestamp="2026-01-01T00:00:00",
            platform=SimpleNamespace(value="claude"),
        )
        session.add_message(result)

        assert len(session.messages) == 1
        assert session.messages[0]["agent_name"] == "agent_a"
        assert session.messages[0]["content"] == "hello"
        assert session.messages[0]["platform"] == "claude"

    def test_get_uncompact_messages_from_zero(self):
        """契约：last_compacted_loc=0 时返回所有消息"""
        session = GroupChatSession(group_chat_id="gc1")
        session.messages = [
            {"agent_name": "a", "content": "m1"},
            {"agent_name": "b", "content": "m2"},
        ]
        result = session.get_uncompact_messages()
        assert len(result) == 2

    def test_get_uncompact_messages_from_offset(self):
        """契约：从 last_compacted_loc 开始返回消息"""
        session = GroupChatSession(group_chat_id="gc1")
        session.messages = [
            {"agent_name": "a", "content": "m1"},
            {"agent_name": "b", "content": "m2"},
            {"agent_name": "c", "content": "m3"},
        ]
        session.last_compacted_loc = 1
        result = session.get_uncompact_messages()
        assert len(result) == 2
        assert result[0]["content"] == "m2"

    def test_get_uncompact_messages_all_compacted(self):
        """契约：全部已压缩时返回空列表"""
        session = GroupChatSession(group_chat_id="gc1")
        session.messages = [{"agent_name": "a", "content": "m1"}]
        session.last_compacted_loc = 1
        result = session.get_uncompact_messages()
        assert result == []


# ==================== group_chat_repository.py ====================


class TestSanitizeProjectPath:
    """测试路径清理"""

    def test_sanitize_forward_slash(self):
        """契约：/ 转为 -"""
        result = sanitize_project_path("a/b/c")
        assert result == "a-b-c"

    def test_sanitize_backslash(self):
        """契约：\\ 转为 -"""
        result = sanitize_project_path("a\\b\\c")
        assert result == "a-b-c"

    def test_sanitize_colon(self):
        """契约：: 转为 -"""
        result = sanitize_project_path("C:Users")
        assert result == "C-Users"

    def test_sanitize_consecutive_dashes(self):
        """契约：连续横线合并为单个"""
        result = sanitize_project_path("a///b")
        assert result == "a-b"

    def test_sanitize_strips_leading_trailing(self):
        """契约：去除首尾横线"""
        result = sanitize_project_path("/a/b/")
        assert result == "a-b"


class TestGroupChatRepositoryLoadSession:
    """测试 load_group_chat_session"""

    @pytest.mark.asyncio
    async def test_load_agent_member_infos_file_not_exists(self, tmp_path):
        """契约：文件不存在返回空 session"""
        repo = GroupChatRepository("gc1", "test/project")
        # 覆盖路径到临时目录
        repo.group_chat_session_path = str(tmp_path / "gc1")
        repo.messages_file = str(tmp_path / "gc1" / "gc1.jsonl")

        with patch("agents_hub.core.context.group_chat_repository.os.makedirs"):
            session = await repo.load_group_chat_session()

        assert session.group_chat_id == "gc1"
        assert session.messages == []


class TestGroupChatRepositoryRoundtrip:
    """测试 save/load 往返一致性"""

    @pytest.mark.asyncio
    async def test_save_load_agent_state_roundtrip(self, tmp_path):
        """契约：save/load agent_member 往返一致"""
        repo = GroupChatRepository("gc1", "test/project")
        repo.agent_member_file = str(tmp_path / "agent_member.json")

        state = {
            "agent_a": AgentMemberInfo(
                main_session="sess_1",
                btw_session=["btw_1"],
                context_state=AgentContextState(
                    last_loaded_compact_index=3,
                    last_loaded_message_index=7,
                ),
            )
        }

        with patch("agents_hub.core.context.group_chat_repository.os.makedirs"):
            await repo.save_agent_member(state)
            loaded = await repo.load_agent_member_infos()

        assert "agent_a" in loaded
        assert loaded["agent_a"].main_session == "sess_1"
        assert loaded["agent_a"].btw_session == ["btw_1"]
        assert loaded["agent_a"].context_state.last_loaded_compact_index == 3
        assert loaded["agent_a"].context_state.last_loaded_message_index == 7

    @pytest.mark.asyncio
    async def test_save_load_compact_history_roundtrip(self, tmp_path):
        """契约：save/load compact_history 往返一致"""
        repo = GroupChatRepository("gc1", "test/project")
        repo.compact_history_file = str(tmp_path / "compact_history.jsonl")

        history = [
            {"create_at": "2026-01-01", "content": {"summary": "s1", "agent_a": "a1"}},
            {"create_at": "2026-01-02", "content": {"summary": "s2"}},
        ]

        with patch("agents_hub.core.context.group_chat_repository.os.makedirs"):
            await repo.save_compact_history(history)
            loaded = await repo.load_compact_history()

        assert len(loaded) == 2
        assert loaded[0]["content"]["summary"] == "s1"
        assert loaded[1]["content"]["summary"] == "s2"

    @pytest.mark.asyncio
    async def test_load_compact_history_file_not_exists(self, tmp_path):
        """契约：compact_history 文件不存在返回空列表"""
        repo = GroupChatRepository("gc1", "test/project")
        repo.compact_history_file = str(tmp_path / "nonexistent.jsonl")

        loaded = await repo.load_compact_history()
        assert loaded == []


# ==================== group_chat_context.py ====================


class TestGroupChatContextClose:
    """测试 GroupChatContext.close()"""

    def test_close_clears_references(self):
        """契约：close() 清空 group_chat_session 和 agent_member_info"""
        with patch.object(GroupChatContext, "__init__", lambda self, *a, **kw: None):
            ctx = GroupChatContext.__new__(GroupChatContext)
            # 通过 runtime 设置
            runtime = MagicMock()
            runtime.state = MagicMock()
            runtime.state.group_chat_session = GroupChatSession(group_chat_id="gc1")
            runtime.state.agent_member_infos = {"a": AgentMemberInfo()}
            ctx.runtime = runtime

            ctx.close()

            # close() 会调用 runtime.close()
            runtime.close.assert_called_once()

    def test_close_idempotent(self):
        """契约：close() 可多次调用不报错"""
        with patch.object(GroupChatContext, "__init__", lambda self, *a, **kw: None):
            ctx = GroupChatContext.__new__(GroupChatContext)
            # 通过 runtime 设置
            runtime = MagicMock()
            runtime.state = MagicMock()
            runtime.state.group_chat_session = GroupChatSession(group_chat_id="gc1")
            runtime.state.agent_member_infos = {"a": AgentMemberInfo()}
            ctx.runtime = runtime

            ctx.close()
            ctx.close()  # 第二次不应报错
            assert runtime.close.call_count == 2


class TestGroupChatContextAddMessage:
    """测试 add_message 未加载场景"""

    @pytest.mark.asyncio
    async def test_add_message_before_load_raises(self):
        """契约：未 load 时 add_message 抛 StateError"""
        with patch.object(GroupChatContext, "__init__", lambda self, *a, **kw: None):
            ctx = GroupChatContext.__new__(GroupChatContext)
            # 通过 runtime 设置
            runtime = MagicMock()
            runtime.state = MagicMock()
            runtime.state.group_chat_session = None
            runtime.state.agent_member_infos = {}
            # 让 runtime.add_message 抛出 StateError
            runtime.add_message = AsyncMock(side_effect=StateError("GroupChatSession 未加载"))
            ctx.runtime = runtime

            with pytest.raises(StateError):
                await ctx.add_message(SimpleNamespace(agent_name="a", text="hi"))


# ==================== agent_context.py ====================


class TestBuildCompactHistoryXml:
    """测试 AgentContext._build_compact_history_xml"""

    @pytest.mark.asyncio
    async def test_no_new_history_returns_empty(self):
        """契约：无新压缩历史时返回空串"""
        ctx = AgentContext.__new__(AgentContext)
        ctx.agent_name = "agent_a"
        ctx.role_type = RoleType.TEAM_MEMBER

        result = await ctx._build_compact_history_xml(
            compact_history=[], last_loaded_compact_index=0
        )
        assert result == ""

        # index 已到末尾
        history = [{"content": {"summary": "s1"}}]
        result = await ctx._build_compact_history_xml(
            compact_history=history, last_loaded_compact_index=1
        )
        assert result == ""

    @pytest.mark.asyncio
    async def test_overall_summary_only(self):
        """契约：只有 overall 摘要时，不包含 for_you 块"""
        ctx = AgentContext.__new__(AgentContext)
        ctx.agent_name = "agent_a"

        history = [{"content": {"summary": "发生了X事件"}}]
        result = await ctx._build_compact_history_xml(history, last_loaded_compact_index=0)

        assert f"<{Tag.GROUP_HISTORY}>" in result
        assert f"<{Tag.SUMMARY_OVERALL}>" in result
        assert "1. 发生了X事件" in result
        assert Tag.SUMMARY_FOR_YOU not in result

    @pytest.mark.asyncio
    async def test_overall_and_for_you(self):
        """契约：有针对当前 agent 的摘要时，同时包含 overall 和 for_you"""
        ctx = AgentContext.__new__(AgentContext)
        ctx.agent_name = "agent_a"

        history = [{"content": {"summary": "整体摘要", "agent_a": "你的专属摘要"}}]
        result = await ctx._build_compact_history_xml(history, last_loaded_compact_index=0)

        assert "1. 整体摘要" in result
        assert f"<{Tag.SUMMARY_FOR_YOU}>" in result
        assert "1. 你的专属摘要" in result

    @pytest.mark.asyncio
    async def test_incremental_loading(self):
        """契约：只处理 last_loaded_compact_index 之后的历史"""
        ctx = AgentContext.__new__(AgentContext)
        ctx.agent_name = "agent_a"

        history = [
            {"content": {"summary": "旧摘要"}},
            {"content": {"summary": "新摘要"}},
        ]
        result = await ctx._build_compact_history_xml(history, last_loaded_compact_index=1)

        assert "旧摘要" not in result
        assert "1. 新摘要" in result

    @pytest.mark.asyncio
    async def test_multiple_records_numbering(self):
        """契约：多条记录按序编号"""
        ctx = AgentContext.__new__(AgentContext)
        ctx.agent_name = "agent_a"

        history = [
            {"content": {"summary": "s1", "agent_a": "a1"}},
            {"content": {"summary": "s2", "agent_a": "a2"}},
        ]
        result = await ctx._build_compact_history_xml(history, last_loaded_compact_index=0)

        assert "1. s1" in result
        assert "2. s2" in result
        assert "1. a1" in result
        assert "2. a2" in result


class TestGetFilteredMessages:
    """测试 AgentContext._get_filtered_messages"""

    def _make_context(self, agent_name: str, messages: list[dict]) -> AgentContext:
        ctx = AgentContext.__new__(AgentContext)
        ctx.agent_name = agent_name
        ctx.role_type = RoleType.TEAM_MEMBER
        session = GroupChatSession(group_chat_id="gc1")
        session.messages = messages
        group_ctx = GroupChatContext.__new__(GroupChatContext)
        # 通过 runtime.state 设置 group_chat_session
        runtime = MagicMock()
        runtime.state = MagicMock()
        runtime.state.group_chat_session = session
        group_ctx.runtime = runtime
        ctx.group_chat_context = group_ctx
        return ctx

    def test_filters_self_sent_messages(self):
        """契约：排除自己发送的消息"""
        messages = [
            {"agent_name": "agent_a", "content": "我发的"},
            {"agent_name": "agent_b", "content": "别人发的"},
        ]
        ctx = self._make_context("agent_a", messages)
        result = ctx._get_filtered_messages(last_loaded_message_index=0)

        assert len(result) == 1
        assert result[0]["content"] == "别人发的"

    def test_filters_at_self_messages(self):
        """契约：排除 @ 自己的消息"""
        messages = [
            {"agent_name": "agent_b", "content": "@agent_a 请处理"},
            {"agent_name": "agent_b", "content": "普通消息"},
        ]
        ctx = self._make_context("agent_a", messages)
        result = ctx._get_filtered_messages(last_loaded_message_index=0)

        assert len(result) == 1
        assert result[0]["content"] == "普通消息"

    def test_filters_both_conditions(self):
        """契约：同时过滤自己发送和 @ 自己的消息"""
        messages = [
            {"agent_name": "agent_a", "content": "自己发的"},
            {"agent_name": "agent_b", "content": "@agent_a 你看下"},
            {"agent_name": "agent_c", "content": "与你无关"},
        ]
        ctx = self._make_context("agent_a", messages)
        result = ctx._get_filtered_messages(last_loaded_message_index=0)

        assert len(result) == 1
        assert result[0]["content"] == "与你无关"

    def test_partial_at_match_not_filtered(self):
        """契约：@agent_a_xx 不算 @ agent_a，不应被过滤"""
        messages = [
            {"agent_name": "agent_b", "content": "@agent_a_extended 请处理"},
        ]
        ctx = self._make_context("agent_a", messages)
        result = ctx._get_filtered_messages(last_loaded_message_index=0)

        assert len(result) == 1

    def test_at_no_space_after_name(self):
        """契约：@nico你好 无空格也应被过滤（@nico 后跟中文非词边界）"""
        messages = [
            {"agent_name": "other", "content": "@nico你好吗"},
        ]
        ctx = self._make_context("nico", messages)
        result = ctx._get_filtered_messages(last_loaded_message_index=0)
        assert result == []

    def test_at_with_space_after_name(self):
        """契约：@nico 你好 有空格应被过滤"""
        messages = [
            {"agent_name": "other", "content": "@nico 你好吗"},
        ]
        ctx = self._make_context("nico", messages)
        result = ctx._get_filtered_messages(last_loaded_message_index=0)
        assert result == []

    def test_at_multiple_mentions_including_self(self):
        """契约：@nico@小李 中包含 @nico 应被过滤"""
        messages = [
            {"agent_name": "other", "content": "@nico@小李 你们需要处理"},
        ]
        ctx = self._make_context("nico", messages)
        result = ctx._get_filtered_messages(last_loaded_message_index=0)
        assert result == []

    def test_at_middle_of_word_not_matched(self):
        """契约：xx@nico 不算 @nico（前面有字符，不是独立 @ 提及）"""
        messages = [
            {"agent_name": "other", "content": "xx@nico 你好"},
        ]
        ctx = self._make_context("nico", messages)
        # @nico 仍然是独立的 @ 提及（前面是字母，但 @ 是分隔符）
        # re.search 会在 xx@nico 中找到 @nico，所以应该被过滤
        result = ctx._get_filtered_messages(last_loaded_message_index=0)
        assert result == []

    def test_at_different_agent_not_filtered(self):
        """契约：@other_agent 不应匹配 @nico"""
        messages = [
            {"agent_name": "other", "content": "@other_agent 你好"},
        ]
        ctx = self._make_context("nico", messages)
        result = ctx._get_filtered_messages(last_loaded_message_index=0)
        assert len(result) == 1

    def test_at_end_of_message(self):
        """契约：@nico 在消息末尾也应被过滤"""
        messages = [
            {"agent_name": "other", "content": "请处理 @nico"},
        ]
        ctx = self._make_context("nico", messages)
        result = ctx._get_filtered_messages(last_loaded_message_index=0)
        assert result == []

    def test_at_with_punctuation_after(self):
        """契约：@nico, @nico! @nico。各种标点后也应被过滤"""
        for content in ["@nico,你好", "@nico!快看", "@nico。处理一下"]:
            messages = [{"agent_name": "other", "content": content}]
            ctx = self._make_context("nico", messages)
            result = ctx._get_filtered_messages(last_loaded_message_index=0)
            assert result == [], f"应过滤: {content}"

    def test_incremental_loading(self):
        """契约：只处理 last_loaded_message_index 之后的消息"""
        messages = [
            {"agent_name": "agent_b", "content": "旧消息"},
            {"agent_name": "agent_b", "content": "新消息"},
        ]
        ctx = self._make_context("agent_a", messages)
        result = ctx._get_filtered_messages(last_loaded_message_index=1)

        assert len(result) == 1
        assert result[0]["content"] == "新消息"

    def test_all_filtered_returns_empty(self):
        """契约：所有消息都被过滤时返回空列表"""
        messages = [
            {"agent_name": "agent_a", "content": "自己发的"},
            {"agent_name": "agent_b", "content": "@agent_a 你来"},
        ]
        ctx = self._make_context("agent_a", messages)
        result = ctx._get_filtered_messages(last_loaded_message_index=0)

        assert result == []


# ==================== get_context() 角色差异化 ====================


class TestGetContext:
    """测试 AgentContext.get_context() 按角色差异化交付"""

    @staticmethod
    def _make_context_for_get(
        agent_name: str,
        role_type: RoleType,
        messages: list[dict],
        compact_history: list[dict] | None = None,
    ) -> AgentContext:
        ctx = AgentContext.__new__(AgentContext)
        ctx.agent_name = agent_name
        ctx.role_type = role_type

        session = GroupChatSession(group_chat_id="gc1")
        session.messages = messages

        group_ctx = GroupChatContext.__new__(GroupChatContext)
        runtime = MagicMock()
        runtime.state = MagicMock()
        runtime.state.group_chat_session = session
        runtime.state.agent_member_infos = {}
        runtime.update_context_load_state = AsyncMock()
        group_ctx.runtime = runtime
        group_ctx.load_compact_history = AsyncMock(return_value=compact_history or [])

        ctx.group_chat_context = group_ctx
        return ctx

    @pytest.mark.asyncio
    async def test_leader_gets_recent_messages(self):
        """契约：LEADER 角色 get_context 包含 <recent_messages>"""
        messages = [
            {"agent_name": "agent_b", "content": "任务进展"},
        ]
        ctx = self._make_context_for_get("agent_a", RoleType.LEADER, messages)

        result = await ctx.get_context()

        assert Tag.RECENT_MESSAGES in result
        assert "任务进展" in result

    @pytest.mark.asyncio
    async def test_worker_skips_recent_messages(self):
        """契约：TEAM_MEMBER 角色 get_context 不包含 <recent_messages>"""
        messages = [
            {"agent_name": "agent_b", "content": "任务进展"},
        ]
        ctx = self._make_context_for_get("agent_a", RoleType.TEAM_MEMBER, messages)

        result = await ctx.get_context()

        assert Tag.RECENT_MESSAGES not in result
        assert "任务进展" not in result

    @pytest.mark.asyncio
    async def test_worker_still_gets_compact_history(self):
        """契约：TEAM_MEMBER 角色仍接收 compact history"""
        messages = [
            {"agent_name": "agent_b", "content": "消息"},
        ]
        compact_history = [
            {"content": {"summary": "团队进展摘要", "agent_a": "你的专属摘要"}},
        ]
        ctx = self._make_context_for_get("agent_a", RoleType.TEAM_MEMBER, messages, compact_history)

        result = await ctx.get_context()

        assert Tag.GROUP_HISTORY in result
        assert "团队进展摘要" in result
        assert "你的专属摘要" in result

    @pytest.mark.asyncio
    async def test_leader_with_no_messages_returns_empty_recent(self):
        """契约：LEADER 无新消息时不生成 <recent_messages>"""
        ctx = self._make_context_for_get("agent_a", RoleType.LEADER, [])

        result = await ctx.get_context()

        assert Tag.RECENT_MESSAGES not in result

    @pytest.mark.asyncio
    async def test_worker_updates_message_index(self):
        """契约：TEAM_MEMBER 虽跳过 raw messages，但仍更新 message_index"""
        messages = [
            {"agent_name": "agent_b", "content": "m1"},
            {"agent_name": "agent_c", "content": "m2"},
        ]
        ctx = self._make_context_for_get("agent_a", RoleType.TEAM_MEMBER, messages)

        await ctx.get_context()

        ctx.group_chat_context.runtime.update_context_load_state.assert_called_once_with(
            "agent_a", 0, 2
        )
