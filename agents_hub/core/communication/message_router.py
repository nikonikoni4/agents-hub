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
from agents_hub.utils.logger import get_logger

logger = get_logger("message_router")


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
        logger.debug("Agent 已注册: %s, 已注册总数=%d", name, len(self._agents_queue))

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
        logger.debug(
            "send_message 入口: call_id=%s, from=%s, to=%s, type=%s, content_len=%d",
            message.call_id,
            message.send_from,
            message.send_to,
            message.message_type,
            len(message.content) if message.content else 0,
        )
        try:
            self._validate_message(message)
            self._agents_queue[message.send_to].put_nowait(message)
            logger.debug(
                "消息投递成功: call_id=%s, to=%s, queue_size=%d",
                message.call_id,
                message.send_to,
                self._agents_queue[message.send_to].qsize(),
            )
        except asyncio.QueueFull:
            logger.debug(
                "消息投递失败: call_id=%s, to=%s, 原因=队列已满",
                message.call_id,
                message.send_to,
            )
            raise MessageDeliveryError(
                reason="目标 Agent 的消息队列已满",
                send_from=message.send_from,
                send_to=message.send_to,
            ) from None
        except (AgentNotFoundError, InvalidMessageError):
            raise  # 直接向上传递
        except Exception as e:
            raise MessageDeliveryError(
                reason=f"未知错误: {str(e)}", send_from=message.send_from, send_to=message.send_to
            ) from e

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
            logger.debug("消息校验失败: call_id=%s, 原因=内容为空", message.call_id)
            raise InvalidMessageError("消息内容不能为空")
        if message.send_from not in self._agents_queue:
            logger.debug(
                "消息校验失败: call_id=%s, 原因=发送者 '%s' 未注册",
                message.call_id,
                message.send_from,
            )
            raise AgentNotFoundError(message.send_from)
        if message.send_to not in self._agents_queue:
            logger.debug(
                "消息校验失败: call_id=%s, 原因=接收者 '%s' 未注册",
                message.call_id,
                message.send_to,
            )
            raise AgentNotFoundError(message.send_to)

    def clear(self):
        """
        清空所有消息队列并注销所有 Agent

        此方法用于资源清理，确保：
        1. 所有队列中的消息被清空
        2. 所有 Agent 注册被移除
        3. 可以多次调用（幂等性）
        """
        # 清空所有队列中的消息
        for queue in self._agents_queue.values():
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

        # 清空注册表
        self._agents_queue.clear()
