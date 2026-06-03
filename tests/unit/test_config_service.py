"""ConfigService 单元测试

契约：
1. get_config 返回当前配置
2. update_config 部分更新单个字段
3. update_config 无有效字段 → ValidationError
4. update_config use_docker=True → 检查 Docker 环境
5. update_config use_docker=False → 跳过 Docker 检查
6. update_config use_docker=True + Docker 未运行 → 502
7. update_config use_docker=True + 镜像构建失败 → 502
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from agents_hub.api.schemas.config import ConfigInfo, ConfigUpdate
from agents_hub.api.services.config_service import ConfigService
from agents_hub.core.foundation.exceptions import DockerNotAvailableError
from agents_hub.exceptions import ExternalServiceError, ValidationError


@pytest.fixture
def service():
    return ConfigService()


@pytest.fixture
def mock_config():
    with patch("agents_hub.api.services.config_service.config") as mc:
        mc.data_path = Mock()
        mc.data_path.__str__ = Mock(return_value="/data")
        mc.mcp_port = 8765
        mc.default_user_name = "user"
        mc.use_docker = False
        mc.docker_image = "ai-tools:latest"
        mc.set_data_path = Mock()
        mc.mcp_port = 8765
        yield mc


def test_get_config_returns_current(service, mock_config):
    """
    契约：get_config 返回当前配置值

    验证方式：
    1. mock config 属性
    2. 调用 get_config
    3. 断言返回 ConfigInfo 且字段正确
    """
    result = service.get_config()

    assert isinstance(result, ConfigInfo)
    assert result.mcp_port == 8765
    assert result.default_user_name == "user"
    assert result.use_docker is False
    assert result.docker_image == "ai-tools:latest"


@pytest.mark.asyncio
async def test_update_config_single_field(service, mock_config):
    """
    契约：部分更新单个字段

    验证方式：
    1. 只传 mcp_port
    2. 断言只更新了 mcp_port
    """
    mock_config.mcp_port = 9999

    update = ConfigUpdate(mcp_port=9999)
    result = await service.update_config(update)

    assert result.mcp_port == 9999


@pytest.mark.asyncio
async def test_update_config_use_docker_false_skips_check(service, mock_config):
    """
    契约：关闭 use_docker → 跳过 Docker 检查

    验证方式：
    1. 传 use_docker=False
    2. DockerManager 不应被实例化
    3. config.use_docker 被设置为 False
    """
    mock_config.use_docker = False

    with patch("agents_hub.agent_bridge.docker.manager.DockerManager") as MockDM:
        update = ConfigUpdate(use_docker=False)
        result = await service.update_config(update)

    MockDM.assert_not_called()
    assert result.use_docker is False


@pytest.mark.asyncio
async def test_update_config_empty_body_raises(service, mock_config):
    """
    契约：无有效字段 → ValidationError

    验证方式：
    1. 传全 None 的 ConfigUpdate
    2. 断言 ValidationError
    """
    update = ConfigUpdate()  # 所有字段都是 None

    with pytest.raises(ValidationError) as exc_info:
        await service.update_config(update)
    assert "至少需要提供一个配置字段" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_config_use_docker_true_docker_not_running(service, mock_config):
    """
    契约：开启 use_docker + Docker 未运行 → DockerNotAvailableError

    验证方式：
    1. mock config.use_docker=False（当前关闭）
    2. 请求 use_docker=True
    3. mock DockerManager.ensure_image_ready 抛出异常
    4. 断言 DockerNotAvailableError
    """
    mock_config.use_docker = False

    with patch("agents_hub.agent_bridge.docker.manager.DockerManager") as MockDM:
        MockDM.return_value.ensure_image_ready = AsyncMock(
            side_effect=DockerNotAvailableError(
                agent_name="config",
                group_chat_id="",
                message="Docker 未运行",
            )
        )

        update = ConfigUpdate(use_docker=True)
        with pytest.raises(DockerNotAvailableError):
            await service.update_config(update)


@pytest.mark.asyncio
async def test_update_config_use_docker_true_build_fails(service, mock_config):
    """
    契约：开启 use_docker + 镜像构建失败 → ExternalServiceError

    验证方式：
    1. mock DockerManager.ensure_image_ready 抛出 ExternalServiceError
    2. 断言 ExternalServiceError
    """
    mock_config.use_docker = False

    with patch("agents_hub.agent_bridge.docker.manager.DockerManager") as MockDM:
        MockDM.return_value.ensure_image_ready = AsyncMock(
            side_effect=ExternalServiceError(
                "Docker 镜像构建失败",
                details={"image": "ai-tools:latest"},
            )
        )

        update = ConfigUpdate(use_docker=True)
        with pytest.raises(ExternalServiceError):
            await service.update_config(update)
