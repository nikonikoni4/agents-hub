"""
DockerContainer 单元测试

契约：
1. DockerContainer 初始化记录 name, agent_name, group_chat_id
2. build_exec_command 构建正确的 docker exec 命令
3. ContainerConfig 承载容器配置参数
"""

from agents_hub.agent_bridge.docker.container import DockerContainer
from agents_hub.agent_bridge.docker.models import ContainerConfig


def test_container_initialization():
    """契约：DockerContainer 初始化记录 name, agent_name, group_chat_id"""
    container = DockerContainer(name="container-test", agent_name="小李", group_chat_id="chat-123")
    assert container.name == "container-test"
    assert container.agent_name == "小李"
    assert container.group_chat_id == "chat-123"


def test_container_build_exec_command():
    """契约：build_exec_command 构建正确的 docker exec 命令"""
    container = DockerContainer(name="container-test", agent_name="小李", group_chat_id="chat-123")
    cmd = container.build_exec_command(command=["claude", "test"], cwd="/workspace")
    assert cmd[0] == "docker"
    assert cmd[1] == "exec"
    assert "-w" in cmd
    assert "/workspace" in cmd
    assert "container-test" in cmd
    assert "claude" in cmd


def test_container_build_exec_command_default_cwd():
    """契约：build_exec_command 默认 cwd 为 /workspace"""
    container = DockerContainer(name="container-test", agent_name="小李", group_chat_id="chat-123")
    cmd = container.build_exec_command(command=["ls"])
    assert "/workspace" in cmd


def test_container_build_exec_command_custom_cwd():
    """契约：build_exec_command 支持自定义 cwd"""
    container = DockerContainer(name="container-test", agent_name="小李", group_chat_id="chat-123")
    cmd = container.build_exec_command(command=["ls"], cwd="/app")
    assert "/app" in cmd
    assert "/workspace" not in cmd


def test_container_build_exec_command_sets_claude_config_dir():
    """契约：build_exec_command 设置 CLAUDE_CONFIG_DIR 环境变量"""
    container = DockerContainer(name="container-test", agent_name="小李", group_chat_id="chat-123")
    cmd = container.build_exec_command(command=["claude", "test"])
    assert "-e" in cmd
    idx = cmd.index("-e")
    assert cmd[idx + 1] == "CLAUDE_CONFIG_DIR=/home/ai-user/.claude"


def test_container_config_dataclass():
    """契约：ContainerConfig 承载容器配置参数"""
    config = ContainerConfig(
        agent_name="小李",
        group_chat_id="chat-123",
        work_root="/home/ai-user/.claude",
        cwd="/workspace",
        container_name="container-小李-chat123",
    )
    assert config.agent_name == "小李"
    assert config.group_chat_id == "chat-123"
    assert config.work_root == "/home/ai-user/.claude"
    assert config.cwd == "/workspace"
    assert config.container_name == "container-小李-chat123"
