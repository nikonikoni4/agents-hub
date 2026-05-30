"""
消息路由器

负责 Agent 之间的消息投递，管理每个 Agent 的私有消息队列。
"""

import asyncio

from agents_hub.core.foundation import (
    AgentMessage,
    AgentNotFoundError,
    InvalidMessageError,
    MessageDeliveryError,
)


class MessageRouter:
    """用于 Agent 之间、系统(user)与 Agent 之间发送消息"""

    def __init__(self):
        self._agents_queue: dict[str, asyncio.Queue] = {}

    def register(self, name: str, queue: asyncio.Queue):
        """
        注册 Agent 的消息队列

        Args:
            name: Agent 名称
            queue: Agent 的私有消息队列
        """
        self._agents_queue[name] = queue

    def unregister(self, name: str):
        """
        注销 Agent 的消息队列

        Args:
            name: Agent 名称
        """
        self._agents_queue.pop(name, None)

    def send_message(self, message: AgentMessage):
        """
        发送消息到目标 Agent 的队列

        Args:
            message: 要发送的消息

        Raises:
            InvalidMessageError: 消息格式错误
            AgentNotFoundError: Agent 不存在
            MessageDeliveryError: 消息投递失败
        """
        try:
            self._validate_message(message)
            self._agents_queue[message.send_to].put_nowait(message)
        except asyncio.QueueFull:
            raise MessageDeliveryError(
                reason="目标 Agent 的消息队列已满",
                send_from=message.send_from,
                send_to=message.send_to,
            )
        except (AgentNotFoundError, InvalidMessageError):
            raise  # 直接向上传递
        except Exception as e:
            raise MessageDeliveryError(
                reason=f"未知错误: {str(e)}", send_from=message.send_from, send_to=message.send_to
            )

    def _validate_message(self, message: AgentMessage):
        """
        验证消息格式

        Args:
            message: 要验证的消息

        Raises:
            InvalidMessageError: 消息内容为空
            AgentNotFoundError: 发送者或接收者不存在
        """
        if not message.content or not message.content.strip():
            raise InvalidMessageError("消息内容不能为空")
        if message.send_from not in self._agents_queue:
            raise AgentNotFoundError(message.send_from)
        if message.send_to not in self._agents_queue:
            raise AgentNotFoundError(message.send_to)
