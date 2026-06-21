import asyncio
from types import SimpleNamespace

import pytest

from agents_hub.core.context import AgentMemberInfo
from agents_hub.core.orchestration.group_chat import GroupChat


@pytest.mark.asyncio
async def test_stop_member_recovers_missing_member_info():
    group_chat = GroupChat.__new__(GroupChat)
    group_chat.group_chat_id = "group-1"
    group_chat.runtime = _RuntimeWithMissingMemberInfo()
    group_chat.manager = None
    group_chat.manager_task = None
    group_chat.workers = {"codex": _FakeAgent("codex")}
    group_chat.worker_tasks = {}
    group_chat.message_router = _FakeMessageRouter()
    group_chat.agent_call_manager = _FakeAgentCallManager()
    group_chat._member_lifecycle_locks = {}

    result = await group_chat.stop_member("codex")

    assert result == {"agent_name": "codex", "status": "stopped", "processed_calls": 0}
    assert group_chat.runtime.member_infos["codex"].status == "stopped"
    assert group_chat.runtime.member_infos["codex"].cwd == "D:/project"
    assert group_chat.runtime.save_contexts == ["Stop agent codex"]
    assert group_chat.workers["codex"].stopped is True
    assert group_chat.message_router.unregistered == ["codex"]


class _RuntimeWithMissingMemberInfo:
    project_path = "D:/project"

    def __init__(self):
        self.member_infos = {}
        self.save_contexts = []
        self.state = SimpleNamespace(agent_member_infos=self.member_infos)

    def get_agent_member_info(self, _agent_name):
        raise KeyError(_agent_name)

    def get_or_create_agent_member_info(self, agent_name):
        if agent_name not in self.member_infos:
            self.member_infos[agent_name] = AgentMemberInfo()
        return self.member_infos[agent_name]

    async def save_agent_members(self, context):
        self.save_contexts.append(context)


class _FakeAgent:
    def __init__(self, name):
        self.name = name
        self.main_session_id = None
        self.message_queue = asyncio.Queue()
        self.stopped = False

    async def stop(self):
        self.stopped = True


class _FakeMessageRouter:
    def __init__(self):
        self.unregistered = []

    def unregister(self, agent_name):
        self.unregistered.append(agent_name)


class _FakeAgentCallManager:
    async def get_runtime_calls_for_agent(self, _agent_name):
        return []

