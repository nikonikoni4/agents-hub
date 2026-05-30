"""
Worker Agent

团队工作者，执行具体任务。
"""
from agents_hub.core.foundation import AgentMessage
from agents_hub.core.communication import MessageRouter, AgentCallManager
from .base_agent import Agent


class Worker(Agent):
    """
    Worker Agent

    职责：
    1. 接收 Manager 分配的任务
    2. 执行具体任务
    3. 返回执行结果
    """

    def __init__(
        self,
        name: str,
        message_router: MessageRouter,
        agent_call_manager: AgentCallManager,
        manager: str
    ):
        """
        初始化 Worker

        Args:
            name: Worker 名称
            message_router: 消息路由器
            agent_call_manager: 调用管理器
            manager: Manager 名称
        """
        super().__init__(name, message_router, agent_call_manager)
        self.manager = manager

    async def handle_task(self, message: AgentMessage) -> str:
        """
        处理任务消息

        Worker 的任务处理流程：
        1. 接收任务
        2. 执行任务
        3. 返回结果给 Manager

        Args:
            message: 任务消息

        Returns:
            任务执行结果
        """
        task = message.content

        # 执行任务
        result = await self.execute(task)

        # 如果任务来自 Manager，发送结果给 Manager
        if message.from_agent == self.manager:
            await self.send_message(self.manager, result)

        return result

    async def _execute_on_platform(self, task: str, call_id: str) -> str:
        """
        在 Agent 平台上执行任务

        Worker 需要调用 agent_bridge 来执行任务

        Args:
            task: 任务描述
            call_id: 调用 ID

        Returns:
            执行结果
        """
        # TODO: 调用 agent_bridge 执行任务
        # 这里需要依赖 agent_bridge 层，但会造成循环依赖
        # 解决方案：通过依赖注入的方式传入 agent_bridge
        raise NotImplementedError(
            "Worker._execute_on_platform 需要依赖 agent_bridge，"
            "需要通过依赖注入的方式传入。"
        )
