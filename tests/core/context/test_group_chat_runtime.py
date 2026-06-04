from datetime import datetime

import pytest

from agents_hub.core.context.group_chat_runtime_state import GroupChatRuntimeState
from agents_hub.core.context.group_chat_session import GroupChatSession
from agents_hub.core.context.group_metadata import GroupMetadata
from agents_hub.core.foundation import StateError


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
