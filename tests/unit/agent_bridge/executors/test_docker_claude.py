"""
DockerClaudeExecutor 单元测试

契约：
1. _build_command 包含 --dangerously-skip-permissions 标志
2. _build_command 包含 prompt 参数
3. 有 session_id 时添加 --resume 参数
4. bare=True 时添加 --bare 参数
"""

from agents_hub.agent_bridge.docker.manager import DockerManager
from agents_hub.agent_bridge.executors.docker_claude import DockerClaudeExecutor
from agents_hub.config.types import AgentPlatform
from agents_hub.roles.models import RoleConfig


def test_build_command_with_skip_permissions():
    """契约：_build_command 包含 --dangerously-skip-permissions 标志"""
    manager = DockerManager()
    executor = DockerClaudeExecutor(manager)
    config = RoleConfig(name="test", platform=AgentPlatform.CLAUDE, bare=False, work_root="/tmp")
    cmd = executor._build_command("test prompt", config, None)
    assert "--dangerously-skip-permissions" in cmd
    assert "test prompt" in cmd


def test_build_command_with_session():
    """契约：有 session_id 时添加 --resume 参数"""
    manager = DockerManager()
    executor = DockerClaudeExecutor(manager)
    config = RoleConfig(name="test", platform=AgentPlatform.CLAUDE, bare=False, work_root="/tmp")
    cmd = executor._build_command("test", config, "session-123")
    assert "--resume" in cmd
    assert "session-123" in cmd


def test_build_command_with_bare():
    """契约：bare=True 时添加 --bare 参数"""
    manager = DockerManager()
    executor = DockerClaudeExecutor(manager)
    config = RoleConfig(name="test", platform=AgentPlatform.CLAUDE, bare=True, work_root="/tmp")
    cmd = executor._build_command("test", config, None)
    assert "--bare" in cmd


def test_build_command_without_bare():
    """契约：bare=False 时不添加 --bare 参数"""
    manager = DockerManager()
    executor = DockerClaudeExecutor(manager)
    config = RoleConfig(name="test", platform=AgentPlatform.CLAUDE, bare=False, work_root="/tmp")
    cmd = executor._build_command("test", config, None)
    assert "--bare" not in cmd


def test_build_command_full_structure():
    """契约：_build_command 构建完整命令结构"""
    manager = DockerManager()
    executor = DockerClaudeExecutor(manager)
    config = RoleConfig(name="test", platform=AgentPlatform.CLAUDE, bare=False, work_root="/tmp")
    cmd = executor._build_command("hello", config, None)
    assert cmd[0].endswith("claude")
    assert "--dangerously-skip-permissions" in cmd
    assert "--print" in cmd
    assert "--verbose" in cmd
    assert "--output-format" in cmd
    assert "stream-json" in cmd
    assert "--include-partial-messages" in cmd
    assert cmd[-1] == "hello"
