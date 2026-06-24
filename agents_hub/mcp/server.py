"""
MCP Server 和 15 个工具

提供 Manager 编排团队协作的能力：
1. call_agent: 派活给团队成员
2. assign_tasks_to_team: 覆盖式更新任务列表
3. archive_task_list: 归档当前 ACTIVE 列表
4. check_agent_call: 查询 AgentCall 状态
5. create_group_chat: 创建新群聊（系统助手专用）
6. create_agent: 创建新的成员角色（系统助手专用）
7. create_loop: 创建循环定义（Leader-only）
8. start_loop: 启动循环执行（Leader-only）
9. stop_loop: 停止运行中的循环执行（Leader-only）
10. delete_loop: 删除循环定义（Leader-only）
11. get_loop_status: 查询循环执行状态（任意 Agent）
12. list_loops: 查询所有 Loop 定义（任意 Agent）
13. list_loop_executions: 查询 Loop 执行历史（任意 Agent）
14. health_check: 健康检查端点

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

import inspect
from datetime import datetime

from fastmcp import FastMCP
from mcp.types import JSONRPCMessage

# Monkey-patch: MCP 库默认 ensure_ascii=True 导致中文变成 \xe6\xb4\xbe...，
# 覆盖 model_dump_json 使其输出可读的 UTF-8 字符。
_original_model_dump_json = JSONRPCMessage.model_dump_json


def _model_dump_json_utf8(self, **kwargs):
    """使用 UTF-8 输出 JSONRPCMessage 的 JSON 字符串。

    Args:
        **kwargs: 传递给原始 model_dump_json 的参数。

    Returns:
        JSON 字符串。
    """
    kwargs.setdefault("ensure_ascii", False)
    return _original_model_dump_json(self, **kwargs)


JSONRPCMessage.model_dump_json = _model_dump_json_utf8  # type: ignore[method-assign]

from dataclasses import asdict  # noqa: E402
from typing import Literal  # noqa: E402

from agents_hub.agent_bridge.models import AgentResult  # noqa: E402
from agents_hub.api.schemas.roles import RoleCreateRequest  # noqa: E402
from agents_hub.api.services.group_chat_service import GroupChatService  # noqa: E402
from agents_hub.api.services.role_service import RoleService  # noqa: E402
from agents_hub.config import config  # noqa: E402
from agents_hub.config.types import AgentPlatform, RoleType  # noqa: E402
from agents_hub.core.foundation import (  # noqa: E402
    AgentMessage,
    AgentNotFoundError,
    GroupChatNotFoundError,
    MessageType,
)
from agents_hub.core.foundation.exceptions import (  # noqa: E402
    FileSystemError,
    LoopExecutionNotFoundError,
    LoopExecutionStateError,
    LoopNotFoundError,
    LoopStateError,
    LoopValidationError,
)
from agents_hub.core.orchestration import group_chat_manager  # noqa: E402
from agents_hub.core.orchestration.group_chat import GroupChat  # noqa: E402
from agents_hub.exceptions import ResourceNotFoundError, StateError, ValidationError  # noqa: E402
from agents_hub.mcp.errors import (  # noqa: E402  # noqa: E402
    AGENT_ALREADY_EXISTS,
    AGENT_CALL_NOT_FOUND,
    AGENT_NOT_FOUND,
    FILE_SYSTEM_ERROR,
    GROUP_CHAT_NOT_FOUND,
    INTERNAL_ERROR,
    INVALID_TOKEN,
    PERMISSION_DENIED,
    VALIDATION_ERROR,
    make_error_response,
)
from agents_hub.realtime import broadcast_group_chat_refresh  # noqa: E402
from agents_hub.roles.exceptions import RoleAlreadyExistsError  # noqa: E402
from agents_hub.utils import get_logger  # noqa: E402
from agents_hub.utils.session_parser import get_group_chat_messages  # noqa: E402

logger = get_logger(__name__)
# ============================================================================
# FastMCP 实例
# ============================================================================

mcp = FastMCP(
    name="Agents Hub MCP Server",
    instructions="提供 Manager 编排团队协作的能力",
    version="0.1.0",
)

group_chat_service = GroupChatService(group_chat_manager=group_chat_manager)
role_service = RoleService()


def _verify_system_token(agent_token: str) -> bool:
    """验证是否为系统助手 token"""
    return agent_token == config.assistant_token


def _find_agent(group_chat, agent_name: str):
    """从 GroupChat 中按名称找到 Agent 实例。"""
    manager = getattr(group_chat, "manager", None)
    if manager is not None and getattr(manager, "name", None) == agent_name:
        return manager

    workers = getattr(group_chat, "workers", {})
    if isinstance(workers, dict):
        return workers.get(agent_name)
    return None


def _make_chat_result(
    group_chat,
    agent_name: str,
    content: str,
    cwd: str | None = None,
    modified_files: list | None = None,
    git_diff_range: str | None = None,
    web_preview: dict | None = None,
) -> AgentResult:
    """构造用于写入群聊的 AgentResult。

    Args:
        group_chat: 当前群聊实例。
        agent_name: 发言 Agent 名称。
        content: 消息内容。
        cwd: Agent 当前工作目录。
        modified_files: 修改文件列表。
        git_diff_range: Git diff 范围。
        web_preview: 网页预览信息。

    Returns:
        群聊消息结果对象。
    """
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
        cwd=cwd,
        modified_files=modified_files,
        git_diff_range=git_diff_range,
        web_preview=web_preview,
    )


async def _send_agent_call_completion_notification(
    group_chat: GroupChat,
    group_chat_id: str,
    send_from: str,
    send_to: str,
    content: str,
) -> None:
    """创建并投递 AgentCall 完成通知，唤醒原调用方。"""
    response_call = await group_chat.agent_call_manager.create_call(
        send_from=send_from,
        send_to=send_to,
        content=content,
        message_type=MessageType.NOTIFICATION,
        timeout_seconds=None,
    )
    logger.info(
        "AgentCall 创建: call_id=%s, sender=%s, receiver=%s",
        response_call.call_id,
        response_call.send_from,
        response_call.send_to,
    )
    message = AgentMessage(
        send_from=send_from,
        send_to=send_to,
        content=content,
        message_type=MessageType.NOTIFICATION,
        call_id=response_call.call_id,
    )
    logger.info("消息投递: from=%s, to=%s", send_from, send_to)
    await group_chat.send_message_to_agent(message)
    await broadcast_group_chat_refresh(group_chat_id)


async def _resolve_group_chat(agent_token: str) -> tuple[str, str, GroupChat] | dict:
    """通过 Agent token 解析并加载群聊。

    Args:
        agent_token: Agent 身份令牌。

    Returns:
        成功时返回 Agent 名称、群聊 ID 和群聊实例；失败时返回错误响应。
    """
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
        logger.warning("Loop 工具群聊不存在: group_chat_id=%s", group_chat_id)
        return make_error_response(
            GROUP_CHAT_NOT_FOUND,
            f"群聊 {group_chat_id} 不存在",
            details={"group_chat_id": group_chat_id},
        )

    return agent_name, group_chat_id, group_chat


def _is_leader(group_chat: GroupChat, agent_name: str) -> bool:
    """判断指定 Agent 是否为当前群聊 Leader。

    Args:
        group_chat: 当前群聊实例。
        agent_name: Agent 名称。

    Returns:
        是 Leader 时返回 True。
    """
    return group_chat.manager is not None and agent_name == group_chat.manager.name


def _permission_denied(agent_name: str, action: str) -> dict:
    """构造 Leader 权限不足的错误响应。

    Args:
        agent_name: 当前 Agent 名称。
        action: 被拒绝的操作描述。

    Returns:
        MCP 错误响应。
    """
    return make_error_response(
        PERMISSION_DENIED,
        f"权限不足：只有 Leader 可以{action}，当前 Agent {agent_name} 不是 Leader",
        details={"agent_name": agent_name, "required_role": "Leader"},
    )


# ============================================================================
# Tool 1: call_agent
# ============================================================================


async def call_agent(
    agent_token: str,
    send_to: str,
    content: str,
) -> dict:
    """
    派活给团队成员

    Args:
        agent_token: 调用者的身份令牌
        send_to: 目标 Agent 名称
        content: 消息内容

    Returns:
        成功: {"call_id": "..."}
        失败: {"error": {"code": "...", "message": "..."}}
    """
    logger.info(
        "MCP 调用: call_agent, send_to=%s, content_len=%d", send_to, len(content) if content else 0
    )
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
            logger.warning("call_agent 群聊不存在: group_chat_id=%s", group_chat_id)
            return make_error_response(
                GROUP_CHAT_NOT_FOUND,
                f"群聊 {group_chat_id} 不存在",
                details={"group_chat_id": group_chat_id},
            )

        # 3. 创建 AgentCall（固定 TASK 类型，避免 AI 误设 NOTIFICATION 导致后续 check_agent_call 失败）
        call = await group_chat.agent_call_manager.create_call(
            send_from=agent_name,
            send_to=send_to,
            content=content,
            message_type=MessageType.TASK,
            timeout_seconds=None,
        )
        logger.info(
            "AgentCall 创建: call_id=%s, sender=%s, receiver=%s",
            call.call_id,
            call.send_from,
            call.send_to,
        )

        # 4. 发送消息
        message = AgentMessage(
            send_from=agent_name,
            send_to=send_to,
            content=content,
            message_type=MessageType.TASK,
            call_id=call.call_id,
        )

        logger.info("消息投递: from=%s, to=%s", agent_name, send_to)
        await group_chat.send_message_to_agent(message)
        await broadcast_group_chat_refresh(group_chat_id)

        # 5. 返回 call_id
        return {"call_id": call.call_id}

    except AgentNotFoundError as e:
        logger.warning("call_agent: Agent 不存在: %s", str(e))
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
        logger.error("call_agent 失败: %s", str(e), exc_info=True)
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

    按 task_id 匹配：已有任务更新，新任务创建，旧列表中不在新列表的任务保留不变。
    当前任务列表见 runtime 中的 <team_workboard>。

    Args:
        agent_token: 调用者的身份令牌
        tasks: 任务列表，每项包含：
            - task_id: 任务标识（已有任务必须使用 <team_workboard> 中的原值）
            - owner: 负责人（必须是 <team_members> 中的成员名）
            - content: 任务描述
            - status: "PENDING"（待执行）/ "RUNNING"（执行中）/ "COMPLETED"（已完成）

    Returns:
        成功: {"created": int, "updated": int, "unchanged": int}
        失败: {"error": {"code": "...", "message": "..."}}
    """
    logger.info("MCP 调用: assign_tasks_to_team, tasks_count=%d", len(tasks) if tasks else 0)
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
            logger.warning("assign_tasks_to_team 群聊不存在: group_chat_id=%s", group_chat_id)
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
        logger.error("assign_tasks_to_team 失败: %s", str(e), exc_info=True)
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
    logger.info("MCP 调用: archive_task_list")
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
            logger.warning("archive_task_list 群聊不存在: group_chat_id=%s", group_chat_id)
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
        logger.error("archive_task_list 失败: %s", str(e), exc_info=True)
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
    logger.info("MCP 调用: check_agent_call, call_id=%s", call_id)
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
            logger.warning("check_agent_call 群聊不存在: group_chat_id=%s", group_chat_id)
            return make_error_response(
                GROUP_CHAT_NOT_FOUND,
                f"群聊 {group_chat_id} 不存在",
                details={"group_chat_id": group_chat_id},
            )

        # 3. 查询 AgentCall
        call = await group_chat.agent_call_manager.get_call(call_id)
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
        logger.error("check_agent_call 失败: %s", str(e), exc_info=True)
        return make_error_response(
            INTERNAL_ERROR,
            f"内部错误: {str(e)}",
            details={"exception": str(e)},
        )


