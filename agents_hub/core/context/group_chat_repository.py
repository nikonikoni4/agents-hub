"""
群聊持久化层

负责群聊数据的文件读写和并发控制。
"""
import asyncio
import json
import os
import re
from datetime import datetime

from agents_hub.core.foundation import LOCAL_DATA_PATH, FileSystemError
from .group_chat_session import GroupChatSession, AgentSessionInfo, AgentContextState


class GroupChatRepository:
    """
    群聊持久化层

    职责：
    1. 文件读写（GroupChatSession, agent_session_state, compact_history）
    2. 并发控制（锁保护文件读写）
    """

    def __init__(self, group_chat_id: str, project_path: str):
        self.group_chat_id = group_chat_id

        # 并发控制锁
        self._session_lock = asyncio.Lock()  # 保护 group_chat_session 文件读写
        self._agent_state_lock = asyncio.Lock()  # 保护 agent_session_state 文件读写
        self._compact_lock = asyncio.Lock()  # 保护 compact_history 文件读写

        # 文件路径
        sanitized_path = self._sanitize_project_path(project_path)
        self.group_chat_session_path = f"{LOCAL_DATA_PATH}/teams/{sanitized_path}/{group_chat_id}"
        self.messages_file = f"{self.group_chat_session_path}/{group_chat_id}.jsonl"
        self.session_file = f"{self.group_chat_session_path}/agent_session_state.json"
        self.compact_history_file = f"{self.group_chat_session_path}/memory/compact_history.jsonl"

    # ==================== 工具方法 ====================

    @staticmethod
    def _sanitize_project_path(project_path: str) -> str:
        """
        将 project_path 转换为安全的存储路径名称。
        将 / : \\ 等 Windows 文件夹命名非法字符转化为 -

        Args:
            project_path: 原始项目路径字符串

        Returns:
            转换后的安全路径名称
        """
        # 将 / : \\ 替换为 -
        sanitized = re.sub(r'[/:\\]', '-', project_path)
        # 移除开头和结尾的 -
        sanitized = sanitized.strip('-')
        # 将连续的 - 合并为单个 -
        sanitized = re.sub(r'-+', '-', sanitized)
        return sanitized

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
            with open(self.messages_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        if data.get('_type') == 'meta_data':
                            meta_data = data
                        else:
                            messages.append(data)
        except OSError as e:
            raise FileSystemError(
                operation="read",
                path=self.messages_file,
                reason=str(e)
            )

        # 构建 GroupChatSession
        session = GroupChatSession(group_chat_id=self.group_chat_id)
        session.messages = messages

        if meta_data:
            session.last_compacted_loc = meta_data.get('last_compact_loc', 0)
            if 'created_at' in meta_data:
                session.created_at = datetime.fromisoformat(meta_data['created_at'])
            if 'updated_at' in meta_data:
                session.updated_at = datetime.fromisoformat(meta_data['updated_at'])
            if 'name' in meta_data:
                session.name = meta_data['name']

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
                with open(self.messages_file, 'w', encoding='utf-8') as f:
                    # 写入 meta_data
                    meta_data = {
                        '_type': 'meta_data',
                        'last_compact_loc': session.last_compacted_loc,
                        'created_at': session.created_at.isoformat(),
                        'updated_at': session.updated_at.isoformat(),
                        'name': session.name
                    }
                    f.write(json.dumps(meta_data, ensure_ascii=False) + '\n')

                    # 写入消息
                    for msg in session.messages:
                        f.write(json.dumps(msg, ensure_ascii=False) + '\n')
            except OSError as e:
                raise FileSystemError(
                    operation="write",
                    path=self.messages_file,
                    reason=str(e)
                )

    # ==================== Agent Session State 持久化 ====================

    async def load_agent_session_state(self) -> dict[str, AgentSessionInfo]:
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
            with open(self.session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except OSError as e:
            raise FileSystemError(
                operation="read",
                path=self.session_file,
                reason=str(e)
            )

        # 转换为 AgentSessionInfo 对象
        result = {}
        for agent_name, session_data in data.items():
            context_state_data = session_data.get('context_state', {})
            result[agent_name] = AgentSessionInfo(
                main_session=session_data.get('main_session', ''),
                btw_session=session_data.get('btw_session', []),
                context_state=AgentContextState(
                    last_loaded_compact_index=context_state_data.get('last_loaded_compact_index', 0),
                    last_loaded_message_index=context_state_data.get('last_loaded_message_index', 0)
                )
            )
        return result

    async def save_agent_session_state(self, state: dict[str, AgentSessionInfo]):
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
                    'main_session': session_info.main_session,
                    'btw_session': session_info.btw_session,
                    'context_state': {
                        'last_loaded_compact_index': session_info.context_state.last_loaded_compact_index,
                        'last_loaded_message_index': session_info.context_state.last_loaded_message_index
                    }
                }

            # 写入文件
            try:
                with open(self.session_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except OSError as e:
                raise FileSystemError(
                    operation="write",
                    path=self.session_file,
                    reason=str(e)
                )

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
            with open(self.compact_history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        compact_history.append(json.loads(line))
        except OSError as e:
            raise FileSystemError(
                operation="read",
                path=self.compact_history_file,
                reason=str(e)
            )

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
                with open(self.compact_history_file, 'w', encoding='utf-8') as f:
                    for record in history:
                        f.write(json.dumps(record, ensure_ascii=False) + '\n')
            except OSError as e:
                raise FileSystemError(
                    operation="write",
                    path=self.compact_history_file,
                    reason=str(e)
                )
