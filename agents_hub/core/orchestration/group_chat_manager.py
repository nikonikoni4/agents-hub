"""
GroupChatManager GroupChat管理器

全局管理所有 GroupChat 实例，提供 call_agent MCP 工具入口。
"""

import threading
from pathlib import Path

from agents_hub.config import config
from agents_hub.core.context import GroupMetadata
from agents_hub.core.foundation import (
    GroupChatNotFoundError,
    GroupChatType,
)
from agents_hub.core.foundation.paths import group_chat_paths
from agents_hub.utils.logger import get_logger

from .group_chat import GroupChat

logger = get_logger(__name__)


class GroupChatManager:
    """
    管理所有 GroupChat 实例的全局注册表

    线程安全：token 索引操作使用 RLock 保护，确保在 FastMCP HTTP 多线程环境下的正确性。
    """

    def __init__(self):
        self._group_chats: dict[str, GroupChat] = {}
        self._tokens: dict[str, tuple[str, str]] = {}  # token → (agent_name, group_chat_id)
        self._token_lock = threading.RLock()  # 保护 _tokens 字典的并发访问

    def register(self, group_chat_id: str, group_chat: GroupChat):
        """注册一个 GroupChat"""
        if not group_chat_id or not isinstance(group_chat_id, str):
            raise ValueError(f"无效的 group_chat_id: {group_chat_id}")
        if not isinstance(group_chat, GroupChat):
            raise ValueError("无效的 group_chat 类型")
        self._group_chats[group_chat_id] = group_chat
        logger.info("GroupChat 已注册: id=%s", group_chat_id)

    def is_active_group(self, group_chat_id: str) -> bool:
        """检查GroupChat的 agent 是否已激活（run() 任务是否在运行）"""
        group_chat = self._group_chats.get(group_chat_id)
        return group_chat is not None and group_chat._activated

    def get_active_group_info(self, group_chat_id: str) -> dict[str, object] | None:
        """
        获取活动GroupChat信息（从 runtime 查询）

        Args:
            group_chat_id: GroupChat ID

        Returns:
            GroupChat信息字典，如果GroupChat不存在则返回 None
        """
        group_chat = self._group_chats.get(group_chat_id)
        if group_chat is None:
            return None
        return group_chat.runtime.get_info_dict(is_active=self.is_active_group(group_chat_id))

    async def load_group_chat(self, group_chat_id: str) -> GroupChat:
        """获取 GroupChat，优先从内存加载，不存在时从磁盘加载

        Args:
            group_chat_id: GroupChat ID

        Returns:
            GroupChat 实例

        Raises:
            GroupChatNotFoundError: GroupChat不存在（内存和磁盘都没有）
        """
        # 1. 优先从内存获取
        group_chat = self._group_chats.get(group_chat_id)
        if group_chat:
            logger.debug("从内存加载GroupChat: id=%s", group_chat_id)
            return group_chat

        # 2. 从磁盘加载
        logger.debug("内存未命中，从磁盘加载GroupChat: id=%s", group_chat_id)
        try:
            return await self.load_group_chat_from_disk(group_chat_id)
        except FileNotFoundError as e:
            logger.warning("GroupChat不存在: id=%s", group_chat_id)
            raise GroupChatNotFoundError(group_chat_id) from e

    async def activate_group_chat(self, group_chat_id: str) -> None:
        """激活GroupChat：启动 agent.run() 任务

        先从内存或磁盘加载 GroupChat，再调用 activate()。
        已激活时重复调用无副作用。

        Args:
            group_chat_id: GroupChat ID

        Raises:
            GroupChatNotFoundError: GroupChat不存在
        """
        group_chat = await self.load_group_chat(group_chat_id)
        logger.info("激活GroupChat: id=%s", group_chat_id)
        await group_chat.activate()

    async def unregister(self, group_chat_id: str, timeout: float = 10.0):
        """
        注销一个 GroupChat，确保资源安全释放

        此方法会先调用 GroupChat.cleanup() 清理所有资源，
        然后再从注册表中删除引用。

        Args:
            group_chat_id: GroupChat ID
            timeout: 清理超时时间（秒），默认 10 秒

        注意：
        - 如果 group_chat_id 不存在，静默返回（幂等性）
        - 清理超时后会强制取消任务
        """
        group_chat = self._group_chats.get(group_chat_id)
        if group_chat:
            logger.info("注销GroupChat: id=%s", group_chat_id)
            # 先清理资源
            await group_chat.cleanup(timeout=timeout)
            # 再删除引用
            self._group_chats.pop(group_chat_id, None)
            # 清理该GroupChat的所有 token
            self.unregister_tokens(group_chat_id)
            logger.info("GroupChat注销完成: id=%s", group_chat_id)

    def register_token(self, token: str, agent_name: str, group_chat_id: str):
        """
        注册一个 token，用于 MCP 工具的身份验证

        Args:
            token: 唯一标识符
            agent_name: Agent 名称
            group_chat_id: GroupChat ID

        线程安全：使用锁保护 token 字典的并发写入
        """
        with self._token_lock:
            self._tokens[token] = (agent_name, group_chat_id)

    def unregister_tokens(self, group_chat_id: str):
        """
        注销指定GroupChat的所有 token

        Args:
            group_chat_id: GroupChat ID

        注意：
        - 如果 group_chat_id 不存在，静默返回（幂等性）

        线程安全：使用锁保护 token 字典的并发修改
        """
        with self._token_lock:
            # 找出所有属于该GroupChat的 token
            tokens_to_remove = [
                token for token, (_, gid) in self._tokens.items() if gid == group_chat_id
            ]
            # 删除这些 token
            for token in tokens_to_remove:
                self._tokens.pop(token, None)

    def resolve_token(self, token: str) -> tuple[str, str] | None:
        """
        解析 token 为身份信息

        Args:
            token: 唯一标识符

        Returns:
            (agent_name, group_chat_id) 或 None（token 不存在时）

        线程安全：使用锁保护 token 字典的并发读取
        """
        with self._token_lock:
            return self._tokens.get(token)

    def list_all_group_chats(self, base_path: str | None = None) -> list[dict]:
        """
        列出所有GroupChat

        扫描 teams/*/*/group_metadata.json 获取所有GroupChat信息。

        Args:
            base_path: GroupChat数据根目录，默认 config.data_path / "teams"

        Returns:
            GroupChat信息列表，每项包含：
            - group_chat_id: GroupChat ID
            - group_chat_name: GroupChat名称
            - project_path: 项目路径
            - created_at: 创建时间（ISO 格式字符串）
            - group_type: GroupChat类型
            - is_active: 是否在内存中活跃
        """
        if base_path is None:
            base_path = str(config.data_path / "teams")

        base = Path(base_path)
        if not base.exists():
            return []

        group_chats = []

        # 扫描 teams/*/*/group_metadata.json
        for project_dir in base.iterdir():
            if not project_dir.is_dir():
                continue

            for group_dir in project_dir.iterdir():
                if not group_dir.is_dir():
                    continue

                metadata_file = group_dir / "group_metadata.json"
                if not metadata_file.exists():
                    continue

                try:
                    # 读取 metadata
                    import json

                    with open(metadata_file, encoding="utf-8") as f:
                        data = json.load(f)

                    metadata = GroupMetadata.from_dict(data)

                    # 构造返回信息
                    group_chats.append(
                        {
                            "group_chat_id": metadata.group_chat_id,
                            "group_chat_name": metadata.group_chat_name,
                            "project_path": metadata.project_path,
                            "created_at": metadata.created_at.isoformat(),
                            "group_type": metadata.group_type,
                            "is_active": self.is_active_group(metadata.group_chat_id),
                        }
                    )
                except Exception:
                    # 读取失败时跳过该GroupChat
                    continue

        return group_chats

    async def load_group_chat_from_disk(
        self, group_chat_id: str, base_path: str | None = None
    ) -> GroupChat:
        """
        从磁盘加载GroupChat到内存

        只需要 group_chat_id，其他信息从磁盘自动加载：
        1. 扫描 base_path 找到 project_path
        2. 读取 group_metadata.json 验证信息
        3. 从 agent_member.json 读取 team members
        4. 创建 GroupChat 实例
        5. 调用 GroupChat.load()
        6. 注册到 GroupChatManager

        Args:
            group_chat_id: GroupChat ID
            base_path: GroupChat数据根目录，默认 config.data_path / "teams"

        Returns:
            加载的 GroupChat 实例

        Raises:
            FileNotFoundError: GroupChat不存在
            ValueError: metadata 验证失败
        """
        import json

        logger.info("从磁盘加载GroupChat: id=%s", group_chat_id)

        if base_path is None:
            base_path = str(config.data_path / "teams")

        # 1. 查找 project_path
        project_path = group_chat_paths.find_project_path_by_group_chat_id(group_chat_id, base_path)
        if project_path is None:
            raise FileNotFoundError(f"找不到GroupChat {group_chat_id} 对应的项目路径")

        # 2. 读取并验证 metadata
        metadata_file = group_chat_paths.metadata_file(group_chat_id, project_path, base_path)
        if not metadata_file.exists():
            raise FileNotFoundError(f"GroupChat元数据文件不存在: {metadata_file}")

        with open(metadata_file, encoding="utf-8") as f:
            data = json.load(f)

        metadata = GroupMetadata.from_dict(data)

        # 验证 group_chat_id 一致性
        if metadata.group_chat_id != group_chat_id:
            raise ValueError(
                f"metadata 中的 group_chat_id ({metadata.group_chat_id}) "
                f"与参数不一致 ({group_chat_id})"
            )

        # 3. 从 agent_member.json 读取 team members
        agent_member_file = group_chat_paths.agent_member_file_path(
            group_chat_id, project_path, base_path
        )
        if not agent_member_file.exists():
            raise FileNotFoundError(f"agent session 状态文件不存在: {agent_member_file}")

        with open(agent_member_file, encoding="utf-8") as f:
            session_data = json.load(f)

        team_members_name = list(session_data.keys())
        if not team_members_name:
            raise ValueError(f"GroupChat {group_chat_id} 没有团队成员信息")

        # 4. 创建 GroupChat 实例
        group_type = GroupChatType(metadata.group_type)
        group_chat = GroupChat(
            team_members_name=team_members_name,
            group_type=group_type,
            project_path=project_path,
            group_chat_id=group_chat_id,
        )

        # 5. 加载GroupChat状态
        await group_chat.load()

        # 6. 激活GroupChat（启动 agent 任务，标记为活跃）
        await group_chat.activate()

        # 7. 注册到 GroupChatManager
        self.register(group_chat_id, group_chat)

        logger.info("磁盘加载GroupChat完成: id=%s, members=%s", group_chat_id, team_members_name)
        return group_chat

    async def create_group_chat(
        self,
        team_members_name: list[str],
        group_type: GroupChatType,
        project_path: str,
        group_chat_name: str | None = None,
        group_chat_id: str | None = None,
    ) -> GroupChat:
        """
        创建并启动新GroupChat

        统一的GroupChat创建入口，自动处理：
        1. 创建 GroupChat 实例
        2. 调用 start() 启动（自动保存 metadata）
        3. 自动注册到 GroupChatManager

        Args:
            team_members_name: 团队成员角色名列表
            group_type: GroupChat类型
            project_path: 项目路径
            group_chat_name: GroupChat名称（可选，默认使用 group_chat_id）
            group_chat_id: GroupChat ID（可选，默认自动生成）

        Returns:
            创建的 GroupChat 实例
        """
        from uuid import uuid4

        logger.info(
            "创建GroupChat: members=%s, type=%s, project=%s",
            team_members_name,
            group_type,
            project_path,
        )

        # 1. 创建 GroupChat 实例
        if group_chat_id is None:
            group_chat_id = str(uuid4())

        group_chat = GroupChat(
            team_members_name=team_members_name,
            group_type=group_type,
            project_path=project_path,
            group_chat_id=group_chat_id,
            group_chat_name=group_chat_name,
        )

        # 2. 启动GroupChat（会自动保存 metadata）
        await group_chat.start()

        # 4. 注册到 GroupChatManager
        self.register(group_chat_id, group_chat)

        logger.info("GroupChat创建完成: id=%s", group_chat_id)
        return group_chat


# 全局单例
group_chat_manager = GroupChatManager()
