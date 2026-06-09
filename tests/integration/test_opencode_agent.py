"""OpenCode Agent 集成测试

测试 Agent 与 OpenCode 的集成：
1. 创建 OpenCode 角色
2. 创建 Agent 实例
3. 通过 Agent.execute 发送消息
4. 验证回复
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from agents_hub.agent_bridge.models import AgentResult
from agents_hub.config.types import AgentPlatform, RoleType
from agents_hub.core.agent import Worker
from agents_hub.core.communication import AgentCallManager, MessageRouter, TaskManager
from agents_hub.core.context import GroupChatContext, GroupChatRuntime
from agents_hub.roles.role_manager import RoleManager
from agents_hub.utils.logger import setup_logging


@pytest.fixture(autouse=True)
def setup_test_logging(tmp_path):
    """初始化日志系统"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir(exist_ok=True)
    setup_logging(log_dir=log_dir, level="DEBUG")


@pytest.fixture
def role_manager():
    return RoleManager()


@pytest.fixture
def opencode_role(role_manager, tmp_path):
    """创建 opencode 角色"""
    role_name = "test_opencode_agent"
    try:
        role_manager.delete_role(role_name)
    except Exception:
        pass

    role = role_manager.create_role(
        name=role_name,
        platform=AgentPlatform.OPENCODE,
        description="测试用 OpenCode 角色",
    )

    # 写入 agent 提示词文件
    work_root = role._work_root
    agents_dir = work_root / "agents"
    agents_dir.mkdir(exist_ok=True)

    agent_md = agents_dir / "test_agent.md"
    agent_md.write_text(
        "你是TestAgent，一个专业的编程助手。回答问题时要简洁。",
        encoding="utf-8",
    )

    yield role

    # 清理
    try:
        role_manager.delete_role(role_name)
    except Exception:
        pass


@pytest.fixture
def project_path(tmp_path):
    """创建临时项目路径"""
    return str(tmp_path / "test_project")


async def mock_agent_execute(*args, **kwargs):
    """模拟 agent 执行，返回 mock 结果"""
    return AgentResult(
        text="我是TestAgent，一个专业的编程助手。",
        session_id="mock_session_123",
        timestamp="2026-06-09T00:00:00",
        agent_name="test_opencode_agent",
        platform=AgentPlatform.OPENCODE,
        role_type=RoleType.TEAM_MEMBER,
    )


class TestOpenCodeAgent:
    """OpenCode Agent 集成测试"""

    @pytest.mark.asyncio
    async def test_agent_execute_with_opencode(self, opencode_role, project_path, tmp_path):
        """
        契约：通过 Agent.execute 调用 OpenCode

        验证方式：
        1. 创建 OpenCode 角色
        2. 创建 Agent 实例
        3. 调用 Agent.execute
        4. 验证返回结果

        如果失败，说明：Agent 与 OpenCode 集成存在问题
        """
        # 创建 GroupChatContext mock
        group_chat_id = "test_group_123"
        runtime = GroupChatRuntime(group_chat_id, project_path)
        group_chat_context = GroupChatContext(runtime)

        # 创建通信组件
        message_router = MessageRouter()
        agent_call_manager = AgentCallManager(group_chat_id, project_path)
        task_manager = TaskManager(group_chat_id, project_path)

        # 创建 Worker
        worker = Worker(
            opencode_role,
            group_chat_context,
            agent_call_manager,
            message_router,
            task_manager,
        )

        # 注册 agent
        message_router.register(worker.name, worker.message_queue)

        # mock agent_platform_client.execute
        with patch("agents_hub.core.agent.base_agent.agent_platform_client") as mock_client:
            mock_client.execute = mock_agent_execute

            # 执行
            result = await worker.execute("你好，请介绍一下自己")

            # 验证结果
            assert result is not None
            assert result.text == "我是TestAgent，一个专业的编程助手。"
            assert result.agent_name == "test_opencode_agent"
            assert result.platform == AgentPlatform.OPENCODE

            print(f"\n[测试结果] Agent 回答: {result.text}")

    @pytest.mark.asyncio
    async def test_agent_build_system_prompt_for_opencode(
        self, opencode_role, project_path, tmp_path
    ):
        """
        契约：为 OpenCode 构建系统提示词

        验证方式：
        1. 创建 OpenCode 角色
        2. 创建 Agent 实例
        3. 调用 _build_system_prompt
        4. 验证返回文件名格式

        如果失败，说明：系统提示词构建存在问题
        """
        # 创建 GroupChatContext mock
        group_chat_id = "test_group_456"
        runtime = GroupChatRuntime(group_chat_id, project_path)
        group_chat_context = GroupChatContext(runtime)

        # 创建通信组件
        message_router = MessageRouter()
        agent_call_manager = AgentCallManager(group_chat_id, project_path)
        task_manager = TaskManager(group_chat_id, project_path)

        # 创建 Worker
        worker = Worker(
            opencode_role,
            group_chat_context,
            agent_call_manager,
            message_router,
            task_manager,
        )

        # 构建系统提示词
        system_prompt = worker._build_system_prompt(task_manager)

        # 验证返回文件名格式
        assert system_prompt is not None
        assert "test_opencode_agent" in system_prompt
        assert group_chat_id in system_prompt

        print(f"\n[测试结果] System prompt 文件名: {system_prompt}")

        # 验证文件已创建
        work_root = Path(opencode_role._work_root)
        agent_file = work_root / "agents" / f"{system_prompt}.md"
        assert agent_file.exists(), f"Agent 文件未创建: {agent_file}"

        # 验证文件内容
        content = agent_file.read_text(encoding="utf-8")
        assert "test_opencode_agent" in content
        assert group_chat_id in content

        print(f"[测试结果] Agent 文件已创建: {agent_file}")
