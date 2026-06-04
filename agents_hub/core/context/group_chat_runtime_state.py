from dataclasses import dataclass, field

from agents_hub.core.context.group_chat_session import AgentMemberInfo, GroupChatSession
from agents_hub.core.context.group_metadata import GroupMetadata


@dataclass
class GroupChatRuntimeState:
    group_chat_id: str
    project_path: str
    group_chat_session: GroupChatSession | None = None
    agent_member_infos: dict[str, AgentMemberInfo] = field(default_factory=dict)
    compact_history: list[dict] = field(default_factory=list)
    metadata: GroupMetadata | None = None
    persistence_error: str | None = None

    def require_session(self) -> GroupChatSession:
        if self.group_chat_session is None:
            from agents_hub.core.foundation import StateError

            raise StateError("GroupChatSession 未加载,请先调用 runtime.load()")
        return self.group_chat_session

    def require_metadata(self) -> GroupMetadata:
        if self.metadata is None:
            from agents_hub.core.foundation import StateError

            raise StateError("GroupMetadata 未加载或未初始化")
        return self.metadata