# ============================================================================
# Tool 5: report_progress [DEPRECATED]
# ============================================================================

# [deprecated] 已弃用，保留代码供参考
# async def report_progress(agent_token: str, content: str, send_to: str | None = None) -> dict:
#     """
#     复杂任务过程汇报：在你执行复杂任务（需要花费1min以上的任务）时调用该工具进行汇报说明。
#     使用时机：
#     - 任务开始前：收到，我将执行<任务名称>
#     - 任务中间：已完成XX，接下来将进行XX
#
#     Args:
#         agent_token: 调用者的身份令牌
#         content: 简短的进展汇报
#         send_to: 可选的 @ 对象；为空时表示普通群聊发言
#
#     Returns:
#         成功: {"ok": True}
#         失败: {"error": {"code": "...", "message": "..."}}
#     """
#     # 已弃用
#     logger.info(
#         "MCP 调用: report_progress, send_to=%s, content_len=%d",
#         send_to,
#         len(content) if content else 0,
#     )
#     try:
#         identity = group_chat_manager.resolve_token(agent_token)
#         if identity is None:
#             return make_error_response(
#                 INVALID_TOKEN,
#                 "身份令牌无效或已过期，请检查 <AGENT_RUNTIME> 块中的 token",
#             )
#
#         agent_name, group_chat_id = identity
#         try:
#             group_chat = await group_chat_manager.load_group_chat(group_chat_id)
#         except GroupChatNotFoundError:
#             logger.warning("report_progress 群聊不存在: group_chat_id=%s", group_chat_id)
#             return make_error_response(
#                 GROUP_CHAT_NOT_FOUND,
#                 f"群聊 {group_chat_id} 不存在",
#                 details={"group_chat_id": group_chat_id},
#             )
#
#         safe_content = redact_token(content)
#         chat_content = (
#             render_for_chat(agent_name, send_to, safe_content) if send_to else safe_content
#         )
#         await group_chat.runtime.add_message(
#             _make_chat_result(group_chat=group_chat, agent_name=agent_name, content=chat_content)
#         )
#         await broadcast_group_chat_refresh(group_chat_id)
#         return {"ok": True}
#
#     except Exception as e:
#         logger.error("report_progress 失败: %s", str(e), exc_info=True)
#         return make_error_response(
#             INTERNAL_ERROR,
#             f"内部错误: {str(e)}",
#             details={"exception": str(e)},
#         )


