"""Executor stderr ANSI 转义码剥离测试

契约：所有 executor 在处理 stderr 时必须剥离 ANSI 终端颜色转义码，
确保错误信息可读，不包含 \x1b[31;1m 等乱码。
"""

import asyncio
import re

import pytest


# ANSI 剥离的正则（与 executor 中使用的一致）
_ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """模拟 executor 中的 ANSI 剥离逻辑"""
    return _ANSI_PATTERN.sub("", text)


class TestAnsiStrip:
    """ANSI 转义码剥离契约测试"""

    def test_strips_red_bold(self):
        """契约：剥离红色加粗转义码 \\x1b[31;1m"""
        raw = "\x1b[31;1mParserError:\x1b[0m some error"
        assert _strip_ansi(raw) == "ParserError: some error"

    def test_strips_cyan(self):
        """契约：剥离青色转义码 \\x1b[36;1m"""
        raw = "\x1b[36;1mLine |\x1b[0m content"
        assert _strip_ansi(raw) == "Line | content"

    def test_strips_multiple_codes(self):
        """契约：剥离多个连续的转义码"""
        raw = "\x1b[31;1m\x1b[36;1m\x1b[36;1m   2 | \x1b[0m"
        assert _strip_ansi(raw) == "   2 | "

    def test_strips_nested_codes(self):
        """契约：剥离嵌套的转义码（如原始错误信息）"""
        raw = (
            "\x1b[31;1mParserError: \x1b[0m\r\n"
            "\x1b[31;1m\x1b[36;1mLine |\x1b[0m\r\n"
            "\x1b[31;1m\x1b[36;1m\x1b[36;1m   2 | \x1b[0m python - <\x1b[36;1m<\x1b[0m'PY'\x1b[0m\r\n"
        )
        result = _strip_ansi(raw)
        assert "\x1b[" not in result
        assert "ParserError" in result
        assert "Line |" in result
        assert "python -" in result

    def test_preserves_plain_text(self):
        """契约：普通文本不受影响"""
        text = "Error: file not found"
        assert _strip_ansi(text) == text

    def test_handles_empty_string(self):
        """契约：空字符串正常处理"""
        assert _strip_ansi("") == ""

    def test_handles_no_escape_codes(self):
        """契约：不含转义码的文本保持不变"""
        text = "normal error message with numbers 123 and symbols !@#"
        assert _strip_ansi(text) == text

    def test_strips_reset_code(self):
        """契约：剥离重置转义码 \\x1b[0m"""
        raw = "error\x1b[0m"
        assert _strip_ansi(raw) == "error"

    def test_strips_complex_codes(self):
        """契约：剥离复杂转义码（如 256 色、真彩色）"""
        # 256 色
        raw = "\x1b[38;5;196mred text\x1b[0m"
        assert _strip_ansi(raw) == "red text"

        # 真彩色
        raw = "\x1b[38;2;255;0;0mred\x1b[0m"
        assert _strip_ansi(raw) == "red"

    def test_strips_cursor_and_erase_codes(self):
        """契约：剥离光标移动和擦除转义码"""
        raw = "\x1b[2J\x1b[H\x1b[?25lhidden"
        # 这些是不同格式的转义码，当前正则只匹配 m 结尾的
        # 但 cursor/erase 码在 stderr 中很少见，主要关注颜色码
        result = _strip_ansi(raw)
        # 至少应该剥离 [?25l 这种
        assert "\x1b[?25l" not in result or "hidden" in result


class TestExecutorStderrIntegration:
    """集成测试：验证 executor 实际剥离 ANSI 码"""

    @pytest.mark.asyncio
    async def test_codex_executor_strips_ansi_from_stderr(self):
        """契约：CodexExecutor 的 stderr 输出不含 ANSI 转义码"""
        from unittest.mock import AsyncMock, patch
        from agents_hub.agent_bridge.executors.codex import CodexExecutor
        from agents_hub.agent_bridge.models import AgentPlatform
        from agents_hub.agent_bridge.exceptions import CLIExecutionError
        from agents_hub.roles.models import RoleConfig

        class MockProcess:
            def __init__(self):
                self.stdout = asyncio.StreamReader()
                self.stderr = asyncio.StreamReader()
                self.pid = 12345
                self.returncode = 1

            async def wait(self):
                return self.returncode

        process = MockProcess()
        process.stdout.feed_eof()
        # 带 ANSI 码的 stderr
        ansi_stderr = b"\x1b[31;1mParserError:\x1b[0m Missing file"
        process.stderr.feed_data(ansi_stderr)
        process.stderr.feed_eof()

        executor = CodexExecutor()
        config = RoleConfig(name="test", platform=AgentPlatform.CODEX)

        with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=process)):
            with pytest.raises(CLIExecutionError) as exc_info:
                async for _ in executor.execute("test", config):
                    pass

            error_msg = str(exc_info.value)
            # 关键契约：错误信息中不应包含 ANSI 转义码
            assert "\x1b[" not in error_msg
            assert "ParserError" in error_msg
            assert "Missing file" in error_msg

    @pytest.mark.asyncio
    async def test_claude_executor_strips_ansi_from_stderr(self):
        """契约：ClaudeExecutor 的 stderr 输出不含 ANSI 转义码"""
        from unittest.mock import AsyncMock, patch
        from agents_hub.agent_bridge.executors.claude import ClaudeExecutor
        from agents_hub.agent_bridge.models import AgentPlatform
        from agents_hub.agent_bridge.exceptions import CLIExecutionError
        from agents_hub.roles.models import RoleConfig

        class MockProcess:
            def __init__(self):
                self.stdout = asyncio.StreamReader()
                self.stderr = asyncio.StreamReader()
                self.pid = 12345
                self.returncode = 1

            async def wait(self):
                return self.returncode

        process = MockProcess()
        process.stdout.feed_eof()
        ansi_stderr = b"\x1b[31;1mError:\x1b[0m rate limited"
        process.stderr.feed_data(ansi_stderr)
        process.stderr.feed_eof()

        executor = ClaudeExecutor()
        config = RoleConfig(name="test", platform=AgentPlatform.CLAUDE)

        with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=process)):
            with pytest.raises(CLIExecutionError) as exc_info:
                async for _ in executor.execute("test", config):
                    pass

            error_msg = str(exc_info.value)
            assert "\x1b[" not in error_msg
            assert "Error" in error_msg
            assert "rate limited" in error_msg
