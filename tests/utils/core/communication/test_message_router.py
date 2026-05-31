"""
MessageRouter 单元测试

契约：
1. register() 后 send_message() 能投递到队列
2. unregister() 后 send_message() 抛 AgentNotFoundError
3. send_message() 空内容抛 InvalidMessageError
4. send_message() 未知发送者抛 AgentNotFoundError
5. send_message() 未知接收者抛 AgentNotFoundError
6. clear() 清空所有队列消息
7. clear() 清空注册表
8. clear() 幂等性
"""

import asyncio

import pytest

from agents_hub.core.communication.message_router import MessageRouter
from agents_hub.core.foundation import (
    AgentMessage,
    AgentNotFoundError,
    InvalidMessageError,
    MessageType,
    SessionType,
)


def create_message(send_from: str, send_to: str, content: str = "hello") -> AgentMessage:
    return AgentMessage(
        call_id="c1",
        content=content,
        send_from=send_from,
        send_to=send_to,
        session_type=SessionType.MAIN,
        message_type=MessageType.NOTIFICATION,
    )


class TestMessageRouterRegister:
    """测试 MessageRouter 注册功能"""

    @pytest.mark.asyncio
    async def test_register_then_send_delivers(self):
        """契约：register() 后 send_message() 能投递到队列"""
        router = MessageRouter()
        queue = asyncio.Queue()
        router.register("agent_a", queue)
        router.register("agent_b", asyncio.Queue())

        msg = create_message("agent_a", "agent_b", "test msg")
        router.send_message(msg)

        received = await queue.get() if False else None
        # 消息应该在 agent_b 的队列中
        agent_b_queue = asyncio.Queue()
        router2 = MessageRouter()
        router2.register("a", asyncio.Queue())
        router2.register("b", agent_b_queue)
        router2.send_message(create_message("a", "b", "hello"))

        result = agent_b_queue.get_nowait()
        assert result.content == "hello"
        assert result.send_to == "b"

    @pytest.mark.asyncio
    async def test_unregister_blocks_send(self):
        """契约：unregister() 后 send_message() 抛 AgentNotFoundError"""
        router = MessageRouter()
        router.register("a", asyncio.Queue())
        router.register("b", asyncio.Queue())
        router.unregister("b")

        with pytest.raises(AgentNotFoundError):
            router.send_message(create_message("a", "b"))

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_silent(self):
        """契约：unregister() 不存在的 agent 不报错"""
        router = MessageRouter()
        router.unregister("nonexistent")  # 应静默返回


class TestMessageRouterSendMessage:
    """测试 MessageRouter 消息发送"""

    @pytest.mark.asyncio
    async def test_send_empty_content_raises(self):
        """契约：空内容抛 InvalidMessageError"""
        router = MessageRouter()
        router.register("a", asyncio.Queue())
        router.register("b", asyncio.Queue())

        with pytest.raises(InvalidMessageError):
            router.send_message(create_message("a", "b", ""))

    @pytest.mark.asyncio
    async def test_send_whitespace_content_raises(self):
        """契约：纯空白内容抛 InvalidMessageError"""
        router = MessageRouter()
        router.register("a", asyncio.Queue())
        router.register("b", asyncio.Queue())

        with pytest.raises(InvalidMessageError):
            router.send_message(create_message("a", "b", "   "))

    @pytest.mark.asyncio
    async def test_send_unknown_sender_raises(self):
        """契约：未知发送者抛 AgentNotFoundError"""
        router = MessageRouter()
        router.register("b", asyncio.Queue())

        with pytest.raises(AgentNotFoundError):
            router.send_message(create_message("unknown", "b"))

    @pytest.mark.asyncio
    async def test_send_unknown_receiver_raises(self):
        """契约：未知接收者抛 AgentNotFoundError"""
        router = MessageRouter()
        router.register("a", asyncio.Queue())

        with pytest.raises(AgentNotFoundError):
            router.send_message(create_message("a", "unknown"))


class TestMessageRouterClear:
    """测试 MessageRouter 清理功能"""

    @pytest.mark.asyncio
    async def test_clear_empties_queues(self):
        """契约：clear() 清空所有队列中的消息"""
        router = MessageRouter()
        q_a = asyncio.Queue()
        q_b = asyncio.Queue()
        router.register("a", q_a)
        router.register("b", q_b)

        # 先注册双方，发一条消息让队列非空
        router.register("sender", asyncio.Queue())
        router.send_message(create_message("sender", "a", "msg1"))
        router.send_message(create_message("sender", "a", "msg2"))

        assert not q_a.empty()

        router.clear()

        assert q_a.empty()

    @pytest.mark.asyncio
    async def test_clear_removes_registrations(self):
        """契约：clear() 清空注册表，之后 send_message 失败"""
        router = MessageRouter()
        router.register("a", asyncio.Queue())
        router.register("b", asyncio.Queue())

        router.clear()

        with pytest.raises(AgentNotFoundError):
            router.send_message(create_message("a", "b"))

    @pytest.mark.asyncio
    async def test_clear_idempotent(self):
        """契约：clear() 可以多次调用不报错"""
        router = MessageRouter()
        router.register("a", asyncio.Queue())
        router.register("b", asyncio.Queue())

        router.clear()
        router.clear()
        router.clear()  # 第三次调用不应报错