# ============================================================================
# Tool 6: complete_task [DEPRECATED]，已被agents_hub\core\agent\base_agent.py的_fallback_close_task替代
# ============================================================================

# [deprecated] 已弃用，保留代码供参考
# async def complete_task(
#     agent_token: str,
#     call_id: str,
#     content: str,
#     modified_files: list[str] | None = None,
#     git_diff_range: str | None = None,
#     web_preview_url: str | None = None,
#     web_preview_title: str | None = None,
#     success: bool = True,
# ) -> dict:
#     """
#     最终任务总结：当你结束这一轮对话之前，必须调用该工具进行任务汇报。
#     若有改动的文件必须使用modified_files和git_diff_range
#     若有HTML或网页需要用于预览，必须使用web_preview_url
#     Args:
#         agent_token: 调用者的身份令牌
#         call_id: 要结束的 AgentCall ID
#         content: 成果汇报（结果、修改文件、注意事项等）
#         success: True 表示完成，False 表示阻塞或失败
#         modified_files: 修改的文件列表（相对路径）
#         git_diff_range: Git diff 范围（格式：commit..commit）
#         web_preview_url: 网页预览 URL（可选）。当完成了一个网页（HTML 文件）时，需要传入此参数让用户预览。
#                         格式:
#                           - 静态 HTML 文件: 文件相对路径，如 "index.html"、"dist/index.html"
#                           - 本地服务器: 完整 URL，如 "http://localhost:3000"、"http://localhost:8000/api"
#         web_preview_title: 网页预览标题（可选），如 "首页"、"登录页面" 等
#
#     Returns:
#         成功: {"call_id": "...", "status": "completed|failed"}
#         失败: {"error": {"code": "...", "message": "..."}}
#     """
#     # 已弃用
#     logger.info(
#         "MCP 调用: complete_task, call_id=%s, success=%s, content_len=%d",
#         call_id,
#         success,
#         len(content) if content else 0,
#     )
#     try:
#         # 1. 验证token
#         identity = group_chat_manager.resolve_token(agent_token)
#         if identity is None:
#             return make_error_response(
#                 INVALID_TOKEN,
#                 "身份令牌无效或已过期，请检查 <AGENT_RUNTIME> 块中的 token",
#             )
#
#         agent_name, group_chat_id = identity
#         # 2. 验证群聊，agent call id, 当前是否是被调用方，call id 是否是TASK若不是不能调用，判断是否重复处理
#         try:
#             group_chat = await group_chat_manager.load_group_chat(group_chat_id)
#         except GroupChatNotFoundError:
#             logger.warning("complete_task 群聊不存在: group_chat_id=%s", group_chat_id)
#             return make_error_response(
#                 GROUP_CHAT_NOT_FOUND,
#                 f"群聊 {group_chat_id} 不存在",
#                 details={"group_chat_id": group_chat_id},
#             )
#
#         call = await group_chat.agent_call_manager.get_call(call_id)
#         if call is None:
#             return make_error_response(
#                 AGENT_CALL_NOT_FOUND,
#                 f"AgentCall {call_id} 不存在，可能已被清理或系统重启导致数据丢失",
#                 details={"call_id": call_id},
#             )
#
#         if call.send_to != agent_name:
#             return make_error_response(
#                 PERMISSION_DENIED,
#                 f"权限不足：只有调用接收者 {call.send_to} 可以结束该调用",
#                 details={"call_id": call_id, "agent_name": agent_name},
#             )
#
#         if call.message_type != MessageType.TASK:
#             return make_error_response(
#                 INVALID_AGENT_CALL_STATE,
#                 "该 AgentCall 是 notification，不需要回复，不能调用 complete_task,可以使用speak_in_the_group在群聊进行非正式回复",
#                 details={"call_id": call_id, "message_type": call.message_type.value},
#             )
#
#         if call.has_agent_response:
#             return make_error_response(
#                 INVALID_AGENT_CALL_STATE,
#                 "该 AgentCall 已经通过 complete_task 闭环，不能重复结束",
#                 details={"call_id": call_id},
#             )
#         # 3. 将token信息从返回的信息中剥离
#         safe_content = redact_token(content)
#
#         # 4. 参数校验：空值时跳过对应处理
#         file_metadata_list = None
#         agent_cwd: str | None = None
#         has_modified_files = modified_files is not None and len(modified_files) > 0
#         has_web_preview = web_preview_url is not None and web_preview_url.strip() != ""
#
#         # 获取 Agent 工作目录（modified_files 和 web_preview_url 都需要）
#         if has_modified_files or has_web_preview:
#             agent = _find_agent(group_chat, agent_name)
#             agent_cwd = (
#                 agent.cwd if agent and hasattr(agent, "cwd") else group_chat.runtime.project_path
#             )
#
#         if has_modified_files:
#             # 构造快照目录
#             snapshot_dir = group_chat_paths.file_snapshots_dir(
#                 group_chat_id, group_chat.runtime.project_path
#             )
#
#             # 为每个文件创建快照
#             file_metadata_list = []
#             assert modified_files is not None, (
#                 "has_modified_files 为 True 时 modified_files 必须非空"
#             )
#             assert agent_cwd is not None, "modified_files 存在时 agent_cwd 必须已初始化"
#             snapshot_failures = []
#             for index, file_path in enumerate(modified_files):
#                 try:
#                     metadata = create_file_snapshot(
#                         snapshot_dir=snapshot_dir,
#                         call_id=call_id,
#                         file_path=file_path,
#                         index=index,
#                         cwd=agent_cwd,
#                         git_diff_range=git_diff_range,
#                     )
#                     file_metadata_list.append(metadata)
#                 except Exception as e:
#                     # 单个文件失败不影响整体
#                     snapshot_failures.append((file_path, str(e)))
#             if snapshot_failures:
#                 logger.warning(
#                     "complete_task: %d 个文件快照创建失败: %s",
#                     len(snapshot_failures),
#                     snapshot_failures,
#                 )
#
#         # 5. 完成call闭环
#         logger.info(
#             "complete_task: call_id=%s, success=%s, safe_content_len=%d",
#             call_id,
#             success,
#             len(safe_content) if safe_content else 0,
#         )
#         await group_chat.agent_call_manager.mark_agent_response(
#             call_id=call_id,
#             content=safe_content,
#             success=success,
#         )
#         logger.info("AgentCall 完成: call_id=%s", call_id)
#         # 6. Agent 调用方走私有通知；user 调用方写入群聊，由前端通过 refresh 拉取。
#         web_preview = None
#         if has_web_preview:
#             assert web_preview_url is not None, (
#                 "has_web_preview 为 True 时 web_preview_url 必须非空"
#             )
#             assert agent_cwd is not None, "web_preview_url 存在时 agent_cwd 必须已初始化"
#             # 只对相对路径转换为 file:/// 绝对路径，HTTP/HTTPS URL 保持不变
#             if not web_preview_url.startswith(("file:///", "http://", "https://")):
#                 abs_path = Path(agent_cwd) / web_preview_url
#                 web_preview_url = f"file:///{abs_path.as_posix()}"
#             web_preview = {"url": web_preview_url, "title": web_preview_title}
#
#         if config.is_user_name(call.send_from):
#             await group_chat.runtime.add_message(
#                 _make_chat_result(
#                     group_chat=group_chat,
#                     agent_name=agent_name,
#                     content=render_for_chat(agent_name, call.send_from, safe_content),
#                     cwd=agent_cwd,
#                     modified_files=file_metadata_list,
#                     git_diff_range=git_diff_range,
#                     web_preview=web_preview,
#                 )
#             )
#             await broadcast_group_chat_refresh(group_chat_id)
#         else:
#             await _send_agent_call_completion_notification(
#                 group_chat=group_chat,
#                 group_chat_id=group_chat_id,
#                 send_from=agent_name,
#                 send_to=call.send_from,
#                 content=safe_content,
#             )
#
#         status = CallStatus.COMPLETED if success else CallStatus.FAILED
#         return {"call_id": call_id, "status": status.value}
#
#     except Exception as e:
#         logger.error("complete_task 失败: %s", str(e), exc_info=True)
#         return make_error_response(
#             INTERNAL_ERROR,
#             f"内部错误: {str(e)}",
#             details={"exception": str(e)},
#         )


