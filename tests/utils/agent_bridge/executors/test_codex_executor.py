"""CodexExecutor 单元测试"""
import os
from unittest.mock import MagicMock
import pytest
from agents_hub.agent_bridge.executors.codex import CodexExecutor, _sanitize_for_codex_cli
from agents_hub.agent_bridge.executors.docker_codex import DockerCodexExecutor

from agents_hub.agent_bridge.executors.codex import CodexExecutor

from agents_hub.agent_bridge.models import AgentPlatform
from agents_hub.config.types import CODEX_COMMAND, DOCKER_CODEX_COMMAND
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


class TestCodexExecutorSystemPrompt:
    """CodexExecutor system_prompt 注入测试"""

    def setup_method(self):
        self.executor = CodexExecutor()
        self.config = RoleConfig(
            name="test",
            platform=AgentPlatform.CODEX,
        )

    def test_build_command_with_system_prompt(self):
        """契约：system_prompt 通过 -c instructions 注入到命令中"""
        cmd = self.executor._build_command(
            "测试", self.config, None, system_prompt="You are a helpful assistant."
        )

        assert "-c" in cmd
        # 找到 -c 后面的 instructions 参数
        c_idx = cmd.index("-c")
        assert "instructions=" in cmd[c_idx + 1]

    def test_build_command_system_prompt_none(self):
        """契约：system_prompt=None 时不注入 -c 参数"""
        cmd = self.executor._build_command("测试", self.config, None, system_prompt=None)

        assert "-c" not in cmd

    def test_build_command_system_prompt_strips_newlines(self):
        """契约：system_prompt 中的换行符被替换为空格"""
        cmd = self.executor._build_command(
            "测试", self.config, None, system_prompt="line1\nline2\rline3"
        )

        c_idx = cmd.index("-c")
        instructions_arg = cmd[c_idx + 1]
        assert "\n" not in instructions_arg
        assert "\r" not in instructions_arg

    def test_build_command_system_prompt_with_single_quote(self):
        """契约：system_prompt 中的单引号被正确转义，不破坏命令结构"""
        system_prompt = "Don't do X. It's a test."
        cmd = self.executor._build_command(
            "测试", self.config, None, system_prompt=system_prompt
        )

        c_idx = cmd.index("-c")
        instructions_arg = cmd[c_idx + 1]
        # instructions 参数应该包含完整内容，单引号被转义
        # 关键：值不能在第一个 ' 处截断
        assert "Don" in instructions_arg
        assert "do X" in instructions_arg
        assert "It" in instructions_arg
        assert "test." in instructions_arg

    def test_build_command_fork_from_with_system_prompt(self):
        """契约：fork 路径下 system_prompt 仍然被注入（当前 bug：fork 提前 return 跳过注入）"""
        cmd = self.executor._build_command(
            "测试", self.config, None, fork_from="source-session", system_prompt="You are helpful."
        )

        # fork 命令应该包含 system_prompt
        assert "-c" in cmd, "fork 路径下 system_prompt 应被注入"
        c_idx = cmd.index("-c")
        assert "instructions=" in cmd[c_idx + 1]

    def test_build_command_fork_from_with_single_quote_in_system_prompt(self):
        """契约：fork 路径下 system_prompt 包含单引号时正确处理"""
        cmd = self.executor._build_command(
            "测试", self.config, None,
            fork_from="source-session",
            system_prompt="Don't do X."
        )

        assert "-c" in cmd, "fork 路径下 system_prompt 应被注入"


class TestDockerCodexExecutorSystemPrompt:
    """DockerCodexExecutor system_prompt 注入测试"""

    def setup_method(self):
        self.executor = DockerCodexExecutor(docker_manager=MagicMock())
        self.config = RoleConfig(
            name="test",
            platform=AgentPlatform.CODEX,
        )

    def test_build_command_with_system_prompt(self):
        """契约：Docker 模式下 system_prompt 通过 -c instructions 注入"""
        cmd = self.executor._build_command(
            "测试", self.config, None, system_prompt="You are a helpful assistant."
        )

        assert "-c" in cmd
        c_idx = cmd.index("-c")
        assert "instructions=" in cmd[c_idx + 1]

    def test_build_command_fork_from_with_system_prompt(self):
        """契约：Docker 模式下 fork 路径 system_prompt 仍被注入"""
        cmd = self.executor._build_command(
            "测试", self.config, None, fork_from="source-session", system_prompt="You are helpful."
        )

        assert "-c" in cmd, "Docker fork 路径下 system_prompt 应被注入"


class TestSanitizeForCodexCli:
    """_sanitize_for_codex_cli 工具函数测试"""

    def test_strips_newlines(self):
        """契约：换行符被替换为空格"""
        result = _sanitize_for_codex_cli("line1\nline2\rline3")
        assert "\n" not in result
        assert "\r" not in result
        assert "line1" in result
        assert "line2" in result

    def test_escapes_single_quotes(self):
        """契约：单引号被正确转义，不会截断值"""
        result = _sanitize_for_codex_cli("Don't do X")
        # shlex.quote 会转义单引号
        assert "Don" in result
        assert "do X" in result

    def test_preserves_normal_text(self):
        """契约：普通文本不受影响"""
        result = _sanitize_for_codex_cli("hello world")
        assert "hello world" in result

    def test_handles_empty_string(self):
        """契约：空字符串返回 shlex.quote 格式的空值（调用方通过 if system_prompt: 跳过空值）"""
        assert _sanitize_for_codex_cli("") == "''"
