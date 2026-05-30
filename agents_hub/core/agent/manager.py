"""
Manager Agent

团队管理者，负责任务分配和协调。
"""

from agents_hub.core.communication import AgentCallManager, MessageRouter
from agents_hub.core.context import GroupChatContext
from agents_hub.core.foundation import Role

from .base_agent import Agent


class Manager(Agent):
    def __init__(
        self,
        role: Role,
        group_chat_context: GroupChatContext,
        agent_call_manager: AgentCallManager,
        message_router: MessageRouter,
    ):
        super().__init__(role, group_chat_context, agent_call_manager, message_router)
