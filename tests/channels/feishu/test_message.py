"""飞书消息解析测试"""

import pytest

from agents_hub.channels.feishu.message import (
    MessageDeduplicator,
    parse_agent_name,
    parse_mentions,
    parse_message,
)


class TestParseMessage:
    """测试 parse_message()"""

    def test_parse_text_message(self):
        """解析文本消息"""
        event = {
            "message": {
                "message_id": "msg_123",
                "chat_id": "oc_xxx",
                "chat_type": "group",
                "content": '{"text":"Hello @user1"}',
                "message_type": "text",
                "sender": {
                    "sender_id": {"user_id": "ou_user1"},
                    "sender_type": "user",
                },
            }
        }
        result = parse_message(event)

        assert result["message_id"] == "msg_123"
        assert result["chat_id"] == "oc_xxx"
        assert result["content"] == "Hello @user1"
        assert result["msg_type"] == "text"
        assert result["sender_id"] == "ou_user1"
        assert result["sender_type"] == "user"

    def test_parse_message_with_mentions(self):
        """解析包含 mention 的消息"""
        event = {
            "message": {
                "message_id": "msg_456",
                "chat_id": "oc_yyy",
                "chat_type": "group",
                "content": '{"text":"@_user_1 请帮我处理这个任务"}',
                "message_type": "text",
                "mentions": [
                    {
                        "key": "@_user_1",
                        "id": {"user_id": "ou_bot1"},
                        "name": "飞书机器人",
                        "tenant_key": "tenant1",
                    }
                ],
                "sender": {
                    "sender_id": {"user_id": "ou_user2"},
                    "sender_type": "user",
                },
            }
        }
        result = parse_message(event)

        assert result["message_id"] == "msg_456"
        assert result["content"] == "@_user_1 请帮我处理这个任务"
        assert result["mentions"] == [
            {
                "key": "@_user_1",
                "id": "ou_bot1",
                "name": "飞书机器人",
            }
        ]

    def test_parse_message_missing_fields(self):
        """解析缺少字段的消息"""
        event = {
            "message": {
                "message_id": "msg_789",
            }
        }
        result = parse_message(event)

        assert result["message_id"] == "msg_789"
        assert result["chat_id"] == ""
        assert result["content"] == ""
        assert result["msg_type"] == "text"
        assert result["sender_id"] == ""
        assert result["sender_type"] == ""
        assert result["mentions"] == []


class TestParseAgentName:
    """测试 parse_agent_name()"""

    def test_parse_at_agent(self):
        """解析 @agent_name"""
        members = ["manager", "coder", "reviewer"]
        content = "@coder 请帮我写一个函数"

        agent_name, clean_content = parse_agent_name(content, members)

        assert agent_name == "coder"
        assert clean_content == "请帮我写一个函数"

    def test_parse_at_manager(self):
        """解析 @manager"""
        members = ["manager", "coder"]
        content = "@manager 我需要帮助"

        agent_name, clean_content = parse_agent_name(content, members)

        assert agent_name == "manager"
        assert clean_content == "我需要帮助"

    def test_parse_unknown_agent(self):
        """未知 agent 默认发给 manager"""
        members = ["manager", "coder"]
        content = "@unknown 你好"

        agent_name, clean_content = parse_agent_name(content, members)

        assert agent_name == "manager"
        assert clean_content == "@unknown 你好"

    def test_parse_no_at_prefix(self):
        """没有 @ 前缀，默认发给 manager"""
        members = ["manager", "coder"]
        content = "请帮我写代码"

        agent_name, clean_content = parse_agent_name(content, members)

        assert agent_name == "manager"
        assert clean_content == "请帮我写代码"

    def test_parse_empty_content(self):
        """空内容"""
        members = ["manager"]
        content = ""

        agent_name, clean_content = parse_agent_name(content, members)

        assert agent_name == "manager"
        assert clean_content == ""

    def test_parse_multiline_content(self):
        """多行内容"""
        members = ["manager", "coder"]
        content = "@coder 请帮我写一个函数\n要求：\n1. 支持异步\n2. 有错误处理"

        agent_name, clean_content = parse_agent_name(content, members)

        assert agent_name == "coder"
        assert clean_content == "请帮我写一个函数\n要求：\n1. 支持异步\n2. 有错误处理"


class TestParseMentions:
    """测试 parse_mentions()"""

    def test_replace_mentions_with_names(self):
        """将 mention 占位符替换为名称"""
        content = "@_user_1 请帮我处理@_user_2 的任务"
        mentions = [
            {"key": "@_user_1", "id": "ou_bot1", "name": "飞书机器人"},
            {"key": "@_user_2", "id": "ou_user1", "name": "张三"},
        ]

        result = parse_mentions(content, mentions)

        assert result == "@飞书机器人 请帮我处理@张三 的任务"

    def test_no_mentions(self):
        """没有 mention"""
        content = "普通消息"
        mentions = []

        result = parse_mentions(content, mentions)

        assert result == "普通消息"

    def test_single_mention(self):
        """单个 mention"""
        content = "@_user_1 你好"
        mentions = [{"key": "@_user_1", "id": "ou_bot1", "name": "飞书机器人"}]

        result = parse_mentions(content, mentions)

        assert result == "@飞书机器人 你好"


class TestMessageDeduplicator:
    """测试消息去重"""

    def test_not_duplicate(self):
        """非重复消息"""
        dedup = MessageDeduplicator()

        assert dedup.is_duplicate("msg_1") is False
        assert dedup.is_duplicate("msg_2") is False

    def test_is_duplicate(self):
        """重复消息"""
        dedup = MessageDeduplicator()

        dedup.is_duplicate("msg_1")
        assert dedup.is_duplicate("msg_1") is True

    def test_cache_eviction(self):
        """缓存淘汰"""
        dedup = MessageDeduplicator(max_size=3)

        # 添加 3 条消息，缓存满
        assert dedup.is_duplicate("msg_1") is False
        assert dedup.is_duplicate("msg_2") is False
        assert dedup.is_duplicate("msg_3") is False

        # 添加第 4 条，淘汰 msg_1
        assert dedup.is_duplicate("msg_4") is False

        # msg_2, msg_3, msg_4 仍在缓存中
        assert dedup.is_duplicate("msg_2") is True
        assert dedup.is_duplicate("msg_3") is True
        assert dedup.is_duplicate("msg_4") is True

    def test_move_to_end_on_access(self):
        """访问时移动到末尾"""
        dedup = MessageDeduplicator(max_size=4)

        # 添加 3 条消息
        dedup.is_duplicate("msg_1")
        dedup.is_duplicate("msg_2")
        dedup.is_duplicate("msg_3")

        # 访问 msg_1，移动到末尾，顺序变为 [msg_2, msg_3, msg_1]
        dedup.is_duplicate("msg_1")

        # 添加第 4 条，淘汰 msg_2（最旧的）
        dedup.is_duplicate("msg_4")

        # msg_1 仍在缓存中（访问后移动到末尾）
        assert dedup.is_duplicate("msg_1") is True
        # msg_3, msg_4 仍在缓存中
        assert dedup.is_duplicate("msg_3") is True
        assert dedup.is_duplicate("msg_4") is True
