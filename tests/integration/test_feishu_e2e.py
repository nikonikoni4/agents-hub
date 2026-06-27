"""飞书 Channel 端到端集成测试

验证飞书 Channel 集成的完整流程：
1. 完整流程：飞书发消息 → Agent 处理 → 回复到飞书
2. 命令系统：/start, /back, /default
3. 增量同步：重启后不重复发送历史消息
4. 断线重连：start/stop 生命周期
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from agents_hub.channels.feishu.channel import FeishuChannel
from agents_hub.channels.feishu.commander import FeishuCommander, WELCOME_TEXT, MESSAGE_TIMEOUT_SECONDS
from agents_hub.channels.feishu.config import FeishuConfig
from agents_hub.channels.feishu.session import FeishuSessionManager, FeishuSessionState
from agents_hub.realtime.dependencies import register_channel_callback, reset_channel_callbacks


@pytest.fixture
def config():
    return FeishuConfig(app_id="test_app", app_secret="test_secret")


@pytest.fixture
def mock_group_chat_service():
    service = MagicMock()
    service.send_message_and_wait = AsyncMock(return_value="Agent 回复内容")
    return service


@pytest.fixture
def channel(config, tmp_path, mock_group_chat_service):
    return FeishuChannel(config, tmp_path, mock_group_chat_service)


# ==================== 场景 1：完整流程 ====================


class TestCompleteFlow:
    """飞书发消息 → Agent 处理 → 回复到飞书"""

    @pytest.mark.asyncio
    async def test_feishu_message_forwarded_to_agent(self, channel, mock_group_chat_service):
        """飞书消息经 commander 转发到 agents-hub 群聊"""
        # Setup: 设置群聊状态
        channel._commander = FeishuCommander(mock_group_chat_service)

        mock_state = FeishuSessionState(
            feishu_chat_id="oc_feishu",
            session_type="group_chat",
            session_id="group_1",
            session_name="团队1",
        )

        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.get_or_create_state.return_value = mock_state

            with patch("agents_hub.channels.feishu.commander.group_chat_manager") as mock_gcm:
                mock_group_chat = MagicMock()
                mock_group_chat.runtime.get_member_dicts.return_value = [{"name": "manager"}]
                mock_gcm.load_group_chat = AsyncMock(return_value=mock_group_chat)

                # 模拟飞书消息事件
                event = {
                    "message": {
                        "message_id": "msg_001",
                        "chat_id": "oc_feishu",
                        "chat_type": "group",
                        "content": '{"text":"请帮我写代码"}',
                        "message_type": "text",
                        "sender": {
                            "sender_id": {"user_id": "ou_user1"},
                            "sender_type": "user",
                        },
                    }
                }

                await channel.on_message(event)

        # 验证：消息被转发到 agents-hub 群聊
        mock_group_chat_service.send_message_and_wait.assert_called_once()
        call_kwargs = mock_group_chat_service.send_message_and_wait.call_args
        assert call_kwargs[1]["group_chat_id"] == "group_1"
        assert call_kwargs[1]["content"] == "请帮我写代码"

    @pytest.mark.asyncio
    async def test_agent_reply_pushed_to_feishu(self, channel):
        """Agent 回复通过广播回调推送到飞书群"""
        # Mock client
        channel._client = MagicMock()
        channel._client.send_message = AsyncMock()

        # 设置状态
        mock_state = FeishuSessionState(
            feishu_chat_id="oc_feishu",
            session_type="group_chat",
            session_id="group_1",
            session_name="团队1",
            last_message_id=0,
        )

        with patch("agents_hub.channels.feishu.session.feishu_session_manager") as mock_sm:
            mock_sm._states = {"oc_feishu": mock_state}
            mock_sm.update_sync_state = MagicMock()
            mock_sm.save = MagicMock()

            # 模拟 Agent 回复的广播消息
            message = {
                "id": 1,
                "content": "代码已写好",
                "send_from": "coder",
            }

            await channel._on_broadcast("group_1", message)

        # 验证：消息被推送到飞书群
        channel._client.send_message.assert_called_once()
        call_args = channel._client.send_message.call_args
        assert call_args[0][0] == "oc_feishu"
        assert "**[coder]**" in call_args[0][1]
        assert "代码已写好" in call_args[0][1]


# ==================== 场景 2：命令系统 ====================


class TestCommandSystem:
    """/start, /back, /default 命令"""

    @pytest.fixture
    def commander(self):
        return FeishuCommander(MagicMock())

    @pytest.mark.asyncio
    async def test_start_command(self, commander):
        """测试 /start 命令进入助手模式"""
        mock_state = FeishuSessionState(
            feishu_chat_id="oc_xxx",
            session_type="idle",
            session_id="",
        )

        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.get_or_create_state.return_value = mock_state
            mock_sm.switch_to_assistant = MagicMock()
            mock_sm.save = MagicMock()

            result = await commander.handle("user1", "/start", "oc_xxx")

        assert "已进入助手模式" in result
        assert "/back" in result

    @pytest.mark.asyncio
    async def test_back_command(self, commander):
        """测试 /back 命令返回命令面板"""
        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.switch_to_idle = MagicMock()
            mock_sm.save = MagicMock()

            result = await commander.handle("user1", "/back", "oc_xxx")

        assert "已返回命令面板" in result
        assert "/start" in result

    @pytest.mark.asyncio
    async def test_welcome_text_in_idle(self, commander):
        """测试 idle 状态返回欢迎文本"""
        mock_state = FeishuSessionState(
            feishu_chat_id="oc_xxx",
            session_type="idle",
            session_id="",
        )

        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.get_or_create_state.return_value = mock_state

            result = await commander.handle("user1", "你好", "oc_xxx")

        assert result == WELCOME_TEXT
        assert "/start" in result


# ==================== 场景 3：增量同步 ====================


class TestIncrementalSync:
    """重启后不重复发送历史消息"""

    @pytest.mark.asyncio
    async def test_no_duplicate_after_restart(self, channel):
        """重启后不会重复发送已同步的消息"""
        # Mock client
        channel._client = MagicMock()
        channel._client.send_message = AsyncMock()

        # 设置状态：last_message_id = 2
        mock_state = FeishuSessionState(
            feishu_chat_id="oc_feishu",
            session_type="group_chat",
            session_id="group_1",
            session_name="团队1",
            last_message_id=2,
        )

        with patch("agents_hub.channels.feishu.session.feishu_session_manager") as mock_sm:
            mock_sm._states = {"oc_feishu": mock_state}
            mock_sm.update_sync_state = MagicMock()
            mock_sm.save = MagicMock()

            # 重新发送 id=1 和 id=2（应该被跳过）
            msg1 = {"id": 1, "content": "消息A", "send_from": "coder"}
            msg2 = {"id": 2, "content": "消息B", "send_from": "coder"}
            await channel._on_broadcast("group_1", msg1)
            await channel._on_broadcast("group_1", msg2)

            # 验证：没有重复发送
            channel._client.send_message.assert_not_called()

            # 新消息 id=3 应该被发送
            msg3 = {"id": 3, "content": "消息C", "send_from": "coder"}
            await channel._on_broadcast("group_1", msg3)
            channel._client.send_message.assert_called_once()


# ==================== 场景 4：断线重连 ====================


class TestReconnection:
    """start/stop 生命周期与资源管理"""

    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self, channel):
        """start → stop 完整生命周期"""
        with patch("agents_hub.channels.feishu.channel.FeishuClient") as MockClient:
            mock_client = MagicMock()
            mock_client.connect = AsyncMock()
            mock_client.disconnect = AsyncMock()
            MockClient.return_value = mock_client

            with patch("agents_hub.realtime.dependencies.register_channel_callback"):
                with patch("agents_hub.channels.feishu.session.feishu_session_manager") as mock_sm:
                    mock_sm.load = MagicMock()

                    await channel.start()

                    # 验证初始化
                    mock_client.connect.assert_called_once()
                    assert channel._client is not None
                    assert channel._commander is not None

                    await channel.stop()

                    # 验证清理
                    mock_client.disconnect.assert_called_once()
                    assert channel._client is None
                    assert channel._commander is None

    @pytest.mark.asyncio
    async def test_message_received_after_reconnect(self, channel, mock_group_chat_service):
        """重连后能正常接收消息"""
        channel._commander = FeishuCommander(mock_group_chat_service)

        mock_state = FeishuSessionState(
            feishu_chat_id="oc_feishu",
            session_type="group_chat",
            session_id="group_1",
            session_name="团队1",
        )

        with patch("agents_hub.channels.feishu.commander.feishu_session_manager") as mock_sm:
            mock_sm.get_or_create_state.return_value = mock_state

            with patch("agents_hub.channels.feishu.commander.group_chat_manager") as mock_gcm:
                mock_group_chat = MagicMock()
                mock_group_chat.runtime.get_member_dicts.return_value = [{"name": "manager"}]
                mock_gcm.load_group_chat = AsyncMock(return_value=mock_group_chat)

                event = {
                    "message": {
                        "message_id": "msg_after_reconnect",
                        "chat_id": "oc_feishu",
                        "chat_type": "group",
                        "content": '{"text":"重连后的消息"}',
                        "message_type": "text",
                        "sender": {
                            "sender_id": {"user_id": "ou_user1"},
                            "sender_type": "user",
                        },
                    }
                }

                await channel.on_message(event)

        # 验证消息正常处理
        mock_group_chat_service.send_message_and_wait.assert_called_once()
