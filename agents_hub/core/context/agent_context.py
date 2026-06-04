"""
Agent 上下文

为 Agent 每次调用提供上下文。
实现增量加载：只加载未加载的压缩历史和未压缩消息。
"""

import re

from agents_hub.core.foundation import StateError, Tag, wrap_xml

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

        # TODO：
        后续再测试中考虑是否真的需要加载与自己不相干的上下文

        Returns:
            XML 标签包裹的上下文字符串。无任何新内容时返回空串。
        """
        parts: list[str] = []

        # 1. 获取 agent 的加载状态
        agent_session_info = self.group_chat_context.agent_member_info.get(self.agent_name)
        if not agent_session_info:
            last_loaded_compact_index = 0
            last_loaded_message_index = 0
        else:
            last_loaded_compact_index = agent_session_info.context_state.last_loaded_compact_index
            last_loaded_message_index = agent_session_info.context_state.last_loaded_message_index

        # 2. 压缩历史 → <group_chat_history>
        compact_history = await self.group_chat_context.load_compact_history()
        compact_history_xml = await self._build_compact_history_xml(
            compact_history, last_loaded_compact_index
        )
        if compact_history_xml:
            parts.append(compact_history_xml)

        # 3. 未压缩的最新消息 → <recent_messages>
        if self.group_chat_context.group_chat_session is None:
            raise StateError("GroupChatSession 未加载，请先调用 load()")
        new_messages = self._get_filtered_messages(last_loaded_message_index)
        if new_messages:
            msg_lines = [f"[{m['agent_name']}]: {m['content']}" for m in new_messages]
            parts.append(wrap_xml(Tag.RECENT_MESSAGES, "\n".join(msg_lines)))

        # 4. 更新 agent 的加载状态
        await self._update_agent_context_state(
            last_loaded_compact_index=len(compact_history),
            last_loaded_message_index=len(self.group_chat_context.group_chat_session.messages),
        )

        return "\n".join(parts)

    async def _build_compact_history_xml(
        self, compact_history: list[dict], last_loaded_compact_index: int
    ) -> str:
        """
        构建压缩历史的 XML 片段

        同类合并：overall（全体摘要）和 for_you（针对当前 agent 的摘要）各自独立编号。

        Args:
            compact_history: 全量压缩历史列表
            last_loaded_compact_index: 上次加载到的压缩历史索引

        Returns:
            XML 字符串，无新内容时返回空串
        """
        new_compact_history = compact_history[last_loaded_compact_index:]
        if not new_compact_history:
            return ""

        overall_items: list[str] = []
        for_you_items: list[str] = []
        for record in new_compact_history:
            content = record["content"]
            overall_items.append(content["summary"])
            if self.agent_name in content:
                for_you_items.append(content[self.agent_name])

        history_blocks: list[str] = [
            wrap_xml(
                Tag.SUMMARY_OVERALL,
                "\n".join(f"{i}. {s}" for i, s in enumerate(overall_items, start=1)),
            )
        ]
        if for_you_items:
            history_blocks.append(
                wrap_xml(
                    Tag.SUMMARY_FOR_YOU,
                    "\n".join(f"{i}. {s}" for i, s in enumerate(for_you_items, start=1)),
                )
            )
        return wrap_xml(Tag.GROUP_HISTORY, "\n".join(history_blocks))

    def _get_filtered_messages(self, last_loaded_message_index: int) -> list[dict]:
        """
        获取过滤后的群聊消息

        过滤规则：
        1. 排除自己发送的消息（agent_name == self.agent_name）
        2. 排除 @ 自己的消息（content 包含 @{self.agent_name}，精确匹配词边界）

        Args:
            last_loaded_message_index: 上次加载到的消息索引

        Returns:
            过滤后的消息列表
        """
        session = self.group_chat_context.group_chat_session
        assert session is not None
        messages = session.messages
        # 负向前瞻：@name 后不能紧跟 ASCII 字母、数字或下划线
        at_pattern = re.compile(rf"@{re.escape(self.agent_name)}(?![_a-zA-Z0-9])")
        return [
            m
            for m in messages[last_loaded_message_index:]
            if m["agent_name"] != self.agent_name and not at_pattern.search(m["content"])
        ]

    async def _update_agent_context_state(
        self, last_loaded_compact_index: int, last_loaded_message_index: int
    ):
        """
        更新 agent 的上下文加载状态

        Args:
            last_loaded_compact_index: 已加载到第几条压缩历史
            last_loaded_message_index: 已加载到第几条原始消息
        """
        # 如果 agent 不存在，创建新的状态
        if self.agent_name not in self.group_chat_context.agent_member_info:
            from .group_chat_session import AgentContextState, AgentMemberInfo

            self.group_chat_context.agent_member_info[self.agent_name] = AgentMemberInfo(
                main_session="",
                btw_session=[],
                context_state=AgentContextState(
                    last_loaded_compact_index=last_loaded_compact_index,
                    last_loaded_message_index=last_loaded_message_index,
                ),
            )
        else:
            # 更新现有状态
            agent_session_info = self.group_chat_context.agent_member_info[self.agent_name]
            agent_session_info.context_state.last_loaded_compact_index = last_loaded_compact_index
            agent_session_info.context_state.last_loaded_message_index = last_loaded_message_index

        # 保存到文件
        await self.group_chat_context.runtime.update_context_load_state(
            self.agent_name,
            last_loaded_compact_index,
            last_loaded_message_index,
        )
