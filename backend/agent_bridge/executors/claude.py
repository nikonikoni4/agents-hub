"""Claude CLI 执行器"""

import asyncio
import logging
from typing import AsyncIterator, Optional
from ..config import RoleConfig

logger = logging.getLogger(__name__)


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

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        except FileNotFoundError:
            logger.error("Claude CLI not found. Please ensure 'claude' is installed and in PATH.")
            raise

        async for line in process.stdout:
            decoded = line.decode("utf-8").strip()
            if decoded:
                yield decoded

        # 等待进程结束并检查返回码
        await process.wait()
        if process.returncode != 0:
            stderr = await process.stderr.read()
            logger.warning(f"Claude CLI exited with code {process.returncode}: {stderr.decode('utf-8')}")

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