# ============================================================================
# Tool 7: request_permission
# ============================================================================


# TODO 这个只是一个示例，之后应该换做是具体的请求，比如添加群成员等，把这个降级为一个基本的工具函数
async def request_permission(
    agent_token: str,
    title: str,
    content: str,
) -> dict:
    """
    向用户请求操作权限

    创建一条权限请求消息显示在群聊中，等待用户批准或拒绝。
    工具立即返回（不阻塞），用户操作后会通过通知告知结果。

    Args:
        agent_token: 调用者的身份令牌
        title: 权限请求标题（如"创建新成员"、"执行终端命令"）
        content: 权限请求的详细描述

    Returns:
        成功: {"request_id": "...", "status": "pending"}
        失败: {"error": {"code": "...", "message": "..."}}
    """
    from uuid import uuid4

    logger.info("MCP 调用: request_permission, title=%s", title)
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
            logger.warning("request_permission 群聊不存在: group_chat_id=%s", group_chat_id)
            return make_error_response(
                GROUP_CHAT_NOT_FOUND,
                f"群聊 {group_chat_id} 不存在",
                details={"group_chat_id": group_chat_id},
            )

        # 3. 构建权限请求数据
        request_id = str(uuid4())
        permission_request = {
            "request_id": request_id,
            "title": title,
            "content": content,
            "status": "pending",
            "requested_by": agent_name,
        }

        # 4. 创建 AgentResult 并写入消息
        agent_result = _make_chat_result(
            group_chat=group_chat,
            agent_name=agent_name,
            content=f"[权限请求] {title}",
        )
        agent_result.permission_request = permission_request

        await group_chat.runtime.add_message(agent_result)
        await broadcast_group_chat_refresh(group_chat_id)

        # 5. 返回 request_id
        return {"request_id": request_id, "status": "pending"}

    except Exception as e:
        logger.error("request_permission 失败: %s", str(e), exc_info=True)
        return make_error_response(
            INTERNAL_ERROR,
            f"内部错误: {str(e)}",
            details={"exception": str(e)},
        )


