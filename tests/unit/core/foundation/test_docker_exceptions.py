"""
Docker 异常类单元测试

契约：
1. DockerConfigError 继承 ValidationError，记录 agent_name, group_chat_id, reason
2. DockerNotAvailableError 继承 ExternalServiceError，记录 agent_name, group_chat_id
3. DockerStartError 继承 ExternalServiceError，记录 container_name
"""

import pytest

from agents_hub.core.foundation.exceptions import (
    DockerConfigError,
    DockerNotAvailableError,
    DockerStartError,
)


def test_docker_config_error():
    """契约：DockerConfigError 记录 agent_name, group_chat_id, reason"""
    error = DockerConfigError(
        agent_name="小李", group_chat_id="chat-123", reason="路径相同"
    )
    assert error.agent_name == "小李"
    assert error.group_chat_id == "chat-123"
    assert "路径相同" in str(error)


def test_docker_not_available_error():
    """契约：DockerNotAvailableError 记录 agent_name, group_chat_id"""
    error = DockerNotAvailableError(
        agent_name="小李",
        group_chat_id="chat-123",
        message="Docker Engine 未运行",
    )
    assert error.agent_name == "小李"
    assert "Docker Engine 未运行" in str(error)


def test_docker_start_error():
    """契约：DockerStartError 记录 container_name"""
    error = DockerStartError(
        container_name="container-小李-chat123", reason="端口冲突"
    )
    assert error.container_name == "container-小李-chat123"
    assert "端口冲突" in str(error)
