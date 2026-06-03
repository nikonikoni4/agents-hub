"""Docker 容器池管理器"""

import asyncio
import logging
import subprocess
import time
from pathlib import Path

from agents_hub.agent_bridge.docker.container import DockerContainer
from agents_hub.config import config
from agents_hub.core.foundation.exceptions import (
    DockerNotAvailableError,
    DockerStartError,
)
from agents_hub.exceptions import StateError

logger = logging.getLogger(__name__)


class DockerManager:
    """Docker 容器池管理器"""

    def __init__(self, cleanup_timeout: float = 10 * 60):
        self._containers: dict[tuple[str, str], DockerContainer] = {}
        self._cleanup_tasks: dict[tuple[str, str], asyncio.Task] = {}
        self._docker_status_cache: tuple[bool, float] = (False, 0)
        self._cache_ttl = 60  # 缓存 30 秒
        self._cleanup_timeout = cleanup_timeout  # 容器空闲销毁等待时间（秒）
        # git 路径修复状态：key → (cwd, worktree_name, orig_git_content, orig_gitdir_content)
        self._git_fix_state: dict[tuple[str, str], tuple[str, str, str, str]] = {}
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

    def _get_project_git_dir(self) -> str | None:
        """获取主仓库的 .git 目录（兼容 worktree），无仓库时返回 None"""
        current = Path.cwd()
        for parent in [current, *current.parents]:
            git_path = parent / ".git"
            if git_path.is_file():
                # worktree：读取 gitdir，再从 worktree 元数据找 commondir
                gitdir = Path(git_path.read_text(encoding="utf-8").strip().removeprefix("gitdir: "))
                commondir_file = gitdir / "commondir"
                if commondir_file.is_file():
                    return str(
                        (gitdir / commondir_file.read_text(encoding="utf-8").strip()).resolve()
                    )
            elif git_path.is_dir():
                return str(git_path.resolve())
        return None

    def _fix_git_paths(self, cwd: str, worktree_name: str, container: DockerContainer) -> None:
        """修复 git worktree 路径引用（volume 共享，直接在宿主机操作）。

        Args:
            cwd: 宿主机 worktree 目录路径，挂载到容器 /workspace，
            比如 D:/desktop/软件开发/agents-hub/.claude/worktrees/feat_group_chat_service
            worktree_name: worktree 名称（目录名），对应 /repo-git/worktrees/<name>
            container: 容器实例，用于关联修复状态
        """
        git_file = Path(cwd) / ".git"
        git_dir = self._get_project_git_dir()
        if git_dir is None:
            raise StateError("worktree 模式下 git_dir 不应为 None")
        gitdir_file = Path(git_dir) / "worktrees" / worktree_name / "gitdir"

        # 存储原始内容
        orig_git = git_file.read_text(encoding="utf-8")
        orig_gitdir = gitdir_file.read_text(encoding="utf-8")

        # 写入容器内路径（volume 同步到容器）
        git_file.write_text(f"gitdir: /repo-git/worktrees/{worktree_name}\n", encoding="utf-8")
        gitdir_file.write_text("/workspace/.git\n", encoding="utf-8")

        key = (container.agent_name, container.group_chat_id)
        self._git_fix_state[key] = (cwd, worktree_name, orig_git, orig_gitdir)
        logger.info(f"已修复 git 路径 (worktree: {worktree_name})")

    def _revert_git_paths(self, container: DockerContainer) -> None:
        """回退 git 路径到原始宿主机路径"""
        key = (container.agent_name, container.group_chat_id)
        state = self._git_fix_state.pop(key, None)
        if not state:
            return

        cwd, worktree_name, orig_git, orig_gitdir = state
        git_file = Path(cwd) / ".git"
        git_dir = self._get_project_git_dir()
        if git_dir is None:
            raise StateError("worktree 模式下 git_dir 不应为 None")
        gitdir_file = Path(git_dir) / "worktrees" / worktree_name / "gitdir"

        git_file.write_text(orig_git, encoding="utf-8")
        gitdir_file.write_text(orig_gitdir, encoding="utf-8")
        logger.info(f"已回退 git 路径 (worktree: {worktree_name})")

    async def _create_container(
        self,
        agent_name: str,
        group_chat_id: str,
        work_root: str,
        cwd: str,
    ) -> DockerContainer:
        """创建新容器。

        Args:
            cwd: 宿主机 worktree 目录路径，挂载到容器 /workspace
        """
        container_name = f"container-{agent_name}-{group_chat_id}"

        if await self._container_exists(container_name):
            logger.info(f"容器 {container_name} 已存在，先删除")
            await asyncio.create_subprocess_exec("docker", "rm", "-f", container_name)

        # 检测 git 仓库（降级：无仓库时不挂载）
        git_dir = self._get_project_git_dir()

        # 检测是否为 worktree（.git 是文件而非目录）
        worktree_name = None
        if git_dir and (Path(cwd) / ".git").is_file():
            worktree_name = Path(cwd).name

        # 构建 docker run 命令
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
        ]

        if git_dir:
            cmd += ["-v", f"{git_dir}:/repo-git:rw"]

        cmd += ["--network", "host", config.docker_image, "sleep", "infinity"]

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

        container = DockerContainer(container_name, agent_name, group_chat_id, worktree_name)

        # worktree 模式：修复 git 路径
        if worktree_name:
            self._fix_git_paths(cwd, worktree_name, container)

        logger.info(f"容器 {container_name} 创建成功")
        return container

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
            await asyncio.sleep(self._cleanup_timeout)

            if key in self._containers:
                container = self._containers[key]
                logger.info(f"开始销毁容器: {container.name}")

                # 回退 git 路径到宿主机原始状态
                try:
                    self._revert_git_paths(container)
                except Exception as e:
                    logger.warning(f"回退 git 路径失败（容器可能已停止）: {e}")

                await asyncio.create_subprocess_exec("docker", "stop", container.name)
                await asyncio.create_subprocess_exec("docker", "rm", container.name)

                del self._containers[key]
                logger.info(f"容器 {container.name} 已销毁（10分钟空闲）")

        if key not in self._cleanup_tasks:
            self._cleanup_tasks[key] = asyncio.create_task(cleanup())
