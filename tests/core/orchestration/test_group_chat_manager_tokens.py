"""
测试 GroupChatManager 的 token 索引管理功能
"""

from agents_hub.core.orchestration.group_chat_manager import GroupChatManager


class TestGroupChatManagerTokens:
    """测试 GroupChatManager 的 token 管理功能"""

    def test_register_token(self):
        """测试注册 token"""
        manager = GroupChatManager()
        token = "test_token_123"
        agent_name = "agent_a"
        group_chat_id = "chat_001"

        manager.register_token(token, agent_name, group_chat_id)

        # 验证 token 已注册
        result = manager.resolve_token(token)
        assert result is not None
        assert result == (agent_name, group_chat_id)

    def test_resolve_token_not_found(self):
        """测试解析不存在的 token 返回 None"""
        manager = GroupChatManager()

        result = manager.resolve_token("non_existent_token")
        assert result is None

    def test_register_multiple_tokens(self):
        """测试注册多个 token"""
        manager = GroupChatManager()

        tokens = [
            ("token_1", "agent_a", "chat_001"),
            ("token_2", "agent_b", "chat_001"),
            ("token_3", "agent_c", "chat_002"),
        ]

        for token, agent_name, group_chat_id in tokens:
            manager.register_token(token, agent_name, group_chat_id)

        # 验证所有 token 都能正确解析
        for token, agent_name, group_chat_id in tokens:
            result = manager.resolve_token(token)
            assert result == (agent_name, group_chat_id)

    def test_unregister_tokens_by_group_chat(self):
        """测试注销群聊的所有 token"""
        manager = GroupChatManager()

        # 注册多个 token，其中两个属于同一个群聊
        manager.register_token("token_1", "agent_a", "chat_001")
        manager.register_token("token_2", "agent_b", "chat_001")
        manager.register_token("token_3", "agent_c", "chat_002")

        # 注销 chat_001 的所有 token
        manager.unregister_tokens("chat_001")

        # 验证 chat_001 的 token 已被注销
        assert manager.resolve_token("token_1") is None
        assert manager.resolve_token("token_2") is None

        # 验证 chat_002 的 token 仍然存在
        assert manager.resolve_token("token_3") == ("agent_c", "chat_002")

    def test_unregister_tokens_empty_group_chat(self):
        """测试注销不存在的群聊 ID（幂等性）"""
        manager = GroupChatManager()

        # 注销不存在的群聊应该不抛出异常
        manager.unregister_tokens("non_existent_chat")

    def test_register_token_overwrite(self):
        """测试重复注册同一个 token 会覆盖"""
        manager = GroupChatManager()

        token = "token_1"
        manager.register_token(token, "agent_a", "chat_001")
        manager.register_token(token, "agent_b", "chat_002")

        # 验证 token 被覆盖为最新的注册信息
        result = manager.resolve_token(token)
        assert result == ("agent_b", "chat_002")

    def test_token_isolation_between_managers(self):
        """测试不同 manager 实例的 token 隔离"""
        manager1 = GroupChatManager()
        manager2 = GroupChatManager()

        manager1.register_token("token_1", "agent_a", "chat_001")

        # manager2 不应该能解析 manager1 的 token
        assert manager2.resolve_token("token_1") is None
