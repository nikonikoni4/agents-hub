"""
群聊运行时 Facade

提供群聊的统一访问接口，管理 State 和 Repository。
"""

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from agents_hub.core.foundation import GroupChatType
from agents_hub.utils.logger import get_logger

from .group_chat_repository import GroupChatRepository
from .group_chat_runtime_state import GroupChatRuntimeState
from .group_chat_session import AgentMemberInfo
from .group_metadata import GroupMetadata

logger = get_logger(__name__)


class GroupChatRuntime:
    """
    群聊运行时 Facade

    职责：
    1. 持有 State（内存状态）和 Repository（持久化层）
    2. 提供查询方法（从内存 State 读取）
    3. 提供命令方法（先更新内存，然后同步持久化）
    4. 持久化失败时设置 error flag 并重新抛出异常
    """

    def __init__(
        self,
        group_chat_id: str,
        project_path: str,
        repository: GroupChatRepository | None = None,
        state: GroupChatRuntimeState | None = None,
        on_change: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        self.group_chat_id = group_chat_id
        self.project_path = project_path
        self.repository = repository or GroupChatRepository(group_chat_id, project_path)
        self.state = state or GroupChatRuntimeState(
            group_chat_id=group_chat_id,
            project_path=project_path,
        )
        self._on_change = on_change

    # ==================== Load ====================

    async def load(self) -> GroupChatRuntimeState:
        """
        从持久化层加载所有状态到内存

        Returns:
            GroupChatRuntimeState: 加载后的状态对象
        """
        self.state.group_chat_session = await self.repository.load_group_chat_session()
        self.state.agent_member_infos = await self.repository.load_agent_member_infos()
        self.state.compact_history = await self.repository.load_compact_history()
        self.state.metadata = await self.repository.load_group_metadata()
        return self.state

    # ==================== Query Methods ====================

    def get_info_dict(self, is_active: bool) -> dict:
        """
        获取群聊信息字典

        Args:
            is_active: 是否活跃

        Returns:
            dict: 群聊信息，包含以下字段：
                - group_chat_id: str, 群聊唯一标识
                - group_chat_name: str, 群聊名称
                - project_path: str, 项目路径
                - group_type: str, 编排模式
                - is_active: bool, 是否活跃
                - last_speaker: str | None, 最后一条消息的发送者（无消息时为 None）
                - last_message: str | None, 最后一条消息内容（无消息时为 None）
                - last_update_time: str | None, 最后一条消息的时间戳（无消息时为 None）
        """
        metadata = self.state.require_metadata()
        info = {
            "group_chat_id": self.group_chat_id,
            "group_chat_name": metadata.group_chat_name,
            "project_path": self.project_path,
            "created_at": metadata.created_at,
            "group_type": metadata.group_type,
            "is_active": is_active,
        }
        session = self.state.group_chat_session
        if session and session.messages:
            last = session.messages[-1]
            info["last_speaker"] = last.get("agent_name")
            info["last_message"] = last.get("content")
            info["last_update_time"] = last.get("timestamp")
        return info

    def get_member_dicts(self) -> list[dict]:
        """
        获取所有成员的信息字典列表

        Returns:
            list[dict]: 成员信息列表
        """
        members = []
        for agent_name, agent_member_info in self.state.agent_member_infos.items():
            members.append(
                {
                    "name": agent_name,
                    "main_session": agent_member_info.main_session,
                    "btw_session": agent_member_info.btw_session,
                    "cwd": agent_member_info.cwd,
                    "use_docker": agent_member_info.use_docker,
                    "status": agent_member_info.status,
                    "context_window": agent_member_info.context_window,
                }
            )
        return members

    def get_message_dicts(self, limit: int = 30, before: str | None = None) -> list[dict]:
        """
        获取消息字典列表（支持游标分页，返回最新消息）

        Args:
            limit: 返回的最大消息数
            before: 游标时间戳，返回此时间之前的消息（严格小于）

        Returns:
            list[dict]: 消息列表，字段映射 agent_name -> speaker
        """
        session = self.state.require_session()

        if before is not None:
            candidates = [msg for msg in session.messages if msg.get("timestamp", "") < before]
        else:
            candidates = session.messages

        # 取末尾 limit 条（最新的）
        start = max(0, len(candidates) - limit)
        messages = candidates[start:]

        # 映射 agent_name -> speaker，并包含所有可选字段
        result = []
        for msg in messages:
            item = {
                "id": msg.get("id"),
                "speaker": msg["agent_name"],
                "content": msg["content"],
                "timestamp": msg.get("timestamp", ""),
                "platform": msg.get("platform", ""),
            }
            # 添加可选字段（如果存在）
            if "cwd" in msg:
                item["cwd"] = msg["cwd"]
            if "modified_files" in msg:
                item["modified_files"] = msg["modified_files"]
            if "git_diff_range" in msg:
                item["git_diff_range"] = msg["git_diff_range"]
            if "permission_request" in msg:
                item["permission_request"] = msg["permission_request"]
            if "web_preview" in msg:
                item["web_preview"] = msg["web_preview"]
            if "files" in msg:
                item["files"] = msg["files"]
            result.append(item)
        return result

    def get_or_create_agent_member_info(self, agent_name: str) -> AgentMemberInfo:
        """
        获取或创建 Agent 会话信息

        Args:
            agent_name: Agent 名称

        Returns:
            AgentMemberInfo: Agent 会话信息
        """
        if agent_name not in self.state.agent_member_infos:
            self.state.agent_member_infos[agent_name] = AgentMemberInfo(cwd=self.project_path)
        return self.state.agent_member_infos[agent_name]

    def get_agent_names(self) -> list[str]:
        """
        获取所有 Agent 名称

        Returns:
            list[str]: Agent 名称列表
        """
        return list(self.state.agent_member_infos.keys())

    async def load_compact_history(self) -> list[dict]:
        """
        加载压缩历史记录

        Returns:
            压缩历史记录列表
        """
        return self.state.compact_history

    def get_project_path(self) -> str:
        """
        获取项目路径

        Returns:
            str: 项目路径
        """
        return self.project_path

    # ==================== Command Methods ====================

    async def initialize_metadata(
        self,
        group_chat_name: str,
        group_type: GroupChatType,
        created_at: datetime | None = None,
    ) -> GroupMetadata:
        """
        初始化群聊元数据

        Args:
            group_chat_name: 群聊名称
            group_type: 群聊类型
            created_at: 创建时间（可选）

        Returns:
            GroupMetadata: 创建的元数据对象
        """
        metadata = GroupMetadata(
            group_chat_id=self.group_chat_id,
            group_chat_name=group_chat_name,
            project_path=self.project_path,
            created_at=created_at or datetime.now(),
            group_type=group_type.value,
        )
        self.state.metadata = metadata
        await self._persist(lambda: self.repository.save_group_metadata(metadata))
        return metadata

    async def set_agent_token_and_default_cwd(self, agent_name: str, token: str) -> AgentMemberInfo:
        """
        设置 Agent 的 token 和默认工作目录

        Args:
            agent_name: Agent 名称
            token: Agent token

        Returns:
            AgentMemberInfo: 更新后的会话信息
        """
        agent_member_info = self.get_or_create_agent_member_info(agent_name)
        agent_member_info.token = token
        agent_member_info.cwd = self.project_path
        await self._persist(
            lambda: self.repository.save_agent_member(self.state.agent_member_infos)
        )
        return agent_member_info

    async def set_agent_use_docker(self, agent_name: str, use_docker: bool) -> AgentMemberInfo:
        """
        设置 Agent 是否使用 Docker

        Args:
            agent_name: Agent 名称
            use_docker: 是否使用 Docker

        Returns:
            AgentMemberInfo: 更新后的会话信息
        """
        agent_member_info = self.get_or_create_agent_member_info(agent_name)
        agent_member_info.use_docker = use_docker
        await self._persist(
            lambda: self.repository.save_agent_member(self.state.agent_member_infos)
        )
        return agent_member_info

    async def update_context_load_state(
        self, agent_name: str, compact_index: int, message_index: int
    ) -> AgentMemberInfo:
        """
        更新 Agent 的上下文加载状态

        Args:
            agent_name: Agent 名称
            compact_index: 已加载的压缩历史索引
            message_index: 已加载的消息索引

        Returns:
            AgentMemberInfo: 更新后的会话信息
        """
        agent_member_info = self.get_or_create_agent_member_info(agent_name)
        agent_member_info.context_state.last_loaded_compact_index = compact_index
        agent_member_info.context_state.last_loaded_message_index = message_index
        await self._persist(
            lambda: self.repository.save_agent_member(self.state.agent_member_infos)
        )
        return agent_member_info

    async def add_message(self, agent_result) -> None:
        """
        添加消息到群聊历史

        Args:
            agent_result: Agent 执行结果
        """
        session = self.state.require_session()
        session.add_message(agent_result)
        current_session = self.state.require_session()
        if session.messages is not current_session.messages:
            logger.warning("群聊 message 引用不一致: session=%s", id(session))
        await self._persist(lambda: self.repository.save_group_chat_session(session))

    async def update_message_field(self, message_id: int, field_path: str, value: Any) -> bool:
        """
        更新消息中的指定字段并持久化

        Args:
            message_id: 消息 ID
            field_path: 字段路径（如 "permission_request.status"）
            value: 新值

        Returns:
            bool: 是否找到并更新了消息
        """
        session = self.state.require_session()
        for msg in session.messages:
            if msg.get("id") == message_id:
                parts = field_path.split(".")
                target = msg
                for part in parts[:-1]:
                    target = target.setdefault(part, {})
                target[parts[-1]] = value
                await self._persist(lambda: self.repository.save_group_chat_session(session))
                return True
        return False

    async def append_compact_record_and_mark_compacted(self, compact_record: dict) -> None:
        """
        追加压缩记录并标记压缩位置

        Args:
            compact_record: 压缩记录
        """
        session = self.state.require_session()
        self.state.compact_history.append(compact_record)
        session.last_compacted_loc = len(session.messages)

        # 保存两个文件
        await self._persist(
            lambda: self.repository.save_compact_history(self.state.compact_history)
        )
        await self._persist(lambda: self.repository.save_group_chat_session(session))

    async def update_agent_member_info_from_result(self, agent_result) -> AgentMemberInfo:
        """
        根据 Agent 执行结果更新会话信息

        Args:
            agent_result: Agent 执行结果（包含 agent_name, session_id）

        Returns:
            AgentMemberInfo: 更新后的会话信息
        """
        agent_member_info = self.get_or_create_agent_member_info(agent_result.agent_name)

        # 如果没有 main_session，设置为当前 session_id
        if not agent_member_info.main_session:
            agent_member_info.main_session = agent_result.session_id
        # 如果 session_id 不同且不在 btw_session 中，追加到 btw_session
        elif (
            agent_result.session_id != agent_member_info.main_session
            and agent_result.session_id not in agent_member_info.btw_session
        ):
            agent_member_info.btw_session.append(agent_result.session_id)

        await self._persist(
            lambda: self.repository.save_agent_member(self.state.agent_member_infos)
        )
        await self._notify_change()
        return agent_member_info

    async def update_agent_context_window(
        self, agent_name: str, context_window: int
    ) -> AgentMemberInfo:
        """
        更新 Agent 的 context_window 并持久化

        Args:
            agent_name: Agent 名称
            context_window: 上下文窗口大小（input_tokens/1000 取整）

        Returns:
            AgentMemberInfo: 更新后的会话信息
        """
        agent_member_info = self.get_or_create_agent_member_info(agent_name)
        old_value = agent_member_info.context_window
        agent_member_info.context_window = context_window
        logger.info(
            "[Runtime] update_context_window: agent=%s, old=%d, new=%d",
            agent_name,
            old_value,
            context_window,
        )
        await self._persist(
            lambda: self.repository.save_agent_member(self.state.agent_member_infos)
        )
        await self._notify_change()
        return agent_member_info

    async def update_agent_status(self, agent_name: str, status: str) -> AgentMemberInfo:
        """
        更新 Agent 的 status 并持久化

        Args:
            agent_name: Agent 名称
            status: 状态值（idle/busy/chatting）

        Returns:
            AgentMemberInfo: 更新后的会话信息
        """
        agent_member_info = self.get_or_create_agent_member_info(agent_name)
        agent_member_info.status = status
        await self._persist(
            lambda: self.repository.save_agent_member(self.state.agent_member_infos)
        )
        await self._notify_change()
        return agent_member_info

    def get_agent_context(self) -> list[dict]:
        """
        获取所有 Agent 的 context_window

        Returns:
            list[dict]: Agent 上下文信息列表，每项包含 name 和 context_window
        """
        return [
            {"name": name, "context_window": info.context_window}
            for name, info in self.state.agent_member_infos.items()
        ]

    def get_agent_status(self) -> list[dict]:
        """
        获取所有 Agent 的 status

        Returns:
            list[dict]: Agent 状态信息列表，每项包含 name 和 status
        """
        return [
            {"name": name, "status": info.status}
            for name, info in self.state.agent_member_infos.items()
        ]

    # ==================== Persistence Helper ====================

    async def _notify_change(self) -> None:
        """通知外部状态变更（通过 on_change 回调）"""
        if self._on_change:
            try:
                await self._on_change(self.group_chat_id)
            except Exception:
                logger.warning("on_change 回调失败", exc_info=True)

    async def _persist(self, save_call) -> None:
        """
        持久化辅助方法

        Args:
            save_call: 持久化调用（async callable）
        """
        try:
            await save_call()
            self.state.persistence_error = None
        except Exception as e:
            self.state.persistence_error = str(e)
            raise

    # ==================== Resource Cleanup ====================

    def close(self) -> None:
        """关闭 Runtime，释放资源"""
        self.repository.close()
