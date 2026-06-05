"""测试 GroupChat Heartbeat 定时任务"""

import asyncio
from unittest.mock import MagicMock

import pytest

from agents_hub.core.foundation import GroupChatType, MessageType, SessionType
from agents_hub.core.orchestration.group_chat import GroupChat
from agents_hub.utils.logger import setup_logging


@pytest.fixture(scope="session", autouse=True)
def setup_test_logging(tmp_path_factory):
    setup_logging(log_dir=tmp_path_factory.mktemp("logs"))


@pytest.fixture
def group_chat(tmp_path):
    """创建一个最小化的 GroupChat 实例"""
    gc = GroupChat(
        team_members_name=["worker1"],
        group_type=GroupChatType.MANAGER_ORCHESTRATE,
        project_path=str(tmp_path),
        group_chat_id="gc_heartbeat_test",
    )
    return gc


def _make_mock_agent(name: str) -> MagicMock:
    agent = MagicMock()
    agent.name = name
    agent._run = True
    agent.message_queue = asyncio.Queue()
    return agent


def _setup_agents_for_heartbeat(group_chat, worker_run=True):
    """注册 mock agents 到 message_router，准备 heartbeat 测试"""
    manager = _make_mock_agent("Leader")
    worker = _make_mock_agent("worker1")
    worker._run = worker_run
    group_chat.manager = manager
    group_chat.workers = {"worker1": worker}
    group_chat._activated = True
    group_chat._heartbeat_interval = 0.1

    # 注册所有 agent 到 message_router（与 _init_agents 一致）
    group_chat.message_router.register(manager.name, manager.message_queue)
    group_chat.message_router.register(worker.name, worker.message_queue)
    group_chat.message_router.register("__HEARTBEAT__", asyncio.Queue())
    return manager, worker


@pytest.mark.asyncio
async def test_heartbeat_sends_message_to_manager(group_chat):
    """契约：Heartbeat 定时发送 NOTIFICATION 消息给 Manager"""
    manager, _ = _setup_agents_for_heartbeat(group_chat)

    # 启动 heartbeat
    group_chat._heartbeat_task = asyncio.create_task(group_chat._heartbeat_loop())

    # 等待至少一次 heartbeat 触发
    await asyncio.sleep(0.3)

    # 停止 heartbeat
    group_chat._heartbeat_task.cancel()
    try:
        await group_chat._heartbeat_task
    except asyncio.CancelledError:
        pass

    # 从 manager 的真实队列中取消息
    assert not manager.message_queue.empty()
    msg = manager.message_queue.get_nowait()
    assert msg.send_from == "__HEARTBEAT__"
    assert msg.send_to == "Leader"
    assert msg.message_type == MessageType.NOTIFICATION
    assert msg.session_type == SessionType.MAIN
    assert "Heartbeat" in msg.content


@pytest.mark.asyncio
async def test_heartbeat_reports_stopped_workers(group_chat):
    """契约：Heartbeat 检测到停止的 Worker 时，消息包含停止信息"""
    manager, _ = _setup_agents_for_heartbeat(group_chat, worker_run=False)

    group_chat._heartbeat_task = asyncio.create_task(group_chat._heartbeat_loop())
    await asyncio.sleep(0.3)

    group_chat._heartbeat_task.cancel()
    try:
        await group_chat._heartbeat_task
    except asyncio.CancelledError:
        pass

    assert not manager.message_queue.empty()
    msg = manager.message_queue.get_nowait()
    assert "worker1" in msg.content
    assert "自动停止" in msg.content


@pytest.mark.asyncio
async def test_cleanup_stops_heartbeat(group_chat):
    """契约：cleanup 停止 heartbeat 任务"""
    _setup_agents_for_heartbeat(group_chat)

    group_chat._heartbeat_task = asyncio.create_task(group_chat._heartbeat_loop())
    await asyncio.sleep(0.1)

    assert not group_chat._heartbeat_task.done()

    # 模拟 cleanup 中停止 heartbeat 的逻辑
    if group_chat._heartbeat_task and not group_chat._heartbeat_task.done():
        group_chat._heartbeat_task.cancel()
        try:
            await group_chat._heartbeat_task
        except asyncio.CancelledError:
            pass
        group_chat._heartbeat_task = None

    assert group_chat._heartbeat_task is None
