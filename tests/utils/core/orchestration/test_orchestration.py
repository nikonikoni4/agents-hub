"""
Orchestration 层单元测试

契约：
1. GroupChatManager: register, load_group_chat, unregister 幂等性
2. Team: 空成员列表抛 ValueError
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_hub.core.foundation import GroupChatNotFoundError
from agents_hub.core.orchestration.group_chat import GroupChat
from agents_hub.core.orchestration.group_chat_manager import GroupChatManager
from agents_hub.core.orchestration.team import Team


# ==================== GroupChatManager ====================


class TestGroupChatManagerRegister:
    """测试 GroupChatManager.register()"""

    @pytest.mark.asyncio
    async def test_register_then_get(self):
        """契约：register() 后 load_group_chat() 返回正确实例"""
        mgr = GroupChatManager()
        mock_gc = MagicMock(spec=GroupChat)
        mgr.register("gc_1", mock_gc)

        result = await mgr.load_group_chat("gc_1")
        assert result is mock_gc

    def test_register_invalid_id_raises(self):
        """契约：无效 group_chat_id 抛 ValueError"""
        mgr = GroupChatManager()
        with pytest.raises(ValueError, match="无效的 group_chat_id"):
            mgr.register("", MagicMock())

    def test_register_none_id_raises(self):
        """契约：None group_chat_id 抛 ValueError"""
        mgr = GroupChatManager()
        with pytest.raises(ValueError, match="无效的 group_chat_id"):
            mgr.register(None, MagicMock())

    def test_register_invalid_type_raises(self):
        """契约：非 GroupChat 类型抛 ValueError"""
        mgr = GroupChatManager()
        with pytest.raises(ValueError, match="无效的 group_chat 类型"):
            mgr.register("gc_1", "not_a_group_chat")


class TestGroupChatManagerGet:
    """测试 GroupChatManager.load_group_chat()"""

    @pytest.mark.asyncio
    async def test_get_nonexistent_raises(self):
        """契约：获取不存在的 GroupChat 抛 GroupChatNotFoundError"""
        mgr = GroupChatManager()
        with pytest.raises(GroupChatNotFoundError):
            await mgr.load_group_chat("nonexistent")


class TestGroupChatManagerUnregister:
    """测试 GroupChatManager.unregister()"""

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_silent(self):
        """契约：unregister 不存在的 ID 静默返回"""
        mgr = GroupChatManager()
        await mgr.unregister("nonexistent")  # 不应报错

    @pytest.mark.asyncio
    async def test_unregister_removes_from_registry(self):
        """契约：unregister 后 load_group_chat 失败"""
        mgr = GroupChatManager()
        mock_gc = MagicMock(spec=GroupChat)
        mock_gc.cleanup = AsyncMock()
        mgr.register("gc_1", mock_gc)

        await mgr.unregister("gc_1")

        with pytest.raises(GroupChatNotFoundError):
            await mgr.load_group_chat("gc_1")

    @pytest.mark.asyncio
    async def test_unregister_calls_cleanup(self):
        """契约：unregister 调用 GroupChat.cleanup()"""
        mgr = GroupChatManager()
        mock_gc = MagicMock(spec=GroupChat)
        mock_gc.cleanup = AsyncMock()
        mgr.register("gc_1", mock_gc)

        await mgr.unregister("gc_1", timeout=5.0)

        mock_gc.cleanup.assert_called_once_with(timeout=5.0)


# ==================== Team ====================


class TestTeam:
    """测试 Team 验证"""

    def test_empty_members_raises(self):
        """契约：空 team_members_name 抛 ValueError"""
        with patch("agents_hub.core.orchestration.team.RoleManager") as mock_rm:
            mock_rm.return_value.list_role_names.return_value = ["a", "b"]
            with pytest.raises(ValueError, match="team_members 不能为空"):
                Team(team_members_name=[])
