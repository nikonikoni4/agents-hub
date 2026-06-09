"""Claude CLI 执行器"""

import asyncio
import logging
import os
from collections.abc import AsyncIterator

from agents_hub.agent_bridge.exceptions import CLIExecutionError, CLINotFoundError
from agents_hub.config.types import CLAUDE_COMMAND
from agents_hub.roles.models import RoleConfig

logger = logging.getLogger(__name__)


class ClaudeExecutor:
    """执行 Claude CLI 命令"""

    async def execute(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None = None,
        cwd: str | None = None,
        fork_from: str | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """
        启动 Claude CLI 并返回原始输出流

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选，用于恢复会话）
            cwd: 项目目录路径（可选，设置 CLI 工作目录）
            fork_from: 源会话 ID（可选，用于从群聊 fork 会话到单聊）
            system_prompt: 系统提示词（可选，通过 --append-system-prompt 注入）

        Returns:
            AsyncIterator[str]: 原始 JSON 字符串流
        """
        cmd = self._build_command(
            prompt, config, session_id, fork_from, system_prompt=system_prompt
        )
        env = self._build_env(config)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=cwd,
            )
        except FileNotFoundError as e:
            logger.error(f"Claude CLI not found: {CLAUDE_COMMAND}")
            raise CLINotFoundError(platform="Claude", command=CLAUDE_COMMAND) from e

        assert process.stdout is not None
        buffer = ""
        while True:
            chunk = await process.stdout.read(256 * 1024)  # 256KB
            if not chunk:
                break
            buffer += chunk.decode("utf-8")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                decoded = line.strip()
                if decoded:
                    yield decoded
        if buffer.strip():
            yield buffer.strip()

        # 等待进程结束并检查返回码
        await process.wait()
        if process.returncode != 0:
            assert process.stderr is not None
            stderr = await process.stderr.read()
            stderr_text = stderr.decode("utf-8")
            logger.error(f"Claude CLI exited with code {process.returncode}: {stderr_text}")
            raise CLIExecutionError(
                platform="Claude", exit_code=process.returncode or 1, stderr=stderr_text
            )

    def _build_command(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None,
        fork_from: str | None = None,
        system_prompt: str | None = None,
    ) -> list:
        """构建 Claude CLI 命令"""
        cmd = [
            CLAUDE_COMMAND,
            "--print",
            "--verbose",
            "--output-format",
            "stream-json",
            "--include-partial-messages",
        ]

        if config.bare:
            cmd.append("--bare")

        if fork_from:
            # fork 会话：从源会话创建新分支
            cmd.extend(["--fork-session", "--resume", fork_from])
        elif session_id:
            # 恢复已有会话
            cmd.extend(["--resume", session_id])

        if system_prompt:
            cmd.extend(["--append-system-prompt", system_prompt])

        cmd.append(prompt)
        return cmd

    def _build_env(self, config: RoleConfig) -> dict:
        """构建环境变量"""
        env = os.environ.copy()
        if config.work_root:
            env["CLAUDE_CONFIG_DIR"] = config.work_root
        return env
