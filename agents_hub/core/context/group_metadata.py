"""
群聊元数据

用于保存群聊的配置信息，独立于消息历史。
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class GroupMetadata:
    """
    群聊元数据

    保存在 group_metadata.json 中，在 GroupChat.start() 时立即创建。
    与 group_chat_session.jsonl（消息历史）解耦，后者在首次消息时才创建。
    """

    group_chat_id: str
    group_chat_name: str  # 默认使用 group_chat_id
    project_path: str  # 项目路径，用于计算存储路径和作为 agent 默认 cwd
    created_at: datetime
    group_type: str = "manager_orchestrate"  # GroupChatType 的值

    def to_dict(self) -> dict:
        """转换为可序列化的字典"""
        return {
            "group_chat_id": self.group_chat_id,
            "group_chat_name": self.group_chat_name,
            "project_path": self.project_path,
            "created_at": self.created_at.isoformat(),
            "group_type": self.group_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GroupMetadata":
        """从字典构造"""
        return cls(
            group_chat_id=data["group_chat_id"],
            group_chat_name=data["group_chat_name"],
            project_path=data["project_path"],
            created_at=datetime.fromisoformat(data["created_at"]),
            group_type=data.get("group_type", "manager_orchestrate"),
        )
