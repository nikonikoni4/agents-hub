"""
Agent Docker 配置校验测试

契约：
1. _validate_docker_config() 当 agent_member_info 不存在时静默跳过
2. _validate_docker_config() 当 use_docker=False 时静默跳过
3. _validate_docker_config() 当 CWD 与群聊路径相同时抛出 DockerConfigError
4. _validate_docker_config() 当 CWD 与群聊路径不同时正常通过
5. _is_same_path() 正确判断路径是否相同
6. _process_message() 在调用 execute 前先校验 Docker 配置
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agents_hub.core.agent.base_agent import Agent
from agents_hub.core.foundation.exceptions import DockerConfigError


def create_mock_role(name: str = "test_agent"):
    """创建 mock Role 对象"""
    role = MagicMock()
    role.get_role_config.return_value = SimpleNamespace(
        name=name,
        role_type=SimpleNamespace(value="team_member"),
        platform=SimpleNamespace(value="claude"),
        description="test agent",
    )
    return role


def create_agent_with_docker_config(
    agent_name: str = "test_agent",
    use_docker: bool = False,
    agent_cwd: str = "/tmp/agent_workspace",
    group_chat_path: str = "/tmp/project",
):
    """创建带有 Docker 配置的 Agent 实例"""
    role = create_mock_role(agent_name)
    group_chat_context = MagicMock()
    group_chat_context.group_chat_id = "gc_test_123"
    group_chat_context.agent_member_info = {
        agent_name: SimpleNamespace(
            main_session="session_1",
            btw_session=[],
            token="test_token",
            cwd=agent_cwd,
            use_docker=use_docker,
        )
    }
    # Mock get_project_path() instead of repository.project_path
    group_chat_context.get_project_path.return_value = group_chat_path

    agent_call_manager = MagicMock()
    message_router = MagicMock()

    return Agent(role, group_chat_context, agent_call_manager, message_router)


class TestValidateDockerConfig:
    """测试 _validate_docker_config() 的所有契约"""

    def test_no_agent_member_info_skips_validation(self):
        """契约 1：agent_member_info 不存在时静默跳过"""
        role = create_mock_role("test_agent")
        group_chat_context = MagicMock()
        group_chat_context.agent_member_info = {}  # 空字典，无 agent_member_info

        agent = Agent(role, group_chat_context, MagicMock(), MagicMock())

        # 不应抛出异常
        agent._validate_docker_config()

    def test_use_docker_false_skips_validation(self):
        """契约 2：use_docker=False 时静默跳过"""
        agent = create_agent_with_docker_config(use_docker=False)

        # 不应抛出异常
        agent._validate_docker_config()

    def test_same_path_raises_docker_config_error(self):
        """契约 3：CWD 与群聊路径相同时抛出 DockerConfigError"""
        agent = create_agent_with_docker_config(
            use_docker=True,
            agent_cwd="/tmp/same_path",
            group_chat_path="/tmp/same_path",
        )

        with pytest.raises(DockerConfigError) as exc_info:
            agent._validate_docker_config()

        assert exc_info.value.agent_name == "test_agent"
        assert exc_info.value.group_chat_id == "gc_test_123"
        assert "Docker 隔离不必要" in str(exc_info.value)

    def test_different_paths_passes_validation(self):
        """契约 4：CWD 与群聊路径不同时正常通过"""
        agent = create_agent_with_docker_config(
            use_docker=True,
            agent_cwd="/tmp/agent_workspace",
            group_chat_path="/tmp/project",
        )

        # 不应抛出异常
        agent._validate_docker_config()


class TestIsSamePath:
    """测试 _is_same_path() 的所有契约"""

    def test_same_absolute_paths(self):
        """契约：相同绝对路径判定为相同"""
        agent = create_agent_with_docker_config()
        assert agent._is_same_path("/tmp/a", "/tmp/a") is True

    def test_different_paths(self):
        """契约：不同路径判定为不同"""
        agent = create_agent_with_docker_config()
        assert agent._is_same_path("/tmp/a", "/tmp/b") is False

    def test_invalid_path_returns_false(self):
        """契约：无效路径返回 False"""
        agent = create_agent_with_docker_config()
        # 不应抛出异常，应返回 False
        result = agent._is_same_path("\x00invalid", "/tmp/a")
        assert result is False


class TestProcessMessageDockerValidation:
    """测试 _process_message() 中的 Docker 配置校验"""

    @pytest.mark.asyncio
    async def test_process_message_validates_before_execute(self):
        """契约：_process_message 在调用 execute 前先校验 Docker 配置"""
        agent = create_agent_with_docker_config(
            use_docker=True,
            agent_cwd="/tmp/same_path",
            group_chat_path="/tmp/same_path",
        )

        # Mock _validate_docker_config 来验证它被调用
        with patch.object(
            agent,
            "_validate_docker_config",
            side_effect=DockerConfigError(
                agent_name="test_agent",
                group_chat_id="gc_test_123",
                reason="test",
            ),
        ) as mock_validate:
            from agents_hub.core.foundation import AgentMessage, MessageType, SessionType

            msg = AgentMessage(
                call_id="call_1",
                send_from="user",
                send_to="test_agent",
                content="hello",
                session_type=SessionType.MAIN,
                message_type=MessageType.NOTIFICATION,
            )

            with pytest.raises(DockerConfigError):
                await agent._process_message(msg, "hello")

            # 验证 _validate_docker_config 被调用
            mock_validate.assert_called_once()
