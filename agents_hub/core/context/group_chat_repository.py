"""
群聊持久化层

负责群聊数据的文件读写和并发控制。
"""

import asyncio
import json
import os
from datetime import datetime

import aiofiles

from agents_hub.core.foundation import FileSystemError, group_chat_paths

from .group_chat_session import AgentContextState, AgentSessionInfo, GroupChatSession


class GroupChatRepository:
    """
    群聊持久化层

    职责：
    1. 文件读写（GroupChatSession, agent_member, compact_history）
    2. 并发控制（锁保护文件读写）
    """

    def __init__(self, group_chat_id: str, project_path: str):
        self.group_chat_id = group_chat_id
        self.project_path = project_path  # 保存 project_path 属性

        # 并发控制锁
        self._session_lock = asyncio.Lock()  # 保护 group_chat_session 文件读写
        self._agent_state_lock = asyncio.Lock()  # 保护 agent_member 文件读写
        self._compact_lock = asyncio.Lock()  # 保护 compact_history 文件读写
        self._metadata_lock = asyncio.Lock()  # 保护 group_metadata 文件读写

        # 文件路径（集中管理）
        self.group_chat_session_path = str(group_chat_paths.base_dir(group_chat_id, project_path))
        self.messages_file = str(group_chat_paths.messages_file(group_chat_id, project_path))
        self.session_file = str(group_chat_paths.session_state_file(group_chat_id, project_path))
        self.compact_history_file = str(
            group_chat_paths.compact_history_file(group_chat_id, project_path)
        )
        self.metadata_file = str(group_chat_paths.metadata_file(group_chat_id, project_path))

    # ==================== GroupChatSession 持久化 ====================

    async def load_group_chat_session(self) -> GroupChatSession:
        """
        从文件加载群聊会话（无锁，读操作）

        Returns:
            GroupChatSession: 加载的会话对象
        """
        # 确保目录存在
        os.makedirs(self.group_chat_session_path, exist_ok=True)

        # 如果文件不存在，返回新的会话
        if not os.path.exists(self.messages_file):
            return GroupChatSession(group_chat_id=self.group_chat_id)

        # 读取 jsonl 文件
        messages = []
        meta_data = None

        try:
            async with aiofiles.open(self.messages_file, encoding="utf-8") as f:
                async for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        if data.get("_type") == "meta_data":
                            meta_data = data
                        else:
                            messages.append(data)
        except OSError as e:
            raise FileSystemError(operation="read", path=self.messages_file, reason=str(e)) from e

        # 构建 GroupChatSession
        session = GroupChatSession(group_chat_id=self.group_chat_id)
        session.messages = messages

        if meta_data:
            session.last_compacted_loc = meta_data.get("last_compact_loc", 0)
            if "created_at" in meta_data:
                session.created_at = datetime.fromisoformat(meta_data["created_at"])
            if "updated_at" in meta_data:
                session.updated_at = datetime.fromisoformat(meta_data["updated_at"])
            if "name" in meta_data:
                session.name = meta_data["name"]

        return session

    async def save_group_chat_session(self, session: GroupChatSession):
        """
        保存 GroupChatSession 到文件（加锁）

        Args:
            session: 要保存的会话对象
        """
        async with self._session_lock:
            # 确保目录存在
            os.makedirs(self.group_chat_session_path, exist_ok=True)

            # 更新时间戳
            session.updated_at = datetime.now()

            # 写入 jsonl 文件
            try:
                async with aiofiles.open(self.messages_file, "w", encoding="utf-8") as f:
                    # 写入 meta_data
                    meta_data = {
                        "_type": "meta_data",
                        "last_compact_loc": session.last_compacted_loc,
                        "created_at": session.created_at.isoformat(),
                        "updated_at": session.updated_at.isoformat(),
                        "name": session.name,
                    }
                    await f.write(json.dumps(meta_data, ensure_ascii=False) + "\n")

                    # 写入消息
                    for msg in session.messages:
                        await f.write(json.dumps(msg, ensure_ascii=False) + "\n")
            except OSError as e:
                raise FileSystemError(
                    operation="write", path=self.messages_file, reason=str(e)
                ) from e

    # ==================== Agent Session State 持久化 ====================

    async def load_agent_member(self) -> dict[str, AgentSessionInfo]:
        """
        加载 agent session 状态（无锁，读操作）

        Returns:
            dict: {agent_name: AgentSessionInfo}
        """
        # 确保目录存在
        os.makedirs(self.group_chat_session_path, exist_ok=True)

        # 如果文件不存在，返回空 dict
        if not os.path.exists(self.session_file):
            return {}

        # 读取 session 文件
        try:
            async with aiofiles.open(self.session_file, encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
        except OSError as e:
            raise FileSystemError(operation="read", path=self.session_file, reason=str(e)) from e

        # 转换为 AgentSessionInfo 对象
        result = {}
        for agent_name, session_data in data.items():
            context_state_data = session_data.get("context_state", {})
            main_session = session_data.get("main_session")
            # Convert empty string to None
            if main_session == "":
                main_session = None
            result[agent_name] = AgentSessionInfo(
                main_session=main_session,
                btw_session=session_data.get("btw_session", []),
                context_state=AgentContextState(
                    last_loaded_compact_index=context_state_data.get(
                        "last_loaded_compact_index", 0
                    ),
                    last_loaded_message_index=context_state_data.get(
                        "last_loaded_message_index", 0
                    ),
                ),
                token=session_data.get("token", ""),  # 加载 token 字段
                cwd=session_data.get("cwd", ""),  # 加载 cwd 字段
                use_docker=session_data.get("use_docker", False),  # 加载 use_docker 字段
            )
        return result

    async def save_agent_member(self, state: dict[str, AgentSessionInfo]):
        """
        保存 agent session 状态到文件（加锁）

        Args:
            state: {agent_name: AgentSessionInfo}
        """
        async with self._agent_state_lock:
            # 确保目录存在
            os.makedirs(self.group_chat_session_path, exist_ok=True)

            # 转换为可序列化的字典
            data = {}
            for agent_name, session_info in state.items():
                data[agent_name] = {
                    "main_session": session_info.main_session,
                    "btw_session": session_info.btw_session,
                    "context_state": {
                        "last_loaded_compact_index": session_info.context_state.last_loaded_compact_index,
                        "last_loaded_message_index": session_info.context_state.last_loaded_message_index,
                    },
                    "token": session_info.token,  # 保存 token 字段
                    "cwd": session_info.cwd,  # 保存 cwd 字段
                    "use_docker": session_info.use_docker,  # 保存 use_docker 字段
                }

            # 写入文件
            try:
                async with aiofiles.open(self.session_file, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(data, ensure_ascii=False, indent=2))
            except OSError as e:
                raise FileSystemError(
                    operation="write", path=self.session_file, reason=str(e)
                ) from e

    # ==================== Compact History 持久化 ====================

    async def load_compact_history(self) -> list[dict]:
        """
        加载压缩历史记录（无锁，读操作）

        Returns:
            压缩历史记录列表
        """
        if not os.path.exists(self.compact_history_file):
            return []

        compact_history = []
        try:
            async with aiofiles.open(self.compact_history_file, encoding="utf-8") as f:
                async for line in f:
                    line = line.strip()
                    if line:
                        compact_history.append(json.loads(line))
        except OSError as e:
            raise FileSystemError(
                operation="read", path=self.compact_history_file, reason=str(e)
            ) from e

        return compact_history

    async def save_compact_history(self, history: list[dict]):
        """
        保存压缩历史记录到文件（加锁）

        Args:
            history: 压缩历史记录列表
        """
        async with self._compact_lock:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.compact_history_file), exist_ok=True)

            # 写入 jsonl 文件
            try:
                async with aiofiles.open(self.compact_history_file, "w", encoding="utf-8") as f:
                    for record in history:
                        await f.write(json.dumps(record, ensure_ascii=False) + "\n")
            except OSError as e:
                raise FileSystemError(
                    operation="write", path=self.compact_history_file, reason=str(e)
                ) from e

    # ==================== Group Metadata 持久化 ====================

    async def save_group_metadata(self, metadata):
        """
        保存群聊元数据到 group_metadata.json（加锁）

        Args:
            metadata: GroupMetadata 对象
        """
        async with self._metadata_lock:
            # 确保目录存在
            os.makedirs(self.group_chat_session_path, exist_ok=True)

            try:
                async with aiofiles.open(self.metadata_file, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(metadata.to_dict(), ensure_ascii=False, indent=2))
            except OSError as e:
                raise FileSystemError(
                    operation="write", path=self.metadata_file, reason=str(e)
                ) from e

    async def load_group_metadata(self):
        """
        从文件加载群聊元数据（无锁，读操作）

        Returns:
            GroupMetadata | None: 如果文件不存在返回 None
        """
        if not os.path.exists(self.metadata_file):
            return None

        try:
            async with aiofiles.open(self.metadata_file, encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

                # 动态导入避免循环依赖
                from agents_hub.core.context.group_metadata import GroupMetadata

                return GroupMetadata.from_dict(data)
        except OSError as e:
            raise FileSystemError(operation="read", path=self.metadata_file, reason=str(e)) from e

    # ==================== 资源清理 ====================

    def close(self):
        """
        关闭 Repository，释放资源

        此方法用于资源清理。当前实现使用 asyncio.Lock，
        不需要显式释放，但预留此接口用于未来可能的文件锁等资源。

        可以多次调用（幂等性）。
        """
        # 当前使用 asyncio.Lock，不需要显式释放
        # 如果未来使用文件锁（如 fcntl.flock），在这里释放
        pass
