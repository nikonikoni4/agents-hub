"""飞书命令系统测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents_hub.channels.feishu.commander import FeishuCommander, HELP_TEXT


@pytest.fixture
def mock_session_manager():
    """创建 mock session manager"""
    manager = MagicMock()
    manager.bind = MagicMock()
    manager.save = MagicMock()
    return manager


@pytest.fixture
def mock_group_chat_service():
    """创建 mock group chat service"""
    service = MagicMock()
    service.send_message_and_wait = AsyncMock(return_value="回复内容")
    return service


@pytest.fixture
def commander(mock_session_manager, mock_group_chat_service):
    """创建测试 Commander"""
    return FeishuCommander(mock_session_manager, mock_group_chat_service)


class TestHelpCommand:
    """测试 /help 命令"""

    @pytest.mark.asyncio
    async def test_help_command(self, commander):
        """测试 /help 命令"""
        result = await commander.handle("user1", "/help", "oc_xxx")
        assert result == HELP_TEXT
        assert "/help" in result
        assert "/bind" in result


class TestAgentsCommand:
    """测试 /agents 命令"""

    @pytest.mark.asyncio
    async def test_agents_command_with_roles(self, commander):
        """测试 /agents 命令（有角色）"""
        # Mock role manager
        mock_role1 = MagicMock()
        mock_role1.name = "coder"
        mock_role1.platform.value = "claude"
        mock_role1.description = "代码专家"

        mock_role2 = MagicMock()
        mock_role2.name = "reviewer"
        mock_role2.platform.value = "codex"
        mock_role2.description = ""

        commander._role_manager = MagicMock()
        commander._role_manager.list_roles.return_value = [mock_role1, mock_role2]

        result = await commander.handle("user1", "/agents", "oc_xxx")

        assert "可用 Agent" in result
        assert "coder" in result
        assert "reviewer" in result
        assert "代码专家" in result

    @pytest.mark.asyncio
    async def test_agents_command_no_roles(self, commander):
        """测试 /agents 命令（无角色）"""
        commander._role_manager = MagicMock()
        commander._role_manager.list_roles.return_value = []

        result = await commander.handle("user1", "/agents", "oc_xxx")
        assert "没有可用的 agent" in result


class TestGroupsCommand:
    """测试 /groups 命令"""

    @pytest.mark.asyncio
    async def test_groups_command_with_groups(self, commander):
        """测试 /groups 命令（有群聊）"""
        mock_groups = [
            {"group_chat_name": "团队1", "group_chat_id": "g1", "is_active": True},
            {"group_chat_name": "团队2", "group_chat_id": "g2", "is_active": False},
        ]

        with patch("agents_hub.channels.feishu.commander.group_chat_manager") as mock_gcm:
            mock_gcm.list_all_group_chats.return_value = mock_groups
            result = await commander.handle("user1", "/groups", "oc_xxx")

        assert "群聊列表" in result
        assert "团队1" in result
        assert "团队2" in result
        assert "活跃" in result
        assert "未激活" in result

    @pytest.mark.asyncio
    async def test_groups_command_no_groups(self, commander):
        """测试 /groups 命令（无群聊）"""
        with patch("agents_hub.channels.feishu.commander.group_chat_manager") as mock_gcm:
            mock_gcm.list_all_group_chats.return_value = []
            result = await commander.handle("user1", "/groups", "oc_xxx")

        assert "没有群聊" in result


class TestBindCommand:
    """测试 /bind 命令"""

    @pytest.mark.asyncio
    async def test_bind_command_success(self, commander, mock_session_manager):
        """测试 /bind 命令成功"""
        mock_groups = [
            {"group_chat_name": "团队1", "group_chat_id": "g1"},
        ]

        with patch("agents_hub.channels.feishu.commander.group_chat_manager") as mock_gcm:
            mock_gcm.list_all_group_chats.return_value = mock_groups
            result = await commander.handle("user1", "/bind 团队1", "oc_xxx")

        assert "已绑定到群聊: 团队1" in result
        mock_session_manager.bind.assert_called_once_with("oc_xxx", "g1", "团队1")
        mock_session_manager.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_bind_command_no_name(self, commander):
        """测试 /bind 命令（无群聊名称）"""
        result = await commander.handle("user1", "/bind", "oc_xxx")
        assert "请指定群聊名称" in result

    @pytest.mark.asyncio
    async def test_bind_command_group_not_found(self, commander):
        """测试 /bind 命令（群聊不存在）"""
        mock_groups = [
            {"group_chat_name": "团队1", "group_chat_id": "g1"},
        ]

        with patch("agents_hub.channels.feishu.commander.group_chat_manager") as mock_gcm:
            mock_gcm.list_all_group_chats.return_value = mock_groups
            result = await commander.handle("user1", "/bind 不存在的群聊", "oc_xxx")

        assert "未找到群聊" in result


class TestBackCommand:
    """测试 /back 命令"""

    @pytest.mark.asyncio
    async def test_back_command(self, commander):
        """测试 /back 命令"""
        result = await commander.handle("user1", "/back", "oc_xxx")
        # 飞书版本简化，直接返回提示
        assert "退出" in result or "帮助" in result


class TestUnknownCommand:
    """测试未知命令"""

    @pytest.mark.asyncio
    async def test_unknown_command(self, commander):
        """测试未知命令"""
        result = await commander.handle("user1", "/unknown", "oc_xxx")
        assert "未知命令" in result
        assert "/help" in result


class TestMessageForwarding:
    """测试消息转发"""

    @pytest.mark.asyncio
    async def test_forward_message_no_binding(self, commander, mock_session_manager):
        """测试转发消息（未绑定）"""
        mock_session_manager.get_mapping.return_value = None

        result = await commander.handle("user1", "Hello", "oc_xxx")
        assert "请先绑定群聊" in result

    @pytest.mark.asyncio
    async def test_forward_message_with_binding(self, commander, mock_session_manager, mock_group_chat_service):
        """测试转发消息（已绑定）"""
        mock_mapping = MagicMock()
        mock_mapping.group_chat_id = "g1"
        mock_mapping.group_chat_name = "团队1"
        mock_session_manager.get_mapping.return_value = mock_mapping

        with patch("agents_hub.channels.feishu.commander.group_chat_manager") as mock_gcm:
            mock_group_chat = MagicMock()
            mock_member = MagicMock()
            mock_member.name = "manager"
            mock_group_chat.runtime.get_member_dicts.return_value = [mock_member]
            mock_gcm.load_group_chat = AsyncMock(return_value=mock_group_chat)

            result = await commander.handle("user1", "Hello", "oc_xxx")

        assert result == "回复内容"
        mock_group_chat_service.send_message_and_wait.assert_called_once()
