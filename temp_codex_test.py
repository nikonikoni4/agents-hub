"""CodexExecutor 单元测试"""

from agents_hub.agent_bridge.executors.codex import CodexExecutor
from agents_hub.agent_bridge.models import AgentPlatform
from agents_hub.config.types import CODEX_COMMAND
from agents_hub.roles.models import RoleConfig


class TestCodexExecutor:
    """CodexExecutor 测试类"""

    def setup_method(self):
        self.executor = CodexExecutor()

    def test_build_command_basic(self):
        """测试构建基本命令"""
        config = RoleConfig(
            name="test",
            platform=AgentPlatform.CODEX,
            work_root="/path/to/codex-home"
        )
        cmd = self.executor._build_command("审查代码", config, None)

        assert CODEX_COMMAND in cmd
        assert "exec" in cmd
        assert "--json" in cmd
        assert "审查代码" in cmd

    def test_build_command_with_session_id(self):
        """测试构建恢复会话的命令（使用 resume 子命令）"""
        config = RoleConfig(
            name="test",
            platform=AgentPlatform.CODEX,
            work_root="/path/to/codex-home"
        )
        cmd = self.executor._build_command("测试", config, "session-123")

        assert "resume" in cmd
        assert "session-123" in cmd
        assert "--json" in cmd

    def test_build_env(self):
        """测试构建环境变量"""
        config = RoleConfig(
            name="test",
            platform=AgentPlatform.CODEX,
            work_root="/path/to/codex-home"
        )
        env = self.executor._build_env(config)

        assert "CODEX_HOME" in env
        assert env["CODEX_HOME"] == "/path/to/codex-home"

    def test_build_env_no_work_root(self):
        """测试没有 work_root 时环境变量"""
        config = RoleConfig(
            name="test",
            platform=AgentPlatform.CODEX,
        )
        env = self.executor._build_env(config)

        # 应该保留原有的环境变量
        assert "PATH" in env
