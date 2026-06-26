"""飞书消息发送测试"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from agents_hub.channels.feishu.channel import FeishuChannel
from agents_hub.channels.feishu.config import FeishuConfig


@pytest.fixture
def config():
    """创建测试配置"""
    return FeishuConfig(
        app_id="test_app_id",
        app_secret="test_app_secret",
    )


@pytest.fixture
def data_path():
    """创建临时数据目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def channel(config, data_path):
    """创建测试 Channel"""
    return FeishuChannel(config, data_path, group_chat_service=MagicMock())


class TestSendToFeishu:
    """测试 send_to_feishu()"""

    @pytest.mark.asyncio
    async def test_send_text_message(self, channel):
        """测试发送文本消息"""
        # Mock client
        channel._client = MagicMock()
        channel._client.send_message = AsyncMock()

        await channel.send_to_feishu(
            chat_id="oc_xxx",
            content="Hello World",
            agent_name="coder",
        )

        # 验证消息格式
        channel._client.send_message.assert_called_once()
        call_args = channel._client.send_message.call_args
        assert call_args[0][0] == "oc_xxx"
        assert "**[coder]** : Hello World" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_send_message_with_members(self, channel):
        """测试发送消息带成员列表"""
        # Mock client
        channel._client = MagicMock()
        channel._client.send_message = AsyncMock()

        await channel.send_to_feishu(
            chat_id="oc_xxx",
            content="任务完成",
            agent_name="manager",
            members=["coder", "reviewer", "architect"],
        )

        # 验证消息格式
        call_args = channel._client.send_message.call_args
        message = call_args[0][1]
        assert "**[manager]** : 任务完成" in message
        assert "群聊成员: coder, reviewer, architect" in message

    @pytest.mark.asyncio
    async def test_send_message_without_members(self, channel):
        """测试发送消息不带成员列表"""
        # Mock client
        channel._client = MagicMock()
        channel._client.send_message = AsyncMock()

        await channel.send_to_feishu(
            chat_id="oc_xxx",
            content="任务完成",
            agent_name="manager",
        )

        # 验证消息格式
        call_args = channel._client.send_message.call_args
        message = call_args[0][1]
        assert "**[manager]** : 任务完成" in message
        assert "群聊成员" not in message

    @pytest.mark.asyncio
    async def test_send_message_no_client(self, channel):
        """测试没有 client 时发送消息"""
        channel._client = None

        # 应该不会抛出异常
        await channel.send_to_feishu(
            chat_id="oc_xxx",
            content="Hello",
            agent_name="coder",
        )

    @pytest.mark.asyncio
    async def test_send_message_handles_error(self, channel):
        """测试发送消息错误处理"""
        from agents_hub.channels.feishu.exceptions import FeishuAPIError

        # Mock client 抛出异常
        channel._client = MagicMock()
        channel._client.send_message = AsyncMock(side_effect=FeishuAPIError("API Error"))

        # 应该抛出异常
        with pytest.raises(FeishuAPIError):
            await channel.send_to_feishu(
                chat_id="oc_xxx",
                content="Hello",
                agent_name="coder",
            )


class TestOnBroadcast:
    """测试 _on_broadcast()"""

    @pytest.mark.asyncio
    async def test_on_broadcast_with_message(self, channel):
        """测试处理有消息的广播"""
        # Mock session manager
        channel._session_manager = MagicMock()
        channel._session_manager.get_mapping.return_value = MagicMock(feishu_chat_id="oc_feishu")
        channel._session_manager.get_sync_state.return_value = MagicMock(last_message_id=0)
        channel._session_manager.update_sync_state = MagicMock()

        # Mock send_to_feishu
        channel.send_to_feishu = AsyncMock()

        message = {
            "id": 1,
            "content": "任务完成",
            "send_from": "coder",
        }

        await channel._on_broadcast("group_123", message)

        # 验证发送消息
        channel.send_to_feishu.assert_called_once()
        call_args = channel.send_to_feishu.call_args
        assert call_args[1]["chat_id"] == "oc_feishu"
        assert call_args[1]["content"] == "任务完成"
        assert call_args[1]["agent_name"] == "coder"

    @pytest.mark.asyncio
    async def test_on_broadcast_without_message(self, channel):
        """测试处理没有消息的广播"""
        # Mock send_to_feishu
        channel.send_to_feishu = AsyncMock()

        await channel._on_broadcast("group_123", None)

        # 应该跳过，不发送消息
        channel.send_to_feishu.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_broadcast_no_binding(self, channel):
        """测试未绑定的群聊"""
        # Mock session manager
        channel._session_manager = MagicMock()
        channel._session_manager.get_mapping.return_value = None

        # Mock send_to_feishu
        channel.send_to_feishu = AsyncMock()

        message = {
            "id": 1,
            "content": "任务完成",
            "send_from": "coder",
        }

        await channel._on_broadcast("group_123", message)

        # 应该跳过，不发送消息
        channel.send_to_feishu.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_broadcast_duplicate_message(self, channel):
        """测试重复消息"""
        # Mock session manager
        channel._session_manager = MagicMock()
        channel._session_manager.get_mapping.return_value = MagicMock(feishu_chat_id="oc_feishu")
        channel._session_manager.get_sync_state.return_value = MagicMock(last_message_id=1)

        # Mock send_to_feishu
        channel.send_to_feishu = AsyncMock()

        message = {
            "id": 1,  # 与 last_message_id 相同
            "content": "任务完成",
            "send_from": "coder",
        }

        await channel._on_broadcast("group_123", message)

        # 应该跳过，不发送消息
        channel.send_to_feishu.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_broadcast_updates_sync_state(self, channel):
        """测试更新同步状态"""
        # Mock session manager
        channel._session_manager = MagicMock()
        channel._session_manager.get_mapping.return_value = MagicMock(feishu_chat_id="oc_feishu")
        channel._session_manager.get_sync_state.return_value = MagicMock(last_message_id=0)
        channel._session_manager.update_sync_state = MagicMock()

        # Mock send_to_feishu
        channel.send_to_feishu = AsyncMock()

        message = {
            "id": 5,
            "content": "任务完成",
            "send_from": "coder",
        }

        await channel._on_broadcast("group_123", message)

        # 验证更新同步状态
        channel._session_manager.update_sync_state.assert_called_once_with("oc_feishu", 5)


class TestCallbackRegistration:
    """测试回调注册"""

    @pytest.mark.asyncio
    async def test_on_broadcast_method_exists(self, channel):
        """测试 _on_broadcast 方法存在"""
        assert hasattr(channel, "_on_broadcast")
        assert callable(channel._on_broadcast)

    @pytest.mark.asyncio
    async def test_send_to_feishu_method_exists(self, channel):
        """测试 send_to_feishu 方法存在"""
        assert hasattr(channel, "send_to_feishu")
        assert callable(channel.send_to_feishu)
