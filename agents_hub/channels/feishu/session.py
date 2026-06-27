"""飞书 Session 状态管理

管理飞书群的会话状态，支持群聊、单聊和助手模式的自动切换。
每个飞书群对应一个状态容器，可以在不同模式间切换。
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents_hub.config import config
from agents_hub.utils import get_logger

logger = get_logger(__name__)

# 常量
FIRST_MESSAGE_MAX_LENGTH = 10  # 单聊历史中第一句话的最大长度
SINGLE_CHAT_HISTORY_MAX_SIZE = 50  # 单聊历史记录的最大数量


@dataclass
class FeishuSessionState:
    """飞书群状态（持久化）

    每个飞书群对应一个 Agent Hub 状态容器，可以是群聊、单聊或助手模式。
    """

    feishu_chat_id: str  # 飞书群 ID（唯一标识，oc_xxx）
    session_type: str  # "group_chat" / "single_chat" / "assistant" / "idle"
    session_id: str  # 群聊 ID / agent 名称 / "assistant" / ""
    session_name: str = ""  # 显示名称（群聊名称或 agent 名称）
    single_chat_id: str = ""  # 单聊会话 ID（single_chat 和 assistant 模式使用）
    last_message_id: int = 0  # 增量同步位置（仅群聊模式使用）
    last_sync_at: str = ""  # 最后同步时间
    created_at: str = ""  # 创建时间
    default_agent: str = ""  # 群聊默认对话 Agent（仅群聊模式使用）
    single_chat_history: list[dict[str, str]] = field(default_factory=list)  # 单聊历史记录

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
            "default_agent": self.default_agent,
            "single_chat_history": self.single_chat_history,
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
            default_agent=data.get("default_agent", ""),
            single_chat_history=data.get("single_chat_history", []),
        )


class FeishuSessionManager:
    """飞书 Session 状态管理

    负责管理飞书群的会话状态，支持群聊、单聊和助手模式。
    每个飞书群对应一个状态容器，可以在不同模式间切换。

    使用全局单例模式，确保线程安全。

    使用方式：
        from agents_hub.channels.feishu.session import feishu_session_manager

        feishu_session_manager.load()
        state = feishu_session_manager.get_or_create_state("oc_xxx")
        feishu_session_manager.switch_to_group_chat("oc_xxx", "group_123", "测试群聊")
        feishu_session_manager.save()
    """

    _instance: FeishuSessionManager | None = None
    _lock = threading.Lock()
    _initialized: bool

    def __new__(cls, data_path: Path | None = None):
        """单例模式（双重检查锁定）"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, data_path: Path | None = None):
        """初始化（单例只初始化一次）"""
        if self._initialized:
            return

        self._data_path = data_path or Path(config.data_path)
        self._channels_dir = self._data_path / "channels" / "feishu"
        self._state_file = self._channels_dir / "session_state.json"
        self._states: dict[str, FeishuSessionState] = {}  # feishu_chat_id -> state
        self._default_session_type = "idle"  # 默认空闲模式，显示命令面板
        self._operation_lock = threading.Lock()  # 操作锁，保护状态修改
        self._initialized = True

    def get_or_create_state(self, feishu_chat_id: str) -> FeishuSessionState:
        """获取或创建状态（首次收到消息时自动创建）

        Args:
            feishu_chat_id: 飞书群 ID

        Returns:
            FeishuSessionState
        """
        with self._operation_lock:
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

    def switch_to_idle(self, feishu_chat_id: str) -> None:
        """切换到 idle 状态（命令面板）

        Args:
            feishu_chat_id: 飞书群 ID
        """
        with self._operation_lock:
            state = self._get_or_create_state_unlocked(feishu_chat_id)
            state.session_type = "idle"
            state.session_id = ""
            state.session_name = ""
            # 保留 single_chat_id，避免重复创建助手单聊
            logger.info("切换到 idle 状态: chat_id=%s", feishu_chat_id)

    def switch_to_group_chat(
        self, feishu_chat_id: str, group_chat_id: str, group_chat_name: str
    ) -> None:
        """切换到群聊模式

        Args:
            feishu_chat_id: 飞书群 ID
            group_chat_id: agents-hub 群聊 ID
            group_chat_name: 群聊名称
        """
        with self._operation_lock:
            state = self._get_or_create_state_unlocked(feishu_chat_id)
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
        with self._operation_lock:
            state = self._get_or_create_state_unlocked(feishu_chat_id)
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
        with self._operation_lock:
            state = self._get_or_create_state_unlocked(feishu_chat_id)
            state.session_type = "assistant"
            state.session_id = config.default_assistant_name
            state.session_name = ""
            # 保留 single_chat_id，避免重复创建单聊
            logger.info("切换到助手模式: chat_id=%s", feishu_chat_id)

    def _get_or_create_state_unlocked(self, feishu_chat_id: str) -> FeishuSessionState:
        """获取或创建状态（不加锁版本，供内部已持锁的方法调用）"""
        if feishu_chat_id not in self._states:
            now = datetime.now(timezone.utc).isoformat()
            self._states[feishu_chat_id] = FeishuSessionState(
                feishu_chat_id=feishu_chat_id,
                session_type=self._default_session_type,
                session_id="",
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

    def update_sync_state(self, feishu_chat_id: str, last_message_id: int) -> None:
        """更新同步状态

        Args:
            feishu_chat_id: 飞书群 ID
            last_message_id: 最后同步的消息 ID
        """
        with self._operation_lock:
            state = self._get_or_create_state_unlocked(feishu_chat_id)
            state.last_message_id = last_message_id
            state.last_sync_at = datetime.now(timezone.utc).isoformat()
            logger.debug("同步状态已更新: %s, message_id=%d", feishu_chat_id, last_message_id)

    def add_single_chat_history(
        self, feishu_chat_id: str, session_id: str, agent_name: str, first_message: str
    ) -> None:
        """添加单聊历史记录

        Args:
            feishu_chat_id: 飞书群 ID
            session_id: 单聊会话 ID
            agent_name: Agent 名称
            first_message: 用户的第一句话
        """
        with self._operation_lock:
            state = self._get_or_create_state_unlocked(feishu_chat_id)

            # 检查是否已存在（避免重复）
            existing = [h for h in state.single_chat_history if h["session_id"] == session_id]
            if existing:
                # 更新第一句话（如果之前为空）
                if not existing[0]["first_message"] and first_message:
                    existing[0]["first_message"] = first_message[:FIRST_MESSAGE_MAX_LENGTH]
                return

            # 添加新记录
            state.single_chat_history.append(
                {
                    "session_id": session_id,
                    "agent_name": agent_name,
                    "first_message": first_message[:FIRST_MESSAGE_MAX_LENGTH]
                    if first_message
                    else "",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            # 限制列表长度
            if len(state.single_chat_history) > SINGLE_CHAT_HISTORY_MAX_SIZE:
                state.single_chat_history = state.single_chat_history[
                    -SINGLE_CHAT_HISTORY_MAX_SIZE:
                ]

            logger.info(
                "添加单聊历史: chat_id=%s, session_id=%s, agent=%s",
                feishu_chat_id,
                session_id,
                agent_name,
            )

    def save(self) -> None:
        """持久化状态到单个文件"""
        with self._operation_lock:
            self._channels_dir.mkdir(parents=True, exist_ok=True)
            states_data = [state.to_dict() for state in self._states.values()]
            self._state_file.write_text(json.dumps(states_data, ensure_ascii=False, indent=2))
            logger.info("Session 状态已保存: states=%d", len(self._states))

    def load(self) -> None:
        """加载状态（支持自动迁移旧格式）"""
        with self._operation_lock:
            if self._state_file.exists():
                try:
                    data = json.loads(self._state_file.read_text())
                    # 自动迁移旧格式
                    migrated = self._migrate_old_format(data)
                    self._states = {
                        item["feishu_chat_id"]: FeishuSessionState.from_dict(item)
                        for item in migrated
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


# 全局单例实例
feishu_session_manager = FeishuSessionManager()
