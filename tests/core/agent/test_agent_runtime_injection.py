"""
测试 Agent Runtime 注入功能

测试覆盖：
- 生成 runtime 内容（Manager 和 Worker）
- runtime 注入到 CLAUDE.md
- runtime 注入到 AGENTS.md
- Manager 包含 team_workboard
- Worker 不包含 team_workboard
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_hub.config.types import RoleType
from agents_hub.core.agent.base_agent import Agent
from agents_hub.core.communication import AgentCallManager, MessageRouter, TaskManager
from agents_hub.core.context import GroupChatContext
from agents_hub.core.foundation import (
    AgentMessage,
    MessageType,
    Role,
    RoleConfig,
    SessionType,
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
def mock_task_manager():
    """创建 mock TaskManager"""
    manager = MagicMock(spec=TaskManager)

    # 模拟 get_active_task_list 返回任务列表
    from agents_hub.core.communication.task import Task, TaskList
    from agents_hub.core.foundation.models import TaskListStatus, TaskStatus
    from datetime import datetime

    task_list = TaskList(
        list_id="list_123",
        group_chat_id="gc_test123",
        status=TaskListStatus.ACTIVE,
        tasks=[
            Task(
                task_id="task_1",
                owner="Worker1",
                content="实现模块A",
                status=TaskStatus.PENDING,
                group_chat_id="gc_test123",
                created_by="Manager",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            Task(
                task_id="task_2",
                owner="Worker2",
                content="测试模块B",
                status=TaskStatus.RUNNING,
                group_chat_id="gc_test123",
                created_by="Manager",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ],
        created_at=datetime.now(),
        archived_at=None,
    )

    manager.get_active_task_list.return_value = task_list
    return manager


@pytest.fixture
def manager_agent(mock_group_chat_context):
    """创建 Manager Agent"""
    # Mock Role 对象
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

    agent = Agent(
        role=role,
        group_chat_context=mock_group_chat_context,
        agent_call_manager=agent_call_manager,
        message_router=message_router,
    )

    return agent


@pytest.fixture
def worker_agent(mock_group_chat_context):
    """创建 Worker Agent"""
    # Mock Role 对象
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

    agent = Agent(
        role=role,
        group_chat_context=mock_group_chat_context,
        agent_call_manager=agent_call_manager,
        message_router=message_router,
    )

    return agent


class TestAgentRuntimeContentGeneration:
    """测试 runtime 内容生成"""

    def test_manager_generates_runtime_with_team_workboard(
        self, manager_agent, mock_group_chat_context, mock_task_manager
    ):
        """测试 Manager 生成包含 team_workboard 的 runtime 内容"""
        # 设置 agent_token
        manager_agent.agent_token = "tok_manager_abc123"

        # 生成 runtime 内容
        content = manager_agent._generate_runtime_content(mock_task_manager)

        # 验证内容格式
        assert "<AGENT_RUNTIME>" in content
        assert "</AGENT_RUNTIME>" in content

        # 验证 identity 部分
        assert "<identity>" in content
        assert "你的名字：Manager" in content
        assert "群聊ID：gc_test123" in content
        assert "身份令牌：tok_manager_abc123" in content
        assert "</identity>" in content

        # 验证 team 部分
        assert "<team>" in content
        assert "团队成员：" in content
        # 应该包含所有成员（除了自己）
        assert "Worker1" in content
        assert "Worker2" in content
        assert "</team>" in content

        # 验证 team_workboard 部分（Manager 特有）
        assert "<team_workboard>" in content
        assert "当前任务列表：" in content
        assert "[PENDING] task_1: 实现模块A (owner: Worker1)" in content
        assert "[RUNNING] task_2: 测试模块B (owner: Worker2)" in content
        assert "</team_workboard>" in content

    def test_worker_generates_runtime_without_team_workboard(
        self, worker_agent, mock_group_chat_context, mock_task_manager
    ):
        """测试 Worker 生成不包含 team_workboard 的 runtime 内容"""
        # 设置 agent_token
        worker_agent.agent_token = "tok_worker1_def456"

        # 生成 runtime 内容
        content = worker_agent._generate_runtime_content(mock_task_manager)

        # 验证内容格式
        assert "<AGENT_RUNTIME>" in content
        assert "</AGENT_RUNTIME>" in content

        # 验证 identity 部分
        assert "<identity>" in content
        assert "你的名字：Worker1" in content
        assert "群聊ID：gc_test123" in content
        assert "身份令牌：tok_worker1_def456" in content
        assert "</identity>" in content

        # 验证 team 部分
        assert "<team>" in content
        assert "团队成员：" in content
        assert "</team>" in content

        # 验证不包含 team_workboard（Worker 不应该有）
        assert "<team_workboard>" not in content
        assert "当前任务列表：" not in content


class TestAgentRuntimeInjection:
    """测试 runtime 注入到文件"""

    @pytest.mark.asyncio
    async def test_inject_runtime_to_claude_md(
        self, manager_agent, mock_group_chat_context, mock_task_manager, tmp_path
    ):
        """测试注入 runtime 到 CLAUDE.md"""
        # 创建临时 work_root
        work_root = tmp_path / "work_root"
        work_root.mkdir()
        manager_agent.role_config.work_root = str(work_root)

        # 创建 CLAUDE.md
        claude_md = work_root / "CLAUDE.md"
        claude_md.write_text("# Project Instructions\n\nSome content here.\n", encoding="utf-8")

        # 设置 agent_token
        manager_agent.agent_token = "tok_manager_abc123"

        # 调用注入方法
        manager_agent._inject_runtime_to_files(mock_task_manager)

        # 验证 CLAUDE.md 被注入
        content = claude_md.read_text(encoding="utf-8")
        assert "<AGENT_RUNTIME>" in content
        assert "你的名字：Manager" in content
        assert "群聊ID：gc_test123" in content
        assert "身份令牌：tok_manager_abc123" in content
        assert "</AGENT_RUNTIME>" in content

    @pytest.mark.asyncio
    async def test_inject_runtime_to_agents_md(
        self, worker_agent, mock_group_chat_context, mock_task_manager, tmp_path
    ):
        """测试注入 runtime 到 AGENTS.md"""
        # 创建临时 work_root
        work_root = tmp_path / "work_root"
        work_root.mkdir()
        worker_agent.role_config.work_root = str(work_root)

        # 创建 AGENTS.md
        agents_md = work_root / "AGENTS.md"
        agents_md.write_text("# Agent Instructions\n\nSome content here.\n", encoding="utf-8")

        # 设置 agent_token
        worker_agent.agent_token = "tok_worker1_def456"

        # 调用注入方法
        worker_agent._inject_runtime_to_files(mock_task_manager)

        # 验证 AGENTS.md 被注入
        content = agents_md.read_text(encoding="utf-8")
        assert "<AGENT_RUNTIME>" in content
        assert "你的名字：Worker1" in content
        assert "群聊ID：gc_test123" in content
        assert "身份令牌：tok_worker1_def456" in content
        assert "</AGENT_RUNTIME>" in content

    @pytest.mark.asyncio
    async def test_inject_runtime_updates_existing_content(
        self, manager_agent, mock_group_chat_context, mock_task_manager, tmp_path
    ):
        """测试注入 runtime 会更新已存在的内容"""
        # 创建临时 work_root
        work_root = tmp_path / "work_root"
        work_root.mkdir()
        manager_agent.role_config.work_root = str(work_root)

        # 创建 CLAUDE.md，包含旧的 runtime 内容
        claude_md = work_root / "CLAUDE.md"
        old_content = """# Project Instructions

<AGENT_RUNTIME>
旧的 runtime 内容
</AGENT_RUNTIME>

Some other content.
"""
        claude_md.write_text(old_content, encoding="utf-8")

        # 设置 agent_token
        manager_agent.agent_token = "tok_manager_new"

        # 调用注入方法
        manager_agent._inject_runtime_to_files(mock_task_manager)

        # 验证 CLAUDE.md 被更新
        content = claude_md.read_text(encoding="utf-8")
        assert "<AGENT_RUNTIME>" in content
        assert "旧的 runtime 内容" not in content
        assert "你的名字：Manager" in content
        assert "身份令牌：tok_manager_new" in content
        assert "Some other content." in content  # 其他内容保持不变
