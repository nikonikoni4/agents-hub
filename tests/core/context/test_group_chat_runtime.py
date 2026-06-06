from datetime import datetime

import pytest

from .conftest import FakeRepository

from agents_hub.core.context.group_chat_runtime import GroupChatRuntime
from agents_hub.core.context.group_chat_runtime_state import GroupChatRuntimeState
from agents_hub.core.context.group_chat_session import AgentMemberInfo, GroupChatSession
from agents_hub.core.context.group_metadata import GroupMetadata
from agents_hub.core.foundation import GroupChatType, StateError


def test_runtime_state_requires_loaded_session():
    state = GroupChatRuntimeState(group_chat_id="gc_1", project_path="/tmp/project")

    with pytest.raises(StateError):
        state.require_session()

    session = GroupChatSession(group_chat_id="gc_1")
    state.group_chat_session = session

    assert state.require_session() is session


def test_runtime_state_requires_metadata():
    state = GroupChatRuntimeState(group_chat_id="gc_1", project_path="/tmp/project")

    with pytest.raises(StateError):
        state.require_metadata()

    metadata = GroupMetadata(
        group_chat_id="gc_1",
        group_chat_name="Test",
        project_path="/tmp/project",
        created_at=datetime(2026, 6, 4, 10, 0, 0),
        group_type="manager_orchestrate",
    )
    state.metadata = metadata

    assert state.require_metadata() is metadata


# ==================== Load and Query Tests ====================


async def test_runtime_loads_files_into_memory_and_queries_dicts():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)

    state = await runtime.load()

    assert state.group_chat_session is not None
    assert state.agent_member_infos["Worker1"].main_session == "s1"
    assert state.compact_history == [{"content": {"summary": "old"}}]
    assert state.metadata is not None

    info = runtime.get_info_dict(is_active=True)
    assert info["group_chat_id"] == "gc_1"
    assert info["group_chat_name"] == "Test"
    assert info["project_path"] == "/tmp/project"
    assert info["group_type"] == "manager_orchestrate"
    assert info["is_active"] is True

    members = runtime.get_member_dicts()
    assert members == [
        {
            "name": "Worker1",
            "main_session": "s1",
            "btw_session": ["b1"],
            "cwd": "/tmp/project/w1",
            "use_docker": True,
        }
    ]

    messages = runtime.get_message_dicts(limit=10)
    assert messages == [
        {
            "speaker": "Worker1",
            "content": "hello",
            "timestamp": "2026-06-04T10:00:00",
            "platform": "claude",
        }
    ]


async def test_get_message_dicts_with_before_cursor():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()

    # 添加更多消息用于测试游标分页
    runtime.state.group_chat_session.messages.extend([
        {"agent_name": "Worker1", "content": "msg2", "timestamp": "2026-06-04T10:01:00", "platform": "claude"},
        {"agent_name": "Worker1", "content": "msg3", "timestamp": "2026-06-04T10:02:00", "platform": "claude"},
    ])

    # 无游标：返回最新 1 条
    latest = runtime.get_message_dicts(limit=1)
    assert len(latest) == 1
    assert latest[0]["content"] == "msg3"

    # before=msg3 的时间戳：返回 msg3 之前的消息
    older = runtime.get_message_dicts(limit=10, before="2026-06-04T10:02:00")
    assert len(older) == 2
    assert older[0]["content"] == "hello"
    assert older[1]["content"] == "msg2"

    # before=msg2 的时间戳：只返回最老的 1 条
    oldest = runtime.get_message_dicts(limit=10, before="2026-06-04T10:01:00")
    assert len(oldest) == 1
    assert oldest[0]["content"] == "hello"

    # before 比所有消息都老：返回空
    empty = runtime.get_message_dicts(limit=10, before="2020-01-01T00:00:00")
    assert empty == []


async def test_get_or_create_agent_member_info_returns_existing():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()

    agent_member_info = runtime.get_or_create_agent_member_info("Worker1")
    assert agent_member_info.main_session == "s1"


async def test_get_or_create_agent_member_info_creates_new():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()

    agent_member_info = runtime.get_or_create_agent_member_info("Worker2")
    assert agent_member_info.main_session is None
    assert agent_member_info.btw_session == []


async def test_get_agent_names_returns_all_names():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()

    names = runtime.get_agent_names()
    assert names == ["Worker1"]


