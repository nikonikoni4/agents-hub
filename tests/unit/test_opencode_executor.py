"""OpenCodeExecutor 单元测试"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from agents_hub.agent_bridge.exceptions import CLIExecutionError, CLINotFoundError
from agents_hub.agent_bridge.executors.opencode import OpenCodeExecutor
from agents_hub.config.types import AgentPlatform
from agents_hub.roles.models import RoleConfig


@pytest.fixture
def executor():
    return OpenCodeExecutor()


@pytest.fixture
def config():
    return RoleConfig(
        name="test-agent",
        platform=AgentPlatform.OPENCODE,
        work_root="D:\\test",
    )


@pytest.fixture
def config_no_work_root():
    return RoleConfig(
        name="test-agent",
        platform=AgentPlatform.OPENCODE,
    )


# =============================================================================
# _build_command
# =============================================================================


class TestBuildCommand:
    """_build_command 方法测试"""

    def test_build_command_basic(self, executor, config):
        """
        契约：基础命令包含 `opencode run --format json`

        验证方式：
        1. 调用 _build_command，只传必填参数
        2. 验证命令列表包含正确的基本命令
        3. 验证 prompt 作为最后一个参数

        如果失败，说明：命令构建逻辑错误
        """
        cmd = executor._build_command("hello", config, None)
        assert cmd[0].endswith("opencode.cmd") or cmd[0] == "opencode"
        assert cmd[1] == "run"
        assert "--format" in cmd
        assert "json" in cmd
        assert cmd[-1] == "hello"

    def test_build_command_with_session_id(self, executor, config):
        """
        契约：有 session_id 时添加 --session 参数

        验证方式：
        1. 调用 _build_command，传入 session_id
        2. 验证命令包含 --session 和对应值

        如果失败，说明：session_id 参数传递逻辑错误
        """
        cmd = executor._build_command("hello", config, "sess_123")
        assert "--session" in cmd
        idx = cmd.index("--session")
        assert cmd[idx + 1] == "sess_123"

    def test_build_command_with_system_prompt(self, executor, config):
        """
        契约：有 system_prompt 时添加 --agent 参数

        验证方式：
        1. 调用 _build_command，传入 system_prompt
        2. 验证命令包含 --agent 和对应值

        如果失败，说明：system_prompt 作为 agent 名称的逻辑错误
        """
        cmd = executor._build_command("hello", config, None, system_prompt="nico")
        assert "--agent" in cmd
        idx = cmd.index("--agent")
        assert cmd[idx + 1] == "nico"

    def test_build_command_with_all_params(self, executor, config):
        """
        契约：所有参数正确组合

        验证方式：
        1. 调用 _build_command，传入所有参数
        2. 验证命令包含所有参数

        如果失败，说明：参数组合逻辑错误
        """
        cmd = executor._build_command("hello", config, "sess_123", system_prompt="nico")
        assert "--session" in cmd
        assert "--agent" in cmd
        assert cmd[-1] == "hello"

    def test_build_command_no_optional_params(self, executor, config):
        """
        契约：无可选参数时命令只包含基本命令和 prompt

        验证方式：
        1. 调用 _build_command，不传可选参数
        2. 验证命令不包含 --session 和 --agent

        如果失败，说明：可选参数处理逻辑错误
        """
        cmd = executor._build_command("hello", config, None)
        assert "--session" not in cmd
        assert "--agent" not in cmd


# =============================================================================
# _build_env
# =============================================================================


class TestBuildEnv:
    """_build_env 方法测试"""

    def test_build_env_with_work_root(self, executor, config):
        """
        契约：有 work_root 时设置 OPENCODE_CONFIG_DIR

        验证方式：
        1. 调用 _build_env，传入有 work_root 的 config
        2. 验证环境变量包含 OPENCODE_CONFIG_DIR

        如果失败，说明：环境变量设置逻辑错误
        """
        env = executor._build_env(config)
        assert "OPENCODE_CONFIG_DIR" in env
        assert env["OPENCODE_CONFIG_DIR"] == "D:\\test"

    def test_build_env_without_work_root(self, executor, config_no_work_root):
        """
        契约：无 work_root 时不修改环境变量

        验证方式：
        1. 调用 _build_env，传入无 work_root 的 config
        2. 验证环境变量不包含 OPENCODE_CONFIG_DIR

        如果失败，说明：work_root 判断逻辑错误
        """
        env = executor._build_env(config_no_work_root)
        assert "OPENCODE_CONFIG_DIR" not in env


# =============================================================================
# _transform_event
# =============================================================================


class TestTransformEvent:
    """_transform_event 方法测试"""

    def test_transform_step_start_to_init(self, executor):
        """
        契约：step_start 转换为 init 类型

        验证方式：
        1. 构造 step_start 事件
        2. 调用 _transform_event
        3. 验证返回 init 类型

        如果失败，说明：事件类型映射错误
        """
        event = {
            "type": "step_start",
            "sessionID": "sess_123",
            "timestamp": 1234567890,
            "part": {"id": "part_1"},
        }
        result = executor._transform_event(event)
        assert result["type"] == "init"
        assert result["session_id"] == "sess_123"
        assert result["timestamp"] == 1234567890

    def test_transform_text_to_text_delta(self, executor):
        """
        契约：text 转换为 text_delta 类型

        验证方式：
        1. 构造 text 事件
        2. 调用 _transform_event
        3. 验证返回 text_delta 类型和文本内容

        如果失败，说明：text 事件处理错误
        """
        event = {
            "type": "text",
            "sessionID": "sess_123",
            "timestamp": 1234567890,
            "part": {
                "text": "hello world",
                "time": {"start": 100, "end": 200},
            },
        }
        result = executor._transform_event(event)
        assert result["type"] == "text_delta"
        assert result["text"] == "hello world"
        assert result["time"] == {"start": 100, "end": 200}

    def test_transform_step_finish_to_turn_complete(self, executor):
        """
        契约：step_finish 转换为 turn_complete 类型

        验证方式：
        1. 构造 step_finish 事件
        2. 调用 _transform_event
        3. 验证返回 turn_complete 类型和 token 信息

        如果失败，说明：step_finish 事件处理错误
        """
        event = {
            "type": "step_finish",
            "sessionID": "sess_123",
            "timestamp": 1234567890,
            "part": {
                "tokens": {"total": 100, "input": 50, "output": 50},
                "cost": 0.01,
                "reason": "stop",
            },
        }
        result = executor._transform_event(event)
        assert result["type"] == "turn_complete"
        assert result["tokens"] == {"total": 100, "input": 50, "output": 50}
        assert result["cost"] == 0.01
        assert result["reason"] == "stop"

    def test_transform_unknown_type(self, executor):
        """
        契约：未知类型保持原样

        验证方式：
        1. 构造未知类型事件
        2. 调用 _transform_event
        3. 验证返回原类型

        如果失败，说明：未知类型处理逻辑错误
        """
        event = {
            "type": "unknown_event",
            "sessionID": "sess_123",
            "timestamp": 1234567890,
            "part": {"data": "value"},
        }
        result = executor._transform_event(event)
        assert result["type"] == "unknown_event"
        assert result["data"] == {"data": "value"}

    def test_transform_missing_fields(self, executor):
        """
        契约：缺少字段时使用默认值

        验证方式：
        1. 构造缺少字段的事件
        2. 调用 _transform_event
        3. 验证使用默认值

        如果失败，说明：字段访问缺少默认值处理
        """
        event = {"type": "text"}
        result = executor._transform_event(event)
        assert result["type"] == "text_delta"
        assert result["text"] == ""
        assert result["session_id"] == ""

    def test_transform_empty_event_type(self, executor):
        """
        契约：空类型作为未知类型处理

        验证方式：
        1. 构造空类型事件
        2. 调用 _transform_event
        3. 验证返回空字符串类型

        如果失败，说明：空类型处理逻辑错误
        """
        event = {"part": {}}
        result = executor._transform_event(event)
        assert result["type"] == ""


# =============================================================================
# execute
# =============================================================================


class TestExecute:
    """execute 方法测试"""

    @pytest.mark.asyncio
    async def test_execute_raises_on_cli_not_found(self, executor, config):
        """
        契约：CLI 不存在时抛出 CLINotFoundError

        验证方式：
        1. mock asyncio.create_subprocess_exec 抛出 FileNotFoundError
        2. 调用 execute
        3. 验证抛出 CLINotFoundError

        如果失败，说明：异常处理逻辑错误
        """
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            with pytest.raises(CLINotFoundError) as exc_info:
                async for _ in executor.execute("hello", config):
                    pass
            assert exc_info.value.details["platform"] == "OpenCode"

    @pytest.mark.asyncio
    async def test_execute_raises_on_non_zero_exit(self, executor, config):
        """
        契约：CLI 返回非零退出码时抛出 CLIExecutionError

        验证方式：
        1. mock 进程返回非零退出码
        2. 调用 execute
        3. 验证抛出 CLIExecutionError

        如果失败，说明：退出码检查逻辑错误
        """
        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.read = AsyncMock(return_value=b"")
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"error message")
        mock_process.wait = AsyncMock()
        mock_process.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with pytest.raises(CLIExecutionError) as exc_info:
                async for _ in executor.execute("hello", config):
                    pass
            assert exc_info.value.details["exit_code"] == 1

    @pytest.mark.asyncio
    async def test_execute_returns_event_stream(self, executor, config):
        """
        契约：正常执行返回事件流

        验证方式：
        1. mock 进程输出有效的 JSON 事件
        2. 调用 execute
        3. 验证返回正确的事件

        如果失败，说明：事件流处理逻辑错误
        """
        output = (
            json.dumps(
                {
                    "type": "text",
                    "sessionID": "sess_123",
                    "timestamp": 1234567890,
                    "part": {"text": "hello"},
                }
            )
            + "\n"
        )

        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.read = AsyncMock(side_effect=[output.encode(), b""])
        mock_process.stderr = AsyncMock()
        mock_process.wait = AsyncMock()
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            events = []
            async for event in executor.execute("hello", config):
                events.append(event)

        assert len(events) == 1
        assert events[0]["type"] == "text_delta"
        assert events[0]["text"] == "hello"
