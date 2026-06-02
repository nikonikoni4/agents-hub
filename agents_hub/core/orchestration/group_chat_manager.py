"""
GroupChatManager 群聊管理器

全局管理所有 GroupChat 实例，提供 call_agent MCP 工具入口。
"""

import threading
from pathlib import Path

from agents_hub.core.communication import AgentCall
from agents_hub.core.context import GroupMetadata
from agents_hub.core.foundation import (
    AgentMessage,
    GroupChatNotFoundError,
    GroupChatType,
    MessageType,
)
from agents_hub.core.foundation.paths import group_chat_paths

from .group_chat import GroupChat
from .team import Team


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

    def get_group_chat(self, group_chat_id: str) -> GroupChat:
        """获取 GroupChat，不存在时抛出 GroupChatNotFoundError"""
        group_chat = self._group_chats.get(group_chat_id)
        if not group_chat:
            raise GroupChatNotFoundError(group_chat_id)
        return group_chat

    async def unregister(self, group_chat_id: str, timeout: float = 10.0):
        """
        注销一个 GroupChat，确保资源安全释放

        此方法会先调用 GroupChat.cleanup() 清理所有资源，
        然后再从注册表中删除引用。

        Args:
            group_chat_id: 群聊 ID
            timeout: 清理超时时间（秒），默认 10 秒

        注意：
        - 如果 group_chat_id 不存在，静默返回（幂等性）
        - 清理超时后会强制取消任务
        """
        group_chat = self._group_chats.get(group_chat_id)
        if group_chat:
            # 先清理资源
            await group_chat.cleanup(timeout=timeout)
            # 再删除引用
            self._group_chats.pop(group_chat_id, None)
            # 清理该群聊的所有 token
            self.unregister_tokens(group_chat_id)

    def register_token(self, token: str, agent_name: str, group_chat_id: str):
        """
        注册一个 token，用于 MCP 工具的身份验证

        Args:
            token: 唯一标识符
            agent_name: Agent 名称
            group_chat_id: 群聊 ID

        线程安全：使用锁保护 token 字典的并发写入
        """
        with self._token_lock:
            self._tokens[token] = (agent_name, group_chat_id)

    def unregister_tokens(self, group_chat_id: str):
        """
        注销指定群聊的所有 token

        Args:
            group_chat_id: 群聊 ID

        注意：
        - 如果 group_chat_id 不存在，静默返回（幂等性）

        线程安全：使用锁保护 token 字典的并发修改
        """
        with self._token_lock:
            # 找出所有属于该群聊的 token
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

    def list_all_group_chats(self, base_path: str = "local_data/teams") -> list[dict]:
        """
        列出所有群聊

        扫描 teams/*/*/group_metadata.json 获取所有群聊信息。

        Args:
            base_path: 群聊数据根目录，默认 "local_data/teams"

        Returns:
            群聊信息列表，每项包含：
            - group_chat_id: 群聊 ID
            - group_chat_name: 群聊名称
            - project_path: 项目路径
            - created_at: 创建时间（ISO 格式字符串）
            - group_type: 群聊类型
            - is_active: 是否在内存中活跃
        """
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
                            "is_active": metadata.group_chat_id in self._group_chats,
                        }
                    )
                except Exception:
                    # 读取失败时跳过该群聊
                    continue

        return group_chats

    async def load_group_chat_from_disk(
        self, group_chat_id: str, project_path: str, team: Team
    ) -> GroupChat:
        """
        从磁盘加载群聊到内存

        1. 读取 group_metadata.json 验证信息
        2. 创建 GroupChat 实例
        3. 调用 GroupChat.load()
        4. 注册到 GroupChatManager

        Args:
            group_chat_id: 群聊 ID
            project_path: 项目路径
            team: 所属 Team 实例

        Returns:
            加载的 GroupChat 实例

        Raises:
            FileNotFoundError: metadata 文件不存在
            ValueError: metadata 验证失败
        """
        # 1. 读取并验证 metadata
        metadata_file = group_chat_paths.metadata_file(group_chat_id, project_path)
        if not metadata_file.exists():
            raise FileNotFoundError(f"群聊元数据文件不存在: {metadata_file}")

        import json

        with open(metadata_file, encoding="utf-8") as f:
            data = json.load(f)

        metadata = GroupMetadata.from_dict(data)

        # 验证 group_chat_id 一致性
        if metadata.group_chat_id != group_chat_id:
            raise ValueError(
                f"metadata 中的 group_chat_id ({metadata.group_chat_id}) "
                f"与参数不一致 ({group_chat_id})"
            )

        # 2. 创建 GroupChat 实例
        group_type = GroupChatType(metadata.group_type)
        group_chat = GroupChat(
            team=team,
            group_type=group_type,
            project_path=project_path,
            group_chat_id=group_chat_id,
        )

        # 3. 加载群聊状态
        await group_chat.load()

        # 4. 注册到 GroupChatManager
        self.register(group_chat_id, group_chat)

        return group_chat

    async def create_group_chat(
        self,
        team: Team,
        group_type: GroupChatType,
        project_path: str,
        group_chat_name: str | None = None,
        group_chat_id: str | None = None,
    ) -> GroupChat:
        """
        创建并启动新群聊

        统一的群聊创建入口，自动处理：
        1. 创建 GroupChat 实例
        2. 调用 start() 启动
        3. 保存 group_metadata.json
        4. 自动注册到 GroupChatManager

        Args:
            team: 所属 Team 实例
            group_type: 群聊类型
            project_path: 项目路径
            group_chat_name: 群聊名称（可选，默认使用 group_chat_id）
            group_chat_id: 群聊 ID（可选，默认自动生成）

        Returns:
            创建的 GroupChat 实例
        """
        from uuid import uuid4

        # 1. 创建 GroupChat 实例
        if group_chat_id is None:
            group_chat_id = str(uuid4())

        group_chat = GroupChat(
            team=team,
            group_type=group_type,
            project_path=project_path,
            group_chat_id=group_chat_id,
        )

        # 2. 启动群聊（会自动保存 metadata）
        await group_chat.start()

        # 3. 如果提供了自定义名称，更新 metadata
        if group_chat_name is not None:
            metadata = await group_chat.group_chat_context.repository.load_group_metadata()
            if metadata:
                metadata.group_chat_name = group_chat_name
                await group_chat.group_chat_context.repository.save_group_metadata(metadata)

        # 4. 注册到 GroupChatManager
        self.register(group_chat_id, group_chat)

        return group_chat


