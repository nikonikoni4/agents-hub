"""Docker Executor 基类"""

import asyncio
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
        # 进程追踪字典：key = session_id, value = Process
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._lock = asyncio.Lock()

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

        # 直接调用 asyncio.create_subprocess_exec，不经过 container.exec()
        # 这样可以获取进程引用并追踪
        docker_cmd = container.build_exec_command(command, cwd="/workspace")

        process = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # 注册进程（如果有 session_id）
        if session_id:
            async with self._lock:
                self._processes[session_id] = process

        try:
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
        finally:
            # 清理进程引用
            if session_id:
                async with self._lock:
                    self._processes.pop(session_id, None)

        await self._docker_manager.release_container(config.name, group_chat_id)

    async def stop_session(self, session_id: str):
        """
        立即终止指定 session 的进程

        Args:
            session_id: 会话 ID
        """
        async with self._lock:
            process = self._processes.get(session_id)
            if process:
                try:
                    process.kill()  # 立即 SIGKILL (Unix) 或 TerminateProcess (Windows)
                    await process.wait()
                    logger.info(f"[DockerExecutor] 已终止 session {session_id} 的进程")
                except ProcessLookupError:
                    # 进程已经退出
                    logger.debug(f"[DockerExecutor] session {session_id} 的进程已不存在")
                finally:
                    self._processes.pop(session_id, None)
