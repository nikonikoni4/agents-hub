"""Docker 模式的 Claude Executor"""

import logging

from agents_hub.agent_bridge.executors.docker_base import DockerExecutor
from agents_hub.config.types import DOCKER_CLAUDE_COMMAND
from agents_hub.roles.models import RoleConfig

logger = logging.getLogger(__name__)


class DockerClaudeExecutor(DockerExecutor):
    """在 Docker 容器内执行 Claude CLI"""

    def _build_command(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None,
    ) -> list[str]:
        """构建 Claude CLI 命令（强制跳过权限检查）"""
        cmd = [
            DOCKER_CLAUDE_COMMAND,
            "--dangerously-skip-permissions",
            "--print",
            "--verbose",
            "--output-format",
            "stream-json",
            "--include-partial-messages",
        ]

        if config.bare:
            cmd.append("--bare")

        if session_id:
            cmd.extend(["--resume", session_id])

        cmd.append(prompt)
        return cmd
