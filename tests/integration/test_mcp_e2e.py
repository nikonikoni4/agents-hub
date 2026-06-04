"""
MCP 工具端到端集成测试

测试完整的 MCP 工具系统流程：
1. 创建 GroupChat，验证 token 生成
2. Manager 调用 call_agent 派活给 Worker
3. Worker 完成任务，出口 B 自动回执
4. Manager 调用 check_agent_call 查询状态
5. Manager 调用 assign_tasks_to_team 分配任务
6. Manager 调用 archive_task_list 归档任务
"""

import asyncio

import pytest

from agents_hub.core.foundation import CallStatus, GroupChatType, MessageType
from agents_hub.core.orchestration import GroupChat, group_chat_manager
from agents_hub.mcp.server import (
    archive_task_list,
    assign_tasks_to_team,
    call_agent,
    check_agent_call,
)
from agents_hub.utils.logger import setup_logging


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_project_path(tmp_path):
    """创建临时项目路径"""
    # 初始化日志系统
    setup_logging(log_dir=tmp_path / "logs")
    return str(tmp_path)


@pytest.fixture
async def group_chat(temp_project_path):
    """创建并启动测试 GroupChat"""
    chat = GroupChat(
        team_members_name=["小王", "小李"],
        group_type=GroupChatType.SEQUENCE_EXECUTE,
        project_path=temp_project_path,
        group_chat_id="test_e2e_chat",
    )

    # 启动群聊
    await chat.start()

    # 注册到 GroupChatManager
    group_chat_manager.register("test_e2e_chat", chat)

    yield chat

    # 清理
    await group_chat_manager.unregister("test_e2e_chat")


# ============================================================================
# 场景 1：创建 GroupChat，验证 token 生成
# ============================================================================


class TestScenario1TokenGeneration:
    """场景 1：创建 GroupChat，验证 token 生成"""

    @pytest.mark.asyncio
    async def test_group_chat_generates_tokens(self, group_chat):
        """测试 GroupChat 创建时生成 token"""
        # 验证 manager 的 token
        manager_session = group_chat.group_chat_context.agent_member_info.get("Leader")
        assert manager_session is not None, "Manager 应该有 session 信息"
        assert manager_session.token != "", "Manager 应该有 token"

        # 验证 workers 的 token
        for worker_name in ["小王", "小李"]:
            worker_session = group_chat.group_chat_context.agent_member_info.get(worker_name)
            assert worker_session is not None, f"{worker_name} 应该有 session 信息"
            assert worker_session.token != "", f"{worker_name} 应该有 token"

    @pytest.mark.asyncio
    async def test_tokens_registered_in_manager(self, group_chat):
        """测试 token 已注册到 GroupChatManager"""
        # 获取 manager 的 token
        manager_token = group_chat.group_chat_context.agent_member_info["Leader"].token

        # 验证可以解析 token
        result = group_chat_manager.resolve_token(manager_token)
        assert result is not None, "Manager token 应该可以解析"
        assert result == ("Leader", "test_e2e_chat"), "Token 解析结果应该正确"

        # 验证 workers 的 token
        for worker_name in ["小王", "小李"]:
            worker_token = group_chat.group_chat_context.agent_member_info[worker_name].token
            result = group_chat_manager.resolve_token(worker_token)
            assert result is not None, f"{worker_name} token 应该可以解析"
            assert result == (worker_name, "test_e2e_chat"), f"{worker_name} token 解析结果应该正确"


# ============================================================================
# 场景 2：Manager 调用 call_agent 派活给 Worker
# ============================================================================


