"""Codex CLI 执行器"""

import asyncio
import logging
import os
from collections.abc import AsyncIterator

from agents_hub.agent_bridge.exceptions import CLIExecutionError, CLINotFoundError
from agents_hub.config.types import CODEX_COMMAND
from agents_hub.roles.models import RoleConfig

logger = logging.getLogger(__name__)


class CodexExecutor:
    """执行 Codex CLI 命令"""

    async def execute(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None = None,
        cwd: str | None = None,
        fork_from: str | None = None,
    ) -> AsyncIterator[str]:
        """
        启动 Codex CLI 并返回原始输出流

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选，用于恢复会话）
            cwd: 项目目录路径（可选，通过 -C 参数指定工作目录）
            fork_from: 源会话 ID（可选，用于从群聊 fork 会话到单聊）

        Returns:
            AsyncIterator[str]: 原始 JSON 字符串流
        """
        # 移除换行符，避免 Codex CLI 命令行解析错误
        # 参考: docs/history-bugs/2026-05-28-cli-system-prompt-blocks-simple-requests.md
        prompt = prompt.replace("\n", " ").replace("\r", " ")

        cmd = self._build_command(prompt, config, session_id, cwd, fork_from)
        env = self._build_env(config)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env
            )
        except FileNotFoundError as e:
            logger.error(f"Codex CLI not found: {CODEX_COMMAND}")
            raise CLINotFoundError(platform="Codex", command=CODEX_COMMAND) from e

        assert process.stdout is not None
        async for line in process.stdout:
            decoded = line.decode("utf-8").strip()
            if decoded:
                yield decoded

        # 等待进程结束并检查返回码
        await process.wait()
        if process.returncode != 0:
            assert process.stderr is not None
            stderr = await process.stderr.read()
            stderr_text = stderr.decode("utf-8")
            logger.error(f"Codex CLI exited with code {process.returncode}: {stderr_text}")
            raise CLIExecutionError(
                platform="Codex", exit_code=process.returncode or 1, stderr=stderr_text
            )

    def _build_command(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None,
        cwd: str | None = None,
        fork_from: str | None = None,
    ) -> list:
        """构建 Codex CLI 命令"""
        if fork_from:
            # fork 会话：从源会话创建新分支
            cmd = [CODEX_COMMAND, "fork", fork_from, prompt]
            if cwd:
                cmd.extend(["-C", cwd])
            return cmd

        if session_id:
            # 恢复已有会话
            cmd = [
                CODEX_COMMAND,
                "exec",
                "resume",
                "--json",
                session_id,
            ]
        else:
            cmd = [
                CODEX_COMMAND,
                "exec",
                "--json",
            ]

        if cwd:
            cmd.extend(["-C", cwd])

        cmd.append(prompt)
        return cmd

    def _build_env(self, config: RoleConfig) -> dict:
        """构建环境变量"""
        env = os.environ.copy()
        if config.work_root:
            env["CODEX_HOME"] = config.work_root
        return env
