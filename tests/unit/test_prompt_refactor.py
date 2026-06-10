"""
提示词重构测试

测试契约：
1. render_for_llm - 输出包含 call_id 和 message_type
2. build_user_prompt - 组装 runtime + context + incoming_message
3. create_role - 写入 CLAUDE/AGENTS.md 系统提示文件
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_hub.config.types import AgentPlatform, RoleType
from agents_hub.core.foundation.message import AgentMessage
from agents_hub.core.foundation.models import MessageType, SessionType
from agents_hub.core.foundation.renderer import render_for_llm

# ==================== render_for_llm 测试 ====================


class TestRenderForLlm:
    """render_for_llm 契约测试"""

    def test_render_for_llm_contains_call_id(self):
        """
        契约：输出包含 call_id

        验证方式：
        1. 创建 AgentMessage，设置 call_id
        2. 调用 render_for_llm
        3. 验证输出包含 call_id
        """
        msg = AgentMessage(
            call_id="test-call-123",
            content="hello",
            send_from="user",
            send_to="manager",
            session_type=SessionType.MAIN,
            message_type=MessageType.TASK,
        )

        result = render_for_llm(msg)

        assert "call_id: test-call-123" in result

    def test_render_for_llm_contains_message_type(self):
        """
        契约：输出包含 message_type

        验证方式：
        1. 创建 AgentMessage，设置 message_type=task
        2. 调用 render_for_llm
        3. 验证输出包含类型信息
        """
        msg = AgentMessage(
            call_id="test-call-123",
            content="hello",
            send_from="user",
            send_to="manager",
            session_type=SessionType.MAIN,
            message_type=MessageType.TASK,
        )

        result = render_for_llm(msg)

        assert "类型：task" in result

    def test_render_for_llm_contains_basic_fields(self):
        """
        契约：输出包含 send_from、send_to、content

        验证方式：
        1. 创建 AgentMessage
        2. 调用 render_for_llm
        3. 验证输出包含基本字段
        """
        msg = AgentMessage(
            call_id="test-call-123",
            content="你能看到这个文件吗",
            send_from="user",
            send_to="manager",
            session_type=SessionType.MAIN,
            message_type=MessageType.TASK,
        )

        result = render_for_llm(msg)

        assert "来自：user" in result
        assert "发送给：manager（你）" in result
        assert "内容：你能看到这个文件吗" in result

    def test_render_for_llm_with_files(self):
        """
        契约：处理文件附件

        验证方式：
        1. 创建 AgentMessage，包含 files
        2. 调用 render_for_llm
        3. 验证输出包含附件信息
        """
        msg = AgentMessage(
            call_id="test-call-123",
            content="查看文件",
            send_from="user",
            send_to="manager",
            session_type=SessionType.MAIN,
            message_type=MessageType.TASK,
            files=[
                {
                    "file_name": "test.md",
                    "file_path": "teams/test/file.md",
                    "file_type": "text/markdown",
                    "file_size": 1024,
                }
            ],
        )

        result = render_for_llm(msg)

        assert "[附件]" in result
        assert "test.md" in result
        assert "text/markdown" in result
        assert "1024B" in result

    def test_render_for_llm_without_files(self):
        """
        契约：无附件时正常工作

        验证方式：
        1. 创建 AgentMessage，files=None
        2. 调用 render_for_llm
        3. 验证输出不包含附件信息
        """
        msg = AgentMessage(
            call_id="test-call-123",
            content="hello",
            send_from="user",
            send_to="manager",
            session_type=SessionType.MAIN,
            message_type=MessageType.TASK,
            files=None,
        )

        result = render_for_llm(msg)

        assert "[附件]" not in result
        assert "call_id: test-call-123" in result

    def test_render_for_llm_empty_content(self):
        """
        契约：空内容时正常工作

        验证方式：
        1. 创建 AgentMessage，content=""
        2. 调用 render_for_llm
        3. 验证输出正常
        """
        msg = AgentMessage(
            call_id="test-call-123",
            content="",
            send_from="user",
            send_to="manager",
            session_type=SessionType.MAIN,
            message_type=MessageType.TASK,
        )

        result = render_for_llm(msg)

        assert "call_id: test-call-123" in result
        assert "内容：" in result

    def test_render_for_llm_notification_type(self):
        """
        契约：NOTIFICATION 类型正确显示

        验证方式：
        1. 创建 AgentMessage，message_type=notification
        2. 调用 render_for_llm
        3. 验证输出包含 notification 类型
        """
        msg = AgentMessage(
            call_id="test-call-123",
            content="通知",
            send_from="agent_a",
            send_to="manager",
            session_type=SessionType.MAIN,
            message_type=MessageType.NOTIFICATION,
        )

        result = render_for_llm(msg)

        assert "类型：notification" in result


# ==================== build_user_prompt 测试 ====================


class TestBuildUserPrompt:
    """build_user_prompt 契约测试"""

    @pytest.fixture
    def mock_group_chat_context(self):
        """创建 mock 的 GroupChatContext"""
        from agents_hub.core.context.group_chat_session import GroupChatSession

        context = MagicMock()
        context.group_chat_id = "test-chat-id"

        # 创建真实的 session
        session = GroupChatSession(group_chat_id="test-chat-id")
        context.group_chat_session = session

        # agent_member_info
        agent_info = MagicMock()
        agent_info.token = "tok_test123"
        agent_info.description = "测试角色"
        agent_info.context_state.last_loaded_compact_index = 0
        agent_info.context_state.last_loaded_message_index = 0

        worker_info = MagicMock()
        worker_info.token = "tok_worker"
        worker_info.description = "工作者"
        worker_info.context_state.last_loaded_compact_index = 0
        worker_info.context_state.last_loaded_message_index = 0

        context.agent_member_info = {
            "manager": agent_info,
            "worker_a": worker_info,
        }

        # repository
        context.repository = MagicMock()
        context.repository.group_chat_session_path = "/tmp/test"

        # runtime
        context.runtime = MagicMock()
        context.runtime.update_context_load_state = AsyncMock()

        # load_compact_history (async)
        context.load_compact_history = AsyncMock(return_value=[])

        return context

    @pytest.mark.asyncio
    async def test_build_user_prompt_contains_runtime(self, mock_group_chat_context):
        """
        契约：输出包含 runtime XML

        验证方式：
        1. 创建 AgentContext
        2. 创建 AgentMessage
        3. 调用 build_user_prompt
        4. 验证输出包含 runtime 标签
        """
        from agents_hub.core.context.agent_context import AgentContext

        agent_context = AgentContext(
            agent_name="manager",
            group_chat_context=mock_group_chat_context,
            role_type=RoleType.LEADER,
        )

        msg = AgentMessage(
            call_id="test-call-123",
            content="测试消息",
            send_from="user",
            send_to="manager",
            session_type=SessionType.MAIN,
            message_type=MessageType.TASK,
        )

        result = await agent_context.build_user_prompt(msg)

        assert "<runtime>" in result
        assert "</runtime>" in result
        assert "tok_test123" in result
        assert "test-chat-id" in result

    @pytest.mark.asyncio
    async def test_build_user_prompt_contains_incoming_message(self, mock_group_chat_context):
        """
        契约：输出包含 incoming_message

        验证方式：
        1. 创建 AgentContext
        2. 创建 AgentMessage
        3. 调用 build_user_prompt
        4. 验证输出包含 incoming_message 标签
        """
        from agents_hub.core.context.agent_context import AgentContext

        agent_context = AgentContext(
            agent_name="manager",
            group_chat_context=mock_group_chat_context,
            role_type=RoleType.LEADER,
        )

        msg = AgentMessage(
            call_id="test-call-123",
            content="测试消息",
            send_from="user",
            send_to="manager",
            session_type=SessionType.MAIN,
            message_type=MessageType.TASK,
        )

        result = await agent_context.build_user_prompt(msg)

        assert "<incoming_message>" in result
        assert "call_id: test-call-123" in result
        assert "测试消息" in result

    @pytest.mark.asyncio
    async def test_build_user_prompt_team_member_no_workboard(self, mock_group_chat_context):
        """
        契约：TEAM_MEMBER 不包含 team_workboard

        验证方式：
        1. 创建 AgentContext，role_type=TEAM_MEMBER
        2. 创建 AgentMessage
        3. 调用 build_user_prompt
        4. 验证输出不包含 team_workboard
        """
        from agents_hub.core.context.agent_context import AgentContext

        agent_context = AgentContext(
            agent_name="worker_a",
            group_chat_context=mock_group_chat_context,
            role_type=RoleType.TEAM_MEMBER,
        )

        msg = AgentMessage(
            call_id="test-call-123",
            content="测试消息",
            send_from="user",
            send_to="worker_a",
            session_type=SessionType.MAIN,
            message_type=MessageType.TASK,
        )

        result = await agent_context.build_user_prompt(msg)

        assert "<team_workboard>" not in result

    @pytest.mark.asyncio
    async def test_build_user_prompt_contains_team_members(self, mock_group_chat_context):
        """
        契约：输出包含 team_members（排除自己）

        验证方式：
        1. 创建 AgentContext，agent_name="manager"
        2. 创建 AgentMessage
        3. 调用 build_user_prompt
        4. 验证输出包含 worker_a 但不包含 manager
        """
        from agents_hub.core.context.agent_context import AgentContext

        agent_context = AgentContext(
            agent_name="manager",
            group_chat_context=mock_group_chat_context,
            role_type=RoleType.LEADER,
        )

        msg = AgentMessage(
            call_id="test-call-123",
            content="测试消息",
            send_from="user",
            send_to="manager",
            session_type=SessionType.MAIN,
            message_type=MessageType.TASK,
        )

        result = await agent_context.build_user_prompt(msg)

        assert "worker_a" in result
        # manager 是自己，不应该出现在 team_members 中
        lines = [line for line in result.split("\n") if "team_members" in line]
        if lines:
            assert "manager" not in lines[0] or "worker_a" in lines[0]


# ==================== create_role 写入系统提示文件 测试 ====================


class TestCreateRoleWritesSystemFile:
    """create_role 写入系统提示文件契约测试"""

    @pytest.fixture
    def temp_agents_dir(self):
        """创建临时 agents 目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def role_manager(self, temp_agents_dir):
        """创建 RoleManager 实例"""
        from agents_hub.roles.role_manager import RoleManager

        return RoleManager(agents_dir=temp_agents_dir)

    @patch("agents_hub.roles.role_manager.RoleManager._init_claude_config")
    @patch("agents_hub.roles.role_manager.RoleManager._init_agents_hub_mcp")
    def test_create_role_writes_claude_md(
        self, mock_mcp, mock_claude, role_manager, temp_agents_dir
    ):
        """
        契约：Claude 平台写入 CLAUDE.md

        验证方式：
        1. 创建 Claude 角色
        2. 验证 CLAUDE.md 存在
        3. 验证内容包含 platform_info、tool_usage、identity、role_instruction
        """
        role_manager.create_role(
            name="test_manager",
            platform=AgentPlatform.CLAUDE,
            type=RoleType.LEADER,
            description="测试管理者",
        )

        claude_md = temp_agents_dir / "test_manager" / "work_root" / "CLAUDE.md"
        assert claude_md.exists()

        content = claude_md.read_text(encoding="utf-8")
        assert "<platform_info>" in content
        assert "<tool_usage>" in content
        assert "<identity>" in content
        assert "<role_instruction>" in content
        assert "测试管理者" in content

    @patch("agents_hub.roles.role_manager.RoleManager._init_codex_config")
    @patch("agents_hub.roles.role_manager.RoleManager._init_agents_hub_mcp")
    def test_create_role_writes_agents_md(
        self, mock_mcp, mock_codex, role_manager, temp_agents_dir
    ):
        """
        契约：Codex 平台写入 AGENTS.md

        验证方式：
        1. 创建 Codex 角色
        2. 验证 AGENTS.md 存在
        3. 验证内容包含 platform_info、tool_usage、identity、role_instruction
        """
        role_manager.create_role(
            name="test_worker",
            platform=AgentPlatform.CODEX,
            type=RoleType.TEAM_MEMBER,
            description="测试工作者",
        )

        agents_md = temp_agents_dir / "test_worker" / "work_root" / "AGENTS.md"
        assert agents_md.exists()

        content = agents_md.read_text(encoding="utf-8")
        assert "<platform_info>" in content
        assert "<tool_usage>" in content
        assert "<identity>" in content
        assert "<role_instruction>" in content
        assert "测试工作者" in content

    @patch("agents_hub.roles.role_manager.RoleManager._init_claude_config")
    @patch("agents_hub.roles.role_manager.RoleManager._init_agents_hub_mcp")
    def test_create_role_leader_uses_manager_template(
        self, mock_mcp, mock_claude, role_manager, temp_agents_dir
    ):
        """
        契约：LEADER 角色使用 Manager 模板

        验证方式：
        1. 创建 LEADER 角色
        2. 验证 CLAUDE.md 包含 Manager 特有的工具和指令
        """
        role_manager.create_role(
            name="leader",
            platform=AgentPlatform.CLAUDE,
            type=RoleType.LEADER,
        )

        claude_md = temp_agents_dir / "leader" / "work_root" / "CLAUDE.md"
        content = claude_md.read_text(encoding="utf-8")

        # Manager 特有的工具
        assert "call_agent" in content
        assert "assign_tasks_to_team" in content
        assert "archive_task_list" in content

        # Manager 特有的指令
        assert "call_agent 派活要求" in content

    @patch("agents_hub.roles.role_manager.RoleManager._init_claude_config")
    @patch("agents_hub.roles.role_manager.RoleManager._init_agents_hub_mcp")
    def test_create_role_team_member_uses_worker_template(
        self, mock_mcp, mock_claude, role_manager, temp_agents_dir
    ):
        """
        契约：TEAM_MEMBER 角色使用 Worker 模板

        验证方式：
        1. 创建 TEAM_MEMBER 角色
        2. 验证 CLAUDE.md 包含 Worker 特有的指令
        """
        role_manager.create_role(
            name="worker",
            platform=AgentPlatform.CLAUDE,
            type=RoleType.TEAM_MEMBER,
        )

        claude_md = temp_agents_dir / "worker" / "work_root" / "CLAUDE.md"
        content = claude_md.read_text(encoding="utf-8")

        # Worker 特有的指令
        assert "阻塞判定" in content
        assert "complete_task回报要求" in content

        # Worker 不应该有 Manager 特有的工具
        assert "call_agent" not in content
        assert "assign_tasks_to_team" not in content

    @patch("agents_hub.roles.role_manager.RoleManager._init_claude_config")
    @patch("agents_hub.roles.role_manager.RoleManager._init_agents_hub_mcp")
    def test_create_role_system_uses_assistant_template(
        self, mock_mcp, mock_claude, role_manager, temp_agents_dir
    ):
        """
        契约：SYSTEM 角色使用 ASSISTANT_SYSTEM_PROMPT 模板

        验证方式：
        1. 创建 SYSTEM 角色
        2. 验证 CLAUDE.md 包含系统助手特有的内容
        3. 验证不包含普通角色的模板内容
        """
        role_manager.create_role(
            name="assistant",
            platform=AgentPlatform.CLAUDE,
            type=RoleType.SYSTEM,
            description="系统助手",
        )

        claude_md = temp_agents_dir / "assistant" / "work_root" / "CLAUDE.md"
        content = claude_md.read_text(encoding="utf-8")

        # 系统助手特有的内容
        assert "Agents Hub 系统助手" in content
        assert "判断是否需要多 Agent" in content
        assert "导航卡片输出格式" in content

        # 不应该包含普通角色的模板内容
        assert "<platform_info>" not in content
        assert "<tool_usage>" not in content
        assert "<identity>" not in content
        assert "<role_instruction>" not in content

    def test_create_role_already_exists_raises(self, role_manager):
        """
        契约：角色已存在且完整时抛出 RoleAlreadyExistsError

        验证方式：
        1. 创建一个角色（模拟完整配置）
        2. 尝试创建同名角色
        3. 验证抛出 RoleAlreadyExistsError
        """
        from agents_hub.roles.exceptions import RoleAlreadyExistsError

        with (
            patch("agents_hub.roles.role_manager.RoleManager._init_claude_config"),
            patch("agents_hub.roles.role_manager.RoleManager._init_agents_hub_mcp"),
            patch(
                "agents_hub.roles.role_manager.RoleManager._is_role_incomplete", return_value=False
            ),
        ):
            role_manager.create_role(
                name="test_role",
                platform=AgentPlatform.CLAUDE,
            )

            with pytest.raises(RoleAlreadyExistsError):
                role_manager.create_role(
                    name="test_role",
                    platform=AgentPlatform.CLAUDE,
                )
