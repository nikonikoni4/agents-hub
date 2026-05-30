"""
Manager Agent

团队管理者，负责任务分配和协调。
"""
from agents_hub.core.foundation import AgentMessage
from agents_hub.core.communication import MessageRouter, AgentCallManager
from .base_agent import Agent


class Manager(Agent):
    """
    Manager Agent

    职责：
    1. 接收用户任务
    2. 分解任务并分配给 Worker
    3. 协调多个 Worker 的工作
    4. 汇总结果并返回
    """

    def __init__(
        self,
        name: str,
        message_router: MessageRouter,
        agent_call_manager: AgentCallManager,
        workers: list[str]
    ):
        """
        初始化 Manager

        Args:
            name: Manager 名称
            message_router: 消息路由器
            agent_call_manager: 调用管理器
            workers: Worker 名称列表
        """
        super().__init__(name, message_router, agent_call_manager)
        self.workers = workers

    async def handle_task(self, message: AgentMessage) -> str:
        """
        处理任务消息

        Manager 的任务处理流程：
        1. 分析任务
        2. 分解任务
        3. 分配给 Worker
        4. 等待 Worker 完成
        5. 汇总结果

        Args:
            message: 任务消息

        Returns:
            任务执行结果
        """
        task = message.content

        # 1. 调用 Agent 平台分析任务
        analysis_prompt = f"""你是一个团队管理者。请分析以下任务，并决定如何分配给团队成员。

任务：{task}

团队成员：{', '.join(self.workers)}

请输出：
1. 任务分解（如果需要）
2. 分配方案（哪个成员负责什么）
"""
        analysis_result = await self.execute(analysis_prompt)

        # 2. 根据分析结果分配任务给 Worker
        # TODO: 解析 analysis_result，提取分配方案
        # 这里暂时简化：将任务发送给第一个 Worker
        if self.workers:
            worker_name = self.workers[0]
            await self.send_message(worker_name, task)

        return analysis_result

    async def _execute_on_platform(self, task: str, call_id: str) -> str:
        """
        在 Agent 平台上执行任务

        Manager 需要调用 agent_bridge 来执行任务

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
            "Manager._execute_on_platform 需要依赖 agent_bridge，"
            "需要通过依赖注入的方式传入。"
        )
