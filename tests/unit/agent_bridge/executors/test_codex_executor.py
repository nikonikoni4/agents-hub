"""CodexExecutor 单元测试"""

import os
import pytest
from agents_hub.agent_bridge.executors.codex import CodexExecutor
from agents_hub.agent_bridge.config import RoleConfig, AgentPlatform


class TestCodexExecutor:
    """CodexExecutor 测试类"""

    def setup_method(self):
        self.executor = CodexExecutor()

    def test_build_command_basic(self):
        """测试构建基本命令"""
        config = RoleConfig(
            platform=AgentPlatform.CODEX,
            system_prompt="你是代码审查专家",
            skills=[],
            codex_home="/path/to/codex-home"
        )
        cmd = self.executor._build_command("审查代码", config, None)

        assert "codex" in cmd
        assert "exec" in cmd
        assert "--json" in cmd
        assert "审查代码" in cmd

    def test_build_command_with_session_id(self):
        """测试构建带 session_id 的命令"""
        config = RoleConfig(
            platform=AgentPlatform.CODEX,
            system_prompt="测试",
            skills=[],
            codex_home="/path/to/codex-home"
        )
        cmd = self.executor._build_command("测试", config, "session-123")

        assert "--session-id" in cmd
        assert "session-123" in cmd

    def test_build_env(self):
        """测试构建环境变量"""
        config = RoleConfig(
            platform=AgentPlatform.CODEX,
            system_prompt="测试",
            skills=[],
            codex_home="/path/to/codex-home"
        )
        env = self.executor._build_env(config)

        assert "CODEX_HOME" in env
        assert env["CODEX_HOME"] == "/path/to/codex-home"

    def test_build_env_no_codex_home(self):
        """测试没有 codex_home 时环境变量"""
        config = RoleConfig(
            platform=AgentPlatform.CODEX,
            system_prompt="测试",
            skills=[]
        )
        env = self.executor._build_env(config)

        # 应该保留原有的环境变量
        assert "PATH" in env
