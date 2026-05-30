"""
Agent 上下文

为 Agent 每次调用提供上下文。
实现增量加载：只加载未加载的压缩历史和未压缩消息。
"""
from .group_chat_context import GroupChatContext


class AgentContext:
    """
    Agent 上下文

    职责：
    1. 为 Agent 提供增量加载的上下文
    2. 只加载该 Agent 未加载过的压缩历史和未压缩消息
    3. 更新 Agent 的上下文加载状态
    """

    def __init__(self, agent_name: str, group_chat_context: GroupChatContext):
        self.agent_name = agent_name
        self.group_chat_context = group_chat_context

    async def get_context(self) -> str:
        """
        获取 Agent 的增量上下文

        逻辑：
        1. 加载未加载的压缩历史（从 last_loaded_compact_index 到最新）
        2. 加载未加载的消息（从 last_loaded_message_index 到最新）

        标志位自动判断是否需要加载：
        - 如果没有新的压缩历史，compact_history[last_loaded_compact_index:] 返回空列表
        - 如果没有新的消息，messages[last_loaded_message_index:] 返回空列表

        Returns:
            格式化的上下文字符串
        """
        context_parts = []

        # 1. 获取 agent 的加载状态
        agent_session_info = self.group_chat_context.agent_session_id.get(self.agent_name)
        if not agent_session_info:
            # 如果 agent 没有状态记录，说明是第一次加载
            last_loaded_compact_index = 0
            last_loaded_message_index = 0
        else:
            last_loaded_compact_index = agent_session_info.context_state.last_loaded_compact_index
            last_loaded_message_index = agent_session_info.context_state.last_loaded_message_index

        # 2. 加载未加载的压缩历史
        compact_history = await self.group_chat_context.load_compact_history()
        new_compact_history = compact_history[last_loaded_compact_index:]

        if new_compact_history:
            context_parts.append("=== 历史消息摘要 ===")
            for record in new_compact_history:
                content = record['content']
                context_parts.append(f"\n[总体]: {content['summary']}")
                if self.agent_name in content:
                    context_parts.append(f"[针对你]: {content[self.agent_name]}")

        # 3. 加载未加载的消息
        new_messages = self.group_chat_context.group_chat_session.messages[last_loaded_message_index:]
        if new_messages:
            context_parts.append("\n=== 最新消息 ===")
            for msg in new_messages:
                context_parts.append(f"[{msg['agent_name']}]: {msg['content']}")

        # 4. 更新 agent 的加载状态
        await self._update_agent_context_state(
            last_loaded_compact_index=len(compact_history),
            last_loaded_message_index=len(self.group_chat_context.group_chat_session.messages)
        )

        return "\n".join(context_parts)

    async def _update_agent_context_state(self, last_loaded_compact_index: int, last_loaded_message_index: int):
        """
        更新 agent 的上下文加载状态

        Args:
            last_loaded_compact_index: 已加载到第几条压缩历史
            last_loaded_message_index: 已加载到第几条原始消息
        """
        # 如果 agent 不存在，创建新的状态
        if self.agent_name not in self.group_chat_context.agent_session_id:
            from .group_chat_session import AgentSessionInfo, AgentContextState
            self.group_chat_context.agent_session_id[self.agent_name] = AgentSessionInfo(
                main_session="",
                btw_session=[],
                context_state=AgentContextState(
                    last_loaded_compact_index=last_loaded_compact_index,
                    last_loaded_message_index=last_loaded_message_index
                )
            )
        else:
            # 更新现有状态
            agent_session_info = self.group_chat_context.agent_session_id[self.agent_name]
            agent_session_info.context_state.last_loaded_compact_index = last_loaded_compact_index
            agent_session_info.context_state.last_loaded_message_index = last_loaded_message_index

        # 保存到文件
        await self.group_chat_context.repository.save_agent_session_state(
            self.group_chat_context.agent_session_id
        )

