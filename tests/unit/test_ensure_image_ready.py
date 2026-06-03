"""DockerManager.ensure_image_ready 单元测试

契约：
1. Docker 运行 + 镜像存在 → 正常返回
2. Docker 未运行 → DockerNotAvailableError
3. Docker 运行 + 镜像不存在 + 无 Dockerfile → ExternalServiceError
4. Docker 运行 + 镜像不存在 + 构建失败 → ExternalServiceError
5. Docker 运行 + 镜像不存在 + 构建成功 → 正常返回
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from agents_hub.agent_bridge.docker.manager import DockerManager
from agents_hub.core.foundation.exceptions import DockerNotAvailableError
from agents_hub.exceptions import ExternalServiceError


@pytest.mark.asyncio
async def test_ensure_image_ready_docker_running_and_image_exists():
    """
    契约：Docker 运行 + 镜像存在 → 无异常返回

    验证方式：
    1. mock _is_docker_running → True
    2. mock docker image inspect → returncode=0
    3. 调用 ensure_image_ready
    4. 无异常
    """
    manager = DockerManager()

    with (
        patch.object(manager, "_is_docker_running", return_value=True),
        patch("asyncio.create_subprocess_exec") as mock_exec,
    ):
        process = AsyncMock()
        process.wait = AsyncMock()
        process.returncode = 0
        mock_exec.return_value = process

        await manager.ensure_image_ready()


@pytest.mark.asyncio
async def test_ensure_image_ready_docker_not_running():
    """
    契约：Docker 未运行 → 抛出 DockerNotAvailableError

    验证方式：
    1. mock _is_docker_running → False
    2. 调用 ensure_image_ready
    3. 断言 DockerNotAvailableError
    """
    manager = DockerManager()

    with patch.object(manager, "_is_docker_running", return_value=False):
        with pytest.raises(DockerNotAvailableError):
            await manager.ensure_image_ready()


@pytest.mark.asyncio
async def test_ensure_image_ready_image_missing_no_dockerfile():
    """
    契约：镜像不存在 + Dockerfile 不存在 → ExternalServiceError

    验证方式：
    1. mock _is_docker_running → True
    2. mock docker image inspect → returncode=1（镜像不存在）
    3. mock Path.exists → False（Dockerfile 不存在）
    4. 断言 ExternalServiceError
    """
    manager = DockerManager()

    mock_dockerfile = Mock()
    mock_dockerfile.exists.return_value = False

    with (
        patch.object(manager, "_is_docker_running", return_value=True),
        patch("asyncio.create_subprocess_exec") as mock_exec,
        patch("agents_hub.agent_bridge.docker.manager.config") as mock_config,
        patch("agents_hub.agent_bridge.docker.manager.Path") as MockPath,
    ):
        # 镜像不存在
        inspect_process = AsyncMock()
        inspect_process.wait = AsyncMock()
        inspect_process.returncode = 1
        mock_exec.return_value = inspect_process

        mock_config.docker_image = "ai-tools:latest"
        mock_config.data_path = "/data"
        MockPath.return_value.__truediv__ = Mock(return_value=mock_dockerfile)

        with pytest.raises(ExternalServiceError) as exc_info:
            await manager.ensure_image_ready()
        assert "Dockerfile" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ensure_image_ready_image_missing_build_fails():
    """
    契约：镜像不存在 + 构建失败 → ExternalServiceError

    验证方式：
    1. mock _is_docker_running → True
    2. mock docker image inspect → returncode=1
    3. mock Path.exists → True（Dockerfile 存在）
    4. mock docker build → returncode=1
    5. 断言 ExternalServiceError
    """
    manager = DockerManager()

    mock_dockerfile = Mock()
    mock_dockerfile.exists.return_value = True
    mock_dockerfile.parent = Mock()
    mock_dockerfile.parent.__str__ = Mock(return_value="/tmp/build")

    with (
        patch.object(manager, "_is_docker_running", return_value=True),
        patch("asyncio.create_subprocess_exec") as mock_exec,
        patch("agents_hub.agent_bridge.docker.manager.config") as mock_config,
        patch("agents_hub.agent_bridge.docker.manager.Path") as MockPath,
    ):
        mock_config.docker_image = "ai-tools:latest"
        mock_config.data_path = "/data"
        MockPath.return_value.__truediv__ = Mock(return_value=mock_dockerfile)

        # 第一次调用是 inspect（镜像不存在），第二次是 build（失败）
        inspect_process = AsyncMock()
        inspect_process.wait = AsyncMock()
        inspect_process.returncode = 1

        build_process = AsyncMock()
        build_process.communicate = AsyncMock(return_value=(b"", b"build error"))
        build_process.returncode = 1

        mock_exec.side_effect = [inspect_process, build_process]

        with pytest.raises(ExternalServiceError) as exc_info:
            await manager.ensure_image_ready()
        assert "构建失败" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ensure_image_ready_image_missing_builds_successfully():
    """
    契约：镜像不存在 + 构建成功 → 正常返回

    验证方式：
    1. mock _is_docker_running → True
    2. mock docker image inspect → returncode=1
    3. mock docker build → returncode=0
    4. 无异常
    """
    manager = DockerManager()

    mock_dockerfile = Mock()
    mock_dockerfile.exists.return_value = True
    mock_dockerfile.parent = Mock()
    mock_dockerfile.parent.__str__ = Mock(return_value="/tmp/build")

    with (
        patch.object(manager, "_is_docker_running", return_value=True),
        patch("asyncio.create_subprocess_exec") as mock_exec,
        patch("agents_hub.agent_bridge.docker.manager.config") as mock_config,
        patch("agents_hub.agent_bridge.docker.manager.Path") as MockPath,
    ):
        mock_config.docker_image = "ai-tools:latest"
        mock_config.data_path = "/data"
        MockPath.return_value.__truediv__ = Mock(return_value=mock_dockerfile)

        inspect_process = AsyncMock()
        inspect_process.wait = AsyncMock()
        inspect_process.returncode = 1

        build_process = AsyncMock()
        build_process.communicate = AsyncMock(return_value=(b"Successfully built", b""))
        build_process.returncode = 0

        mock_exec.side_effect = [inspect_process, build_process]

        await manager.ensure_image_ready()
