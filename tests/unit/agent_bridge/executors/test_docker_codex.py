"""
DockerCodexExecutor 单元测试

契约：
1. _build_command 包含 --dangerously-bypass-approvals-and-sandbox 标志
2. _build_command 包含 prompt 参数
3. 有 session_id 时添加 --resume 参数
"""

from agents_hub.agent_bridge.docker.manager import DockerManager
from agents_hub.agent_bridge.executors.docker_codex import DockerCodexExecutor
from agents_hub.config.types import AgentPlatform
from agents_hub.roles.models import RoleConfig


def test_build_command_with_bypass_approvals():
    """契约：_build_command 包含 --dangerously-bypass-approvals-and-sandbox 标志"""
    manager = DockerManager()
    executor = DockerCodexExecutor(manager)
    config = RoleConfig(name="test", platform=AgentPlatform.CODEX, bare=False, work_root="/tmp")
    cmd = executor._build_command("test prompt", config, None)
    assert "--dangerously-bypass-approvals-and-sandbox" in cmd
    assert "test prompt" in cmd


def test_build_command_with_session():
    """契约：有 session_id 时添加 --resume 参数"""
    manager = DockerManager()
    executor = DockerCodexExecutor(manager)
    config = RoleConfig(name="test", platform=AgentPlatform.CODEX, bare=False, work_root="/tmp")
    cmd = executor._build_command("test", config, "session-456")
    assert "--resume" in cmd
    assert "session-456" in cmd


def test_build_command_full_structure():
    """契约：_build_command 构建完整命令结构"""
    manager = DockerManager()
    executor = DockerCodexExecutor(manager)
    config = RoleConfig(name="test", platform=AgentPlatform.CODEX, bare=False, work_root="/tmp")
    cmd = executor._build_command("hello", config, None)
    assert cmd[0].endswith("codex.cmd")
    assert "--dangerously-bypass-approvals-and-sandbox" in cmd
    assert "--print" in cmd
    assert "--output-format" in cmd
    assert "stream-json" in cmd
    assert cmd[-1] == "hello"