# 全局单例
group_chat_manager = GroupChatManager()


def call_agent(
    group_chat_id: str,
    send_from: str,
    send_to: str,
    content: str,
    need_response: bool,
    timeout_seconds: int | None = None,
) -> str:
    """
    call_agent MCP 工具入口

    Agent 平台（Claude Code / Codex）通过 MCP 调用此函数与别的 agent 对话。

    Args:
        group_chat_id: 群聊 ID
        send_from: 发送者名称
        send_to: 接收者名称
        content: 发送的内容（问题或任务）
        need_response: 是否需要被调用的 agent 回复
        timeout_seconds: 超时阈值（秒）

    Returns:
        call_id 用于查询调用状态
    """
    try:
        # 1. 获取 group chat
        group_chat = group_chat_manager.get_group_chat(group_chat_id)

        # 2. 创建 AgentCall
        call: AgentCall = group_chat.agent_call_manager.create_call(
            send_from=send_from,
            send_to=send_to,
            content=content,
            message_type=MessageType.TASK if need_response else MessageType.NOTIFICATION,
            timeout_seconds=timeout_seconds,
        )

        # 3. 通过 MessageRouter 发送消息
        group_chat.message_router.send_message(
            AgentMessage(
                call_id=call.call_id,
                send_from=call.send_from,
                send_to=call.send_to,
                content=call.content,
                message_type=call.message_type,
            )
        )

        return call.call_id

    except Exception as e:
        # TODO: 需要适配 MCP tool 的错误响应格式
        # 当前返回错误信息字符串，正式版本应使用 to_mcp_response()
        if hasattr(e, "to_mcp_response"):
            return str(e.to_mcp_response())
        return str(e)
