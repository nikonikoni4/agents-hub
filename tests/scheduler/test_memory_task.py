"""MemoryTask 单元测试

测试记忆任务执行的核心功能：
- execute() 调用 agent_platform_client.execute
- 错误处理（不抛出异常，返回错误描述）
- prompt 构建
- history.jsonl 裁剪
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_hub.scheduler.task.memory_task import MemoryTask, trim_history_jsonl


@pytest.fixture
def memory_task() -> MemoryTask:
    return MemoryTask()


class TestMemoryTaskExecute:
    """execute() 方法测试"""

    @pytest.mark.asyncio
    async def test_execute_success(self, memory_task: MemoryTask):
        """正常执行返回成功消息"""
        mock_result = MagicMock()
        mock_result.text = "记忆收集完成"

        with (
            patch("agents_hub.scheduler.task.memory_task.agent_platform_client") as mock_client,
            patch("agents_hub.scheduler.task.memory_task.RoleManager") as mock_rm_cls,
            patch("agents_hub.scheduler.task.memory_task.config") as mock_config,
        ):
            mock_client.execute = AsyncMock(return_value=mock_result)
            mock_role = MagicMock()
            mock_role.get_role_config.return_value = MagicMock()
            mock_rm_cls.return_value.get_role.return_value = mock_role
            mock_config.default_memory_assistant_name = "Agents-Hub-Memory-Assistant"
            mock_config.assistant_token = "agents-hub-system"

            result = await memory_task.execute("chat-1", None)

        assert "记忆收集完成" in result
        mock_client.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_failure_returns_error(self, memory_task: MemoryTask):
        """执行失败时返回错误描述，不抛出异常"""
        with (
            patch("agents_hub.scheduler.task.memory_task.agent_platform_client") as mock_client,
            patch("agents_hub.scheduler.task.memory_task.RoleManager") as mock_rm_cls,
            patch("agents_hub.scheduler.task.memory_task.config") as mock_config,
        ):
            mock_client.execute = AsyncMock(side_effect=RuntimeError("CLI 超时"))
            mock_role = MagicMock()
            mock_role.get_role_config.return_value = MagicMock()
            mock_rm_cls.return_value.get_role.return_value = mock_role
            mock_config.default_memory_assistant_name = "Agents-Hub-Memory-Assistant"
            mock_config.assistant_token = "agents-hub-system"

            result = await memory_task.execute("chat-1", None)

        assert "失败" in result or "CLI 超时" in result

    @pytest.mark.asyncio
    async def test_execute_prompt_includes_agent_token(self, memory_task: MemoryTask):
        """prompt 包含 agent token"""
        mock_result = MagicMock()
        mock_result.text = "完成"

        with (
            patch("agents_hub.scheduler.task.memory_task.agent_platform_client") as mock_client,
            patch("agents_hub.scheduler.task.memory_task.RoleManager") as mock_rm_cls,
            patch("agents_hub.scheduler.task.memory_task.config") as mock_config,
        ):
            mock_client.execute = AsyncMock(return_value=mock_result)
            mock_role = MagicMock()
            mock_role_config = MagicMock()
            mock_role.get_role_config.return_value = mock_role_config
            mock_rm_cls.return_value.get_role.return_value = mock_role
            mock_config.default_memory_assistant_name = "Agents-Hub-Memory-Assistant"
            mock_config.assistant_token = "agents-hub-system"

            await memory_task.execute("chat-1", "2026-06-24T10:00:00Z")

        call_kwargs = mock_client.execute.call_args
        prompt = call_kwargs.kwargs.get("prompt") or call_kwargs[0][0]
        assert "agents-hub-system" in prompt
        assert "chat-1" in prompt
        assert "2026-06-24T10:00:00Z" in prompt

    @pytest.mark.asyncio
    async def test_execute_first_run_prompt(self, memory_task: MemoryTask):
        """首次执行时 prompt 包含首次执行提示"""
        mock_result = MagicMock()
        mock_result.text = "完成"

        with (
            patch("agents_hub.scheduler.task.memory_task.agent_platform_client") as mock_client,
            patch("agents_hub.scheduler.task.memory_task.RoleManager") as mock_rm_cls,
            patch("agents_hub.scheduler.task.memory_task.config") as mock_config,
        ):
            mock_client.execute = AsyncMock(return_value=mock_result)
            mock_role = MagicMock()
            mock_role.get_role_config.return_value = MagicMock()
            mock_rm_cls.return_value.get_role.return_value = mock_role
            mock_config.default_memory_assistant_name = "Agents-Hub-Memory-Assistant"
            mock_config.assistant_token = "agents-hub-system"

            await memory_task.execute("chat-1", None)

        call_kwargs = mock_client.execute.call_args
        prompt = call_kwargs.kwargs.get("prompt") or call_kwargs[0][0]
        assert "首次" in prompt


class TestBuildMemoryPrompt:
    """prompt 构建测试"""

    def test_prompt_with_last_updated(self):
        from agents_hub.scheduler.task.memory_task import _build_memory_prompt

        prompt = _build_memory_prompt("chat-1", "2026-06-24T10:00:00Z")
        assert "chat-1" in prompt
        assert "2026-06-24T10:00:00Z" in prompt
        assert "首次" not in prompt

    def test_prompt_without_last_updated(self):
        from agents_hub.scheduler.task.memory_task import _build_memory_prompt

        prompt = _build_memory_prompt("chat-1", None)
        assert "chat-1" in prompt
        assert "首次" in prompt


class TestTrimHistoryJsonl:
    """history.jsonl 裁剪测试"""

    def test_no_file_does_nothing(self, tmp_path: Path):
        trim_history_jsonl(tmp_path / "nonexistent.jsonl")

    def test_under_limit_unchanged(self, tmp_path: Path):
        path = tmp_path / "history.jsonl"
        lines = [f'{{"i": {i}}}' for i in range(5)]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        trim_history_jsonl(path, max_lines=10)

        result = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(result) == 5

    def test_over_limit_trims(self, tmp_path: Path):
        path = tmp_path / "history.jsonl"
        lines = [f'{{"i": {i}}}' for i in range(1500)]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        trim_history_jsonl(path, max_lines=1000)

        result = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(result) == 1000
        # 保留的是最后 1000 条
        import json

        first = json.loads(result[0])
        assert first["i"] == 500
