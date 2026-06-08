"""
测试工具使用说明注入和消息格式化功能

测试覆盖：
- _generate_tool_usage_content 生成工具使用说明（Manager 和 Worker）
- _inject_tool_usage_to_files 注入工具使用说明到文件
- 注入幂等性：多次注入不会重复添加标签
- send_message_to_agent 消息格式化
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agents_hub.config.types import RoleType
from agents_hub.core.agent.manager import Manager
from agents_hub.core.agent.worker import Worker
from agents_hub.core.communication import AgentCallManager, MessageRouter
from agents_hub.core.context import GroupChatContext
from agents_hub.core.foundation import (
    Role,
    RoleConfig,
    render_for_chat,
)


@pytest.fixture
def mock_group_chat_context():
    """创建 mock GroupChatContext"""
    context = MagicMock(spec=GroupChatContext)
    context.group_chat_id = "gc_test123"
    context.agent_member_info = {
        "Manager": MagicMock(token="tok_manager_abc123"),
        "Worker1": MagicMock(token="tok_worker1_def456"),
        "Worker2": MagicMock(token="tok_worker2_ghi789"),
    }
    return context


@pytest.fixture
def manager_agent(mock_group_chat_context):
    """创建 Manager Agent"""
    role = MagicMock(spec=Role)
    role_config = RoleConfig(
        name="Manager",
        platform=MagicMock(),
        description="负责任务分派和协调",
        work_root=str(Path("D:/test/work_root")),
        role_type=RoleType.LEADER,
    )
    role.get_role_config.return_value = role_config

    agent_call_manager = MagicMock(spec=AgentCallManager)
    message_router = MagicMock(spec=MessageRouter)

    agent = Manager(
        role=role,
        group_chat_context=mock_group_chat_context,
        agent_call_manager=agent_call_manager,
        message_router=message_router,
    )

    return agent


@pytest.fixture
def worker_agent(mock_group_chat_context):
    """创建 Worker Agent"""
    role = MagicMock(spec=Role)
    role_config = RoleConfig(
        name="Worker1",
        platform=MagicMock(),
        description="执行具体任务",
        work_root=str(Path("D:/test/work_root")),
        role_type=RoleType.TEAM_MEMBER,
    )
    role.get_role_config.return_value = role_config

    agent_call_manager = MagicMock(spec=AgentCallManager)
    message_router = MagicMock(spec=MessageRouter)

    agent = Worker(
        role=role,
        group_chat_context=mock_group_chat_context,
        agent_call_manager=agent_call_manager,
        message_router=message_router,
    )

    return agent


class TestToolUsageContentGeneration:
    """测试工具使用说明内容生成"""

    def test_manager_generates_all_tools(self, manager_agent):
        """
        契约：Manager 应该生成包含所有 6 个工具的说明

        验证方式：
        1. 调用 _generate_tool_usage_content
        2. 验证包含所有工具名称
        3. 验证角色标识为 Manager
        """
        content = manager_agent._generate_tool_usage_content()

        # 验证 XML 标签
        assert content.startswith("<tool_usage>")
        assert content.endswith("</tool_usage>")

        # 验证 Manager 标识
        assert "作为 Manager，你可以使用以下工具：" in content

        # 验证所有 6 个工具
        assert "**call_agent**" in content
        assert "**assign_tasks_to_team**" in content
        assert "**archive_task_list**" in content
        assert "**check_agent_call**" in content
        assert "**speak_in_group_chat**" in content
        assert "**finish_agent_call**" in content

    def test_worker_generates_only_two_tools(self, worker_agent):
        """
        契约：Worker 应该只生成 speak_in_group_chat 和 finish_agent_call 的说明

        验证方式：
        1. 调用 _generate_tool_usage_content
        2. 验证只包含两个工具
        3. 验证角色标识为 Worker
        """
        content = worker_agent._generate_tool_usage_content()

        # 验证 XML 标签
        assert content.startswith("<tool_usage>")
        assert content.endswith("</tool_usage>")

        # 验证 Worker 标识
        assert "作为 Worker，你可以使用以下工具：" in content

        # 验证只包含两个工具
        assert "**speak_in_group_chat**" in content
        assert "**finish_agent_call**" in content

        # 验证不包含 Manager 专属工具
        assert "call_agent" not in content
        assert "assign_tasks_to_team" not in content
        assert "archive_task_list" not in content
        assert "check_agent_call" not in content

    def test_tool_usage_contains_display_rules(self, manager_agent):
        """
        契约：工具使用说明应该包含群聊消息显示规则

        验证方式：
        1. 调用 _generate_tool_usage_content
        2. 验证包含显示规则
        """
        content = manager_agent._generate_tool_usage_content()

        assert "群聊消息显示规则" in content
        assert "speak_in_group_chat" in content
        assert "finish_agent_call" in content
        assert "不要同时调用 speak_in_group_chat 和 finish_agent_call" in content
        assert "任务结束时使用 finish_agent_call" in content

    def test_tool_usage_content_is_consistent(self, manager_agent):
        """
        契约：多次调用生成的内容应该完全一致

        验证方式：
        1. 多次调用 _generate_tool_usage_content
        2. 验证每次生成的内容完全相同
        """
        content1 = manager_agent._generate_tool_usage_content()
        content2 = manager_agent._generate_tool_usage_content()
        content3 = manager_agent._generate_tool_usage_content()

        assert content1 == content2 == content3


class TestToolUsageInjection:
    """测试工具使用说明注入到文件"""

    def test_inject_tool_usage_to_claude_md(self, manager_agent, tmp_path):
        """
        契约：应该将工具使用说明注入到 CLAUDE.md 的 TOOL_USAGE 标记中

        验证方式：
        1. 创建临时 CLAUDE.md
        2. 调用 _inject_tool_usage_to_files
        3. 验证内容被正确注入
        """
        # 创建临时 work_root
        work_root = tmp_path / "work_root"
        work_root.mkdir()
        manager_agent.role_config.work_root = str(work_root)

        # 创建 CLAUDE.md
        claude_md = work_root / "CLAUDE.md"
        claude_md.write_text("# Project Instructions\n\nSome content here.\n", encoding="utf-8")

        # 调用注入方法
        manager_agent._inject_tool_usage_to_files()

        # 验证 CLAUDE.md 被注入
        content = claude_md.read_text(encoding="utf-8")
        assert "<TOOL_USAGE>" in content
        assert "</TOOL_USAGE>" in content
        assert "作为 Manager，你可以使用以下工具：" in content
        assert "**call_agent**" in content
        assert "Some content here." in content  # 其他内容保持不变

    def test_inject_tool_usage_to_agents_md(self, worker_agent, tmp_path):
        """
        契约：应该将工具使用说明注入到 AGENTS.md 的 TOOL_USAGE 标记中

        验证方式：
        1. 创建临时 AGENTS.md
        2. 调用 _inject_tool_usage_to_files
        3. 验证内容被正确注入
        """
        # 创建临时 work_root
        work_root = tmp_path / "work_root"
        work_root.mkdir()
        worker_agent.role_config.work_root = str(work_root)

        # 创建 AGENTS.md
        agents_md = work_root / "AGENTS.md"
        agents_md.write_text("# Agent Instructions\n\nSome content here.\n", encoding="utf-8")

        # 调用注入方法
        worker_agent._inject_tool_usage_to_files()

        # 验证 AGENTS.md 被注入
        content = agents_md.read_text(encoding="utf-8")
        assert "<TOOL_USAGE>" in content
        assert "</TOOL_USAGE>" in content
        assert "作为 Worker，你可以使用以下工具：" in content
        assert "**speak_in_group_chat**" in content
        assert "Some content here." in content  # 其他内容保持不变

    def test_inject_tool_usage_idempotent(self, manager_agent, tmp_path):
        """
        契约：多次注入应该幂等，不会重复添加标签

        验证方式：
        1. 创建临时 CLAUDE.md
        2. 多次调用 _inject_tool_usage_to_files
        3. 验证只有一个 TOOL_USAGE 块
        4. 验证没有多余的内容

        如果失败，说明：注入函数没有正确替换已有内容，而是追加了新内容
        """
        # 创建临时 work_root
        work_root = tmp_path / "work_root"
        work_root.mkdir()
        manager_agent.role_config.work_root = str(work_root)

        # 创建 CLAUDE.md
        claude_md = work_root / "CLAUDE.md"
        claude_md.write_text("# Project Instructions\n", encoding="utf-8")

        # 多次调用注入方法
        manager_agent._inject_tool_usage_to_files()
        manager_agent._inject_tool_usage_to_files()
        manager_agent._inject_tool_usage_to_files()

        # 读取最终内容
        content = claude_md.read_text(encoding="utf-8")

        # 验证只有一个 TOOL_USAGE 块
        assert content.count("<TOOL_USAGE>") == 1, f"发现多个 <TOOL_USAGE> 标签: {content.count('<TOOL_USAGE>')}"
        assert content.count("</TOOL_USAGE>") == 1, f"发现多个 </TOOL_USAGE> 标签: {content.count('</TOOL_USAGE>')}"

        # 验证没有重复的内容
        assert content.count("作为 Manager，你可以使用以下工具：") == 1
        assert content.count("**call_agent**") == 1

        # 验证文件结构完整
        assert content.startswith("# Project Instructions\n")
        assert "<TOOL_USAGE>" in content
        assert "</TOOL_USAGE>" in content

    def test_inject_tool_usage_updates_existing(self, manager_agent, tmp_path):
        """
        契约：注入应该更新已存在的 TOOL_USAGE 内容

        验证方式：
        1. 创建包含旧 TOOL_USAGE 的 CLAUDE.md
        2. 调用 _inject_tool_usage_to_files
        3. 验证旧内容被替换，新内容被注入
        """
        # 创建临时 work_root
        work_root = tmp_path / "work_root"
        work_root.mkdir()
        manager_agent.role_config.work_root = str(work_root)

        # 创建包含旧 TOOL_USAGE 的 CLAUDE.md
        claude_md = work_root / "CLAUDE.md"
        old_content = """# Project Instructions

