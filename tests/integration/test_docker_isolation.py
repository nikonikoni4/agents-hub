"""Docker 沙箱隔离端到端集成测试

测试 Docker 容器提供的文件系统隔离效果：
1. 容器内可以读取挂载的工作目录文件
2. 容器内无法读取未挂载的主仓库文件
3. 无法通过相对路径跳出容器挂载范围

前置条件：
- Docker Desktop 已安装并运行
- 已构建 ai-tools:latest 镜像（见 explore/docker-experiment/Dockerfile.ai-tools）
"""

import asyncio
import subprocess
import tempfile
from pathlib import Path

import pytest


def docker_available() -> bool:
    """检查 Docker 是否可用"""
    try:
        result = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


IMAGE_NAME = "ai-tools:latest"


@pytest.fixture
def docker_image():
    """验证 ai-tools 镜像存在"""
    if not docker_available():
        pytest.skip("Docker not available")
    result = subprocess.run(
        ["docker", "images", "-q", IMAGE_NAME],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )
    if not result.stdout.strip():
        pytest.skip(f"Docker image '{IMAGE_NAME}' not found. Build it first:")
    return IMAGE_NAME


@pytest.mark.integration
@pytest.mark.skipif(not docker_available(), reason="Docker not available")
class TestDockerIsolation:
    """Docker 沙箱文件系统隔离测试"""

    async def _run_in_container(self, container_name: str, command: str) -> tuple[int, str]:
        """在容器内执行命令，返回 (returncode, stdout)"""
        process = await asyncio.create_subprocess_exec(
            "docker", "exec", container_name,
            "sh", "-c", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return process.returncode, stdout.decode().strip()

    async def _create_container(
        self, container_name: str, worktree_path: str, main_repo_path: str
    ) -> str:
        """创建测试容器，只挂载 worktree 目录"""
        # 先清理可能存在的同名容器
        cleanup = await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", container_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await cleanup.wait()

        # 创建容器：只挂载 worktree，不挂载 main repo
        process = await asyncio.create_subprocess_exec(
            "docker", "run", "-d",
            "--name", container_name,
            "-v", f"{worktree_path}:/workspace:rw",
            "--network", "host",
            IMAGE_NAME,
            "sleep", "infinity",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            pytest.fail(f"Failed to create container: {stderr.decode()}")

        return container_name

    async def _destroy_container(self, container_name: str):
        """销毁测试容器"""
        process = await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", container_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.wait()

    @pytest.mark.asyncio
    async def test_can_read_mounted_worktree(self, docker_image):
        """验证：容器内可以读取挂载的 worktree 文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            worktree = Path(tmpdir) / "worktree"
            worktree.mkdir()
            (worktree / "README.md").write_text("Worktree content")
            (worktree / "src").mkdir()
            (worktree / "src" / "main.py").write_text("print('hello')")

            container_name = "test-isolation-read-worktree"
            try:
                await self._create_container(container_name, str(worktree), "")

                # 读取挂载的文件
                rc, content = await self._run_in_container(
                    container_name, "cat /workspace/README.md"
                )
                assert rc == 0
                assert content == "Worktree content"

                # 读取嵌套文件
                rc, content = await self._run_in_container(
                    container_name, "cat /workspace/src/main.py"
                )
                assert rc == 0
                assert content == "print('hello')"
            finally:
                await self._destroy_container(container_name)

    @pytest.mark.asyncio
    async def test_cannot_read_main_repo(self, docker_image):
        """验证：容器内无法读取未挂载的主仓库文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            main_repo = Path(tmpdir) / "main_repo"
            worktree = Path(tmpdir) / "worktree"
            main_repo.mkdir()
            worktree.mkdir()

            # 主仓库独有文件
            (main_repo / "MAIN_ONLY.md").write_text("Main repo secret")
            (worktree / "README.md").write_text("Worktree file")

            container_name = "test-isolation-no-main-repo"
            try:
                await self._create_container(
                    container_name, str(worktree), str(main_repo)
                )

                # 确认 worktree 文件可读
                rc, _ = await self._run_in_container(
                    container_name, "cat /workspace/README.md"
                )
                assert rc == 0

                # 尝试读取主仓库文件（通过绝对路径 - 应该失败）
                rc, _ = await self._run_in_container(
                    container_name, "cat /main_repo/MAIN_ONLY.md 2>/dev/null"
                )
                assert rc != 0, "Should not be able to read main repo files"
            finally:
                await self._destroy_container(container_name)

    @pytest.mark.asyncio
    async def test_cannot_escape_via_relative_path(self, docker_image):
        """验证：无法通过相对路径跳出容器挂载范围"""
        with tempfile.TemporaryDirectory() as tmpdir:
            worktree = Path(tmpdir) / "worktree"
            worktree.mkdir()
            (worktree / "README.md").write_text("Worktree file")

            container_name = "test-isolation-no-escape"
            try:
                await self._create_container(container_name, str(worktree), "")

                # 尝试通过相对路径向上跳
                rc, _ = await self._run_in_container(
                    container_name,
                    "cat /workspace/../../../etc/passwd 2>/dev/null"
                )
                # 在 Docker 中，路径会被截断到 /，但 passwd 在 /etc/passwd
                # 关键验证：不能读取 /workspace 以外的挂载内容
                # 读取 /etc/passwd 可能成功（容器有该文件），但读取主仓库文件一定失败

                # 尝试读取主仓库（通过 ../ 跳出 workspace）
                main_only = Path(tmpdir) / "main_repo" / "SECRET.md"
                main_only.parent.mkdir(exist_ok=True)
                main_only.write_text("secret")

                # 重新创建容器，挂载 worktree 但不挂载 main_repo
                await self._destroy_container(container_name)
                await self._create_container(container_name, str(worktree), "")

                rc, _ = await self._run_in_container(
                    container_name,
                    "cat /workspace/../SECRET.md 2>/dev/null"
                )
                assert rc != 0, "Relative path escape should fail"
            finally:
                await self._destroy_container(container_name)

    @pytest.mark.asyncio
    async def test_isolation_boundary_with_shared_parent(self, docker_image):
        """验证：即使 worktree 和 main_repo 在同一父目录下，隔离依然有效"""
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir) / "project"
            parent.mkdir()

            main_repo = parent / "main"
            worktree = parent / "worktree"
            main_repo.mkdir()
            worktree.mkdir()

            (main_repo / "MAIN_SECRET.md").write_text("Main only")
            (worktree / "README.md").write_text("Worktree only")

            container_name = "test-isolation-shared-parent"
            try:
                await self._create_container(container_name, str(worktree), str(main_repo))

                # worktree 文件可读
                rc, content = await self._run_in_container(
                    container_name, "cat /workspace/README.md"
                )
                assert rc == 0
                assert content == "Worktree only"

                # 主仓库文件不可读
                rc, _ = await self._run_in_container(
                    container_name, "cat /MAIN_SECRET.md 2>/dev/null"
                )
                assert rc != 0, "Should not access main repo via shared parent"

                # 通过相对路径也不行
                rc, _ = await self._run_in_container(
                    container_name,
                    "cat /workspace/../MAIN_SECRET.md 2>/dev/null"
                )
                assert rc != 0, "Relative path escape to sibling should fail"
            finally:
                await self._destroy_container(container_name)