# ============================================================================
# Tool 8: create_group_chat
# ============================================================================


async def create_group_chat(
    agent_token: str,
    team_members: list[str],
    project_path: str,
    group_chat_name: str | None = None,
) -> dict:
    """
    创建新群聊（系统助手专用）

    Args:
        agent_token: 系统助手身份令牌
        team_members: 团队成员角色名列表
        project_path: 项目路径（必须为绝对路径）
        group_chat_name: 群聊名称（可选）

    Returns:
        成功: {"group_chat_id": "...", "group_chat_name": "...", "project_path": "...", ...}
        失败: {"error": {"code": "...", "message": "..."}}
    """
    logger.info(
        "MCP 调用: create_group_chat, team_members=%s, project_path=%s", team_members, project_path
    )
    try:
        # 1. 系统身份验证
        if not _verify_system_token(agent_token):
            return make_error_response(
                PERMISSION_DENIED,
                "权限不足：只有系统助手可以创建群聊",
                details={"required_token": "config.assistant_token"},
            )

        # 2. 委托 GroupChatService
        info = await group_chat_service.create_group_chat(
            team_members=team_members,
            project_path=project_path,
            group_chat_name=group_chat_name,
        )

        # 3. 返回结果
        return {
            "group_chat_id": info.group_chat_id,
            "group_chat_name": info.group_chat_name,
            "project_path": info.project_path,
            "group_type": info.group_type.value,
            "members": team_members,
        }

    except ValidationError as e:
        logger.warning("create_group_chat 参数校验失败: %s", str(e))
        return make_error_response(
            VALIDATION_ERROR,
            str(e),
            details=e.details,
        )
    except ResourceNotFoundError as e:
        logger.warning("create_group_chat 资源不存在: %s", str(e))
        return make_error_response(
            AGENT_NOT_FOUND,
            str(e),
            details=e.details,
        )
    except StateError as e:
        logger.warning("create_group_chat 状态错误: %s", str(e))
        return make_error_response(
            INTERNAL_ERROR,
            f"群聊启动失败: {str(e)}",
            details=e.details,
        )
    except Exception as e:
        logger.error("create_group_chat 失败: %s", str(e), exc_info=True)
        return make_error_response(
            INTERNAL_ERROR,
            f"内部错误: {str(e)}",
            details={"exception": str(e)},
        )


# ============================================================================
# Tool 9: create_agent
# ============================================================================


async def create_agent(
    agent_token: str,
    name: str,
    platform: Literal["claude", "codex"],
    description: str | None = None,
) -> dict:
    """
    创建新的成员角色（系统助手专用）

    Args:
        agent_token: 系统助手身份令牌
        name: 角色名称（必须是合法的目录名）
        platform: 平台类型（claude 或 codex）
        description: 角色描述（可选）

    Returns:
        成功: {"name": "...", "platform": "...", ...}
        失败: {"error": {"code": "...", "message": "..."}}
    """
    logger.info("MCP 调用: create_agent, name=%s, platform=%s", name, platform)
    try:
        # 1. 系统身份验证
        if not _verify_system_token(agent_token):
            return make_error_response(
                PERMISSION_DENIED,
                "权限不足：只有系统助手可以创建成员",
                details={"required_token": "config.assistant_token"},
            )

        # 2. 委托 RoleService
        request = RoleCreateRequest(
            name=name,
            platform=platform,
            description=description,
            type="team_member",
        )
        role_info = role_service.create_role(request)

        # 3. 返回结果
        return asdict(role_info)

    except ValueError as e:
        logger.warning("create_agent 参数校验失败: %s", str(e))
        return make_error_response(
            VALIDATION_ERROR,
            str(e),
            details={"name": name},
        )
    except RoleAlreadyExistsError as e:
        logger.warning("create_agent 角色已存在: %s", str(e))
        return make_error_response(
            AGENT_ALREADY_EXISTS,
            str(e),
            details={"name": name},
        )
    except Exception as e:
        logger.error("create_agent 失败: %s", str(e), exc_info=True)
        return make_error_response(
            INTERNAL_ERROR,
            f"内部错误: {str(e)}",
            details={"exception": str(e)},
        )


