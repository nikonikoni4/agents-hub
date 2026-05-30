"""
Agent 基类

所有 Agent 的基类，包含消息处理、执行逻辑。
"""
from abc import ABC, abstractmethod
from typing import Optional

from agents_hub.core.foundation import AgentMessage, MessageType
from agents_hub.core.communication import MessageRouter, AgentCallManager, AgentCall


class Agent(ABC):
    """
    Agent 基类

    职责：
    1. 接收和处理消息
    2. 执行任务
    3. 发送消息给其他 Agent
    4. 管理自己的调用状态
    """

    def __init__(
        self,
        name: str,
        message_router: MessageRouter,
        agent_call_manager: AgentCallManager
    ):
        """
        初始化 Agent

        Args:
            name: Agent 名称
            message_router: 消息路由器
            agent_call_manager: 调用管理器
        """
        self.name = name
        self.message_router = message_router
        self.agent_call_manager = agent_call_manager

    async def receive_message(self, message: AgentMessage) -> Optional[str]:
        """
        接收消息并处理

        Args:
            message: 接收到的消息

        Returns:
            处理结果（如果需要回复）
        """
        # 根据消息类型分发处理
        if message.message_type == MessageType.TASK:
            return await self.handle_task(message)
        elif message.message_type == MessageType.NOTIFICATION:
            await self.handle_notification(message)
            return None
        else:
            return None

    @abstractmethod
    async def handle_task(self, message: AgentMessage) -> str:
        """
        处理任务消息

        Args:
            message: 任务消息

        Returns:
            任务执行结果
        """
        pass

    async def handle_notification(self, message: AgentMessage):
        """
        处理通知消息

        Args:
            message: 通知消息
        """
        # 默认实现：记录日志
        print(f"[{self.name}] 收到通知: {message.content}")

    async def send_message(
        self,
        to_agent: str,
        content: str,
        message_type: MessageType = MessageType.TASK
    ) -> str:
        """
        发送消息给其他 Agent

        Args:
            to_agent: 目标 Agent 名称
            content: 消息内容
            message_type: 消息类型

        Returns:
            消息 ID
        """
        message = AgentMessage(
            from_agent=self.name,
            to_agent=to_agent,
            content=content,
            message_type=message_type
        )
        return await self.message_router.send_message(message)

    async def execute(self, task: str) -> str:
        """
        执行任务（调用 Agent 平台）

        Args:
            task: 任务描述

        Returns:
            执行结果
        """
        # 创建调用记录
        call = await self.agent_call_manager.create_call(
            agent_name=self.name,
            task=task
        )

        try:
            # 调用 Agent 平台执行任务
            result = await self._execute_on_platform(task, call.call_id)

            # 更新调用状态为完成
            await self.agent_call_manager.complete_call(call.call_id, result)

            return result
        except Exception as e:
            # 更新调用状态为失败
            await self.agent_call_manager.fail_call(call.call_id, str(e))
            raise

    @abstractmethod
    async def _execute_on_platform(self, task: str, call_id: str) -> str:
        """
        在 Agent 平台上执行任务（子类实现）

        Args:
            task: 任务描述
            call_id: 调用 ID

        Returns:
            执行结果
        """
        pass
