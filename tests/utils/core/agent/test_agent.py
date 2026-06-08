"""
Agent 层单元测试

契约：
1. stop() 设置 _run=False 并发送哨兵消息
2. Manager/Worker 是 Agent 子类
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from agents_hub.core.agent.base_agent import Agent
from agents_hub.core.agent.manager import Manager
from agents_hub.core.agent.worker import Worker


def create_mock_role(name: str = "test_agent"):
    """创建 mock Role 对象"""
    role = MagicMock()
    role.get_role_config.return_value = SimpleNamespace(
        name=name,
        role_type=SimpleNamespace(value="team_member"),
        platform=SimpleNamespace(value="claude"),
        description="test agent",
    )
    return role


@pytest.fixture
def mock_deps():
    """提供 Agent 所需的 mock 依赖"""
    group_chat_context = MagicMock()
    group_chat_context.agent_member_info = {}
    agent_call_manager = MagicMock()
    message_router = MagicMock()
    return group_chat_context, agent_call_manager, message_router


class TestAgentStop:
    """测试 Agent.stop()"""

    @pytest.mark.asyncio
    async def test_stop_sets_run_false(self, mock_deps):
        """契约：stop() 设置 _run 为 False"""
        role = create_mock_role("agent_a")
        gcc, acm, router = mock_deps
        agent = Agent(role, gcc, acm, router)

        assert agent._run is True
        await agent.stop()
        assert agent._run is False

    @pytest.mark.asyncio
    async def test_stop_sends_sentinel(self, mock_deps):
        """契约：stop() 发送哨兵消息到队列"""
        role = create_mock_role("agent_a")
        gcc, acm, router = mock_deps
        agent = Agent(role, gcc, acm, router)

        await agent.stop()

        msg = agent.message_queue.get_nowait()
        assert msg.call_id == "__STOP__"
        assert msg.send_from == "__SYSTEM__"
        assert msg.send_to == "agent_a"
        assert msg.content == "__STOP__"


class TestManagerWorkerInheritance:
    """测试 Manager/Worker 继承关系"""

    def test_manager_is_agent_subclass(self):
        """契约：Manager 继承 Agent"""
        assert issubclass(Manager, Agent)

    def test_worker_is_agent_subclass(self):
        """契约：Worker 继承 Agent"""
        assert issubclass(Worker, Agent)