# ============================================================================
# Loop Tools
# ============================================================================


async def create_loop(
    agent_token: str,
    nodes: list[dict],
    max_iterations: int,
    name: str | None = None,
) -> dict:
    """创建循环定义（Leader-only）。

    **重要**：必须先使用 loop-design skill 完成需求澄清和提示词设计，确保节点设计合理后再调用此工具。

    Args:
        agent_token: Leader 的身份令牌。
        nodes: 循环节点列表，每个节点包含：
            - node_type: "normal"（执行节点）或 "terminator"（判断节点，决定是否退出循环）
            - agent_name: 执行该节点的 Agent 名称
            - role_description: 节点职责描述
            - output_schema_prompt: 输出格式要求（Markdown 格式）
            - output_schema_fields: 必需字段列表，每个元素是 Markdown 标题，如 ["## 实现代码", "## 修改说明"]，用于系统校验输出格式
            - max_retries: 重试次数（可选，默认 3）
        max_iterations: 最大循环轮数。
        name: 循环名称（可选），用于识别和管理。

    Returns:
        成功: {"loop_id": "...", "created_at": "..."}
        失败: {"error": {"code": "...", "message": "..."}}
    """
    logger.info(
        "MCP 调用: create_loop, name=%s, nodes=%d, max_iterations=%d",
        name,
        len(nodes) if nodes else 0,
        max_iterations,
    )
    try:
        resolved = await _resolve_group_chat(agent_token)
        if isinstance(resolved, dict):
            return resolved

        agent_name, _group_chat_id, group_chat = resolved
        if not _is_leader(group_chat, agent_name):
            return _permission_denied(agent_name, "创建循环")

        loop = await group_chat.create_loop(
            nodes=nodes,
            max_iterations=max_iterations,
            name=name,
        )
        return {"loop_id": loop.loop_id, "created_at": loop.created_at.isoformat()}

    except (LoopValidationError, ValueError) as e:
        logger.warning("create_loop 参数校验失败: %s", str(e))
        details = getattr(e, "details", None)
        return make_error_response(VALIDATION_ERROR, str(e), details=details)
    except AgentNotFoundError as e:
        logger.warning("create_loop Agent 不存在: %s", str(e))
        return make_error_response(AGENT_NOT_FOUND, str(e), details=e.details)
    except Exception as e:
        logger.error("create_loop 失败: %s", str(e), exc_info=True)
        return make_error_response(
            INTERNAL_ERROR,
            f"内部错误: {str(e)}",
            details={"exception": str(e)},
        )


async def start_loop(agent_token: str, loop_id: str, initial_task: str) -> dict:
    """启动循环执行（Leader-only）。

    启动一个已创建的循环定义，创建新的执行实例。
    同一个循环定义可以多次启动，每次传入不同的 initial_task。

    Args:
        agent_token: Leader 的身份令牌。
        loop_id: 要启动的循环定义 ID（从 create_loop 返回值获取）。
        initial_task: 本次执行的初始任务内容，发送给第一个节点。

    Returns:
        成功: {"execution_id": "...", "loop_id": "...", "status": "running"}
        失败: {"error": {"code": "...", "message": "..."}}
    """
    logger.info("MCP 调用: start_loop, loop_id=%s", loop_id)
    try:
        resolved = await _resolve_group_chat(agent_token)
        if isinstance(resolved, dict):
            return resolved

        agent_name, _group_chat_id, group_chat = resolved
        if not _is_leader(group_chat, agent_name):
            return _permission_denied(agent_name, "启动循环")

        result = await group_chat.create_and_start_loop(loop_id, initial_task)
        return result

    except LoopExecutionStateError as e:
        logger.warning("start_loop 状态错误: %s", str(e))
        return make_error_response(VALIDATION_ERROR, str(e), details=e.details)
    except Exception as e:
        logger.error("start_loop 失败: %s", str(e), exc_info=True)
        return make_error_response(
            INTERNAL_ERROR,
            f"内部错误: {str(e)}",
            details={"exception": str(e)},
        )


async def stop_loop(agent_token: str, execution_id: str) -> dict:
    """停止正在运行的循环执行实例（Leader-only）。

    停止循环后，参与的 Agent 将恢复为普通状态，可以接收其他任务。

    Args:
        agent_token: Leader 的身份令牌。
        execution_id: 要停止的执行实例 ID。

    Returns:
        成功: {"execution_id": "...", "status": "paused"}
        失败: {"error": {"code": "...", "message": "..."}}
    """
    logger.info("MCP 调用: stop_loop, execution_id=%s", execution_id)
    try:
        resolved = await _resolve_group_chat(agent_token)
        if isinstance(resolved, dict):
            return resolved

        agent_name, _group_chat_id, group_chat = resolved
        if not _is_leader(group_chat, agent_name):
            return _permission_denied(agent_name, "停止循环")

        execution = await group_chat.stop_loop(execution_id)
        return {"execution_id": execution.execution_id, "status": execution.status}

    except (LoopExecutionNotFoundError, LoopExecutionStateError) as e:
        logger.warning("stop_loop 状态错误: %s", str(e))
        return make_error_response(VALIDATION_ERROR, str(e), details=e.details)
    except Exception as e:
        logger.error("stop_loop 失败: %s", str(e), exc_info=True)
        return make_error_response(
            INTERNAL_ERROR,
            f"内部错误: {str(e)}",
            details={"exception": str(e)},
        )


