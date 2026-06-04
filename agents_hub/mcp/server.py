"""
MCP Server 和 6 个工具

提供 Manager 编排团队协作的能力：
1. call_agent: 派活给团队成员
2. assign_tasks_to_team: 覆盖式更新任务列表
3. archive_task_list: 归档当前 ACTIVE 列表
4. check_agent_call: 查询 AgentCall 状态
5. speak_in_group_chat: 在群聊中公开发言
6. finish_agent_call: 结束一个需要回复的 AgentCall

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
# TODO 缺乏工具调用错误统计，需要增加显式的工具错误调用统计，但是在外围无法直接关闭agent的工具调用循环，
# 只能做提醒或者强行关闭一致错误的agent（调用错误可能是系统问题，直接停止是比较好的选择）

from datetime import datetime

from fastmcp import FastMCP

from agents_hub.agent_bridge.models import AgentResult
from agents_hub.config import config
from agents_hub.config.types import AgentPlatform, RoleType
from agents_hub.core.foundation import (
    AgentMessage,
    AgentNotFoundError,
    CallStatus,
    GroupChatNotFoundError,
    MessageType,
    render_for_chat,
)
from agents_hub.core.foundation.token import redact_token
from agents_hub.core.orchestration import group_chat_manager
from agents_hub.core.orchestration.group_chat import GroupChat
from agents_hub.mcp.errors import (
    AGENT_CALL_NOT_FOUND,
    AGENT_NOT_FOUND,
    GROUP_CHAT_NOT_FOUND,
    INTERNAL_ERROR,
    INVALID_AGENT_CALL_STATE,
    INVALID_TOKEN,
    PERMISSION_DENIED,
    make_error_response,
)
from agents_hub.realtime.dependencies import broadcast_group_chat_refresh

# ============================================================================
# FastMCP 实例
# ============================================================================

mcp = FastMCP(
    name="Agents Hub MCP Server",
    instructions="提供 Manager 编排团队协作的能力",
    version="0.1.0",
)


def _find_agent(group_chat, agent_name: str):
    """从 GroupChat 中按名称找到 Agent 实例。"""
    manager = getattr(group_chat, "manager", None)
    if manager is not None and getattr(manager, "name", None) == agent_name:
        return manager

    workers = getattr(group_chat, "workers", {})
    if isinstance(workers, dict):
        return workers.get(agent_name)
    return None


def _make_chat_result(group_chat, agent_name: str, content: str) -> AgentResult:
    agent = _find_agent(group_chat, agent_name)
    platform = getattr(getattr(agent, "role_config", None), "platform", AgentPlatform.CLAUDE)
    role_type = getattr(agent, "role_type", RoleType.TEAM_MEMBER)

    return AgentResult(
        text=content,
        session_id="",
        timestamp=datetime.now().isoformat(),
        agent_name=agent_name,
        platform=platform,
        role_type=role_type,
    )


def _send_agent_call_completion_notification(
    group_chat: GroupChat,
    send_from: str,
    send_to: str,
    content: str,
) -> None:
    """创建并投递 AgentCall 完成通知，唤醒原调用方。"""
    response_call = group_chat.agent_call_manager.create_call(
        send_from=send_from,
        send_to=send_to,
        content=content,
        message_type=MessageType.NOTIFICATION,
        timeout_seconds=None,
    )
    message = AgentMessage(
        send_from=send_from,
        send_to=send_to,
        content=content,
        message_type=MessageType.NOTIFICATION,
        call_id=response_call.call_id,
    )
    group_chat.message_router.send_message(message)


# ============================================================================
# Tool 1: call_agent
# ============================================================================


async def call_agent(
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
            group_chat = await group_chat_manager.load_group_chat(group_chat_id)
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


async def assign_tasks_to_team(agent_token: str, tasks: list[dict]) -> dict:
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
            group_chat = await group_chat_manager.load_group_chat(group_chat_id)
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


async def archive_task_list(agent_token: str) -> dict:
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
            group_chat = await group_chat_manager.load_group_chat(group_chat_id)
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


async def check_agent_call(agent_token: str, call_id: str) -> dict:
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
            group_chat = await group_chat_manager.load_group_chat(group_chat_id)
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
            "has_agent_response": call.has_agent_response,
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
# Tool 5: speak_in_group_chat
# ============================================================================


async def speak_in_group_chat(agent_token: str, content: str, send_to: str | None = None) -> dict:
    """
    在群聊中公开发言。

    Args:
        agent_token: 调用者的身份令牌
        content: 公开发言内容
        send_to: 可选的 @ 对象；为空时表示普通群聊发言

    Returns:
        成功: {"ok": True}
        失败: {"error": {"code": "...", "message": "..."}}
    """
    try:
        identity = group_chat_manager.resolve_token(agent_token)
        if identity is None:
            return make_error_response(
                INVALID_TOKEN,
                "身份令牌无效或已过期，请检查 <AGENT_RUNTIME> 块中的 token",
            )

        agent_name, group_chat_id = identity
        try:
            group_chat = await group_chat_manager.load_group_chat(group_chat_id)
        except GroupChatNotFoundError:
            return make_error_response(
                GROUP_CHAT_NOT_FOUND,
                f"群聊 {group_chat_id} 不存在",
                details={"group_chat_id": group_chat_id},
            )

        safe_content = redact_token(content)
        chat_content = (
            render_for_chat(agent_name, send_to, safe_content) if send_to else safe_content
        )
        # TODO : [DESIGN] 当前在agent_Context中使用了_get_filtered_messages，会忽略掉所有@agent或agent发起的信息，
        # 所以如果这里的群聊信息如果是使用了speak_in_the_group@某个agent，这个agent实际上是不会收到这个消息的
        # 需要某个机制去区分finish_agent_call 和 speak_in_group_chat的区别
        # 这里暂时不做处理
        await group_chat.group_chat_context.add_message(
            _make_chat_result(group_chat=group_chat, agent_name=agent_name, content=chat_content)
        )
        await broadcast_group_chat_refresh(group_chat_id)
        return {"ok": True}

    except Exception as e:
        return make_error_response(
            INTERNAL_ERROR,
            f"内部错误: {str(e)}",
            details={"exception": str(e)},
        )


# ============================================================================
# Tool 6: finish_agent_call
# ============================================================================


async def finish_agent_call(
    agent_token: str,
    call_id: str,
    content: str,
    success: bool = True,
) -> dict:
    """
    结束一个需要回复的 AgentCall，并向原调用方投递完成通知以唤醒下一轮处理。

    Args:
        agent_token: 调用者的身份令牌
        call_id: 要结束的 AgentCall ID
        content: 最终回复内容
        success: True 表示完成，False 表示失败或无法继续

    Returns:
        成功: {"call_id": "...", "status": "completed|failed"}
        失败: {"error": {"code": "...", "message": "..."}}
    """
    try:
        # 1. 验证token
        identity = group_chat_manager.resolve_token(agent_token)
        if identity is None:
            return make_error_response(
                INVALID_TOKEN,
                "身份令牌无效或已过期，请检查 <AGENT_RUNTIME> 块中的 token",
            )

        agent_name, group_chat_id = identity
        # 2. 验证群聊，agent call id, 当前是否是被调用方，call id 是否是TASK若不是不能调用，判断是否重复处理
        try:
            group_chat = await group_chat_manager.load_group_chat(group_chat_id)
        except GroupChatNotFoundError:
            return make_error_response(
                GROUP_CHAT_NOT_FOUND,
                f"群聊 {group_chat_id} 不存在",
                details={"group_chat_id": group_chat_id},
            )

        call = group_chat.agent_call_manager.get_call(call_id)
        if call is None:
            return make_error_response(
                AGENT_CALL_NOT_FOUND,
                f"AgentCall {call_id} 不存在，可能已被清理或系统重启导致数据丢失",
                details={"call_id": call_id},
            )

        if call.send_to != agent_name:
            return make_error_response(
                PERMISSION_DENIED,
                f"权限不足：只有调用接收者 {call.send_to} 可以结束该调用",
                details={"call_id": call_id, "agent_name": agent_name},
            )

        if call.message_type != MessageType.TASK:
            return make_error_response(
                INVALID_AGENT_CALL_STATE,
                "该 AgentCall 是 notification，不需要回复，不能调用 finish_agent_call,可以使用speak_in_the_group在群聊进行非正式回复",
                details={"call_id": call_id, "message_type": call.message_type.value},
            )

        if call.has_agent_response:
            return make_error_response(
                INVALID_AGENT_CALL_STATE,
                "该 AgentCall 已经通过 finish_agent_call 闭环，不能重复结束",
                details={"call_id": call_id},
            )
        # 3. 将token信息从返回的信息中剥离
        safe_content = redact_token(content)
        # 4. 完成call闭环
        # TODO : [DESIGN] 这里会把结果发在result中，但是当前也会在直接发送给agent信息，
        # 如果agent调用check_agent_call，实际上会得到2份结果，但是这里先不管
        # 一个可行的方法是使用 “agent call结束，具体内容{agent_name}会直接发送信息给你”
        group_chat.agent_call_manager.mark_agent_response(
            call_id=call_id,
            content=safe_content,  #  “agent call结束，具体内容{agent_name}会直接发送信息给你”
            success=success,
        )
        # 5. Agent 调用方走私有通知；user 调用方写入群聊，由前端通过 refresh 拉取。
        if config.is_user_name(call.send_from):
            await group_chat.group_chat_context.add_message(
                _make_chat_result(
                    group_chat=group_chat,
                    agent_name=agent_name,
                    content=render_for_chat(agent_name, call.send_from, safe_content),
                )
            )
        else:
            _send_agent_call_completion_notification(
                group_chat=group_chat,
                send_from=agent_name,
                send_to=call.send_from,
                content=safe_content,
            )
        await broadcast_group_chat_refresh(group_chat_id)

        status = CallStatus.COMPLETED if success else CallStatus.FAILED
        return {"call_id": call_id, "status": status.value}

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
mcp.tool()(speak_in_group_chat)
mcp.tool()(finish_agent_call)
