"""
Agent 上下文

为 Agent 每次调用提供上下文。
主要实现对于 GroupChatSession 有选择的作为 AgentContext。
"""
from .group_chat_context import GroupChatContext


class AgentContext:
    """
    Agent 上下文

    TODO: 未实现
    根据注释，应该"有选择的"提供上下文：
    1. 可能需要根据 agent 的角色、任务类型等过滤上下文
    2. 提供方法获取格式化的上下文字符串
    3. 或者直接删除这个类，使用 GroupChatContext.get_agent_context()
    """

    def __init__(self, agent_name: str, group_chat_context: GroupChatContext):
        self.agent_name = agent_name
        self.group_chat_context = group_chat_context
