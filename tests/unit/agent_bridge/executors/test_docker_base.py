"""
DockerExecutor 基类单元测试

契约：
1. DockerExecutor 是抽象类，不能直接实例化
2. 缺少 _build_command 实现时实例化抛出 TypeError
"""

import pytest

from agents_hub.agent_bridge.executors.docker_base import DockerExecutor


def test_docker_executor_is_abstract():
    """契约：DockerExecutor 是抽象类，不能直接实例化"""
    with pytest.raises(TypeError):
        DockerExecutor(None)
