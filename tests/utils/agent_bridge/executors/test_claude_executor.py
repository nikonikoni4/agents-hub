"""ClaudeExecutor 单元测试"""

from agents_hub.agent_bridge.executors.claude import ClaudeExecutor
from agents_hub.agent_bridge.models import AgentPlatform
from agents_hub.config.types import CLAUDE_COMMAND
from agents_hub.roles.models import RoleConfig


class TestClaudeExecutor:
    """ClaudeExecutor 测试类"""

    def setup_method(self):
        self.executor = ClaudeExecutor()

    def test_build_command_basic(self):
        """测试构建基本命令"""
        config = RoleConfig(
            name="test",
            platform=AgentPlatform.CLAUDE,
        )
        cmd = self.executor._build_command("审查代码", config, None)

        assert CLAUDE_COMMAND in cmd
        assert "--print" in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd
        assert "审查代码" in cmd

    def test_build_command_no_system_prompt_flag(self):
        """测试不传 system_prompt 时命令不包含 --append-system-prompt"""
        config = RoleConfig(
            name="test",
            platform=AgentPlatform.CLAUDE,
        )
        cmd = self.executor._build_command("测试", config, None)

        assert "--append-system-prompt" not in cmd

    def test_build_command_with_system_prompt(self):
        """契约：传入 system_prompt 时命令包含 --append-system-prompt"""
        config = RoleConfig(
            name="test",
            platform=AgentPlatform.CLAUDE,
        )
        cmd = self.executor._build_command(
            "测试", config, None, system_prompt="You are a helpful assistant."
        )

        assert "--append-system-prompt" in cmd
        sp_idx = cmd.index("--append-system-prompt")
        assert cmd[sp_idx + 1] == "You are a helpful assistant."

    def test_build_command_system_prompt_none(self):
        """契约：system_prompt=None 时不注入 --append-system-prompt"""
        config = RoleConfig(
            name="test",
            platform=AgentPlatform.CLAUDE,
        )
        cmd = self.executor._build_command("测试", config, None, system_prompt=None)

        assert "--append-system-prompt" not in cmd

    def test_build_command_no_plugin_dir_flag(self):
        """测试命令不再包含 --plugin-dir（由 CLI 从目录自动加载）"""
        config = RoleConfig(
            name="test",
            platform=AgentPlatform.CLAUDE,
        )
        cmd = self.executor._build_command("测试", config, None)

        assert "--plugin-dir" not in cmd

    def test_build_command_with_session_id(self):
        """测试构建带 session_id 的命令"""
        config = RoleConfig(
            name="test",
            platform=AgentPlatform.CLAUDE,
        )
        cmd = self.executor._build_command("测试", config, "session-123")

        assert "--resume" in cmd
        assert "session-123" in cmd

    def test_build_command_no_session_id(self):
        """测试不带 session_id 时 --resume 不出现"""
        config = RoleConfig(
            name="test",
            platform=AgentPlatform.CLAUDE,
        )
        cmd = self.executor._build_command("测试", config, None)

        assert "--resume" not in cmd

    def test_build_command_verbose_flag(self):
        """测试命令包含 --verbose"""
        config = RoleConfig(
            name="test",
            platform=AgentPlatform.CLAUDE,
        )
        cmd = self.executor._build_command("测试", config, None)

        assert "--verbose" in cmd

    def test_build_command_include_partial_messages(self):
        """测试命令包含 --include-partial-messages"""
        config = RoleConfig(
            name="test",
            platform=AgentPlatform.CLAUDE,
        )
        cmd = self.executor._build_command("测试", config, None)

        assert "--include-partial-messages" in cmd

    def test_build_command_prompt_is_last(self):
        """测试 prompt 是命令的最后一个参数"""
        config = RoleConfig(
            name="test",
            platform=AgentPlatform.CLAUDE,
        )
        cmd = self.executor._build_command("用户输入", config, None)

        assert cmd[-1] == "用户输入"

    def test_build_command_full_scenario(self):
        """测试完整场景：带 session_id"""
        config = RoleConfig(
            name="test",
            platform=AgentPlatform.CLAUDE,
        )
        cmd = self.executor._build_command("审查 PR", config, "session-abc")

        # 基本参数
        assert CLAUDE_COMMAND in cmd
        assert "--print" in cmd
        assert "--verbose" in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd
        assert "--include-partial-messages" in cmd

        # 不应包含 system_prompt 和 skills 相关参数
        assert "--append-system-prompt" not in cmd
        assert "--plugin-dir" not in cmd

        # session_id
        assert "--resume" in cmd
        assert "session-abc" in cmd

        # prompt 是最后一个参数
        assert cmd[-1] == "审查 PR"

    def test_build_env(self):
        """测试构建环境变量"""
        config = RoleConfig(
            name="test",
            platform=AgentPlatform.CLAUDE,
            work_root="/path/to/claude-config"
        )
        env = self.executor._build_env(config)

        assert "CLAUDE_CONFIG_DIR" in env
        assert env["CLAUDE_CONFIG_DIR"] == "/path/to/claude-config"

    def test_build_env_no_work_root(self):
        """测试没有 work_root 时环境变量"""
        config = RoleConfig(
            name="test",
            platform=AgentPlatform.CLAUDE,
        )
        env = self.executor._build_env(config)

        # 应该保留原有的环境变量
        assert "PATH" in env
        assert "CLAUDE_CONFIG_DIR" not in env
