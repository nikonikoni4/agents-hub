"""飞书 Session 映射与同步状态管理

管理飞书群到 agents-hub 群聊的映射关系，以及增量同步状态。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents_hub.utils import get_logger

logger = get_logger(__name__)


@dataclass
class FeishuSessionMapping:
    """飞书群绑定关系（持久化）"""

    feishu_chat_id: str  # 飞书群 ID（oc_xxx，创建后不变）
    group_chat_id: str  # agents-hub 群聊 ID
    group_chat_name: str  # agents-hub 群聊名称（便于显示）
    bound_at: str  # 绑定时间

    def to_dict(self) -> dict[str, Any]:
        """转为字典"""
        return {
            "feishu_chat_id": self.feishu_chat_id,
            "group_chat_id": self.group_chat_id,
            "group_chat_name": self.group_chat_name,
            "bound_at": self.bound_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FeishuSessionMapping:
        """从字典创建"""
        return cls(
            feishu_chat_id=data["feishu_chat_id"],
            group_chat_id=data["group_chat_id"],
            group_chat_name=data["group_chat_name"],
            bound_at=data["bound_at"],
        )


@dataclass
class FeishuSyncState:
    """同步状态（持久化）"""

    feishu_chat_id: str  # 飞书群 ID
    last_message_id: int = 0  # 最后同步的消息 ID
    last_sync_at: str = ""  # 最后同步时间

    def to_dict(self) -> dict[str, Any]:
        """转为字典"""
        return {
            "feishu_chat_id": self.feishu_chat_id,
            "last_message_id": self.last_message_id,
            "last_sync_at": self.last_sync_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FeishuSyncState:
        """从字典创建"""
        return cls(
            feishu_chat_id=data["feishu_chat_id"],
            last_message_id=data.get("last_message_id", 0),
            last_sync_at=data.get("last_sync_at", ""),
        )


class FeishuSessionManager:
    """飞书 Session 映射与同步状态管理

    负责管理飞书群到 agents-hub 群聊的映射关系，
    以及增量同步状态的持久化。

    使用方式：
        manager = FeishuSessionManager(data_path)
        manager.load()
        manager.bind("oc_xxx", "group_123", "测试群聊")
        manager.save()
    """

    def __init__(self, data_path: Path):
        self._data_path = data_path
        self._channels_dir = data_path / "channels" / "feishu"
        self._mapping_file = self._channels_dir / "session_mapping.json"
        self._sync_state_file = self._channels_dir / "sync_state.json"
        self._mappings: dict[str, FeishuSessionMapping] = {}  # feishu_chat_id -> mapping
        self._sync_states: dict[str, FeishuSyncState] = {}  # feishu_chat_id -> sync_state
        self._group_to_feishu: dict[str, str] = {}  # group_chat_id -> feishu_chat_id（反向索引）

    def bind(self, feishu_chat_id: str, group_chat_id: str, group_chat_name: str) -> None:
        """绑定飞书群到 agents-hub 群聊。

        Args:
            feishu_chat_id: 飞书群 ID
            group_chat_id: agents-hub 群聊 ID
            group_chat_name: agents-hub 群聊名称
        """
        now = datetime.now(timezone.utc).isoformat()
        self._mappings[feishu_chat_id] = FeishuSessionMapping(
            feishu_chat_id=feishu_chat_id,
            group_chat_id=group_chat_id,
            group_chat_name=group_chat_name,
            bound_at=now,
        )
        self._group_to_feishu[group_chat_id] = feishu_chat_id
        logger.info("飞书群已绑定: %s -> %s (%s)", feishu_chat_id, group_chat_id, group_chat_name)

    def unbind(self, feishu_chat_id: str) -> None:
        """解绑飞书群。

        Args:
            feishu_chat_id: 飞书群 ID
        """
        if feishu_chat_id in self._mappings:
            mapping = self._mappings[feishu_chat_id]
            self._group_to_feishu.pop(mapping.group_chat_id, None)
            del self._mappings[feishu_chat_id]
            logger.info("飞书群已解绑: %s", feishu_chat_id)

        # 同时清理同步状态
        if feishu_chat_id in self._sync_states:
            del self._sync_states[feishu_chat_id]

    def get_mapping(self, feishu_chat_id: str) -> FeishuSessionMapping | None:
        """获取绑定关系。

        Args:
            feishu_chat_id: 飞书群 ID

        Returns:
            绑定关系，不存在则返回 None
        """
        return self._mappings.get(feishu_chat_id)

    def get_mapping_by_group_chat_id(self, group_chat_id: str) -> FeishuSessionMapping | None:
        """通过 agents-hub 群聊 ID 获取绑定关系。

        Args:
            group_chat_id: agents-hub 群聊 ID

        Returns:
            绑定关系，不存在则返回 None
        """
        feishu_chat_id = self._group_to_feishu.get(group_chat_id)
        if feishu_chat_id:
            return self._mappings.get(feishu_chat_id)
        return None

    def get_sync_state(self, feishu_chat_id: str) -> FeishuSyncState:
        """获取同步状态（不存在则创建）。

        Args:
            feishu_chat_id: 飞书群 ID

        Returns:
            同步状态
        """
        if feishu_chat_id not in self._sync_states:
            now = datetime.now(timezone.utc).isoformat()
            self._sync_states[feishu_chat_id] = FeishuSyncState(
                feishu_chat_id=feishu_chat_id,
                last_message_id=0,
                last_sync_at=now,
            )
        return self._sync_states[feishu_chat_id]

    def update_sync_state(self, feishu_chat_id: str, last_message_id: int) -> None:
        """更新同步状态。

        Args:
            feishu_chat_id: 飞书群 ID
            last_message_id: 最后同步的消息 ID
        """
        now = datetime.now(timezone.utc).isoformat()
        self._sync_states[feishu_chat_id] = FeishuSyncState(
            feishu_chat_id=feishu_chat_id,
            last_message_id=last_message_id,
            last_sync_at=now,
        )
        logger.debug("同步状态已更新: %s, message_id=%d", feishu_chat_id, last_message_id)

    def save(self) -> None:
        """持久化映射关系和同步状态"""
        # 创建目录
        self._channels_dir.mkdir(parents=True, exist_ok=True)

        # 保存映射关系
        mappings_data = [mapping.to_dict() for mapping in self._mappings.values()]
        self._mapping_file.write_text(json.dumps(mappings_data, ensure_ascii=False, indent=2))

        # 保存同步状态
        states_data = [state.to_dict() for state in self._sync_states.values()]
        self._sync_state_file.write_text(json.dumps(states_data, ensure_ascii=False, indent=2))

        logger.info(
            "Session 数据已保存: mappings=%d, sync_states=%d",
            len(self._mappings),
            len(self._sync_states),
        )

    def load(self) -> None:
        """加载映射关系和同步状态"""
        # 加载映射关系
        if self._mapping_file.exists():
            try:
                data = json.loads(self._mapping_file.read_text())
                self._mappings = {
                    item["feishu_chat_id"]: FeishuSessionMapping.from_dict(item) for item in data
                }
                # 重建反向索引
                self._group_to_feishu = {
                    m.group_chat_id: m.feishu_chat_id for m in self._mappings.values()
                }
                logger.info("已加载 %d 个映射关系", len(self._mappings))
            except (json.JSONDecodeError, KeyError):
                logger.error("加载映射关系失败", exc_info=True)
                self._mappings = {}

        # 加载同步状态
        if self._sync_state_file.exists():
            try:
                data = json.loads(self._sync_state_file.read_text())
                self._sync_states = {
                    item["feishu_chat_id"]: FeishuSyncState.from_dict(item) for item in data
                }
                logger.info("已加载 %d 个同步状态", len(self._sync_states))
            except (json.JSONDecodeError, KeyError):
                logger.error("加载同步状态失败", exc_info=True)
                self._sync_states = {}