async def test_runtime_close_closes_repository():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)

    runtime.close()

    assert repository.closed is True


# ==================== Command Tests ====================


class MockAgentResult:
    def __init__(self, agent_name="Worker1", session_id="s1", text="hello"):
        from agents_hub.config.types import AgentPlatform

        self.agent_name = agent_name
        self.session_id = session_id
        self.text = text
        self.timestamp = "2026-06-04T10:00:00"
        self.platform = AgentPlatform.CLAUDE


async def test_runtime_commands_update_memory_then_persist():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()

    metadata = await runtime.initialize_metadata(
        group_chat_name="New Name",
        group_type=GroupChatType.MANAGER_ORCHESTRATE,
        created_at=datetime(2026, 6, 4, 11, 0, 0),
    )
    assert runtime.state.metadata is metadata
    assert repository.saved_metadata is metadata

    agent_member_info = await runtime.set_agent_token_and_default_cwd("Worker1", "tok_1")
    assert agent_member_info.token == "tok_1"
    assert agent_member_info.cwd == "/tmp/project/w1"
    assert repository.saved_sessions is runtime.state.agent_member_infos

    await runtime.set_agent_use_docker("Worker1", False)
    assert runtime.state.agent_member_infos["Worker1"].use_docker is False

    await runtime.update_context_load_state("Worker1", 3, 7)
    context_state = runtime.state.agent_member_infos["Worker1"].context_state
    assert context_state.last_loaded_compact_index == 3
    assert context_state.last_loaded_message_index == 7

    await runtime.add_message(MockAgentResult(text="new message"))
    assert runtime.state.group_chat_session.messages[-1]["content"] == "new message"
    assert repository.saved_group_session is runtime.state.group_chat_session

    compact_record = {"create_at": "2026-06-04T12:00:00", "content": {"summary": "sum"}}
    await runtime.append_compact_record_and_mark_compacted(compact_record)
    assert runtime.state.compact_history[-1] == compact_record
    assert repository.saved_compact_history is runtime.state.compact_history
    assert runtime.state.group_chat_session.last_compacted_loc == len(
        runtime.state.group_chat_session.messages
    )


async def test_update_agent_member_info_handles_empty_main_session():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()

    # Create new agent with no main_session
    result = MockAgentResult(agent_name="Worker2", session_id="s2")
    agent_member_info = await runtime.update_agent_member_info_from_result(result)

    assert agent_member_info.main_session == "s2"
    assert agent_member_info.btw_session == []


async def test_update_agent_member_info_appends_different_session_to_btw():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()

    # Worker1 already has main_session="s1"
    result = MockAgentResult(agent_name="Worker1", session_id="s2")
    agent_member_info = await runtime.update_agent_member_info_from_result(result)

    assert agent_member_info.main_session == "s1"
    assert "s2" in agent_member_info.btw_session


async def test_persistence_error_flag_set_on_failure():
    repository = FakeRepository()

    # Make save fail
    async def failing_save(metadata):
        raise IOError("Disk full")

    repository.save_group_metadata = failing_save

    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()

    with pytest.raises(IOError):
        await runtime.initialize_metadata("Test", GroupChatType.MANAGER_ORCHESTRATE)

    assert runtime.state.persistence_error == "Disk full"


async def test_persistence_error_cleared_on_success():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()

    # Set error manually
    runtime.state.persistence_error = "Previous error"

    # Successful operation should clear it
    await runtime.initialize_metadata("Test", GroupChatType.MANAGER_ORCHESTRATE)

    assert runtime.state.persistence_error is None


async def test_group_chat_context_uses_runtime_for_message_and_session_commands():
    from agents_hub.core.context.agent_context import AgentContext
    from agents_hub.core.context.group_chat_context import GroupChatContext

    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()
    context = GroupChatContext(runtime)

    result = MockAgentResult(agent_name="Worker2", session_id="s2", text="hello from w2")
    await context.update_agent_member_info(result)
    await context.add_message(result)

    assert runtime.state.agent_member_infos["Worker2"].main_session == "s2"
    assert runtime.state.group_chat_session.messages[-1]["agent_name"] == "Worker2"
    assert repository.saved_sessions is runtime.state.agent_member_infos
    assert repository.saved_group_session is runtime.state.group_chat_session