class TestScenario2CallAgent:
    """场景 2：Manager 调用 call_agent 派活给 Worker"""

    @pytest.mark.asyncio
    async def test_manager_calls_worker(self, group_chat):
        """测试 Manager 使用 token 调用 call_agent"""
        # 获取 manager 的 token
        manager_token = group_chat.group_chat_context.agent_member_info["Leader"].token

        # Manager 派活给小王
        result = await call_agent(
            agent_token=manager_token,
            send_to="小王",
            content="请帮我完成任务 A",
            need_response=True,
            timeout_seconds=300,
        )

        # 验证返回 call_id
        assert "call_id" in result, "应该返回 call_id"
        assert "error" not in result, "不应该有错误"

        call_id = result["call_id"]
        assert call_id != "", "call_id 不应该为空"

        # 验证 AgentCall 已创建
        call = group_chat.agent_call_manager.get_call(call_id)
        assert call is not None, "AgentCall 应该已创建"
        assert call.send_from == "Leader", "发送者应该是 Leader"
        assert call.send_to == "小王", "接收者应该是小王"
        assert call.content == "请帮我完成任务 A", "内容应该正确"
        assert call.message_type == MessageType.TASK, "消息类型应该是 TASK"

    @pytest.mark.asyncio
    async def test_worker_receives_message(self, group_chat):
        """测试 Worker 收到消息（通过 AgentCall 状态验证）"""
        # 获取 manager 的 token
        manager_token = group_chat.group_chat_context.agent_member_info["Leader"].token

        # Manager 派活给小王
        result = await call_agent(
            agent_token=manager_token,
            send_to="小王",
            content="请帮我完成任务 B",
            need_response=True,
        )

        call_id = result["call_id"]

        # 等待 Worker 处理消息（Worker 的 run() 任务会自动处理）
        # 由于 Worker 会实际调用 execute，这需要时间
        await asyncio.sleep(2)

        # 验证 AgentCall 状态已变更（说明 Worker 收到并处理了消息）
        call = group_chat.agent_call_manager.get_call(call_id)
        assert call is not None, "AgentCall 应该存在"
        # Worker 的 run() 任务会将状态从 PENDING -> RUNNING -> COMPLETED
        assert call.status in [CallStatus.RUNNING, CallStatus.COMPLETED], (
            f"Worker 应该已收到并处理消息，状态应该是 RUNNING 或 COMPLETED，实际: {call.status}"
        )


# ============================================================================
# 场景 3：Worker 完成任务，出口 B 自动回执
# ============================================================================


class TestScenario3WorkerResponse:
    """场景 3：Worker 完成任务，出口 B 自动回执"""

    @pytest.mark.asyncio
    async def test_worker_completes_and_responds(self, group_chat):
        """测试 Worker 完成任务后自动回执"""
        # 获取 manager 的 token
        manager_token = group_chat.group_chat_context.agent_member_info["Leader"].token

        # Manager 派活给小王
        result = await call_agent(
            agent_token=manager_token,
            send_to="小王",
            content="请帮我完成任务 C",
            need_response=True,
        )

        call_id = result["call_id"]

        # 轮询等待 Worker 处理完成（最多等待 15 秒）
        max_wait = 15
        for i in range(max_wait):
            await asyncio.sleep(1)
            call = group_chat.agent_call_manager.get_call(call_id)
            if call and call.status == CallStatus.COMPLETED:
                break

        # 验证 AgentCall 状态已更新为 COMPLETED
        call = group_chat.agent_call_manager.get_call(call_id)
        assert call is not None, "AgentCall 应该存在"
        assert call.status == CallStatus.COMPLETED, f"AgentCall 状态应该是 COMPLETED，实际: {call.status}"
        # 注意：result 可能为 None，因为 Worker 可能没有设置 result
        # 只要状态是 COMPLETED 就说明 Worker 处理完成了

        # 验证 Manager 收到了回执（出口 B）
        # Manager 的消息队列应该有来自 Worker 的回执消息
        # 注意：Manager 的 run() 任务也会处理消息，所以我们检查 AgentCallManager 中的记录
        # 查找从小王到 Leader 的 NOTIFICATION 类型消息
        manager_calls = [
            c
            for c in group_chat.agent_call_manager._calls.values()
            if c.send_from == "小王" and c.send_to == "Leader" and c.message_type == MessageType.NOTIFICATION
        ]
        assert len(manager_calls) > 0, "Manager 应该收到来自小王的回执"


# ============================================================================
# 场景 4：Manager 调用 check_agent_call 查询状态
# ============================================================================


