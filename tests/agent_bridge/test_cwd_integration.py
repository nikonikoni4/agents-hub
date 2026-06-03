"""
AgentBridge cwd 参数集成测试

验证 Claude 和 Codex 执行器的 cwd 参数是否正常工作。
测试通过让 CLI 输出当前工作目录来验证。

运行方式：
    pytest tests/agent_bridge/test_cwd_integration.py -v -s
"""

import os
import subprocess
import tempfile

import pytest

from agents_hub.agent_bridge.bridge import AgentBridge
from agents_hub.config.types import AgentPlatform
from agents_hub.roles.models import RoleConfig


def create_test_config(platform: AgentPlatform, name: str) -> RoleConfig:
    """创建测试用角色配置"""
    return RoleConfig(name=name, platform=platform)


def create_git_repo(base_dir: str, name: str) -> str:
    """在 base_dir 下创建一个 git 仓库"""
    repo_dir = os.path.join(base_dir, name)
    os.makedirs(repo_dir, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
    return repo_dir


def extract_dir_name(path: str) -> str:
    """从路径中提取目录名（兼容 Windows/Unix 路径格式）"""
    # 移除末尾的斜杠
    path = path.rstrip("/\\")
    # 取最后一段
    return os.path.basename(path)


@pytest.fixture
def bridge():
    return AgentBridge()


@pytest.fixture
def test_dirs():
    """创建两个临时测试目录（包含 git 仓库）"""
    with tempfile.TemporaryDirectory(prefix="test_cwd_") as base_dir:
        dir_a = create_git_repo(base_dir, "project_a")
        dir_b = create_git_repo(base_dir, "project_b")
        yield dir_a, dir_b


@pytest.mark.integration
class TestClaudeCwd:
    """测试 Claude 执行器的 cwd 参数"""

    @pytest.mark.asyncio
    async def test_claude_outputs_cwd(self, bridge: AgentBridge, test_dirs):
        """
        契约：Claude CLI 在指定的 cwd 目录下启动

        验证方式：
        1. 创建两个不同的临时目录（git 仓库）
        2. 分别在两个目录下执行 Claude CLI
        3. 让 CLI 输出当前工作目录
        4. 验证输出的目录名与指定的 cwd 一致
        """
        dir_a, dir_b = test_dirs
        config = create_test_config(AgentPlatform.CLAUDE, "test-claude")

        prompt = "输出你当前的工作目录路径，只输出路径，不要其他内容"

        # 在 dir_a 执行
        result_a = await bridge.execute(prompt, config, cwd=dir_a)
        # 在 dir_b 执行
        result_b = await bridge.execute(prompt, config, cwd=dir_b)

        print(f"\nClaude dir_a: {dir_a}")
        print(f"Claude output_a: {result_a.text}")
        print(f"\nClaude dir_b: {dir_b}")
        print(f"Claude output_b: {result_b.text}")

        # 验证输出包含对应的目录名（兼容不同路径格式）
        name_a = extract_dir_name(dir_a)
        name_b = extract_dir_name(dir_b)

        assert name_a in result_a.text, \
               f"Claude 在 dir_a 执行时输出的路径不匹配: expected contains '{name_a}', got='{result_a.text}'"

        assert name_b in result_b.text, \
               f"Claude 在 dir_b 执行时输出的路径不匹配: expected contains '{name_b}', got='{result_b.text}'"


@pytest.mark.integration
@pytest.mark.skip(reason="Codex API key 有问题，暂时跳过")
class TestCodexCwd:
    """测试 Codex 执行器的 cwd 参数"""

    @pytest.mark.asyncio
    async def test_codex_outputs_cwd(self, bridge: AgentBridge, test_dirs):
        """
        契约：Codex CLI 在指定的 cwd 目录下启动

        验证方式：
        1. 创建两个不同的临时目录（git 仓库）
        2. 分别在两个目录下执行 Codex CLI
        3. 让 CLI 输出当前工作目录
        4. 验证输出的目录名与指定的 cwd 一致
        """
        dir_a, dir_b = test_dirs
        config = create_test_config(AgentPlatform.CODEX, "test-codex")

        prompt = "输出你当前的工作目录路径，只输出路径，不要其他内容"

        # 在 dir_a 执行
        result_a = await bridge.execute(prompt, config, cwd=dir_a)
        # 在 dir_b 执行
        result_b = await bridge.execute(prompt, config, cwd=dir_b)

        print(f"\nCodex dir_a: {dir_a}")
        print(f"Codex output_a: {result_a.text}")
        print(f"\nCodex dir_b: {dir_b}")
        print(f"Codex output_b: {result_b.text}")

        # 验证输出包含对应的目录名（兼容不同路径格式）
        name_a = extract_dir_name(dir_a)
        name_b = extract_dir_name(dir_b)

        assert name_a in result_a.text, \
               f"Codex 在 dir_a 执行时输出的路径不匹配: expected contains '{name_a}', got='{result_a.text}'"

        assert name_b in result_b.text, \
               f"Codex 在 dir_b 执行时输出的路径不匹配: expected contains '{name_b}', got='{result_b.text}'"


@pytest.mark.integration
class TestCwdNotSpecified:
    """测试不指定 cwd 时的默认行为"""

    @pytest.mark.asyncio
    async def test_claude_default_cwd(self, bridge: AgentBridge):
        """
        契约：不指定 cwd 时，CLI 使用进程当前目录

        验证方式：
        1. 不指定 cwd 执行
        2. 验证输出包含当前工作目录名
        """
        config = create_test_config(AgentPlatform.CLAUDE, "test-claude")
        prompt = "输出你当前的工作目录路径，只输出路径，不要其他内容"

        result = await bridge.execute(prompt, config)

        current_dir = os.getcwd()
        current_name = extract_dir_name(current_dir)

        print(f"\nClaude default cwd: {current_dir}")
        print(f"Claude output: {result.text}")

        # 验证输出包含当前目录名
        assert current_name in result.text, \
               f"Claude 默认 cwd 输出不匹配: expected contains '{current_name}', got='{result.text}'"
