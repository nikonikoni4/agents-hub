"""
GroupChatManager 群聊管理器

全局管理所有 GroupChat 实例，提供 call_agent MCP 工具入口。
"""
from agents_hub.core.foundation import (
    AgentMessage,
    MessageType,
    GroupChatNotFoundError,
)
from agents_hub.core.communication import AgentCall

from .group_chat import GroupChat


class GroupChatManager:
    """管理所有 GroupChat 实例的全局注册表"""

    def __init__(self):
        self._group_chats: dict[str, GroupChat] = {}

    def register(self, group_chat_id: str, group_chat: GroupChat):
        """注册一个 GroupChat"""
        if not group_chat_id or not isinstance(group_chat_id, str):
            raise ValueError(f"无效的 group_chat_id: {group_chat_id}")
        if not isinstance(group_chat, GroupChat):
            raise ValueError(f"无效的 group_chat 类型")
        self._group_chats[group_chat_id] = group_chat

    def get_group_chat(self, group_chat_id: str) -> GroupChat:
        """获取 GroupChat，不存在时抛出 GroupChatNotFoundError"""
        group_chat = self._group_chats.get(group_chat_id)
        if not group_chat:
            raise GroupChatNotFoundError(group_chat_id)
        return group_chat

    def unregister(self, group_chat_id: str):
        """注销一个 GroupChat"""
        self._group_chats.pop(group_chat_id, None)


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
        if hasattr(e, 'to_mcp_response'):
            return str(e.to_mcp_response())
        return str(e)
