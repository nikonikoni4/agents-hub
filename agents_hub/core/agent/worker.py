"""
Worker Agent

团队工作者，执行具体任务。
"""
from agents_hub.core.foundation import Role
from agents_hub.core.communication import AgentCallManager
from agents_hub.core.context import GroupChatContext
from .base_agent import Agent


class Worker(Agent):
    def __init__(self, role: Role, group_chat_context: GroupChatContext, agent_call_manager: AgentCallManager):
        super().__init__(role, group_chat_context, agent_call_manager)