async def delete_loop(agent_token: str, loop_id: str) -> dict:
    """删除循环定义（Leader-only）。

    删除已完成或已停止的循环。正在运行的循环需要先 stop_loop 再删除。

    Args:
        agent_token: Leader 的身份令牌。
        loop_id: 要删除的循环 ID。

    Returns:
        成功: {"success": true}
        失败: {"error": {"code": "...", "message": "..."}}
    """
    logger.info("MCP 调用: delete_loop, loop_id=%s", loop_id)
    try:
        resolved = await _resolve_group_chat(agent_token)
        if isinstance(resolved, dict):
            return resolved

        agent_name, _group_chat_id, group_chat = resolved
        if not _is_leader(group_chat, agent_name):
            return _permission_denied(agent_name, "删除循环")

        await group_chat.delete_loop(loop_id)
        return {"success": True}

    except (LoopNotFoundError, LoopStateError) as e:
        logger.warning("delete_loop 状态错误: %s", str(e))
        return make_error_response(VALIDATION_ERROR, str(e), details=e.details)
    except Exception as e:
        logger.error("delete_loop 失败: %s", str(e), exc_info=True)
        return make_error_response(
            INTERNAL_ERROR,
            f"内部错误: {str(e)}",
            details={"exception": str(e)},
        )


async def get_loop_status(agent_token: str, execution_id: str) -> dict:
    """查询循环执行状态（任意 Agent 可调用）。

    查询执行实例的当前状态，包括循环进度、当前节点、错误信息等。

    Args:
        agent_token: 调用者的身份令牌。
        execution_id: 要查询的执行实例 ID。

    Returns:
        成功: {
            "execution_id": "执行实例 ID",
            "loop_id": "循环定义 ID",
            "status": "created/running/paused/completed/failed",
            "current_iteration": 当前轮次,
            "max_iterations": 最大轮次,
            "current_node": "当前执行的 Agent 名称",
            "error": "错误信息（仅 failed 状态）"
        }
        失败: {"error": {"code": "...", "message": "..."}}
    """
    logger.info("MCP 调用: get_loop_status, execution_id=%s", execution_id)
    try:
        resolved = await _resolve_group_chat(agent_token)
        if isinstance(resolved, dict):
            return resolved

        _agent_name, _group_chat_id, group_chat = resolved
        return group_chat.get_loop_status(execution_id)

    except LoopExecutionNotFoundError as e:
        logger.warning("get_loop_status LoopExecution 不存在: %s", str(e))
        return make_error_response(VALIDATION_ERROR, str(e), details=e.details)
    except Exception as e:
        logger.error("get_loop_status 失败: %s", str(e), exc_info=True)
        return make_error_response(
            INTERNAL_ERROR,
            f"内部错误: {str(e)}",
            details={"exception": str(e)},
        )


async def list_loops(
    agent_token: str,
) -> dict:
    """查询所有 Loop 定义（任意 Agent 可调用）。

    查询当前群聊的所有 Loop 定义，返回摘要信息。
    不依赖内存，直接读取 JSONL 文件。

    Args:
        agent_token: 调用者的身份令牌。

    Returns:
        成功: {
            "loops": [
                {
                    "loop_id": "循环定义 ID",
                    "name": "循环名称（可选）",
                    "created_at": "创建时间",
                    "updated_at": "更新时间",
                    "max_iterations": 最大轮次,
                    "nodes_count": 节点数量,
                    "in_memory": true/false
                },
                ...
            ]
        }
        失败: {"error": {"code": "...", "message": "..."}}
    """
    logger.info("MCP 调用: list_loops")
    try:
        resolved = await _resolve_group_chat(agent_token)
        if isinstance(resolved, dict):
            return resolved

        _agent_name, _group_chat_id, group_chat = resolved
        loop_manager = group_chat._get_loop_manager()

        loops = loop_manager.list_loops()

        return {"loops": loops}

    except FileSystemError as e:
        logger.warning("list_loops 文件读取失败: %s", str(e))
        return make_error_response(
            FILE_SYSTEM_ERROR,
            str(e),
            details=e.details,
        )
    except Exception as e:
        logger.error("list_loops 失败: %s", str(e), exc_info=True)
        return make_error_response(
            INTERNAL_ERROR,
            f"内部错误: {str(e)}",
            details={"exception": str(e)},
        )


async def list_loop_executions(
    agent_token: str,
    loop_id: str | None = None,
    status: str | None = None,
) -> dict:
    """查询 Loop 执行历史（任意 Agent 可调用）。

    查询当前群聊的所有 Loop 执行实例，返回摘要信息。
    不依赖内存，直接读取 JSONL 文件。

    Args:
        agent_token: 调用者的身份令牌。
        loop_id: 可选的 Loop ID 过滤，只返回该 Loop 的执行历史。
        status: 可选的状态过滤（"created"/"running"/"paused"/"completed"/"failed"）。

    Returns:
        成功: {
            "executions": [
                {
                    "execution_id": "执行实例 ID",
                    "loop_id": "关联的 Loop ID",
                    "initial_task": "初始任务",
                    "status": "执行状态",
                    "created_at": "创建时间",
                    "updated_at": "更新时间",
                    "current_iteration": 当前轮次,
                    "in_memory": true/false
                },
                ...
            ]
        }
        失败: {"error": {"code": "...", "message": "..."}}
    """
    logger.info("MCP 调用: list_loop_executions, loop_id=%s, status=%s", loop_id, status)
    try:
        resolved = await _resolve_group_chat(agent_token)
        if isinstance(resolved, dict):
            return resolved

        _agent_name, _group_chat_id, group_chat = resolved
        loop_execution_manager = group_chat._get_loop_execution_manager()

        executions = loop_execution_manager.list_executions(loop_id=loop_id, status=status)

        return {"executions": executions}

    except FileSystemError as e:
        logger.warning("list_loop_executions 文件读取失败: %s", str(e))
        return make_error_response(
            FILE_SYSTEM_ERROR,
            str(e),
            details=e.details,
        )
    except Exception as e:
        logger.error("list_loop_executions 失败: %s", str(e), exc_info=True)
        return make_error_response(
            INTERNAL_ERROR,
            f"内部错误: {str(e)}",
            details={"exception": str(e)},
        )


