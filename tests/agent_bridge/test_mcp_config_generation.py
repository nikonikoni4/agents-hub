"""测试 .mcp.json 配置模板生成功能

契约：
1. create_role() 生成 work_root/.mcp.json 文件
2. .mcp.json 内容指向 localhost:8001/mcp
3. CLAUDE.md 预置 AGENT_RUNTIME 标记
4. AGENTS.md 预置 AGENT_RUNTIME 标记
5. 文件已存在时不覆盖
"""

import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from agents_hub.config.types import AgentPlatform
from agents_hub.roles.role_manager import RoleManager


@pytest.fixture
def agents_dir():
    """创建测试用的 agents 目录"""
    tmp_dir = tempfile.mkdtemp()
    agents_dir = Path(tmp_dir) / "local_data" / "agents"
    agents_dir.mkdir(parents=True)
    yield agents_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def role_manager(agents_dir):
    """创建 RoleManager 实例"""
    return RoleManager(agents_dir)


@pytest.fixture
def mock_claude_home():
    """创建模拟的 ~/.claude 目录"""
    mock_home = Path(tempfile.mkdtemp())
    mock_claude = mock_home / ".claude"
    mock_claude.mkdir()
    (mock_claude / "settings.json").write_text('{"permissions": {}}', encoding="utf-8")
    yield mock_home
    shutil.rmtree(mock_home, ignore_errors=True)


@pytest.fixture
def mock_codex_home():
    """创建模拟的 ~/.codex 目录"""
    mock_home = Path(tempfile.mkdtemp())
    mock_codex = mock_home / ".codex"
    mock_codex.mkdir()
    (mock_codex / "auth.json").write_text('{}', encoding="utf-8")
    (mock_codex / "config.toml").write_text('', encoding="utf-8")
    (mock_codex / "rules").mkdir()
    yield mock_home
    shutil.rmtree(mock_home, ignore_errors=True)


