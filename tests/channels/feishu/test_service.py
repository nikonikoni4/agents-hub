"""FeishuSessionService 单元测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_hub.channels.feishu.service import FeishuSessionService
from agents_hub.core.foundation import GroupChatNotFoundError


@pytest.fixture
def service():
    return FeishuSessionService()


class TestBindToGroupChat:
    """bind_to_group_chat 测试"""

    @pytest.mark.asyncio
    async def test_success(self, service):
        """绑定成功"""
        mock_gc = MagicMock()
        mock_gc.runtime.get_info_dict.return_value = {"group_chat_name": "Research Team"}

        with patch("agents_hub.channels.feishu.service.group_chat_manager") as mock_gcm:
            mock_gcm.load_group_chat = AsyncMock(return_value=mock_gc)

            with patch("agents_hub.channels.feishu.service.feishu_session_manager") as mock_sm:
                mock_sm.switch_to_group_chat = MagicMock()
                mock_sm.save = MagicMock()

                result = await service.bind_to_group_chat("oc_feishu", "group_1")

                assert result["status"] == "bound"
                assert result["group_chat_id"] == "group_1"
                assert result["group_chat_name"] == "Research Team"
                mock_sm.switch_to_group_chat.assert_called_once_with(
                    "oc_feishu", "group_1", "Research Team"
                )
                mock_sm.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_group_chat_not_found(self, service):
        """群聊不存在时抛出异常"""
        with patch("agents_hub.channels.feishu.service.group_chat_manager") as mock_gcm:
            mock_gcm.load_group_chat = AsyncMock(
                side_effect=GroupChatNotFoundError("group_invalid")
            )

            with pytest.raises(GroupChatNotFoundError):
                await service.bind_to_group_chat("oc_feishu", "group_invalid")


class TestBindToSingleChat:
    """bind_to_single_chat 测试"""

    @pytest.mark.asyncio
    async def test_success(self, service):
        """绑定成功"""
        mock_chat = MagicMock()
        mock_chat.agent_name = "coder"

        with patch("agents_hub.channels.feishu.service.single_chat_manager") as mock_scm:
            mock_scm.get_single_chat.return_value = mock_chat

            with patch("agents_hub.channels.feishu.service.feishu_session_manager") as mock_sm:
                mock_sm.switch_to_single_chat = MagicMock()
                mock_sm.save = MagicMock()

                result = await service.bind_to_single_chat("oc_feishu", "sc_1")

                assert result["status"] == "bound"
                assert result["session_id"] == "sc_1"
                assert result["agent_name"] == "coder"
                mock_sm.switch_to_single_chat.assert_called_once_with(
                    "oc_feishu", "coder", "sc_1"
                )
                mock_sm.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_not_found(self, service):
        """单聊不存在时抛出异常"""
        with patch("agents_hub.channels.feishu.service.single_chat_manager") as mock_scm:
            mock_scm.get_single_chat.side_effect = ValueError("不存在")

            with pytest.raises(ValueError):
                await service.bind_to_single_chat("oc_feishu", "sc_invalid")


class TestCreateSingleChat:
    """create_single_chat 测试"""

    @pytest.mark.asyncio
    async def test_success(self, service):
        """创建成功"""
        mock_response = MagicMock()
        mock_response.single_chat_id = "sc_new"

        with patch("agents_hub.channels.feishu.service.single_chat_manager") as mock_scm:
            mock_scm.create_single_chat = AsyncMock(return_value=mock_response)

            with patch("agents_hub.channels.feishu.service.feishu_session_manager") as mock_sm:
                mock_sm.add_single_chat_history = MagicMock()
                mock_sm.switch_to_single_chat = MagicMock()
                mock_sm.save = MagicMock()

                result = await service.create_single_chat("oc_feishu", "coder")

                assert result["status"] == "created"
                assert result["single_chat_id"] == "sc_new"
                assert result["agent_name"] == "coder"
                mock_sm.add_single_chat_history.assert_called_once_with(
                    "oc_feishu", "sc_new", "coder", ""
                )
                mock_sm.switch_to_single_chat.assert_called_once_with(
                    "oc_feishu", "coder", "sc_new"
                )
                mock_sm.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_failure(self, service):
        """创建失败时抛出异常"""
        with patch("agents_hub.channels.feishu.service.single_chat_manager") as mock_scm:
            mock_scm.create_single_chat = AsyncMock(
                side_effect=Exception("agent 不存在")
            )

            with pytest.raises(Exception, match="agent 不存在"):
                await service.create_single_chat("oc_feishu", "invalid_agent")
