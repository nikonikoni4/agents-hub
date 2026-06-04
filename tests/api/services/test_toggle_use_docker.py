"""GroupChatService.toggle_use_docker 单元测试

契约：
1. 成员存在 + 全局开 + Docker 可用 → 更新内存 + 持久化
2. 群聊不存在 → ResourceNotFoundError
3. 角色不是群成员 → ResourceNotFoundError
4. 全局 use_docker=False + 请求开启 → ValidationError
5. Docker 未启动 → DockerNotAvailableError
6. 关闭 use_docker → 跳过 Docker 检查
7. 角色无 session_info → 新建 AgentSessionInfo
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from agents_hub.api.schemas.group_chats import GroupChatMember
from agents_hub.api.services.group_chat_service import GroupChatService
from agents_hub.core.context.group_chat_session import AgentSessionInfo
from agents_hub.core.foundation.exceptions import DockerNotAvailableError
from agents_hub.core.foundation import GroupChatNotFoundError
from agents_hub.exceptions import ResourceNotFoundError, ValidationError


@pytest.fixture
def mock_group_chat_manager():
    return Mock()


@pytest.fixture
def service(mock_group_chat_manager):
    return GroupChatService(mock_group_chat_manager)


def _make_mock_group_chat(members=None, manager_name=None):
    """构造 mock GroupChat"""
    gc = Mock()
    gc.team_members_name = members or ["Worker1", "Worker2"]
    gc.manager = Mock(name=manager_name) if manager_name else None
    if gc.manager:
        gc.manager.name = manager_name
    gc.runtime = Mock()
    gc.runtime.set_agent_use_docker = AsyncMock(
        return_value=AgentSessionInfo(main_session="s1", use_docker=True)
    )
    return gc


@pytest.mark.asyncio
async def test_toggle_use_docker_enable_success(service, mock_group_chat_manager):
    """
    契约：开启 Docker — 全局开 + Docker 可用 → 更新内存 + 持久化 + 返回 GroupChatMember

    验证方式：
    1. mock 群聊存在，成员 Worker1
    2. mock config.use_docker=True
    3. mock DockerManager.ensure_image_ready 成功
    4. 调用 toggle_use_docker
    5. 断言返回 GroupChatMember(use_docker=True)
    6. 断言 runtime 命令已调用
    """
    mock_gc = _make_mock_group_chat()
    mock_gc.runtime.set_agent_use_docker = AsyncMock(
        return_value=AgentSessionInfo(main_session="s1", cwd="/path", use_docker=True)
    )
    mock_group_chat_manager.load_group_chat = AsyncMock(return_value=mock_gc)

    with (
        patch("agents_hub.api.services.group_chat_service.config") as mock_config,
        patch("agents_hub.agent_bridge.docker.manager.DockerManager") as MockDM,
    ):
        mock_config.use_docker = True
        MockDM.return_value.ensure_image_ready = AsyncMock()

        result = await service.toggle_use_docker("gc_1", "Worker1", True)

    assert isinstance(result, GroupChatMember)
    assert result.use_docker is True
    mock_gc.runtime.set_agent_use_docker.assert_called_once_with("Worker1", True)


@pytest.mark.asyncio
async def test_toggle_use_docker_disable_success(service, mock_group_chat_manager):
    """
    契约：关闭 Docker — 跳过所有检查，直接更新

    验证方式：
    1. mock 群聊存在
    2. 不 mock DockerManager（不应被调用）
    3. 调用 toggle_use_docker(False)
    4. 断言 use_docker=False
    """
    mock_gc = _make_mock_group_chat()
    mock_gc.runtime.set_agent_use_docker = AsyncMock(
        return_value=AgentSessionInfo(main_session="s1", cwd="/path", use_docker=False)
    )
    mock_group_chat_manager.load_group_chat = AsyncMock(return_value=mock_gc)

    with patch("agents_hub.api.services.group_chat_service.config") as mock_config:
        mock_config.use_docker = True  # 全局开

        result = await service.toggle_use_docker("gc_1", "Worker1", False)

    assert result.use_docker is False
    mock_gc.runtime.set_agent_use_docker.assert_called_once_with("Worker1", False)


@pytest.mark.asyncio
async def test_toggle_use_docker_creates_session_if_missing(service, mock_group_chat_manager):
    """
    契约：角色无 session_info → 新建 AgentSessionInfo

    验证方式：
    1. mock 群聊存在，但 agent_session_id 中无该角色
    2. 调用 toggle_use_docker
    3. 断言 runtime 命令已调用
    """
    mock_gc = _make_mock_group_chat()
    mock_gc.runtime.set_agent_use_docker = AsyncMock(
        return_value=AgentSessionInfo(main_session=None, cwd=None, use_docker=True)
    )
    mock_group_chat_manager.load_group_chat = AsyncMock(return_value=mock_gc)

    with (
        patch("agents_hub.api.services.group_chat_service.config") as mock_config,
        patch("agents_hub.agent_bridge.docker.manager.DockerManager") as MockDM,
    ):
        mock_config.use_docker = True
        MockDM.return_value.ensure_image_ready = AsyncMock()

        result = await service.toggle_use_docker("gc_1", "Worker1", True)

    mock_gc.runtime.set_agent_use_docker.assert_called_once_with("Worker1", True)
    assert result.use_docker is True


@pytest.mark.asyncio
async def test_toggle_use_docker_chat_not_found(service, mock_group_chat_manager):
    """
    契约：群聊不存在 → ResourceNotFoundError

    验证方式：
    1. mock load_group_chat 抛出 GroupChatNotFoundError
    2. 断言 ResourceNotFoundError
    """
    mock_group_chat_manager.load_group_chat = AsyncMock(
        side_effect=GroupChatNotFoundError("gc_nonexistent")
    )

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await service.toggle_use_docker("gc_nonexistent", "Worker1", True)
    assert "gc_nonexistent" in str(exc_info.value)


@pytest.mark.asyncio
async def test_toggle_use_docker_role_not_member(service, mock_group_chat_manager):
    """
    契约：角色不是群成员 → ResourceNotFoundError

    验证方式：
    1. mock 群聊存在，成员只有 Worker1, Worker2
    2. 请求 role_name="Hacker"
    3. 断言 ResourceNotFoundError
    """
    mock_gc = _make_mock_group_chat(members=["Worker1", "Worker2"])
    mock_group_chat_manager.load_group_chat = AsyncMock(return_value=mock_gc)

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await service.toggle_use_docker("gc_1", "Hacker", True)
    assert "Hacker" in str(exc_info.value)
    assert "不是群聊" in str(exc_info.value)


@pytest.mark.asyncio
async def test_toggle_use_docker_global_disabled(service, mock_group_chat_manager):
    """
    契约：全局 use_docker=False + 请求开启 → ValidationError

    验证方式：
    1. mock 群聊存在
    2. mock config.use_docker=False
    3. 请求 use_docker=True
    4. 断言 ValidationError，提示全局已禁用
    """
    mock_gc = _make_mock_group_chat()
    mock_group_chat_manager.load_group_chat = AsyncMock(return_value=mock_gc)

    with patch("agents_hub.api.services.group_chat_service.config") as mock_config:
        mock_config.use_docker = False

        with pytest.raises(ValidationError) as exc_info:
            await service.toggle_use_docker("gc_1", "Worker1", True)
        assert "全局 Docker 功能已禁用" in str(exc_info.value)


@pytest.mark.asyncio
async def test_toggle_use_docker_docker_not_running(service, mock_group_chat_manager):
    """
    契约：Docker 未启动 → DockerNotAvailableError（502）

    验证方式：
    1. mock 群聊存在
    2. mock config.use_docker=True
    3. mock DockerManager.ensure_image_ready 抛出 DockerNotAvailableError
    4. 断言 DockerNotAvailableError
    """
    mock_gc = _make_mock_group_chat()
    mock_group_chat_manager.load_group_chat = AsyncMock(return_value=mock_gc)

    with (
        patch("agents_hub.api.services.group_chat_service.config") as mock_config,
        patch("agents_hub.agent_bridge.docker.manager.DockerManager") as MockDM,
    ):
        mock_config.use_docker = True
        MockDM.return_value.ensure_image_ready = AsyncMock(
            side_effect=DockerNotAvailableError(
                agent_name="Worker1",
                group_chat_id="gc_1",
                message="Docker 未运行",
            )
        )

        with pytest.raises(DockerNotAvailableError):
            await service.toggle_use_docker("gc_1", "Worker1", True)


@pytest.mark.asyncio
async def test_toggle_use_docker_disable_skips_docker_check(service, mock_group_chat_manager):
    """
    契约：关闭 Docker 时即使 Docker 不可用也不报错

    验证方式：
    1. mock 群聊存在
    2. 不 mock DockerManager（不应被实例化）
    3. 请求 use_docker=False
    4. 成功返回
    """
    mock_gc = _make_mock_group_chat()
    mock_gc.runtime.set_agent_use_docker = AsyncMock(
        return_value=AgentSessionInfo(main_session="s1", cwd="/path", use_docker=False)
    )
    mock_group_chat_manager.load_group_chat = AsyncMock(return_value=mock_gc)

    with (
        patch("agents_hub.api.services.group_chat_service.config") as mock_config,
        patch("agents_hub.agent_bridge.docker.manager.DockerManager") as MockDM,
    ):
        mock_config.use_docker = True

        result = await service.toggle_use_docker("gc_1", "Worker1", False)

    assert result.use_docker is False
    # DockerManager 不应被实例化
    MockDM.assert_not_called()