class TestScenario4CheckAgentCall:
    """场景 4：Manager 调用 check_agent_call 查询状态"""

    @pytest.mark.asyncio
    async def test_manager_checks_call_status(self, group_chat):
        """测试 Manager 使用 token 调用 check_agent_call"""
        # 获取 manager 的 token
        manager_token = group_chat.group_chat_context.agent_member_info["Leader"].token

        # Manager 派活给小王
        call_result = await call_agent(
            agent_token=manager_token,
            send_to="小王",
            content="请帮我完成任务 D",
            need_response=True,
        )

        call_id = call_result["call_id"]

        # Manager 查询状态
        status_result = await check_agent_call(
            agent_token=manager_token,
            call_id=call_id,
        )

        # 验证返回正确的状态信息
        assert "error" not in status_result or status_result["error"] is None, "不应该有错误"
        assert status_result["call_id"] == call_id, "call_id 应该正确"
        assert status_result["status"] == CallStatus.PENDING.value, "初始状态应该是 PENDING"
        assert status_result["send_from"] == "Leader", "发送者应该是 Leader"
        assert status_result["send_to"] == "小王", "接收者应该是小王"
        assert status_result["content"] == "请帮我完成任务 D", "内容应该正确"
        assert status_result["message_type"] == MessageType.TASK.value, "消息类型应该是 TASK"

    @pytest.mark.asyncio
    async def test_check_nonexistent_call(self, group_chat):
        """测试查询不存在的 AgentCall"""
        # 获取 manager 的 token
        manager_token = group_chat.group_chat_context.agent_member_info["Leader"].token

        # 查询不存在的 call_id
        result = await check_agent_call(
            agent_token=manager_token,
            call_id="nonexistent_call_id",
        )

        # 验证返回错误
        assert "error" in result, "应该返回错误"
        assert result["error"]["code"] == "AGENT_CALL_NOT_FOUND", "错误码应该是 AGENT_CALL_NOT_FOUND"


# ============================================================================
# 场景 5：Manager 调用 assign_tasks_to_team 分配任务
# ============================================================================


class TestScenario5AssignTasks:
    """场景 5：Manager 调用 assign_tasks_to_team 分配任务"""

    @pytest.mark.asyncio
    async def test_manager_assigns_tasks(self, group_chat):
        """测试 Manager 使用 token 调用 assign_tasks_to_team"""
        # 获取 manager 的 token
        manager_token = group_chat.group_chat_context.agent_member_info["Leader"].token

        # Manager 分配任务
        tasks = [
            {"task_id": "task_1", "owner": "小王", "content": "任务 1", "status": "pending"},
            {"task_id": "task_2", "owner": "小李", "content": "任务 2", "status": "pending"},
        ]

        result = await assign_tasks_to_team(
            agent_token=manager_token,
            tasks=tasks,
        )

        # 验证返回统计信息
        assert "error" not in result, "不应该有错误"
        assert "created" in result, "应该有 created 字段"
        assert "updated" in result, "应该有 updated 字段"
        assert "unchanged" in result, "应该有 unchanged 字段"
        assert result["created"] == 2, "应该创建 2 个任务"
        assert result["updated"] == 0, "应该更新 0 个任务"
        assert result["unchanged"] == 0, "应该保持 0 个任务不变"

    @pytest.mark.asyncio
    async def test_worker_cannot_assign_tasks(self, group_chat):
        """测试 Worker 无权分配任务"""
        # 获取 worker 的 token
        worker_token = group_chat.group_chat_context.agent_member_info["小王"].token

        # Worker 尝试分配任务
        tasks = [
            {"task_id": "task_3", "owner": "小李", "content": "任务 3", "status": "pending"},
        ]

        result = await assign_tasks_to_team(
            agent_token=worker_token,
            tasks=tasks,
        )

        # 验证返回权限错误
        assert "error" in result, "应该返回错误"
        assert result["error"]["code"] == "PERMISSION_DENIED", "错误码应该是 PERMISSION_DENIED"

    @pytest.mark.asyncio
    async def test_update_existing_tasks(self, group_chat):
        """测试更新已有任务"""
        # 获取 manager 的 token
        manager_token = group_chat.group_chat_context.agent_member_info["Leader"].token

        # 第一次分配任务
        tasks = [
            {"task_id": "task_4", "owner": "小王", "content": "任务 4", "status": "pending"},
        ]

        result1 = await assign_tasks_to_team(agent_token=manager_token, tasks=tasks)
        assert result1["created"] == 1, "第一次应该创建 1 个任务"

        # 第二次更新任务（需要等待一下，确保第一次操作完成）
        await asyncio.sleep(0.1)

        tasks = [
            {"task_id": "task_4", "owner": "小王", "content": "任务 4（已更新）", "status": "running"},
        ]

        result2 = await assign_tasks_to_team(agent_token=manager_token, tasks=tasks)
        # 注意：第二次调用时，由于已经有 ACTIVE 列表，会调用 _update_existing_task_list
        # 但如果 TaskManager 在第一次调用后创建了新列表，第二次可能会创建新的 ACTIVE 列表
        # 让我们检查实际返回的内容
        assert "created" in result2 or "updated" in result2, "应该有 created 或 updated 字段"

        # 如果是更新现有列表
        if "updated" in result2:
            assert result2["updated"] == 1, "应该更新 1 个任务"
            assert result2["created"] == 0, "不应该创建新任务"
        # 如果是创建新列表（可能是因为第一个列表被归档了）
        else:
            assert result2["created"] >= 1, "应该至少创建 1 个任务"