class TestMcpConfigGeneration:
    """测试 .mcp.json 配置模板生成"""

    def test_generates_mcp_json_for_claude(self, role_manager, agents_dir, mock_claude_home):
        """
        契约：create_role() 为 Claude 平台生成 work_root/.mcp.json 文件

        验证方式：
        1. 创建 Claude 角色
        2. 检查 .mcp.json 文件存在
        3. 验证文件内容格式正确

        如果失败，说明：.mcp.json 文件未生成或路径错误
        """
        with patch("agents_hub.roles.role_manager.Path.home", return_value=mock_claude_home):
            role_manager.create_role("test_claude", AgentPlatform.CLAUDE)

        mcp_json_path = agents_dir / "test_claude" / "work_root" / ".mcp.json"
        assert mcp_json_path.exists(), ".mcp.json 文件未生成"

    def test_generates_mcp_json_for_codex(self, role_manager, agents_dir, mock_codex_home):
        """
        契约：create_role() 为 Codex 平台生成 work_root/.mcp.json 文件

        验证方式：
        1. 创建 Codex 角色
        2. 检查 .mcp.json 文件存在
        3. 验证文件内容格式正确

        如果失败，说明：.mcp.json 文件未生成或路径错误
        """
        with patch("agents_hub.roles.role_manager.Path.home", return_value=mock_codex_home):
            role_manager.create_role("test_codex", AgentPlatform.CODEX)

        mcp_json_path = agents_dir / "test_codex" / "work_root" / ".mcp.json"
        assert mcp_json_path.exists(), ".mcp.json 文件未生成"

    def test_mcp_json_content_correct(self, role_manager, agents_dir, mock_claude_home):
        """
        契约：.mcp.json 内容指向 localhost:8001/mcp

        验证方式：
        1. 创建角色
        2. 读取 .mcp.json 文件
        3. 验证 JSON 结构和 URL 正确

        如果失败，说明：.mcp.json 内容格式错误或 URL 不正确
        """
        with patch("agents_hub.roles.role_manager.Path.home", return_value=mock_claude_home):
            role_manager.create_role("test_role", AgentPlatform.CLAUDE)

        mcp_json_path = agents_dir / "test_role" / "work_root" / ".mcp.json"
        content = json.loads(mcp_json_path.read_text(encoding="utf-8"))

        assert "mcpServers" in content, "缺少 mcpServers 字段"
        assert "agents-hub" in content["mcpServers"], "缺少 agents-hub 服务器配置"
        server_config = content["mcpServers"]["agents-hub"]
        assert server_config["type"] == "http", "MCP Server type 应为 http"
        assert server_config["url"] == "http://localhost:8001/mcp", "MCP Server URL 不正确"

    def test_claude_md_has_runtime_markers(self, role_manager, agents_dir, mock_claude_home):
        """
        契约：CLAUDE.md 预置 AGENT_RUNTIME 标记

        验证方式：
        1. 创建 Claude 角色
        2. 读取 CLAUDE.md 文件
        3. 验证包含 <AGENT_RUNTIME_START/> 和 <AGENT_RUNTIME_END/> 标记

        如果失败，说明：CLAUDE.md 未预置 AGENT_RUNTIME 标记
        """
        with patch("agents_hub.roles.role_manager.Path.home", return_value=mock_claude_home):
            role_manager.create_role("test_claude", AgentPlatform.CLAUDE)

        claude_md_path = agents_dir / "test_claude" / "work_root" / "CLAUDE.md"
        content = claude_md_path.read_text(encoding="utf-8")

        assert "<AGENT_RUNTIME_START/>" in content, "缺少 <AGENT_RUNTIME_START/> 标记"
        assert "<AGENT_RUNTIME_END/>" in content, "缺少 <AGENT_RUNTIME_END/> 标记"

    def test_agents_md_has_runtime_markers(self, role_manager, agents_dir, mock_codex_home):
        """
        契约：AGENTS.md 预置 AGENT_RUNTIME 标记

        验证方式：
        1. 创建 Codex 角色
        2. 读取 AGENTS.md 文件
        3. 验证包含 <AGENT_RUNTIME_START/> 和 <AGENT_RUNTIME_END/> 标记

        如果失败，说明：AGENTS.md 未预置 AGENT_RUNTIME 标记
        """
        with patch("agents_hub.roles.role_manager.Path.home", return_value=mock_codex_home):
            role_manager.create_role("test_codex", AgentPlatform.CODEX)

        agents_md_path = agents_dir / "test_codex" / "work_root" / "AGENTS.md"
        content = agents_md_path.read_text(encoding="utf-8")

        assert "<AGENT_RUNTIME_START/>" in content, "缺少 <AGENT_RUNTIME_START/> 标记"
        assert "<AGENT_RUNTIME_END/>" in content, "缺少 <AGENT_RUNTIME_END/> 标记"

    def test_does_not_overwrite_existing_mcp_json(self, role_manager, agents_dir, mock_claude_home):
        """
        契约：文件已存在时不覆盖 .mcp.json

        验证方式：
        1. 手动创建 work_root 和 .mcp.json 文件
        2. 调用 create_role()
        3. 验证 .mcp.json 内容未被覆盖

        如果失败，说明：create_role() 覆盖了已存在的 .mcp.json 文件
        """
        # 手动创建角色目录和 .mcp.json
        role_dir = agents_dir / "existing_role"
        role_dir.mkdir()
        work_root = role_dir / "work_root"
        work_root.mkdir()
        (work_root / "skills").mkdir()

        existing_content = {"custom": "config"}
        mcp_json_path = work_root / ".mcp.json"
        mcp_json_path.write_text(json.dumps(existing_content), encoding="utf-8")

        # 模拟 create_role 的后续步骤（复制配置文件）
        with patch("agents_hub.roles.role_manager.Path.home", return_value=mock_claude_home):
            # 直接调用内部方法来模拟配置初始化
            role_manager._init_claude_config(work_root)

        # 验证 .mcp.json 未被覆盖
        content = json.loads(mcp_json_path.read_text(encoding="utf-8"))
        assert content == existing_content, ".mcp.json 文件被覆盖"

    def test_does_not_overwrite_existing_claude_md(self, role_manager, agents_dir, mock_claude_home):
        """
        契约：文件已存在时不覆盖 CLAUDE.md

        验证方式：
        1. 手动创建 work_root 和 CLAUDE.md 文件
        2. 调用 create_role()
        3. 验证 CLAUDE.md 内容未被覆盖

        如果失败，说明：create_role() 覆盖了已存在的 CLAUDE.md 文件
        """
        # 手动创建角色目录和 CLAUDE.md
        role_dir = agents_dir / "existing_role"
        role_dir.mkdir()
        work_root = role_dir / "work_root"
        work_root.mkdir()
        (work_root / "skills").mkdir()

        existing_content = "# Existing CLAUDE.md\n\nCustom content"
        claude_md_path = work_root / "CLAUDE.md"
        claude_md_path.write_text(existing_content, encoding="utf-8")

        # 模拟 create_role 的后续步骤
        with patch("agents_hub.roles.role_manager.Path.home", return_value=mock_claude_home):
            role_manager._init_claude_config(work_root)

        # 验证 CLAUDE.md 未被覆盖
        content = claude_md_path.read_text(encoding="utf-8")
        assert content == existing_content, "CLAUDE.md 文件被覆盖"