<TOOL_USAGE>
旧的工具使用说明
</TOOL_USAGE>

Some other content.
"""
        claude_md.write_text(old_content, encoding="utf-8")

        # 调用注入方法
        manager_agent._inject_tool_usage_to_files()

        # 验证 CLAUDE.md 被更新
        content = claude_md.read_text(encoding="utf-8")
        assert "<TOOL_USAGE>" in content
        assert "旧的工具使用说明" not in content
        assert "作为 Manager，你可以使用以下工具：" in content
        assert "Some other content." in content  # 其他内容保持不变

    def test_inject_runtime_and_tool_usage_idempotent(self, manager_agent, mock_group_chat_context, tmp_path):
        """
        契约：同时注入 runtime 和 tool_usage 应该幂等

        验证方式：
        1. 创建临时 CLAUDE.md
        2. 多次调用 _inject_runtime_to_files 和 _inject_tool_usage_to_files
        3. 验证每个标记块只有一个

        如果失败，说明：注入函数之间相互干扰或没有正确替换
        """
        # 创建临时 work_root
        work_root = tmp_path / "work_root"
        work_root.mkdir()
        manager_agent.role_config.work_root = str(work_root)

        # 创建 CLAUDE.md
        claude_md = work_root / "CLAUDE.md"
        claude_md.write_text("# Project Instructions\n", encoding="utf-8")

        # Mock agent_token property
        with patch.object(type(manager_agent), 'agent_token', new_callable=lambda: property(lambda self: "tok_manager_abc123")):
            # 多次调用注入方法
            for _ in range(3):
                manager_agent._inject_runtime_to_files()
                manager_agent._inject_tool_usage_to_files()

        # 读取最终内容
        content = claude_md.read_text(encoding="utf-8")

        # 验证每个标记块只有一个
        assert content.count("<AGENT_RUNTIME>") == 1, f"发现多个 <AGENT_RUNTIME> 标签: {content.count('<AGENT_RUNTIME>')}"
        assert content.count("</AGENT_RUNTIME>") == 1, f"发现多个 </AGENT_RUNTIME> 标签: {content.count('</AGENT_RUNTIME>')}"
        assert content.count("<TOOL_USAGE>") == 1, f"发现多个 <TOOL_USAGE> 标签: {content.count('<TOOL_USAGE>')}"
        assert content.count("</TOOL_USAGE>") == 1, f"发现多个 </TOOL_USAGE> 标签: {content.count('</TOOL_USAGE>')}"

        # 验证内容正确
        assert "你的名字：Manager" in content
        assert "作为 Manager，你可以使用以下工具：" in content


class TestSendMessageFormatting:
    """测试 send_message_to_agent 消息格式化"""

    def test_render_for_chat_adds_at_prefix(self):
        """
        契约：render_for_chat 应该添加 @ 前缀

        验证方式：
        1. 调用 render_for_chat
        2. 验证输出格式正确
        """
        result = render_for_chat("Manager", "Worker1", "你好")
        assert result == "@Worker1 你好"

    def test_render_for_chat_preserves_content(self):
        """
        契约：render_for_chat 应该保留原始内容

        验证方式：
        1. 调用 render_for_chat 带复杂内容
        2. 验证内容完整保留
        """
        content = "这是一个很长的消息\n包含换行和特殊字符：@#$%"
        result = render_for_chat("Manager", "Worker1", content)
        assert result == f"@Worker1 {content}"

    def test_message_already_formatted_not_double_at(self):
        """
        契约：已经格式化的消息不应该被重复添加 @

        验证方式：
        1. 创建已经包含 @ 前缀的消息
        2. 模拟 send_message_to_agent 的格式化逻辑
        3. 验证不会重复添加 @

        如果失败，说明：格式化判断逻辑有误
        """
        # 模拟 send_message_to_agent 中的格式化逻辑
        send_from = "Manager"
        send_to = "Worker1"

        # 已经格式化的消息
        already_formatted = "@Worker1 你好"
        content = already_formatted
        if not content.startswith(f"@{send_to}"):
            content = render_for_chat(send_from, send_to, content)

        # 应该保持原样
        assert content == "@Worker1 你好"
        assert content.count("@Worker1") == 1

    def test_message_not_formatted_adds_at(self):
        """
        契约：未格式化的消息应该添加 @ 前缀

        验证方式：
        1. 创建未格式化的消息
        2. 模拟 send_message_to_agent 的格式化逻辑
        3. 验证正确添加 @
        """
        # 模拟 send_message_to_agent 中的格式化逻辑
        send_from = "Manager"
        send_to = "Worker1"

        # 未格式化的消息
        not_formatted = "你好"
        content = not_formatted
        if not content.startswith(f"@{send_to}"):
            content = render_for_chat(send_from, send_to, content)

        # 应该添加 @
        assert content == "@Worker1 你好"

    def test_message_with_different_target_not_confused(self):
        """
        契约：@ 其他目标的消息不应该被误判为已格式化

        验证方式：
        1. 创建 @ 其他目标的消息
        2. 模拟 send_message_to_agent 的格式化逻辑
        3. 验证正确添加 @

        如果失败，说明：startswith 判断过于宽泛
        """
        send_from = "Manager"
        send_to = "Worker1"

        # @ 其他目标的消息
        other_target = "@Worker2 你好"
        content = other_target
        if not content.startswith(f"@{send_to}"):
            content = render_for_chat(send_from, send_to, content)

        # 应该重新格式化
        assert content == "@Worker1 @Worker2 你好"


class TestMarkdownInjectorIdempotent:
    """测试 markdown_injector 的幂等性"""

    def test_replace_marked_section_idempotent(self, tmp_path):
        """
        契约：replace_marked_section 多次调用应该幂等

        验证方式：
        1. 创建测试文件
        2. 多次调用 replace_marked_section
        3. 验证只有一个标记块
        4. 验证内容正确

        如果失败，说明：replace_marked_section 没有正确替换已有内容
        """
        from agents_hub.core.utils.markdown_injector import replace_marked_section

        # 创建测试文件
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\n", encoding="utf-8")

        # 多次调用
        for i in range(5):
            replace_marked_section(test_file, "TEST_MARKER", f"content_{i}")

        # 读取最终内容
        content = test_file.read_text(encoding="utf-8")

        # 验证只有一个标记块
        assert content.count("<TEST_MARKER>") == 1, f"发现多个 <TEST_MARKER> 标签: {content.count('<TEST_MARKER>')}"
        assert content.count("</TEST_MARKER>") == 1, f"发现多个 </TEST_MARKER> 标签: {content.count('</TEST_MARKER>')}"

        # 验证内容是最后一次写入的
        assert "content_4" in content
        assert "content_0" not in content
        assert "content_1" not in content

    def test_replace_marked_section_preserves_other_content(self, tmp_path):
        """
        契约：replace_marked_section 应该保留其他内容

        验证方式：
        1. 创建包含多个部分的文件
        2. 调用 replace_marked_section
        3. 验证其他内容保持不变
        """
        from agents_hub.core.utils.markdown_injector import replace_marked_section

        # 创建测试文件
        test_file = tmp_path / "test.md"
        original_content = """# Title

