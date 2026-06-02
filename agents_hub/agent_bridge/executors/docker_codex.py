"""Docker 模式的 Codex Executor"""

import logging

from agents_hub.agent_bridge.executors.docker_base import DockerExecutor
from agents_hub.config.types import CODEX_COMMAND
from agents_hub.roles.models import RoleConfig

logger = logging.getLogger(__name__)


class DockerCodexExecutor(DockerExecutor):
    """在 Docker 容器内执行 Codex CLI"""

    def _build_command(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None,
    ) -> list[str]:
        """构建 Codex CLI 命令（强制跳过审批和沙箱）"""
        cmd = [
            CODEX_COMMAND,
            "--dangerously-bypass-approvals-and-sandbox",
            "--print",
            "--output-format",
            "stream-json",
        ]

        if session_id:
            cmd.extend(["--resume", session_id])

        cmd.append(prompt)
        return cmd
