"""Claude CLI 执行器"""

import asyncio
from typing import AsyncIterator, Optional
from ..config import RoleConfig


class ClaudeExecutor:
    """执行 Claude CLI 命令"""

    async def execute(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        启动 Claude CLI 并返回原始输出流

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选，用于恢复会话）

        Returns:
            AsyncIterator[str]: 原始 JSON 字符串流
        """
        cmd = self._build_command(prompt, config, session_id)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
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
        """构建 Claude CLI 命令"""
        cmd = [
            "claude",
            "--print",
            "--verbose",
            "--output-format", "stream-json",
            "--include-partial-messages",
            "--append-system-prompt", config.system_prompt,
        ]

        # 添加 skills（plugin-dir）
        for skill in config.skills:
            cmd.extend(["--plugin-dir", skill])

        # 添加 session_id（恢复会话）
        if session_id:
            cmd.extend(["--resume", session_id])

        cmd.append(prompt)
        return cmd