# ============================================================================
# Tool 10: health_check
# ============================================================================


async def health_check() -> dict:
    """
    健康检查端点

    Returns:
        成功: {"status": "healthy", "timestamp": "..."}
    """
    logger.info("MCP 调用: health_check")
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================================
# Tool 15: get_memory_context
# ============================================================================


async def get_memory_context(
    agent_token: str,
    group_chat_id: str,
    last_updated: str | None = None,
) -> dict:
    """
    获取记忆助手所需的上下文数据

    Args:
        agent_token: 记忆助手的身份令牌
        group_chat_id: 群聊ID
        last_updated: 上次更新时间（ISO 8601 格式）

    Returns:
        成功: {
            "group_chat_id": "...",
            "last_updated": "...",
            "history_summary": "...",  # 历史总结内容
            "new_messages": "...",     # 新消息内容
            "context": "..."           # 拼接后的完整上下文
        }
        失败: {"error": {"code": "...", "message": "..."}}
    """
    import json
    from datetime import datetime as dt

    logger.info("MCP 调用: get_memory_context, group_chat_id=%s", group_chat_id)
    try:
        # 1. Token 验证
        identity = group_chat_manager.resolve_token(agent_token)
        if identity is None:
            return make_error_response(
                INVALID_TOKEN,
                "身份令牌无效或已过期，请检查 <AGENT_RUNTIME> 块中的 token",
            )

        agent_name, resolved_group_chat_id = identity

        # 2. 校验 group_chat_id 与 token 归属关系
        if group_chat_id != resolved_group_chat_id:
            return make_error_response(
                PERMISSION_DENIED,
                f"权限不足：token 对应群聊 {resolved_group_chat_id}，不能访问群聊 {group_chat_id}",
                details={
                    "requested_group_chat_id": group_chat_id,
                    "token_group_chat_id": resolved_group_chat_id,
                },
            )

        # 3. 角色权限校验：仅记忆助手可调用
        if agent_name != config.default_memory_assistant_name:
            return make_error_response(
                PERMISSION_DENIED,
                f"权限不足：只有记忆助手可以调用此工具，当前 Agent {agent_name} 不是记忆助手",
                details={
                    "agent_name": agent_name,
                    "required_role": config.default_memory_assistant_name,
                },
            )

        # 4. 读取历史总结文件
        history_file = config.memory_path / "agents_hub_history" / "history.jsonl"
        history_summary = ""
        if history_file.exists():
            try:
                lines = history_file.read_text(encoding="utf-8").strip().splitlines()
                if lines:
                    # 取最后一行作为最新总结
                    last_entry = json.loads(lines[-1])
                    history_summary = last_entry.get("summary", "")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("读取 history.jsonl 失败: %s", e)

        # 5. 获取新消息
        after_time = None
        if last_updated:
            try:
                after_time = dt.fromisoformat(last_updated)
            except (ValueError, TypeError):
                logger.warning("last_updated 格式无效: %s，将返回全部消息", last_updated)

        new_messages = get_group_chat_messages(group_chat_id, after_time=after_time)

        # 6. 拼接上下文
        context_parts = []
        if history_summary:
            context_parts.append(f"[历史总结]\n{history_summary}")
        if new_messages:
            context_parts.append(f"[新消息]\n{new_messages}")
        context = "\n\n".join(context_parts) if context_parts else ""

        return {
            "group_chat_id": group_chat_id,
            "last_updated": last_updated or "",
            "history_summary": history_summary,
            "new_messages": new_messages,
            "context": context,
        }

    except Exception as e:
        logger.error("get_memory_context 失败: %s", str(e), exc_info=True)
        return make_error_response(
            INTERNAL_ERROR,
            f"内部错误: {str(e)}",
            details={"exception": str(e)},
        )


# ============================================================================
# 注册工具到 FastMCP
# ============================================================================


def _register_tool_with_docstring(tool_func):
    """注册工具时保留完整 docstring，避免 FastMCP 只暴露第一段摘要。"""
    return mcp.tool(description=inspect.getdoc(tool_func))(tool_func)


_register_tool_with_docstring(call_agent)
_register_tool_with_docstring(assign_tasks_to_team)
_register_tool_with_docstring(archive_task_list)
_register_tool_with_docstring(check_agent_call)
# mcp.tool()(report_progress)
# mcp.tool()(complete_task)
# mcp.tool()(request_permission)
_register_tool_with_docstring(create_group_chat)
_register_tool_with_docstring(create_agent)
_register_tool_with_docstring(create_loop)
_register_tool_with_docstring(start_loop)
_register_tool_with_docstring(stop_loop)
_register_tool_with_docstring(delete_loop)
_register_tool_with_docstring(get_loop_status)
_register_tool_with_docstring(list_loops)
_register_tool_with_docstring(list_loop_executions)
_register_tool_with_docstring(health_check)
_register_tool_with_docstring(get_memory_context)
