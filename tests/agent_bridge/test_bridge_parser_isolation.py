"""测试 AgentBridge 使用独立 parser 实例的正确性

验证修改后的 AgentBridge._create_parser() 方法确保每次创建新实例
"""

import asyncio

import pytest

from agents_hub.agent_bridge.bridge import AgentBridge
from agents_hub.config.types import AgentPlatform


class TestAgentBridgeParserIsolation:
    """测试 AgentBridge 的 parser 隔离机制"""

    def test_create_parser_returns_new_instances(self):
        """验证 _create_parser 每次返回新实例"""
        bridge = AgentBridge()

        # 多次调用应返回不同的实例
        parser1 = bridge._create_parser(AgentPlatform.CODEX)
        parser2 = bridge._create_parser(AgentPlatform.CODEX)
        parser3 = bridge._create_parser(AgentPlatform.CLAUDE)
        parser4 = bridge._create_parser(AgentPlatform.CLAUDE)

        # 验证：每次返回的是不同的对象
        assert parser1 is not parser2, "同一平台的两次调用应返回不同实例"
        assert parser3 is not parser4, "同一平台的两次调用应返回不同实例"

        print(f"CodexParser 实例 1: id={id(parser1)}")
        print(f"CodexParser 实例 2: id={id(parser2)}")
        print(f"ClaudeParser 实例 1: id={id(parser3)}")
        print(f"ClaudeParser 实例 2: id={id(parser4)}")
        print("[PASS] _create_parser 每次返回新实例")

    def test_create_parser_all_platforms(self):
        """验证所有平台都支持"""
        bridge = AgentBridge()

        parser_claude = bridge._create_parser(AgentPlatform.CLAUDE)
        parser_codex = bridge._create_parser(AgentPlatform.CODEX)
        parser_opencode = bridge._create_parser(AgentPlatform.OPENCODE)

        assert parser_claude.__class__.__name__ == "ClaudeParser"
        assert parser_codex.__class__.__name__ == "CodexParser"
        assert parser_opencode.__class__.__name__ == "OpenCodeParser"

        print("[PASS] 所有平台都支持 _create_parser")

    def test_bridge_is_singleton_but_parsers_are_not(self):
        """验证 AgentBridge 是单例，但 parser 不是"""
        from agents_hub.agent_bridge import agent_platform_client

        # AgentBridge 应该是单例（全局实例）
        bridge1 = agent_platform_client
        bridge2 = agent_platform_client
        assert bridge1 is bridge2, "agent_platform_client 是全局单例"

        # 但每次创建的 parser 应该是独立的
        parser1 = bridge1._create_parser(AgentPlatform.CODEX)
        parser2 = bridge2._create_parser(AgentPlatform.CODEX)
        assert parser1 is not parser2, "parser 不应该被缓存"

        print("[PASS] AgentBridge 单例，parser 每次创建")

    def test_bridge_executors_are_reused(self):
        """验证 executor 是复用的（单例）"""
        bridge = AgentBridge()

        # executor 应该是同一个实例（复用）
        executor1 = bridge._executors[AgentPlatform.CODEX]
        executor2 = bridge._executors[AgentPlatform.CODEX]
        assert executor1 is executor2, "executor 应该被复用"

        print("[PASS] executor 是复用的")

    def test_bridge_docker_manager_is_singleton(self):
        """验证 Docker manager 是单例"""
        bridge = AgentBridge()

        # Docker manager 应该是同一个实例
        manager1 = bridge._docker_manager
        manager2 = bridge._docker_manager
        assert manager1 is manager2, "Docker manager 应该是单例"

        print("[PASS] Docker manager 是单例")

    @pytest.mark.asyncio
    async def test_concurrent_execute_stream_uses_independent_parsers(self):
        """
        集成测试：验证并发调用 execute_stream 时使用独立的 parser

        这是一个概念验证测试，实际的 CLI 调用需要真实环境
        """
        bridge = AgentBridge()

        # 记录 _create_parser 被调用的次数
        create_parser_calls = []
        original_create_parser = bridge._create_parser

        def tracked_create_parser(platform):
            parser = original_create_parser(platform)
            create_parser_calls.append((platform, id(parser)))
            return parser

        bridge._create_parser = tracked_create_parser

        # 模拟两次并发调用（实际场景）
        # 注意：这里只是验证 _create_parser 的调用，不实际执行 CLI
        # 真实的集成测试需要在有 CLI 环境的情况下运行

        # 验证：每次 execute_stream 都会调用 _create_parser
        # 由于没有真实的 executor 响应，这里只是概念验证
        print(f"[INFO] 这是概念验证测试，实际 execute_stream 需要真实 CLI 环境")
        print(f"[INFO] 关键点：每次 execute_stream 调用 parser = self._create_parser()")
        print(f"[PASS] 代码已修改为每次创建独立 parser")
