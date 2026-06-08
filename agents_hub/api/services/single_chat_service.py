"""单聊 Service 层

管理单聊生命周期、索引持久化和消息流式发送。
"""

import dataclasses
import json
import threading
from collections import OrderedDict
from collections.abc import AsyncIterator
from datetime import datetime
from enum import Enum
from pathlib import Path
from uuid import uuid4

from agents_hub.agent_bridge import agent_platform_client
from agents_hub.agent_bridge.models import StreamEvent
from agents_hub.api.schemas.single_chat import (
    CreateSingleChatRequest,
    CreateSingleChatResponse,
    MessageHistoryResponse,
    SessionMessageResponse,
    SingleChatIndex,
    SingleChatListResponse,
    SingleChatResponse,
    SingleChatType,
)
from agents_hub.config import config
from agents_hub.config.types import AgentPlatform
from agents_hub.exceptions import ResourceNotFoundError, ValidationError
from agents_hub.roles import RoleManager
from agents_hub.utils.logger import get_logger
from agents_hub.utils.session_parser import SessionMessage, parse_session_file

logger = get_logger(__name__)


class SingleChatManager:
    """单聊管理器

    全局单例：通过 __new__ + 锁保证整个进程只有一个实例。
    缓存状态（_cache）必须全局唯一，避免多实例导致数据不一致。

    职责：
    - 管理单聊索引（CRUD + 持久化到 index.json）
    - LRU 缓存消息历史
    - 调用 agent_bridge 发送消息（流式）
    """

    _instance: "SingleChatManager | None" = None
    _initialized: bool = False
    _creation_lock: threading.Lock = threading.Lock()

    def __new__(cls, data_path: Path | None = None):
        if cls._instance is None:
            with cls._creation_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, data_path: Path | None = None):
        if SingleChatManager._initialized:
            return
        self._data_path = data_path or Path(config.data_path) / "single_chats"
        self._index_file = self._data_path / "index.json"
        self._index: dict[str, SingleChatIndex] = {}
        self._cache: OrderedDict[str, list[SessionMessage]] = OrderedDict()
        self._max_cached = 15
        self._role_manager = RoleManager()

        # 确保目录存在
        self._data_path.mkdir(parents=True, exist_ok=True)

        # 加载索引
        self._load_index()
        SingleChatManager._initialized = True

    @classmethod
    def _reset_instance(cls):
        """重置单例状态，仅供测试使用"""
        if cls._instance is not None:
            cls._instance._index.clear()
            cls._instance._cache.clear()
        cls._instance = None
        cls._initialized = False

    @staticmethod
    def _resolve_session_path(
        session_id: str, platform: AgentPlatform, work_root: str | None
    ) -> str | None:
        """根据 session_id 和平台查找会话文件路径

        Args:
            session_id: 会话 ID
            platform: 平台类型
            work_root: 角色工作根目录（RoleConfig.work_root）

        Returns:
            会话文件路径字符串，未找到返回 None
        """
        if not work_root:
            return None
        if platform == AgentPlatform.CLAUDE:
            search_dir = Path(work_root) / "projects"
        elif platform == AgentPlatform.CODEX:
            search_dir = Path(work_root) / "sessions"
        else:
            return None  # type: ignore[unreachable]
        if not search_dir.exists():
            return None
        for f in search_dir.rglob(f"*{session_id}*.jsonl"):
            return str(f)
        return None

    def _load_index(self):
        """从文件加载索引"""
        if not self._index_file.exists():
            return
        try:
            with open(self._index_file, encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("single_chats", []):
                    index = SingleChatIndex(**item)
                    self._index[index.single_chat_id] = index
        except (json.JSONDecodeError, OSError, ValueError) as e:
            logger.warning("Failed to load single chat index: %s", e)

    def _save_index(self):
        """保存索引到文件"""
        data = {"single_chats": [idx.model_dump(mode="json") for idx in self._index.values()]}
        with open(self._index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def create_single_chat(
        self, request: CreateSingleChatRequest
    ) -> CreateSingleChatResponse:
        """创建单聊

        Args:
            request: 创建请求

        Returns:
            CreateSingleChatResponse

        Raises:
            ResourceNotFoundError: agent 不存在
            ValidationError: fork/continue 类型缺少 group_chat_id
        """
        single_chat_id = str(uuid4())

        # 验证 agent 存在（RoleNotFoundError 会自然传播到全局异常处理器）
        role = self._role_manager.get_role(request.agent_name)
        role_config = role.get_role_config()

        session_id = None
        session_path = None
        cwd = request.cwd

        # fork 或 continue 类型：从群聊获取 agent 会话信息
        if request.type in (SingleChatType.FORK, SingleChatType.CONTINUE_GROUP_CHAT):
            if not request.group_chat_id:
                raise ValidationError(
                    "fork/continue 类型必须提供 group_chat_id",
                    details={"type": request.type.value},
                )

            from agents_hub.core.orchestration.group_chat_manager import group_chat_manager

            group_chat = await group_chat_manager.load_group_chat(request.group_chat_id)
            agent_info = group_chat.runtime.get_or_create_agent_member_info(request.agent_name)
            if agent_info:
                session_id = agent_info.main_session
                cwd = cwd or agent_info.cwd

            # fork 类型：不继承 session_id（从 fork_from 创建新会话）
            if request.type == SingleChatType.FORK:
                session_id = None

        # continue_group_chat 类型：解析已有 session 的文件路径
        if session_id:
            session_path = self._resolve_session_path(
                session_id, role_config.platform, role_config.work_root
            )

        index = SingleChatIndex(
            single_chat_id=single_chat_id,
            single_chat_name=request.single_chat_name,
            type=request.type,
            agent_name=request.agent_name,
            platform=role_config.platform,
            session_id=session_id,
            session_path=session_path,
            group_chat_id=request.group_chat_id,
            cwd=cwd or str(Path.cwd()),
        )

        self._index[single_chat_id] = index
        self._save_index()

        logger.info(
            "Single chat created: id=%s, agent=%s, type=%s",
            single_chat_id,
            request.agent_name,
            request.type.value,
        )

        return CreateSingleChatResponse(
            single_chat_id=single_chat_id,
            single_chat_name=request.single_chat_name,
            type=request.type,
        )

    def get_single_chat(self, single_chat_id: str) -> SingleChatIndex:
        """获取单聊索引

        Args:
            single_chat_id: 单聊 ID

        Returns:
            SingleChatIndex

        Raises:
            ResourceNotFoundError: 单聊不存在
        """
        if single_chat_id not in self._index:
            raise ResourceNotFoundError(
                f"单聊不存在: {single_chat_id}",
                details={"single_chat_id": single_chat_id},
            )
        return self._index[single_chat_id]

    def get_single_chat_response(self, single_chat_id: str) -> SingleChatResponse:
        """获取单聊详情（响应格式）

        Args:
            single_chat_id: 单聊 ID

        Returns:
            SingleChatResponse

        Raises:
            ResourceNotFoundError: 单聊不存在
        """
        index = self.get_single_chat(single_chat_id)
        return self._to_response(index)

    def list_single_chats(self) -> SingleChatListResponse:
        """列出所有单聊（按 last_active_at 降序）"""
        chats = [self._to_response(idx) for idx in self._index.values()]
        chats.sort(key=lambda x: x.last_active_at, reverse=True)
        return SingleChatListResponse(single_chats=chats)

    def _to_response(self, index: SingleChatIndex) -> SingleChatResponse:
        """转换为响应格式"""
        return SingleChatResponse(
            single_chat_id=index.single_chat_id,
            single_chat_name=index.single_chat_name,
            type=index.type,
            agent_name=index.agent_name,
            platform=index.platform,
            session_id=index.session_id,
            group_chat_id=index.group_chat_id,
            cwd=index.cwd,
            created_at=index.created_at,
            last_active_at=index.last_active_at,
        )

    @staticmethod
    def _serialize_event(event: StreamEvent) -> str:
        """将 StreamEvent 序列化为 JSON 字符串"""

        def _default(obj: object) -> object:
            if isinstance(obj, Enum):
                return obj.value
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        return json.dumps(dataclasses.asdict(event), default=_default, ensure_ascii=False)

    async def send_message_stream(self, single_chat_id: str, content: str) -> AsyncIterator[str]:
        """发送消息（流式）

        Args:
            single_chat_id: 单聊 ID
            content: 消息内容

        Yields:
            StreamEvent: 流式事件

        Raises:
            ResourceNotFoundError: 单聊不存在
        """
        index = self.get_single_chat(single_chat_id)
        role = self._role_manager.get_role(index.agent_name)
        role_config = role.get_role_config()

        fork_from = None
        session_id = index.session_id

        # fork 类型且尚未有 session_id：从群聊获取 fork 源
        if index.type == SingleChatType.FORK and not index.session_id and index.group_chat_id:
            from agents_hub.core.orchestration.group_chat_manager import (
                group_chat_manager,
            )

            group_chat = await group_chat_manager.load_group_chat(index.group_chat_id)
            agent_info = group_chat.runtime.get_or_create_agent_member_info(index.agent_name)
            if agent_info:
                fork_from = agent_info.main_session

        session_updated = False
        async for event in agent_platform_client.execute_stream(
            prompt=content,
            config=role_config,
            session_id=session_id,
            cwd=index.cwd,
            fork_from=fork_from,
        ):
            yield self._serialize_event(event)

            # 首次获取 session_id 时更新索引
            if event.session_id and not index.session_id:
                index.session_id = event.session_id
                session_updated = True

        # 首次获取 session_id 时解析并设置 session_path
        if session_updated and index.session_id:
            index.session_path = self._resolve_session_path(
                index.session_id, index.platform, role_config.work_root
            )

        # 流结束后更新活跃时间和索引
        index.last_active_at = datetime.now().isoformat()
        self._save_index()

        # 清除 LRU 缓存，下次 get_messages 重新加载
        self._cache.pop(single_chat_id, None)

    async def get_messages(self, single_chat_id: str) -> list[SessionMessage]:
        """获取消息历史

        Args:
            single_chat_id: 单聊 ID

        Returns:
            list[SessionMessage]: 消息列表

        Raises:
            ResourceNotFoundError: 单聊不存在
        """
        index = self.get_single_chat(single_chat_id)

        # LRU 缓存命中
        if single_chat_id in self._cache:
            self._cache.move_to_end(single_chat_id)
            return self._cache[single_chat_id]

        if not index.session_path:
            return []

        try:
            session_path = Path(index.session_path)
            messages = parse_session_file(session_path, index.platform)

            # 写入 LRU 缓存
            self._cache[single_chat_id] = messages
            if len(self._cache) > self._max_cached:
                self._cache.popitem(last=False)

            return messages
        except (OSError, ValueError) as e:
            logger.error("Failed to load messages for %s: %s", single_chat_id, e)
            return []

    async def get_messages_response(self, single_chat_id: str) -> MessageHistoryResponse:
        """获取消息历史（响应格式）

        Args:
            single_chat_id: 单聊 ID

        Returns:
            MessageHistoryResponse

        Raises:
            ResourceNotFoundError: 单聊不存在
        """
        messages = await self.get_messages(single_chat_id)
        return MessageHistoryResponse(
            messages=[
                SessionMessageResponse(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    timestamp=m.timestamp,
                    model=m.model,
                )
                for m in messages
            ]
        )


# 全局实例
single_chat_manager = SingleChatManager()
