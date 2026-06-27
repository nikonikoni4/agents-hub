"""飞书命令系统测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents_hub.channels.feishu.commander import FeishuCommander, WELCOME_TEXT, MESSAGE_TIMEOUT_SECONDS
from agents_hub.channels.feishu.session import FeishuSessionState


@pytest.fixture
def mock_group_chat_service():
    """创建 mock group chat service"""
    service = MagicMock()
    service.send_message_and_wait = AsyncMock(return_value="回复内容")
    return service


@pytest.fixture
def commander(mock_group_chat_service):
    """创建测试 Commander"""
    return FeishuCommander(mock_group_chat_service)


def make_state(chat_id="oc_xxx", session_type="idle", session_id="", session_name="", single_chat_id=""):
    """创建测试用状态"""
    return FeishuSessionState(
        feishu_chat_id=chat_id,
        session_type=session_type,
        session_id=session_id,
        session_name=session_name,
        single_chat_id=single_chat_id,
    )


class TestStartCommand:
    """测试 /start 命令"""

    @pytest.mark.asyncio
    async def test_start_in_idle_state(self, commander):
        """测试在 idle 状态发送 /start 进入助手模式"""
        mock_state = make_state(session_type="idle")

        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.get_or_create_state.return_value = mock_state
            mock_sm.switch_to_assistant = MagicMock()
            mock_sm.save = MagicMock()

            result = await commander.handle("user1", "/start", "oc_xxx")

        assert "已进入助手模式" in result
        mock_sm.switch_to_assistant.assert_called_once_with("oc_xxx")
        mock_sm.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_already_in_assistant(self, commander):
        """测试在助手模式发送 /start（会被转发给助手）"""
        mock_state = make_state(session_type="assistant", single_chat_id="sc_123")

        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.get_or_create_state.return_value = mock_state

            with patch.object(commander, "_forward_to_assistant", new_callable=AsyncMock) as mock_forward:
                mock_forward.return_value = "助手回复"

                result = await commander.handle("user1", "/start", "oc_xxx")

        # 在助手模式下，/start 被当作普通消息转发给助手
        assert result == "助手回复"


class TestBackCommand:
    """测试 /back 命令"""

    @pytest.mark.asyncio
    async def test_back_from_assistant(self, commander):
        """测试从助手模式返回"""
        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.switch_to_idle = MagicMock()
            mock_sm.save = MagicMock()

            result = await commander.handle("user1", "/back", "oc_xxx")

        assert "已返回命令面板" in result
        assert "/start" in result
        mock_sm.switch_to_idle.assert_called_once_with("oc_xxx")

    @pytest.mark.asyncio
    async def test_back_from_group_chat(self, commander):
        """测试从群聊模式返回"""
        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.switch_to_idle = MagicMock()
            mock_sm.save = MagicMock()

            result = await commander.handle("user1", "/back", "oc_xxx")

        assert "已返回命令面板" in result
        mock_sm.switch_to_idle.assert_called_once_with("oc_xxx")

    @pytest.mark.asyncio
    async def test_back_from_single_chat(self, commander):
        """测试从单聊模式返回"""
        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.switch_to_idle = MagicMock()
            mock_sm.save = MagicMock()

            result = await commander.handle("user1", "/back", "oc_xxx")

        assert "已返回命令面板" in result
        mock_sm.switch_to_idle.assert_called_once_with("oc_xxx")

    @pytest.mark.asyncio
    async def test_back_is_highest_priority(self, commander):
        """测试 /back 是最高优先级（即使在 idle 状态）"""
        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.switch_to_idle = MagicMock()
            mock_sm.save = MagicMock()

            result = await commander.handle("user1", "/back", "oc_xxx")

        assert "已返回命令面板" in result


class TestDefaultCommand:
    """测试 /default 命令"""

    @pytest.mark.asyncio
    async def test_default_in_group_chat(self, commander):
        """测试在群聊模式设置默认 agent"""
        mock_state = make_state(session_type="group_chat", session_id="g1", session_name="团队1")

        mock_role = MagicMock()
        mock_role.name = "pm"

        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.get_or_create_state.return_value = mock_state
            mock_sm.save = MagicMock()

            commander._role_manager = MagicMock()
            commander._role_manager.list_roles.return_value = [mock_role]

            result = await commander.handle("user1", "/default pm", "oc_xxx")

        assert "已设置默认对话对象: pm" in result
        assert mock_state.default_agent == "pm"

    @pytest.mark.asyncio
    async def test_default_not_in_group_chat(self, commander):
        """测试在 idle 状态发送 /default（返回欢迎文本）"""
        mock_state = make_state(session_type="idle")

        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.get_or_create_state.return_value = mock_state

            result = await commander.handle("user1", "/default pm", "oc_xxx")

        # 在 idle 状态，/default 不是 /start，所以返回 WELCOME_TEXT
        assert result == WELCOME_TEXT

    @pytest.mark.asyncio
    async def test_default_in_assistant_state(self, commander):
        """测试在助手模式发送 /default（会被转发给助手）"""
        mock_state = make_state(session_type="assistant", single_chat_id="sc_123")

        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.get_or_create_state.return_value = mock_state

            with patch.object(commander, "_forward_to_assistant", new_callable=AsyncMock) as mock_forward:
                mock_forward.return_value = "助手回复"

                result = await commander.handle("user1", "/default pm", "oc_xxx")

        # 在助手模式下，/default 被当作普通消息转发给助手
        assert result == "助手回复"

    @pytest.mark.asyncio
    async def test_default_no_agent_name(self, commander, mock_group_chat_service):
        """测试 /default 无参数（当作普通消息转发到群聊）"""
        mock_state = make_state(session_type="group_chat", session_id="g1", session_name="团队1")

        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.get_or_create_state.return_value = mock_state

            with patch("agents_hub.channels.feishu.commander.group_chat_manager") as mock_gcm:
                mock_group_chat = MagicMock()
                mock_group_chat.runtime.get_member_dicts.return_value = [{"name": "manager"}]
                mock_gcm.load_group_chat = AsyncMock(return_value=mock_group_chat)

                result = await commander.handle("user1", "/default", "oc_xxx")

        # /default 不带空格，不匹配 "/default " 前缀，作为普通消息转发到群聊
        assert "回复内容" in result
        mock_group_chat_service.send_message_and_wait.assert_called_once()


class TestIdleStateRouting:
    """测试 idle 状态路由"""

    @pytest.mark.asyncio
    async def test_non_command_returns_welcome(self, commander):
        """测试 idle 状态非命令消息返回欢迎文本"""
        mock_state = make_state(session_type="idle")

        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.get_or_create_state.return_value = mock_state

            result = await commander.handle("user1", "你好", "oc_xxx")

        assert result == WELCOME_TEXT
        assert "/start" in result

    @pytest.mark.asyncio
    async def test_unknown_command_returns_welcome(self, commander):
        """测试 idle 状态未知命令返回欢迎文本"""
        mock_state = make_state(session_type="idle")

        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.get_or_create_state.return_value = mock_state

            result = await commander.handle("user1", "/unknown", "oc_xxx")

        # 在 idle 状态，/unknown 不是 /start，所以返回 WELCOME_TEXT
        assert result == WELCOME_TEXT


class TestAssistantStateRouting:
    """测试助手状态路由"""

    @pytest.mark.asyncio
    async def test_assistant_message_forwarding(self, commander):
        """测试助手状态消息转发"""
        mock_state = make_state(session_type="assistant", single_chat_id="sc_123")

        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.get_or_create_state.return_value = mock_state

            with patch.object(commander, "_forward_to_assistant", new_callable=AsyncMock) as mock_forward:
                mock_forward.return_value = "助手回复"

                result = await commander.handle("user1", "你好", "oc_xxx")

        assert result == "助手回复"
        mock_forward.assert_called_once_with("oc_xxx", "你好")

    @pytest.mark.asyncio
    async def test_assistant_state_change_detection(self, commander):
        """测试助手状态变化检测（MCP 工具切换）"""
        mock_state_before = make_state(session_type="assistant")
        mock_state_after = make_state(session_type="group_chat", session_id="g1", session_name="团队1")

        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            # 第一次调用返回 assistant 状态，第二次返回 group_chat 状态
            mock_sm.get_or_create_state.side_effect = [mock_state_before, mock_state_after]

            with patch.object(commander, "_forward_to_assistant", new_callable=AsyncMock) as mock_forward:
                mock_forward.return_value = "已切换到群聊"

                result = await commander.handle("user1", "进入团队1", "oc_xxx")

        assert "已切换到群聊" in result
        assert "已进入团队1" in result
        assert "/back 返回" in result


class TestGroupChatStateRouting:
    """测试群聊状态路由"""

    @pytest.mark.asyncio
    async def test_group_chat_message_forwarding(self, commander, mock_group_chat_service):
        """测试群聊状态消息转发"""
        mock_state = make_state(session_type="group_chat", session_id="g1", session_name="团队1")

        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.get_or_create_state.return_value = mock_state

            with patch("agents_hub.channels.feishu.commander.group_chat_manager") as mock_gcm:
                mock_group_chat = MagicMock()
                mock_group_chat.runtime.get_member_dicts.return_value = [{"name": "manager"}]
                mock_gcm.load_group_chat = AsyncMock(return_value=mock_group_chat)

                result = await commander.handle("user1", "Hello", "oc_xxx")

        assert "回复内容" in result
        mock_group_chat_service.send_message_and_wait.assert_called_once()

    @pytest.mark.asyncio
    async def test_group_chat_deleted_error_message(self, commander):
        """测试群聊已删除时错误消息包含群聊名称"""
        from agents_hub.core.foundation import GroupChatNotFoundError

        mock_state = make_state(session_type="group_chat", session_id="g1", session_name="团队1")
        mock_state.feishu_chat_id = "oc_xxx"

        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.get_or_create_state.return_value = mock_state
            mock_sm.switch_to_idle = MagicMock()
            mock_sm.save = MagicMock()

            with patch("agents_hub.channels.feishu.commander.group_chat_manager") as mock_gcm:
                mock_gcm.load_group_chat = AsyncMock(side_effect=GroupChatNotFoundError("g1"))

                result = await commander.handle("user1", "Hello", "oc_xxx")

        # 验证错误消息包含群聊名称（在 switch_to_idle 清空之前保存的）
        assert "团队1" in result
        assert "已删除" in result
        assert "已返回命令面板" in result
        mock_sm.switch_to_idle.assert_called_once_with("oc_xxx")


class TestSingleChatStateRouting:
    """测试单聊状态路由"""

    @pytest.mark.asyncio
    async def test_single_chat_message_forwarding(self, commander):
        """测试单聊状态消息转发"""
        mock_state = make_state(session_type="single_chat", session_id="researcher", single_chat_id="sc_123")

        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.get_or_create_state.return_value = mock_state

            with patch.object(commander, "_forward_to_single_chat", new_callable=AsyncMock) as mock_forward:
                mock_forward.return_value = "单聊回复"

                result = await commander.handle("user1", "你好", "oc_xxx")

        assert result == "单聊回复"
        mock_forward.assert_called_once_with(mock_state, "你好")

    @pytest.mark.asyncio
    async def test_single_chat_missing_single_chat_id(self, commander):
        """测试单聊状态缺少 single_chat_id 的错误处理"""
        mock_state = make_state(session_type="single_chat", session_id="researcher", single_chat_id="")

        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.get_or_create_state.return_value = mock_state

            # 直接调用 _forward_to_single_chat 测试错误路径
            result = await commander._forward_to_single_chat(mock_state, "你好")

        assert "单聊会话不存在" in result
        assert "/start" in result
