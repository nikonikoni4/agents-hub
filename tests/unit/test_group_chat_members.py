"""
群成员管理功能测试

测试契约：
1. GroupChatService.add_group_chat_members - 添加群成员
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_hub.api.services.group_chat_service import GroupChatService

# ==================== 辅助类 ====================


class MockRoleManager:
    """模拟 RoleManager"""

    def get_role(self, name: str):
        """模拟获取角色，不存在时抛出异常"""
        if name in ["manager", "worker1", "worker2", "new_worker"]:
            return MagicMock()
        raise ValueError(f"Role not found: {name}")


# ==================== GroupChatService.add_group_chat_members 测试 ====================


class TestAddGroupChatMembers:
    """GroupChatService.add_group_chat_members 契约测试"""

    @pytest.fixture
    def mock_service(self):
        """创建 mock 的 GroupChatService"""
        mock_manager = MagicMock()
        service = GroupChatService(group_chat_manager=mock_manager)
        return service, mock_manager

    def _create_mock_group_chat(self, members: list[str], member_dicts: list[dict]):
        """创建 mock 群聊"""
        mock_group_chat = MagicMock()
        mock_group_chat.team_members_name = members
        mock_group_chat.group_chat_name = "test-chat"
        mock_group_chat.group_type = MagicMock()
        mock_group_chat.runtime.get_member_dicts.return_value = member_dicts
        mock_group_chat.add_member = AsyncMock()  # ✅ Mock add_member
        mock_group_chat.runtime.initialize_metadata = AsyncMock()
        return mock_group_chat

    @pytest.mark.asyncio
    async def test_add_members_success(self, mock_service):
        """
        契约：成功添加成员

        验证方式：
        1. 创建 mock 群聊，已有成员 ["manager", "worker1"]
        2. 调用 add_group_chat_members 添加 ["worker2"]
        3. 验证返回的成员列表包含新成员
        """
        service, mock_manager = mock_service

        member_dicts = [
            {
                "name": "manager",
                "main_session": "s1",
                "btw_session": [],
                "cwd": "/tmp",
                "use_docker": False,
            },
            {
                "name": "worker1",
                "main_session": "s2",
                "btw_session": [],
                "cwd": "/tmp",
                "use_docker": False,
            },
            {
                "name": "worker2",
                "main_session": None,
                "btw_session": [],
                "cwd": "/tmp",
                "use_docker": False,
            },
        ]
        mock_group_chat = self._create_mock_group_chat(["manager", "worker1"], member_dicts)
        mock_manager.load_group_chat = AsyncMock(return_value=mock_group_chat)

        with patch(
            "agents_hub.api.services.group_chat_service.RoleManager", return_value=MockRoleManager()
        ):
            with patch(
                "agents_hub.api.services.group_chat_service.broadcast_group_chat_refresh",
                new_callable=AsyncMock,
            ):
                result = await service.add_group_chat_members("test-chat", ["worker2"])

        assert len(result) == 3
        assert any(m.name == "worker2" for m in result)

    @pytest.mark.asyncio
    async def test_add_members_idempotent(self, mock_service):
        """
        契约：添加已存在的成员是幂等的

        验证方式：
        1. 创建 mock 群聊，已有成员 ["manager", "worker1"]
        2. 调用 add_group_chat_members 添加 ["worker1"]
        3. 验证 add_member 被调用（内部处理幂等）
        """
        service, mock_manager = mock_service

        member_dicts = [
            {
                "name": "manager",
                "main_session": "s1",
                "btw_session": [],
                "cwd": "/tmp",
                "use_docker": False,
            },
            {
                "name": "worker1",
                "main_session": "s2",
                "btw_session": [],
                "cwd": "/tmp",
                "use_docker": False,
            },
        ]
        mock_group_chat = self._create_mock_group_chat(["manager", "worker1"], member_dicts)
        mock_manager.load_group_chat = AsyncMock(return_value=mock_group_chat)

        with patch(
            "agents_hub.api.services.group_chat_service.RoleManager", return_value=MockRoleManager()
        ):
            with patch(
                "agents_hub.api.services.group_chat_service.broadcast_group_chat_refresh",
                new_callable=AsyncMock,
            ):
                await service.add_group_chat_members("test-chat", ["worker1"])

        # 验证 add_member 被调用
        mock_group_chat.add_member.assert_called_once_with("worker1")

    @pytest.mark.asyncio
    async def test_add_members_invalid_role_raises(self, mock_service):
        """
        契约：添加不存在的角色时抛出异常

        验证方式：
        1. 创建 mock 群聊
        2. 调用 add_group_chat_members 添加不存在的角色
        3. 验证抛出 ValueError
        """
        service, mock_manager = mock_service

        mock_group_chat = MagicMock()
        mock_group_chat.team_members_name = ["manager"]
        mock_manager.load_group_chat = AsyncMock(return_value=mock_group_chat)

        with patch(
            "agents_hub.api.services.group_chat_service.RoleManager", return_value=MockRoleManager()
        ):
            with pytest.raises(ValueError):
                await service.add_group_chat_members("test-chat", ["invalid_role"])
