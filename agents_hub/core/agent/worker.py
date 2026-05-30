"""
Worker Agent

团队工作者，执行具体任务。
"""
from agents_hub.core.foundation import AgentMessage
from agents_hub.core.communication import MessageRouter, AgentCallManager
from .base_agent import Agent
class Worker(Agent):
    def __init__(self,role):
        super().__init__(role) 
        pass
    pass