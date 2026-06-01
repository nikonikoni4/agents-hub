"""
MCP Server 和 4 个工具

提供 Manager 编排团队协作的能力：
1. call_agent: 派活给团队成员
2. assign_tasks_to_team: 覆盖式更新任务列表
3. archive_task_list: 归档当前 ACTIVE 列表
4. check_agent_call: 查询 AgentCall 状态

维护说明：
- 当前 tool 数量少，且共享同一套 token 解析、GroupChat 获取和错误响应约定，
  所以集中放在 server.py 中是可以接受的。
- 当出现以下任一情况时，再拆分到 agents_hub/mcp/tools/：
  1. tool 数量超过 5-6 个；
  2. 单个 tool 逻辑明显变长，影响阅读 server.py 的主入口职责；
  3. 需要为 tool 单独编写测试；
  4. tool 开始分化为多个领域，例如 agent、task、history、role；
  5. token 解析、权限校验、GroupChat 获取等重复逻辑继续增加。
- 拆分优先采用 tools/<domain>.py 或 tools/<tool_name>.py；只有当某个 tool
  自身包含复杂 schema、辅助函数或测试夹具时，才升级为独立文件夹。
"""

from fastmcp import FastMCP

from agents_hub.core.foundation import (
    AgentMessage,
    AgentNotFoundError,
    GroupChatNotFoundError,
    MessageType,
)
from agents_hub.core.orchestration import group_chat_manager
from agents_hub.mcp.errors import (
    AGENT_CALL_NOT_FOUND,
    AGENT_NOT_FOUND,
    GROUP_CHAT_NOT_FOUND,
    INTERNAL_ERROR,
    INVALID_TOKEN,
    PERMISSION_DENIED,
    make_error_response,
)

# ============================================================================
# FastMCP 实例
# ============================================================================

mcp = FastMCP(
    name="Agents Hub MCP Server",
    instructions="提供 Manager 编排团队协作的能力",
    version="0.1.0",
)

# ============================================================================
# Tool 1: call_agent
# ============================================================================


def call_agent(
    agent_token: str,
    send_to: str,
    content: str,
    need_response: bool = True,
    timeout_seconds: int = 300,
) -> dict:
    """
    派活给团队成员

    Args:
        agent_token: 调用者的身份令牌
        send_to: 目标 Agent 名称
        content: 消息内容
        need_response: 是否需要响应（默认 True）
        timeout_seconds: 超时时间（秒，默认 300）

    Returns:
        成功: {"call_id": "..."}
        失败: {"error": {"code": "...", "message": "..."}}
    """
    try:
        # 1. 身份解析
        identity = group_chat_manager.resolve_token(agent_token)
        if identity is None:
            return make_error_response(
                INVALID_TOKEN,
                "身份令牌无效或已过期，请检查 <AGENT_RUNTIME> 块中的 token",
            )

        agent_name, group_chat_id = identity

        # 2. 获取 GroupChat
        try:
            group_chat = group_chat_manager.get_group_chat(group_chat_id)
        except GroupChatNotFoundError:
            return make_error_response(
                GROUP_CHAT_NOT_FOUND,
                f"群聊 {group_chat_id} 不存在",
                details={"group_chat_id": group_chat_id},
            )

        # 3. 创建 AgentCall
        message_type = MessageType.TASK if need_response else MessageType.NOTIFICATION
        call = group_chat.agent_call_manager.create_call(
            send_from=agent_name,
            send_to=send_to,
            content=content,
            message_type=message_type,
            timeout_seconds=timeout_seconds if need_response else None,
        )

        # 4. 发送消息
        message = AgentMessage(
            send_from=agent_name,
            send_to=send_to,
            content=content,
            message_type=message_type,
            call_id=call.call_id,
        )

        group_chat.message_router.send_message(message)

        # 5. 返回 call_id
        return {"call_id": call.call_id}

    except AgentNotFoundError as e:
        agent_name = e.details.get("agent_name", "unknown")
        return make_error_response(
            AGENT_NOT_FOUND,
            f"Agent {agent_name} 不存在",
            details={"agent_name": agent_name},
        )
    except GroupChatNotFoundError:
        # 已经在上面处理过了，这里是为了避免被 Exception 捕获
        raise
    except Exception as e:
        return make_error_response(
            INTERNAL_ERROR,
            f"内部错误: {str(e)}",
            details={"exception": str(e)},
        )


# ============================================================================
# Tool 2: assign_tasks_to_team
# ============================================================================


