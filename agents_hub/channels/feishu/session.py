"""飞书 Session 状态管理

管理飞书群的会话状态，支持群聊、单聊和助手模式的自动切换。
每个飞书群对应一个状态容器，可以在不同模式间切换。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents_hub.config import config
from agents_hub.utils import get_logger

logger = get_logger(__name__)


@dataclass
class FeishuSessionState:
    """飞书群状态（持久化）

    每个飞书群对应一个 Agent Hub 状态容器，可以是群聊、单聊或助手模式。
    """

    feishu_chat_id: str  # 飞书群 ID（唯一标识，oc_xxx）
    session_type: str  # "group_chat" / "single_chat" / "assistant"
    session_id: str  # 群聊 ID / agent 名称 / "assistant"
    session_name: str = ""  # 显示名称（群聊名称或 agent 名称）
    single_chat_id: str = ""  # 单聊会话 ID（single_chat 和 assistant 模式使用）
    last_message_id: int = 0  # 增量同步位置（仅群聊模式使用）
    last_sync_at: str = ""  # 最后同步时间
    created_at: str = ""  # 创建时间

    def to_dict(self) -> dict[str, Any]:
        """转为字典"""
        return {
            "feishu_chat_id": self.feishu_chat_id,
            "session_type": self.session_type,
            "session_id": self.session_id,
            "session_name": self.session_name,
            "single_chat_id": self.single_chat_id,
            "last_message_id": self.last_message_id,
            "last_sync_at": self.last_sync_at,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FeishuSessionState:
        """从字典创建"""
        return cls(
            feishu_chat_id=data["feishu_chat_id"],
            session_type=data["session_type"],
            session_id=data["session_id"],
            session_name=data.get("session_name", ""),
            single_chat_id=data.get("single_chat_id", ""),
            last_message_id=data.get("last_message_id", 0),
            last_sync_at=data.get("last_sync_at", ""),
            created_at=data.get("created_at", ""),
        )


class FeishuSessionManager:
    """飞书 Session 状态管理

    负责管理飞书群的会话状态，支持群聊、单聊和助手模式。
    每个飞书群对应一个状态容器，可以在不同模式间切换。

    使用方式：
        manager = FeishuSessionManager(data_path)
        manager.load()
        state = manager.get_or_create_state("oc_xxx")  # 自动创建默认状态
        manager.switch_to_group_chat("oc_xxx", "group_123", "测试群聊")
        manager.save()
    """

    def __init__(self, data_path: Path):
        self._data_path = data_path
        self._channels_dir = data_path / "channels" / "feishu"
        self._state_file = self._channels_dir / "session_state.json"
        self._states: dict[str, FeishuSessionState] = {}  # feishu_chat_id -> state
        self._default_session_type = "idle"  # 默认空闲模式，显示命令面板

    def get_or_create_state(self, feishu_chat_id: str) -> FeishuSessionState:
        """获取或创建状态（首次收到消息时自动创建）

        Args:
            feishu_chat_id: 飞书群 ID

        Returns:
            FeishuSessionState
        """
        if feishu_chat_id not in self._states:
            now = datetime.now(timezone.utc).isoformat()
            self._states[feishu_chat_id] = FeishuSessionState(
                feishu_chat_id=feishu_chat_id,
                session_type=self._default_session_type,
                session_id="",  # idle 模式无 session_id
                session_name="",
                single_chat_id="",
                last_message_id=0,
                last_sync_at=now,
                created_at=now,
            )
            logger.info(
                "自动创建飞书状态: chat_id=%s, type=%s",
                feishu_chat_id,
                self._default_session_type,
            )
        return self._states[feishu_chat_id]

    def switch_to_group_chat(
        self, feishu_chat_id: str, group_chat_id: str, group_chat_name: str
    ) -> None:
        """切换到群聊模式

        Args:
            feishu_chat_id: 飞书群 ID
            group_chat_id: agents-hub 群聊 ID
            group_chat_name: 群聊名称
        """
        state = self.get_or_create_state(feishu_chat_id)
        state.session_type = "group_chat"
        state.session_id = group_chat_id
        state.session_name = group_chat_name
        state.single_chat_id = ""  # 清空单聊 ID
        logger.info(
            "切换到群聊模式: chat_id=%s, group=%s (%s)",
            feishu_chat_id,
            group_chat_id,
            group_chat_name,
        )

    def switch_to_single_chat(
        self, feishu_chat_id: str, agent_name: str, single_chat_id: str
    ) -> None:
        """切换到单聊模式

        Args:
            feishu_chat_id: 飞书群 ID
            agent_name: agent 名称
            single_chat_id: 单聊会话 ID
        """
        state = self.get_or_create_state(feishu_chat_id)
        state.session_type = "single_chat"
        state.session_id = agent_name
        state.session_name = agent_name
        state.single_chat_id = single_chat_id
        logger.info("切换到单聊模式: chat_id=%s, agent=%s", feishu_chat_id, agent_name)

    def switch_to_assistant(self, feishu_chat_id: str) -> None:
        """切换回助手模式

        Args:
            feishu_chat_id: 飞书群 ID
        """
        state = self.get_or_create_state(feishu_chat_id)
        state.session_type = "assistant"
        state.session_id = config.default_assistant_name
        state.session_name = ""
        # 保留 single_chat_id，避免重复创建单聊
        logger.info("切换到助手模式: chat_id=%s", feishu_chat_id)

    def update_sync_state(self, feishu_chat_id: str, last_message_id: int) -> None:
        """更新同步状态

        Args:
            feishu_chat_id: 飞书群 ID
            last_message_id: 最后同步的消息 ID
        """
        state = self.get_or_create_state(feishu_chat_id)
        state.last_message_id = last_message_id
        state.last_sync_at = datetime.now(timezone.utc).isoformat()
        logger.debug("同步状态已更新: %s, message_id=%d", feishu_chat_id, last_message_id)

    def save(self) -> None:
        """持久化状态到单个文件"""
        self._channels_dir.mkdir(parents=True, exist_ok=True)
        states_data = [state.to_dict() for state in self._states.values()]
        self._state_file.write_text(json.dumps(states_data, ensure_ascii=False, indent=2))
        logger.info("Session 状态已保存: states=%d", len(self._states))

    def load(self) -> None:
        """加载状态（支持自动迁移旧格式）"""
        if self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text())
                # 自动迁移旧格式
                migrated = self._migrate_old_format(data)
                self._states = {
                    item["feishu_chat_id"]: FeishuSessionState.from_dict(item) for item in migrated
                }
                logger.info("已加载 %d 个状态", len(self._states))
            except (json.JSONDecodeError, KeyError) as e:
                logger.error("加载状态失败: %s", e, exc_info=True)
                self._states = {}

    def _migrate_old_format(self, data: list[dict]) -> list[dict]:
        """迁移旧的 FeishuSessionMapping 格式到新的 FeishuSessionState 格式

        旧格式（FeishuSessionMapping）:
        {
            "feishu_chat_id": "oc_xxx",
            "group_chat_id": "group_123",
            "group_chat_name": "测试群聊",
            "bound_at": "2026-06-26T10:00:00"
        }

        新格式（FeishuSessionState）:
        {
            "feishu_chat_id": "oc_xxx",
            "session_type": "group_chat",
            "session_id": "group_123",
            "session_name": "测试群聊",
            "single_chat_id": "",
            "last_message_id": 0,
            "last_sync_at": "",
            "created_at": "2026-06-26T10:00:00"
        }
        """
        migrated = []
        for item in data:
            # 检测旧格式：有 group_chat_id 字段
            if "group_chat_id" in item:
                logger.info("迁移旧格式状态: %s", item["feishu_chat_id"])
                migrated.append(
                    {
                        "feishu_chat_id": item["feishu_chat_id"],
                        "session_type": "group_chat",
                        "session_id": item["group_chat_id"],
                        "session_name": item.get("group_chat_name", ""),
                        "single_chat_id": "",
                        "last_message_id": 0,
                        "last_sync_at": "",
                        "created_at": item.get("bound_at", ""),
                    }
                )
            else:
                # 新格式，直接保留
                migrated.append(item)
        return migrated