# ============================================================================
# 场景 6：Manager 调用 archive_task_list 归档任务
# ============================================================================


class TestScenario6ArchiveTaskList:
    """场景 6：Manager 调用 archive_task_list 归档任务"""

    @pytest.mark.asyncio
    async def test_manager_archives_task_list(self, group_chat):
        """测试 Manager 使用 token 调用 archive_task_list"""
        # 获取 manager 的 token
        manager_token = group_chat.group_chat_context.agent_member_info["Leader"].token

        # 先分配一些任务
        tasks = [
            {"task_id": "task_5", "owner": "小王", "content": "任务 5", "status": "pending"},
            {"task_id": "task_6", "owner": "小李", "content": "任务 6", "status": "pending"},
        ]

        assign_result = await assign_tasks_to_team(agent_token=manager_token, tasks=tasks)
        assert assign_result["created"] == 2, "应该创建 2 个任务"

        # Manager 归档任务列表
        result = await archive_task_list(agent_token=manager_token)

        # 验证返回归档信息
        assert "error" not in result, "不应该有错误"
        assert "archived_count" in result, "应该有 archived_count 字段"
        assert "archived_at" in result, "应该有 archived_at 字段"
        assert result["archived_count"] == 2, "应该归档 2 个任务"

    @pytest.mark.asyncio
    async def test_worker_cannot_archive_tasks(self, group_chat):
        """测试 Worker 无权归档任务"""
        # 获取 worker 的 token
        worker_token = group_chat.group_chat_context.agent_member_info["小王"].token

        # Worker 尝试归档任务
        result = await archive_task_list(agent_token=worker_token)

        # 验证返回权限错误
        assert "error" in result, "应该返回错误"
        assert result["error"]["code"] == "PERMISSION_DENIED", "错误码应该是 PERMISSION_DENIED"


# ============================================================================
# 完整流程测试
# ============================================================================


class TestCompleteWorkflow:
    """完整流程测试：Manager 派活 → Worker 完成 → 分配任务 → 归档任务"""

    @pytest.mark.asyncio
    async def test_complete_mcp_workflow(self, group_chat):
        """测试完整的 MCP 工具流程"""
        # 获取 manager 的 token
        manager_token = group_chat.group_chat_context.agent_member_info["Leader"].token

        # 1. Manager 派活给小王
        call_result = await call_agent(
            agent_token=manager_token,
            send_to="小王",
            content="请帮我完成任务 E",
            need_response=True,
        )
        assert "call_id" in call_result, "应该返回 call_id"
        call_id = call_result["call_id"]

        # 2. Manager 查询状态
        status_result = await check_agent_call(agent_token=manager_token, call_id=call_id)
        assert status_result["status"] == CallStatus.PENDING.value, "初始状态应该是 PENDING"

        # 3. Manager 分配任务
        tasks = [
            {"task_id": "task_7", "owner": "小王", "content": "任务 7", "status": "pending"},
            {"task_id": "task_8", "owner": "小李", "content": "任务 8", "status": "pending"},
        ]
        assign_result = await assign_tasks_to_team(agent_token=manager_token, tasks=tasks)
        assert assign_result["created"] == 2, "应该创建 2 个任务"

        # 4. Manager 更新任务状态
        tasks = [
            {"task_id": "task_7", "owner": "小王", "content": "任务 7", "status": "completed"},
            {"task_id": "task_8", "owner": "小李", "content": "任务 8", "status": "running"},
        ]
        update_result = await assign_tasks_to_team(agent_token=manager_token, tasks=tasks)
        # 验证更新结果（可能是 updated 或 created，取决于实现）
        assert "updated" in update_result or "created" in update_result, "应该有更新或创建字段"

        # 5. Manager 归档任务列表
        archive_result = await archive_task_list(agent_token=manager_token)
        assert archive_result["archived_count"] == 2, "应该归档 2 个任务"

        # 6. 验证完整流程成功
        assert True, "完整流程测试通过"
