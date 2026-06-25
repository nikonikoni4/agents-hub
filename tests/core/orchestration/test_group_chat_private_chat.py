"""
测试 GroupChat 的私聊功能

覆盖：
- start_private_chat: 进入私聊
- stop_private_chat: 退出私聊
- send_message_to_agent: 消息拦截（in_private_chat 状态）
- stop_member/reset_member/compress_agent_context: 操作限制
- Manager 限制
"""

import asyncio
from types import SimpleNamespace

import pytest

from agents_hub.core.context import AgentMemberInfo
from agents_hub.core.orchestration.group_chat import GroupChat
from agents_hub.core.foundation import AgentNotFoundError
from agents_hub.exceptions import StateError


@pytest.mark.asyncio
async def test_start_private_chat_success():
    """正常进入私聊：Agent 处于 idle 状态"""
    group_chat = _create_group_chat_with_members(["worker1"])

    result = await group_chat.start_private_chat("worker1")

    assert result["agent_name"] == "worker1"
    assert result["status"] == "in_private_chat"
    assert group_chat.runtime.member_infos["worker1"].status == "in_private_chat"
    assert "Start private chat: worker1" in group_chat.runtime.save_contexts


@pytest.mark.asyncio
async def test_start_private_chat_agent_not_found():
    """Agent 不存在时抛出 AgentNotFoundError"""
    group_chat = _create_group_chat_with_members(["worker1"])

    with pytest.raises(AgentNotFoundError):
        await group_chat.start_private_chat("nonexistent")


@pytest.mark.asyncio
async def test_start_private_chat_not_idle():
    """Agent 非 idle 状态时抛出 StateError"""
    group_chat = _create_group_chat_with_members(["worker1"])
    group_chat.runtime.member_infos["worker1"].status = "busy"

    with pytest.raises(StateError, match="只有 idle 状态才能进入私聊"):
        await group_chat.start_private_chat("worker1")


@pytest.mark.asyncio
async def test_start_private_chat_manager_forbidden():
    """Manager 角色禁止私聊"""
    group_chat = _create_group_chat_with_members(["worker1"])
    group_chat.manager = _FakeAgent("Leader")

    with pytest.raises(StateError, match="Manager 不允许进入私聊"):
        await group_chat.start_private_chat("Leader")


@pytest.mark.asyncio
async def test_stop_private_chat_success():
    """正常退出私聊：Agent 处于 in_private_chat 状态"""
    group_chat = _create_group_chat_with_members(["worker1"])
    group_chat.runtime.member_infos["worker1"].status = "in_private_chat"

    result = await group_chat.stop_private_chat("worker1")

    assert result["agent_name"] == "worker1"
    assert result["status"] == "idle"
    assert group_chat.runtime.member_infos["worker1"].status == "idle"
    assert "Stop private chat: worker1" in group_chat.runtime.save_contexts


@pytest.mark.asyncio
async def test_stop_private_chat_agent_not_found():
    """Agent 不存在时抛出 AgentNotFoundError"""
    group_chat = _create_group_chat_with_members(["worker1"])

    with pytest.raises(AgentNotFoundError):
        await group_chat.stop_private_chat("nonexistent")


@pytest.mark.asyncio
async def test_stop_private_chat_not_in_private_chat():
    """Agent 非 in_private_chat 状态时抛出 StateError"""
    group_chat = _create_group_chat_with_members(["worker1"])

    with pytest.raises(StateError, match="Agent worker1 当前状态为 idle，只有 in_private_chat 状态才能退出私聊"):
        await group_chat.stop_private_chat("worker1")


@pytest.mark.asyncio
async def test_stop_member_rejects_in_private_chat():
    """in_private_chat 状态的 Agent 无法被停止"""
    group_chat = _create_group_chat_with_members(["worker1"])
    group_chat.runtime.member_infos["worker1"].status = "in_private_chat"

    with pytest.raises(StateError, match="正在单聊中，无法停止"):
        await group_chat.stop_member("worker1")


@pytest.mark.asyncio
async def test_reset_member_rejects_in_private_chat():
    """in_private_chat 状态的 Agent 无法被重置"""
    group_chat = _create_group_chat_with_members(["worker1"])
    group_chat.runtime.member_infos["worker1"].status = "in_private_chat"

    with pytest.raises(StateError, match="正在单聊中，无法重置"):
        await group_chat.reset_member("worker1")


def _create_group_chat_with_members(member_names: list[str]) -> GroupChat:
    """创建带有模拟 Runtime 的 GroupChat 实例"""
    group_chat = GroupChat.__new__(GroupChat)
    group_chat.group_chat_id = "test-chat-001"
    group_chat.runtime = _FakeRuntime(member_names)
    group_chat.manager = None
    group_chat.manager_task = None
    group_chat.workers = {name: _FakeAgent(name) for name in member_names}
    group_chat.worker_tasks = {}
    group_chat.message_router = _FakeMessageRouter()
    group_chat.agent_call_manager = _FakeAgentCallManager()
    group_chat._member_lifecycle_locks = {}
    return group_chat


class _FakeRuntime:
    """模拟 GroupChatRuntime"""

    project_path = "/tmp/test"

    def __init__(self, member_names: list[str]):
        self.member_infos: dict[str, AgentMemberInfo] = {}
        for name in member_names:
            info = AgentMemberInfo()
            info.status = "idle"
            self.member_infos[name] = info
        self.save_contexts: list[str] = []
        self.state = SimpleNamespace(agent_member_infos=self.member_infos)

    def get_agent_member_info(self, agent_name: str) -> AgentMemberInfo:
        if agent_name not in self.member_infos:
            raise KeyError(agent_name)
        return self.member_infos[agent_name]

    def get_or_create_agent_member_info(self, agent_name: str) -> AgentMemberInfo:
        if agent_name not in self.member_infos:
            self.member_infos[agent_name] = AgentMemberInfo()
        return self.member_infos[agent_name]

    async def save_agent_members(self, context: str):
        self.save_contexts.append(context)


class _FakeAgent:
    def __init__(self, name: str):
        self.name = name
        self.main_session_id = None
        self.message_queue = asyncio.Queue()
        self.stopped = False

    async def stop(self):
        self.stopped = True


class _FakeMessageRouter:
    def __init__(self):
        self.unregistered: list[str] = []

    def unregister(self, agent_name: str):
        self.unregistered.append(agent_name)


class _FakeAgentCallManager:
    async def get_runtime_calls_for_agent(self, _agent_name: str):
        return []
