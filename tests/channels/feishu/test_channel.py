"""飞书 Channel 测试"""

import pytest
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
def channel(config):
    """创建测试 Channel"""
    return FeishuChannel(config)


class TestOnMessage:
    """测试 on_message() 方法"""

    @pytest.mark.asyncio
    async def test_on_message_parses_and_deduplicates(self, channel):
        """测试消息解析和去重"""
        event = {
            "message": {
                "message_id": "msg_123",
                "chat_id": "oc_xxx",
                "chat_type": "group",
                "content": '{"text":"Hello"}',
                "message_type": "text",
                "sender": {
                    "sender_id": {"user_id": "ou_user1"},
                    "sender_type": "user",
                },
            }
        }

        # Mock commander.handle
        channel._commander = MagicMock()
        channel._commander.handle = AsyncMock(return_value="回复内容")

        # 第一次调用应该处理
        await channel.on_message(event)
        channel._commander.handle.assert_called_once()

        # 第二次调用相同消息应该被去重
        channel._commander.handle.reset_mock()
        await channel.on_message(event)
        channel._commander.handle.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_with_at_agent(self, channel):
        """测试 @agent 解析"""
        event = {
            "message": {
                "message_id": "msg_456",
                "chat_id": "oc_xxx",
                "chat_type": "group",
                "content": '{"text":"@coder 请帮我写代码"}',
                "message_type": "text",
                "sender": {
                    "sender_id": {"user_id": "ou_user1"},
                    "sender_type": "user",
                },
            }
        }

        # 设置群聊成员列表
        channel._members = ["manager", "coder", "reviewer"]

        # Mock commander.handle
        channel._commander = MagicMock()
        channel._commander.handle = AsyncMock(return_value="已处理")

        await channel.on_message(event)

        # 验证 commander.handle 被调用，参数包含解析后的 agent_name
        call_args = channel._commander.handle.call_args
        assert call_args[0][0] == "ou_user1"  # user_id
        assert call_args[0][1] == "请帮我写代码"  # clean_content

    @pytest.mark.asyncio
    async def test_on_message_with_mentions(self, channel):
        """测试 mention 占位符替换"""
        event = {
            "message": {
                "message_id": "msg_789",
                "chat_id": "oc_xxx",
                "chat_type": "group",
                "content": '{"text":"@_user_1 请帮我处理"}',
                "message_type": "text",
                "mentions": [
                    {
                        "key": "@_user_1",
                        "id": {"user_id": "ou_bot1"},
                        "name": "飞书机器人",
                    }
                ],
                "sender": {
                    "sender_id": {"user_id": "ou_user1"},
                    "sender_type": "user",
                },
            }
        }

        # Mock commander.handle
        channel._commander = MagicMock()
        channel._commander.handle = AsyncMock(return_value="已处理")

        await channel.on_message(event)

        # 验证 mention 被替换
        call_args = channel._commander.handle.call_args
        assert call_args[0][1] == "@飞书机器人 请帮我处理"

    @pytest.mark.asyncio
    async def test_on_message_default_to_manager(self, channel):
        """测试默认发送给 manager"""
        event = {
            "message": {
                "message_id": "msg_101",
                "chat_id": "oc_xxx",
                "chat_type": "group",
                "content": '{"text":"请帮我处理任务"}',
                "message_type": "text",
                "sender": {
                    "sender_id": {"user_id": "ou_user1"},
                    "sender_type": "user",
                },
            }
        }

        # Mock commander.handle
        channel._commander = MagicMock()
        channel._commander.handle = AsyncMock(return_value="已处理")

        await channel.on_message(event)

        # 验证默认发送给 manager
        call_args = channel._commander.handle.call_args
        assert call_args[0][0] == "ou_user1"  # user_id
        assert call_args[0][1] == "请帮我处理任务"  # content

    @pytest.mark.asyncio
    async def test_on_message_handles_error(self, channel):
        """测试错误处理"""
        event = {
            "message": {
                "message_id": "msg_error",
                "chat_id": "oc_xxx",
                "chat_type": "group",
                "content": "invalid json",
                "message_type": "text",
                "sender": {
                    "sender_id": {"user_id": "ou_user1"},
                    "sender_type": "user",
                },
            }
        }

        # 应该不会抛出异常
        await channel.on_message(event)

    @pytest.mark.asyncio
    async def test_on_message_empty_content(self, channel):
        """测试空内容消息"""
        event = {
            "message": {
                "message_id": "msg_empty",
                "chat_id": "oc_xxx",
                "chat_type": "group",
                "content": '{"text":""}',
                "message_type": "text",
                "sender": {
                    "sender_id": {"user_id": "ou_user1"},
                    "sender_type": "user",
                },
            }
        }

        # Mock commander.handle
        channel._commander = MagicMock()
        channel._commander.handle = AsyncMock(return_value="已处理")

        # 空内容应该被跳过
        await channel.on_message(event)
        channel._commander.handle.assert_not_called()
