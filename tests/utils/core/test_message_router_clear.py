import asyncio

import pytest

from agents_hub.core.communication import MessageRouter
from agents_hub.core.foundation import AgentMessage


def create_message_router_with_agents(names: list) -> MessageRouter:
    """创建并注册多个 Agent 的 MessageRouter"""
    router = MessageRouter()
    for name in names:
        router.register(name, asyncio.Queue())
    return router


def create_message(send_from: str, send_to: str, content: str = "test") -> AgentMessage:
    """创建测试消息"""
    return AgentMessage(call_id="test-call", content=content, send_from=send_from, send_to=send_to)


@pytest.mark.asyncio
async def test_clear_queue():
    """清空队列中的所有消息
    契约 : 测试message_router.clear()能否正确清空队列中的消息

    测试方法：
    1. 确保初始状态队列中有数据
    2. 执行清空
    3. 确保清空之后队列中无数据

    如果步骤3失败，说明队列中数据没有被清空，clear()无效
    """
    message_router = create_message_router_with_agents(["A", "B", "C"])
    a_to_b_message = create_message(send_from="A", send_to="B")
    b_to_c_message = create_message(send_from="B", send_to="C")
    c_to_a_message = create_message(send_from="C", send_to="A")
    # 这里由于事件循环没有启动，所以不同执行任务，可以直接发送消息
    message_router.send_message(a_to_b_message)
    message_router.send_message(b_to_c_message)
    message_router.send_message(c_to_a_message)
    queue_list = []
    # 确保每个agent的队列里面都有消息
    for name in message_router._agents_queue:
        queue = message_router._agents_queue[name]
        queue_list.append(queue)
        assert queue.qsize() > 0, "队列写入失败"
    # 执行清空
    message_router.clear()
    for queue in queue_list:
        assert queue.qsize() == 0, "队列内容未清空"


@pytest.mark.asyncio
async def test_clear_registry():
    """清空注册表
    契约：测试message_router.clear之后注册表是否清空

    1. 确保测试之前有数据
    2. 执行清空
    3. 确保清空之后为空

    若步骤3失败，则说明执行清空失败

    """
    message_router = create_message_router_with_agents(["A", "B", "C"])
    # 确保有agent
    assert len(message_router._agents_queue) > 0, "初始化agent数据失败"
    message_router.clear()
    assert len(message_router._agents_queue) == 0


@pytest.mark.asyncio
async def test_idempotence():
    """幂等性：重复调用不出错"""
    message_router = create_message_router_with_agents(["A", "B", "C"])
    a_to_b_message = create_message(send_from="A", send_to="B")
    b_to_c_message = create_message(send_from="B", send_to="C")
    c_to_a_message = create_message(send_from="C", send_to="A")
    # 这里由于事件循环没有启动，所以不同执行任务，可以直接发送消息
    message_router.send_message(a_to_b_message)
    message_router.send_message(b_to_c_message)
    message_router.send_message(c_to_a_message)
    message_router.clear()
    message_router.clear()
    message_router.clear()
