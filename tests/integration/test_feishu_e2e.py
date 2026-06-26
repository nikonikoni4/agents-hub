"""飞书 Channel 端到端集成测试

验证飞书 Channel 集成的完整流程：
1. 完整流程：飞书发消息 → Agent 处理 → 回复到飞书
2. 命令系统：/help, /agents, /groups, /bind
3. 增量同步：重启后不重复发送历史消息
4. 断线重连：start/stop 生命周期
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from agents_hub.channels.feishu.channel import FeishuChannel
from agents_hub.channels.feishu.commander import FeishuCommander, HELP_TEXT, MESSAGE_TIMEOUT_SECONDS
from agents_hub.channels.feishu.config import FeishuConfig
from agents_hub.channels.feishu.session import FeishuSessionManager
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
        # Setup: 绑定飞书群到 agents-hub 群聊
        channel._session_manager = FeishuSessionManager(channel._data_path)
        channel._session_manager.bind("oc_feishu", "group_1", "团队1")
        channel._session_manager.save()

        # Mock group_chat_manager（commander 内部使用）
        with patch("agents_hub.channels.feishu.commander.group_chat_manager") as mock_gcm:
            mock_group_chat = MagicMock()
            mock_group_chat.runtime.get_member_dicts.return_value = [{"name": "manager"}]
            mock_gcm.load_group_chat = AsyncMock(return_value=mock_group_chat)

            # 初始化 commander
            channel._commander = FeishuCommander(
                channel._session_manager, mock_group_chat_service
            )

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
        # Setup: 绑定并初始化
        channel._session_manager = FeishuSessionManager(channel._data_path)
        channel._session_manager.bind("oc_feishu", "group_1", "团队1")

        # Mock client
        channel._client = MagicMock()
        channel._client.send_message = AsyncMock()

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

    @pytest.mark.asyncio
    async def test_full_roundtrip(self, channel, mock_group_chat_service):
        """完整往返：飞书消息 → Agent 处理 → 广播回复 → 推送到飞书"""
        # Setup
        channel._session_manager = FeishuSessionManager(channel._data_path)
        channel._session_manager.bind("oc_feishu", "group_1", "团队1")
        channel._session_manager.save()

        channel._client = MagicMock()
        channel._client.send_message = AsyncMock()

        with patch("agents_hub.channels.feishu.commander.group_chat_manager") as mock_gcm:
            mock_group_chat = MagicMock()
            mock_group_chat.runtime.get_member_dicts.return_value = [{"name": "manager"}]
            mock_gcm.load_group_chat = AsyncMock(return_value=mock_group_chat)

            channel._commander = FeishuCommander(
                channel._session_manager, mock_group_chat_service
            )

            # Step 1: 飞书用户发送消息
            event = {
                "message": {
                    "message_id": "msg_001",
                    "chat_id": "oc_feishu",
                    "chat_type": "group",
                    "content": '{"text":"帮我写代码"}',
                    "message_type": "text",
                    "sender": {
                        "sender_id": {"user_id": "ou_user1"},
                        "sender_type": "user",
                    },
                }
            }
            await channel.on_message(event)

        # Step 2: Agent 处理完成，广播回复
        agent_reply = {
            "id": 1,
            "content": "代码已完成",
            "send_from": "coder",
        }
        await channel._on_broadcast("group_1", agent_reply)

        # 验证完整链路
        mock_group_chat_service.send_message_and_wait.assert_called_once()
        channel._client.send_message.assert_called_once()


# ==================== 场景 2：命令系统 ====================


class TestCommandSystem:
    """/help, /agents, /groups, /bind 命令"""

    @pytest.fixture
    def commander(self, channel):
        channel._session_manager = FeishuSessionManager(channel._data_path)
        return FeishuCommander(channel._session_manager, MagicMock())

    @pytest.mark.asyncio
    async def test_help_command(self, commander):
        result = await commander.handle("user1", "/help", "oc_xxx")
        assert result == HELP_TEXT
        assert "/help" in result
        assert "/bind" in result

    @pytest.mark.asyncio
    async def test_agents_command(self, commander):
        mock_role = MagicMock()
        mock_role.name = "coder"
        mock_role.platform.value = "claude"
        mock_role.description = "代码专家"
        commander._role_manager = MagicMock()
        commander._role_manager.list_roles.return_value = [mock_role]

        result = await commander.handle("user1", "/agents", "oc_xxx")
        assert "coder" in result
        assert "代码专家" in result

    @pytest.mark.asyncio
    async def test_groups_command(self, commander):
        mock_groups = [
            {"group_chat_name": "团队1", "group_chat_id": "g1", "is_active": True},
        ]

        with patch("agents_hub.channels.feishu.commander.group_chat_manager") as mock_gcm:
            mock_gcm.list_all_group_chats.return_value = mock_groups
            result = await commander.handle("user1", "/groups", "oc_xxx")

        assert "团队1" in result
        assert "活跃" in result

    @pytest.mark.asyncio
    async def test_bind_command(self, commander, channel):
        mock_groups = [
            {"group_chat_name": "团队1", "group_chat_id": "g1"},
        ]

        with patch("agents_hub.channels.feishu.commander.group_chat_manager") as mock_gcm:
            mock_gcm.list_all_group_chats.return_value = mock_groups
            result = await commander.handle("user1", "/bind 团队1", "oc_xxx")

        assert "已绑定到群聊: 团队1" in result

        # 验证绑定关系已持久化
        channel._session_manager.load()
        mapping = channel._session_manager.get_mapping("oc_xxx")
        assert mapping is not None
        assert mapping.group_chat_id == "g1"


# ==================== 场景 3：增量同步 ====================


class TestIncrementalSync:
    """重启后不重复发送历史消息"""

    @pytest.mark.asyncio
    async def test_no_duplicate_after_restart(self, config, tmp_path, mock_group_chat_service):
        """重启后不会重复发送已同步的消息"""
        # Phase 1: 第一个 channel 实例处理消息
        channel1 = FeishuChannel(config, tmp_path, mock_group_chat_service)
        channel1._session_manager = FeishuSessionManager(tmp_path)
        channel1._session_manager.bind("oc_feishu", "group_1", "团队1")

        channel1._client = MagicMock()
        channel1._client.send_message = AsyncMock()

        # 处理消息 id=1
        msg1 = {"id": 1, "content": "消息A", "send_from": "coder"}
        await channel1._on_broadcast("group_1", msg1)

        # 处理消息 id=2
        msg2 = {"id": 2, "content": "消息B", "send_from": "coder"}
        await channel1._on_broadcast("group_1", msg2)

        # 保存状态
        channel1._session_manager.save()

        assert channel1._client.send_message.call_count == 2

        # Phase 2: 新 channel 实例（模拟重启）
        channel2 = FeishuChannel(config, tmp_path, mock_group_chat_service)
        channel2._session_manager = FeishuSessionManager(tmp_path)
        channel2._session_manager.load()  # 从磁盘加载

        channel2._client = MagicMock()
        channel2._client.send_message = AsyncMock()

        # 重新发送 id=1 和 id=2（应该被跳过）
        await channel2._on_broadcast("group_1", msg1)
        await channel2._on_broadcast("group_1", msg2)

        # 验证：没有重复发送
        channel2._client.send_message.assert_not_called()

        # 新消息 id=3 应该被发送
        msg3 = {"id": 3, "content": "消息C", "send_from": "coder"}
        await channel2._on_broadcast("group_1", msg3)
        channel2._client.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_state_persists_across_instances(self, config, tmp_path):
        """同步状态在实例间正确持久化"""
        # 创建并更新同步状态
        manager1 = FeishuSessionManager(tmp_path)
        manager1.bind("oc_feishu", "group_1", "团队1")
        manager1.update_sync_state("oc_feishu", 42)
        manager1.save()

        # 新实例加载
        manager2 = FeishuSessionManager(tmp_path)
        manager2.load()

        state = manager2.get_sync_state("oc_feishu")
        assert state.last_message_id == 42


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
                await channel.start()

                # 验证初始化
                mock_client.connect.assert_called_once()
                assert channel._client is not None
                assert channel._session_manager is not None
                assert channel._commander is not None

                await channel.stop()

                # 验证清理
                mock_client.disconnect.assert_called_once()
                assert channel._client is None
                assert channel._commander is None

    @pytest.mark.asyncio
    async def test_restart_reinitializes_state(self, channel):
        """重启后状态重新初始化"""
        with patch("agents_hub.channels.feishu.channel.FeishuClient") as MockClient:
            mock_client = MagicMock()
            mock_client.connect = AsyncMock()
            mock_client.disconnect = AsyncMock()
            MockClient.return_value = mock_client

            with patch("agents_hub.realtime.dependencies.register_channel_callback"):
                # 第一次启动
                await channel.start()
                first_client = channel._client

                # 停止
                await channel.stop()
                assert channel._client is None

                # 重启
                await channel.start()

                # 验证：新的 client 实例
                assert channel._client is not None
                assert mock_client.connect.call_count == 2

                await channel.stop()

    @pytest.mark.asyncio
    async def test_message_received_after_reconnect(self, channel, mock_group_chat_service):
        """重连后能正常接收消息"""
        channel._session_manager = FeishuSessionManager(channel._data_path)
        channel._session_manager.bind("oc_feishu", "group_1", "团队1")

        channel._client = MagicMock()
        channel._client.send_message = AsyncMock()

        channel._commander = FeishuCommander(
            channel._session_manager, mock_group_chat_service
        )

        # 模拟重连后收到消息
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
