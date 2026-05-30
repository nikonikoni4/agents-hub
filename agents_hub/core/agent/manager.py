"""
Manager Agent

团队管理者，负责任务分配和协调。
"""
from agents_hub.core.foundation import AgentMessage
from agents_hub.core.communication import MessageRouter, AgentCallManager
from .base_agent import Agent
from agents_hub.roles import RoleManager
class Manager(Agent):
    def __init__(self,role):
        super().__init__(role) 
        pass
    pass