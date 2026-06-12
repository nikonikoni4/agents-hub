"""压缩相关异常类"""


class AgentBusyError(Exception):
    """Agent 正在执行任务，无法压缩上下文"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        super().__init__(f"Agent {agent_name} 正在执行任务，无法压缩上下文")
