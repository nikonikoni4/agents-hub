"""ClaudeExecutor 单元测试"""

import pytest
from backend.agent_bridge.executors.claude import ClaudeExecutor
from backend.agent_bridge.config import RoleConfig, AgentPlatform


class TestClaudeExecutor:
    """ClaudeExecutor 测试类"""

    def setup_method(self):
        self.executor = ClaudeExecutor()

    def test_build_command_basic(self):
        """测试构建基本命令"""
        config = RoleConfig(
            platform=AgentPlatform.CLAUDE,
            system_prompt="你是代码审查专家",
            skills=[]
        )
        cmd = self.executor._build_command("审查代码", config, None)

        assert "claude" in cmd
        assert "--print" in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd
        assert "--append-system-prompt" in cmd
        assert "你是代码审查专家" in cmd
        assert "审查代码" in cmd

    def test_build_command_with_session_id(self):
        """测试构建带 session_id 的命令"""
        config = RoleConfig(
            platform=AgentPlatform.CLAUDE,
            system_prompt="测试",
            skills=[]
        )
        cmd = self.executor._build_command("测试", config, "session-123")

        assert "--resume" in cmd
        assert "session-123" in cmd

    def test_build_command_with_skills(self):
        """测试构建带 skills 的命令"""
        config = RoleConfig(
            platform=AgentPlatform.CLAUDE,
            system_prompt="测试",
            skills=["code-review", "security-check"]
        )
        cmd = self.executor._build_command("测试", config, None)

        assert "--plugin-dir" in cmd
        assert "code-review" in cmd
        assert "security-check" in cmd

    def test_build_command_no_skills(self):
        """测试不带 skills 时 --plugin-dir 不出现"""
        config = RoleConfig(
            platform=AgentPlatform.CLAUDE,
            system_prompt="测试",
            skills=[]
        )
        cmd = self.executor._build_command("测试", config, None)

        assert "--plugin-dir" not in cmd

    def test_build_command_no_session_id(self):
        """测试不带 session_id 时 --resume 不出现"""
        config = RoleConfig(
            platform=AgentPlatform.CLAUDE,
            system_prompt="测试",
            skills=[]
        )
        cmd = self.executor._build_command("测试", config, None)

        assert "--resume" not in cmd

    def test_build_command_verbose_flag(self):
        """测试命令包含 --verbose"""
        config = RoleConfig(
            platform=AgentPlatform.CLAUDE,
            system_prompt="测试",
            skills=[]
        )
        cmd = self.executor._build_command("测试", config, None)

        assert "--verbose" in cmd

    def test_build_command_include_partial_messages(self):
        """测试命令包含 --include-partial-messages"""
        config = RoleConfig(
            platform=AgentPlatform.CLAUDE,
            system_prompt="测试",
            skills=[]
        )
        cmd = self.executor._build_command("测试", config, None)

        assert "--include-partial-messages" in cmd

    def test_build_command_prompt_is_last(self):
        """测试 prompt 是命令的最后一个参数"""
        config = RoleConfig(
            platform=AgentPlatform.CLAUDE,
            system_prompt="系统提示",
            skills=[]
        )
        cmd = self.executor._build_command("用户输入", config, None)

        assert cmd[-1] == "用户输入"

    def test_build_command_full_scenario(self):
        """测试完整场景：带 skills、session_id、system_prompt"""
        config = RoleConfig(
            platform=AgentPlatform.CLAUDE,
            system_prompt="你是安全审查专家",
            skills=["code-review", "security-check"]
        )
        cmd = self.executor._build_command("审查 PR", config, "session-abc")

        # 基本参数
        assert "claude" in cmd
        assert "--print" in cmd
        assert "--verbose" in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd
        assert "--include-partial-messages" in cmd

        # system prompt
        assert "--append-system-prompt" in cmd
        assert "你是安全审查专家" in cmd

        # skills
        assert "--plugin-dir" in cmd
        assert "code-review" in cmd
        assert "security-check" in cmd

        # session_id
        assert "--resume" in cmd
        assert "session-abc" in cmd

        # prompt 是最后一个参数
        assert cmd[-1] == "审查 PR"
