"""
GroupChatManager 群聊管理器

全局管理所有 GroupChat 实例，提供 call_agent MCP 工具入口。
"""

import threading

from agents_hub.core.communication import AgentCall
from agents_hub.core.foundation import (
    AgentMessage,
    GroupChatNotFoundError,
    MessageType,
)

from .group_chat import GroupChat


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
