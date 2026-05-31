"""
Communication layer - 通信层

负责消息路由和调用管理，只依赖 foundation 层。
"""

from .agent_call import AgentCall
from .agent_call_manager import AgentCallManager
from .message_router import MessageRouter
from .task import Task, TaskList
from .task_manager import TaskManager

__all__ = [
    "MessageRouter",
    "AgentCall",
    "AgentCallManager",
    "Task",
    "TaskList",
    "TaskManager",
]
