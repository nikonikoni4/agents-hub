"""Realtime event contract tests"""

import pytest

from agents_hub.realtime.dependencies import broadcast_group_chat_refresh
from agents_hub.realtime.events import RefreshSignal, make_refresh_signal


def test_make_refresh_signal_uses_existing_refresh_shape():
    signal = make_refresh_signal("chat-123")

    payload = signal.model_dump(mode="json")
    assert payload["type"] == "refresh"
    assert payload["group_chat_id"] == "chat-123"
    assert "timestamp" in payload


def test_refresh_signal_defaults_to_refresh_type():
    signal = RefreshSignal(group_chat_id="chat-123")

    assert signal.type == "refresh"


@pytest.mark.asyncio
async def test_broadcast_group_chat_refresh_uses_manager_payload():
    class FakeManager:
        def __init__(self):
            self.calls = []

        async def broadcast(self, group_chat_id, message):
            self.calls.append((group_chat_id, message))

    manager = FakeManager()

    await broadcast_group_chat_refresh("chat-123", manager=manager)

    assert len(manager.calls) == 1
    group_chat_id, payload = manager.calls[0]
    assert group_chat_id == "chat-123"
    assert payload["type"] == "refresh"
    assert payload["group_chat_id"] == "chat-123"
    assert "timestamp" in payload
