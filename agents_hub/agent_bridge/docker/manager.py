"""Docker 容器池管理器"""

import asyncio
import logging
import subprocess
import time
from pathlib import Path

from agents_hub.agent_bridge.docker.container import DockerContainer
from agents_hub.core.foundation.exceptions import (
    DockerNotAvailableError,
    DockerStartError,
)

logger = logging.getLogger(__name__)


class DockerManager:
    """Docker 容器池管理器"""

    def __init__(self):
        self._containers: dict[tuple[str, str], DockerContainer] = {}
        self._cleanup_tasks: dict[tuple[str, str], asyncio.Task] = {}
        self._docker_status_cache: tuple[bool, float] = (False, 0)
        self._cache_ttl = 60  # 缓存 30 秒
        # TODO 需要检测docker 镜像是否存在

    def _is_docker_running(self) -> bool:
        """检查 Docker Engine 是否运行（带缓存）"""
        now = time.time()
        cached_status, cached_time = self._docker_status_cache

        if now - cached_time < self._cache_ttl:
            return cached_status

        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            status = result.returncode == 0
        except Exception:
            status = False

        self._docker_status_cache = (status, now)
        return status

    async def _container_exists(self, container_name: str) -> bool:
        """检查容器是否已存在"""
        process = await asyncio.create_subprocess_exec(
            "docker",
            "ps",
            "-a",
            "--filter",
            f"name={container_name}",
            "--format",
            "{{.Names}}",
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        return bool(stdout.strip())

    def _get_project_git_dir(self) -> str:
        """获取主仓库的 .git 目录（兼容 worktree）"""
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError("不在 git 仓库中")
        return str(Path(result.stdout.strip()).resolve())

    async def _create_container(
        self,
        agent_name: str,
        group_chat_id: str,
        work_root: str,
        cwd: str,
    ) -> DockerContainer:
        """创建新容器"""
        container_name = f"container-{agent_name}-{group_chat_id}"

        if await self._container_exists(container_name):
            logger.info(f"容器 {container_name} 已存在，先删除")
            await asyncio.create_subprocess_exec("docker", "rm", "-f", container_name)

        git_dir = self._get_project_git_dir()  # TODO 这里有问题
        cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "-v",
            f"{work_root}:/home/ai-user/.claude:rw",
            "-v",
            f"{cwd}:/workspace:rw",
            "-v",
            f"{git_dir}:/repo-git:rw",
            "--network",
            "host",
            "ai-tools:latest",
            "sleep",
            "infinity",
        ]

        logger.info(f"创建容器: {container_name}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.wait()

        if process.returncode != 0:
            assert process.stderr is not None
            stderr = await process.stderr.read()
            raise DockerStartError(container_name=container_name, reason=stderr.decode())

        logger.info(f"容器 {container_name} 创建成功")
        return DockerContainer(container_name, agent_name, group_chat_id)

    async def get_or_create_container(
        self,
        agent_name: str,
        group_chat_id: str,
        work_root: str,
        cwd: str,
    ) -> DockerContainer:
        """获取或创建容器（懒启动 + 懒检查）"""
        key = (agent_name, group_chat_id)

        if not self._is_docker_running():
            raise DockerNotAvailableError(
                agent_name=agent_name,
                group_chat_id=group_chat_id,
                message=(
                    "Docker Engine 未运行，无法启动沙箱容器。\n\n"
                    "解决方案：\n"
                    "1. 启动 Docker Desktop\n"
                    "2. 或在 agent_session_state.json 中设置 use_docker=false"
                ),
            )

        if key in self._cleanup_tasks:
            self._cleanup_tasks[key].cancel()
            del self._cleanup_tasks[key]

        if key in self._containers:
            return self._containers[key]

        self._containers[key] = await self._create_container(
            agent_name, group_chat_id, work_root, cwd
        )

        return self._containers[key]

    async def release_container(
        self,
        agent_name: str,
        group_chat_id: str,
    ):
        """释放容器（启动延迟销毁）"""
        key = (agent_name, group_chat_id)

        async def cleanup():
            await asyncio.sleep(10 * 60)  # 等待 10 分钟

            if key in self._containers:
                container = self._containers[key]
                logger.info(f"开始销毁容器: {container.name}")

                await asyncio.create_subprocess_exec("docker", "stop", container.name)
                await asyncio.create_subprocess_exec("docker", "rm", container.name)

                del self._containers[key]
                logger.info(f"容器 {container.name} 已销毁（10分钟空闲）")

        if key not in self._cleanup_tasks:
            self._cleanup_tasks[key] = asyncio.create_task(cleanup())
