from datetime import datetime

from agents_hub.core.context.group_chat_session import AgentMember, GroupChatSession
from agents_hub.core.context.group_metadata import GroupMetadata


class FakeRepository:
    def __init__(self):
        self.group_chat_id = "gc_1"
        self.project_path = "/tmp/project"
        self.saved_metadata = None
        self.saved_sessions = None
        self.saved_group_session = None
        self.saved_compact_history = None
        self.closed = False

    async def load_group_chat_session(self):
        session = GroupChatSession(group_chat_id="gc_1")
        session.messages = [
            {
                "agent_name": "Worker1",
                "content": "hello",
                "timestamp": "2026-06-04T10:00:00",
                "platform": "claude",
            }
        ]
        return session

    async def load_agent_member(self):
        return {
            "Worker1": AgentMember(
                main_session="s1",
                btw_session=["b1"],
                cwd="/tmp/project/w1",
                use_docker=True,
            )
        }

    async def load_compact_history(self):
        return [{"content": {"summary": "old"}}]

    async def load_group_metadata(self):
        return GroupMetadata(
            group_chat_id="gc_1",
            group_chat_name="Test",
            project_path="/tmp/project",
            created_at=datetime(2026, 6, 4, 10, 0, 0),
            group_type="manager_orchestrate",
        )

    async def save_group_metadata(self, metadata):
        self.saved_metadata = metadata

    async def save_agent_member(self, state):
        self.saved_sessions = state

    async def save_group_chat_session(self, session):
        self.saved_group_session = session

    async def save_compact_history(self, history):
        self.saved_compact_history = history

    def close(self):
        self.closed = True
