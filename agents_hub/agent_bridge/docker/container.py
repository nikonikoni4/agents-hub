"""Docker 容器抽象"""

import asyncio
import logging
from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


class DockerContainer:
    """Docker 容器抽象"""

    def __init__(
        self, name: str, agent_name: str, group_chat_id: str, worktree_name: str | None = None
    ):
        self.name = name
        self.agent_name = agent_name
        self.group_chat_id = group_chat_id
        self.worktree_name = worktree_name

    def build_exec_command(
        self,
        command: list[str],
        cwd: str = "/workspace",
    ) -> list[str]:
        """构建 docker exec 命令"""
        cmd = [
            "docker",
            "exec",
            "-w",
            cwd,
            "-e",
            "CLAUDE_CONFIG_DIR=/home/ai-user/.claude",
            self.name,
            *command,
        ]
        return cmd

    async def exec(
        self,
        command: list[str],
        cwd: str = "/workspace",
    ) -> AsyncIterator[str]:
        """在容器内执行命令并流式返回输出"""
        cmd = self.build_exec_command(command, cwd)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        assert process.stdout is not None
        async for line in process.stdout:
            decoded = line.decode("utf-8").strip()
            if decoded:
                yield decoded

        await process.wait()

        if process.returncode != 0:
            assert process.stderr is not None
            stderr = await process.stderr.read()
            stderr_text = stderr.decode("utf-8")
            logger.error(f"Container exec failed: {stderr_text}")
            raise RuntimeError(f"Container exec failed: {stderr_text}")
