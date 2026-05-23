"""Codex CLI 执行器"""

import asyncio
import os
from typing import AsyncIterator, Optional
from ..config import RoleConfig


class CodexExecutor:
    """执行 Codex CLI 命令"""

    async def execute(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        启动 Codex CLI 并返回原始输出流

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选，用于恢复会话）

        Returns:
            AsyncIterator[str]: 原始 JSON 字符串流
        """
        cmd = self._build_command(prompt, config, session_id)
        env = self._build_env(config)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )

        async for line in process.stdout:
            decoded = line.decode("utf-8").strip()
            if decoded:
                yield decoded

    def _build_command(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: Optional[str]
    ) -> list:
        """构建 Codex CLI 命令"""
        cmd = [
            "codex",
            "exec",
            "--json",
        ]

        # 添加 session_id（恢复会话）
        if session_id:
            cmd.extend(["--session-id", session_id])

        cmd.append(prompt)
        return cmd

    def _build_env(self, config: RoleConfig) -> dict:
        """构建环境变量"""
        env = os.environ.copy()
        if config.codex_home:
            env["CODEX_HOME"] = config.codex_home
        return env
