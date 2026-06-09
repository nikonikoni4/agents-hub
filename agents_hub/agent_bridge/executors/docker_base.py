"""Docker Executor 基类"""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from agents_hub.agent_bridge.docker.manager import DockerManager
from agents_hub.roles.models import RoleConfig

logger = logging.getLogger(__name__)


class DockerExecutor(ABC):
    """Docker Executor 基类"""

    def __init__(self, docker_manager: DockerManager):
        self._docker_manager = docker_manager

    @abstractmethod
    def _build_command(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None,
        *,
        fork_from: str | None = None,
        system_prompt: str | None = None,
    ) -> list[str]:
        """构建容器内执行的命令（子类实现）"""
        pass

    async def execute(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None = None,
        cwd: str | None = None,
        group_chat_id: str | None = None,
        fork_from: str | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """在 Docker 容器内执行命令"""
        if not cwd:
            raise ValueError("Docker 模式下必须提供 cwd")
        if not group_chat_id:
            raise ValueError("Docker 模式下必须提供 group_chat_id")
        if not config.work_root:
            raise ValueError("Docker 模式下必须提供 work_root")

        container = await self._docker_manager.get_or_create_container(
            agent_name=config.name,
            group_chat_id=group_chat_id,
            work_root=config.work_root,
            cwd=cwd,
        )

        command = self._build_command(
            prompt, config, session_id, fork_from=fork_from, system_prompt=system_prompt
        )

        async for line in container.exec(command, cwd="/workspace"):
            yield line

        await self._docker_manager.release_container(config.name, group_chat_id)