## Section 1
Content 1

## Section 2
Content 2
"""
        test_file.write_text(original_content, encoding="utf-8")

        # 调用 replace_marked_section
        replace_marked_section(test_file, "NEW_SECTION", "New content")

        # 读取最终内容
        content = test_file.read_text(encoding="utf-8")

        # 验证其他内容保持不变
        assert "# Title" in content
        assert "## Section 1" in content
        assert "Content 1" in content
        assert "## Section 2" in content
        assert "Content 2" in content

        # 验证新内容被添加
        assert "<NEW_SECTION>" in content
        assert "New content" in content
        assert "</NEW_SECTION>" in content

    def test_replace_marked_section_multiple_markers(self, tmp_path):
        """
        契约：replace_marked_section 应该正确处理多个不同的标记

        验证方式：
        1. 创建测试文件
        2. 注入多个不同的标记
        3. 验证每个标记块只有一个
        """
        from agents_hub.core.utils.markdown_injector import replace_marked_section

        # 创建测试文件
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\n", encoding="utf-8")

        # 注入多个不同的标记
        replace_marked_section(test_file, "MARKER_A", "Content A")
        replace_marked_section(test_file, "MARKER_B", "Content B")
        replace_marked_section(test_file, "MARKER_C", "Content C")

        # 读取最终内容
        content = test_file.read_text(encoding="utf-8")

        # 验证每个标记块只有一个
        assert content.count("<MARKER_A>") == 1
        assert content.count("</MARKER_A>") == 1
        assert content.count("<MARKER_B>") == 1
        assert content.count("</MARKER_B>") == 1
        assert content.count("<MARKER_C>") == 1
        assert content.count("</MARKER_C>") == 1

        # 验证内容正确
        assert "Content A" in content
        assert "Content B" in content
        assert "Content C" in content

    def test_replace_marked_section_idempotent_multiple_markers(self, tmp_path):
        """
        契约：多个标记的多次注入应该幂等

        验证方式：
        1. 创建测试文件
        2. 多次注入多个不同的标记
        3. 验证每个标记块只有一个

        如果失败，说明：多个标记之间相互干扰
        """
        from agents_hub.core.utils.markdown_injector import replace_marked_section

        # 创建测试文件
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\n", encoding="utf-8")

        # 多次注入多个不同的标记
        for i in range(3):
            replace_marked_section(test_file, "MARKER_A", f"Content A_{i}")
            replace_marked_section(test_file, "MARKER_B", f"Content B_{i}")

        # 读取最终内容
        content = test_file.read_text(encoding="utf-8")

        # 验证每个标记块只有一个
        assert content.count("<MARKER_A>") == 1, f"发现多个 <MARKER_A> 标签: {content.count('<MARKER_A>')}"
        assert content.count("</MARKER_A>") == 1, f"发现多个 </MARKER_A> 标签: {content.count('</MARKER_A>')}"
        assert content.count("<MARKER_B>") == 1, f"发现多个 <MARKER_B> 标签: {content.count('<MARKER_B>')}"
        assert content.count("</MARKER_B>") == 1, f"发现多个 </MARKER_B> 标签: {content.count('</MARKER_B>')}"

        # 验证内容是最后一次写入的
        assert "Content A_2" in content
        assert "Content B_2" in content
        assert "Content A_0" not in content
        assert "Content B_0" not in content