def assign_tasks_to_team(agent_token: str, tasks: list[dict]) -> dict:
    """
    覆盖式更新任务列表（Leader-only）

    Args:
        agent_token: 调用者的身份令牌
        tasks: 任务列表 [{"task_id": "...", "owner": "...", "content": "...", "status": "..."}]

    Returns:
        成功: {"created": int, "updated": int, "unchanged": int}
        失败: {"error": {"code": "...", "message": "..."}}
    """
    try:
        # 1. 身份解析
        identity = group_chat_manager.resolve_token(agent_token)
        if identity is None:
            return make_error_response(
                INVALID_TOKEN,
                "身份令牌无效或已过期，请检查 <AGENT_RUNTIME> 块中的 token",
            )

        agent_name, group_chat_id = identity

        # 2. 获取 GroupChat
        try:
            group_chat = group_chat_manager.get_group_chat(group_chat_id)
        except GroupChatNotFoundError:
            return make_error_response(
                GROUP_CHAT_NOT_FOUND,
                f"群聊 {group_chat_id} 不存在",
                details={"group_chat_id": group_chat_id},
            )

        # 3. 权限校验（Leader-only）
        is_leader = group_chat.manager is not None and agent_name == group_chat.manager.name
        if not is_leader:
            return make_error_response(
                PERMISSION_DENIED,
                f"权限不足：只有 Leader 可以分配任务，当前 Agent {agent_name} 不是 Leader",
                details={"agent_name": agent_name, "required_role": "Leader"},
            )

        # 4. 分配任务
        result = group_chat.task_manager.assign_tasks(
            group_chat_id=group_chat_id,
            tasks=tasks,
            created_by=agent_name,
        )

        return result

    except Exception as e:
        return make_error_response(
            INTERNAL_ERROR,
            f"内部错误: {str(e)}",
            details={"exception": str(e)},
        )


# ============================================================================
# Tool 3: archive_task_list
# ============================================================================


def archive_task_list(agent_token: str) -> dict:
    """
    归档当前 ACTIVE 列表（Leader-only）

    Args:
        agent_token: 调用者的身份令牌

    Returns:
        成功: {"archived_list_id": "...", "archived_tasks_count": int}
        失败: {"error": {"code": "...", "message": "..."}}
    """
    try:
        # 1. 身份解析
        identity = group_chat_manager.resolve_token(agent_token)
        if identity is None:
            return make_error_response(
                INVALID_TOKEN,
                "身份令牌无效或已过期，请检查 <AGENT_RUNTIME> 块中的 token",
            )

        agent_name, group_chat_id = identity

        # 2. 获取 GroupChat
        try:
            group_chat = group_chat_manager.get_group_chat(group_chat_id)
        except GroupChatNotFoundError:
            return make_error_response(
                GROUP_CHAT_NOT_FOUND,
                f"群聊 {group_chat_id} 不存在",
                details={"group_chat_id": group_chat_id},
            )

        # 3. 权限校验（Leader-only）
        is_leader = group_chat.manager is not None and agent_name == group_chat.manager.name
        if not is_leader:
            return make_error_response(
                PERMISSION_DENIED,
                f"权限不足：只有 Leader 可以归档任务列表，当前 Agent {agent_name} 不是 Leader",
                details={"agent_name": agent_name, "required_role": "Leader"},
            )

        # 4. 归档任务列表
        result = group_chat.task_manager.archive_task_list(
            group_chat_id=group_chat_id,
        )

        return result

    except Exception as e:
        return make_error_response(
            INTERNAL_ERROR,
            f"内部错误: {str(e)}",
            details={"exception": str(e)},
        )


# ============================================================================
# Tool 4: check_agent_call
# ============================================================================


def check_agent_call(agent_token: str, call_id: str) -> dict:
    """
    查询 AgentCall 状态

    Args:
        agent_token: 调用者的身份令牌
        call_id: AgentCall ID

    Returns:
        成功: {
            "call_id": "...",
            "status": "...",
            "send_from": "...",
            "send_to": "...",
            "content": "...",
            "message_type": "...",
            "result": "..." | None,
            "error": "..." | None
        }
        失败: {"error": {"code": "...", "message": "..."}}
    """
    try:
        # 1. 身份解析
        identity = group_chat_manager.resolve_token(agent_token)
        if identity is None:
            return make_error_response(
                INVALID_TOKEN,
                "身份令牌无效或已过期，请检查 <AGENT_RUNTIME> 块中的 token",
            )

        agent_name, group_chat_id = identity

        # 2. 获取 GroupChat
        try:
            group_chat = group_chat_manager.get_group_chat(group_chat_id)
        except GroupChatNotFoundError:
            return make_error_response(
                GROUP_CHAT_NOT_FOUND,
                f"群聊 {group_chat_id} 不存在",
                details={"group_chat_id": group_chat_id},
            )

        # 3. 查询 AgentCall
        call = group_chat.agent_call_manager.get_call(call_id)
        if call is None:
            return make_error_response(
                AGENT_CALL_NOT_FOUND,
                f"AgentCall {call_id} 不存在，可能已被清理或系统重启导致数据丢失",
                details={"call_id": call_id},
            )

        # 4. 返回状态信息
        result_content = None
        if call.result is not None:
            # 假设 result 是 AgentResult 对象，有 content 属性
            result_content = getattr(call.result, "content", str(call.result))

        return {
            "call_id": call.call_id,
            "status": call.status.value,
            "send_from": call.send_from,
            "send_to": call.send_to,
            "content": call.content,
            "message_type": call.message_type.value,
            "result": result_content,
            "error": call.error,
        }

    except Exception as e:
        return make_error_response(
            INTERNAL_ERROR,
            f"内部错误: {str(e)}",
            details={"exception": str(e)},
        )


# ============================================================================
# 注册工具到 FastMCP
# ============================================================================

mcp.tool()(call_agent)
mcp.tool()(assign_tasks_to_team)
mcp.tool()(archive_task_list)
mcp.tool()(check_agent_call)
