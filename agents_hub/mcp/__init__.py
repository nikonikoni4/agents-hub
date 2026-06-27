"""
MCP 层

提供 MCP (Model Context Protocol) 相关的工具和服务。
"""

from agents_hub.mcp.errors import (  # noqa: E402
    AGENT_ALREADY_EXISTS,
    AGENT_CALL_NOT_FOUND,
    AGENT_NOT_FOUND,
    AGENT_OFFLINE,
    GROUP_CHAT_NOT_FOUND,
    INTERNAL_ERROR,
    INVALID_AGENT_CALL_STATE,
    INVALID_TASK_FORMAT,
    # 错误码常量
    INVALID_TOKEN,
    PERMISSION_DENIED,
    TASK_LIST_NOT_FOUND,
    VALIDATION_ERROR,
    # 错误响应函数
    make_error_response,
)
from agents_hub.mcp.server import (
    archive_task_list,
    assign_tasks_to_team,
    bind_to_group_chat,
    bind_to_single_chat,
    call_agent,
    check_agent_call,
    # complete_task,
    create_agent,
    create_group_chat,
    create_loop,
    create_single_chat,
    delete_loop,
    get_current_binding,
    get_loop_status,
    get_memory_context,
    list_group_chats,
    list_loop_executions,
    list_loops,
    list_single_chat_history,
    # report_progress,
    start_loop,
    stop_loop,
)

__all__ = [
    # 错误码常量
    "INVALID_TOKEN",
    "PERMISSION_DENIED",
    "GROUP_CHAT_NOT_FOUND",
    "AGENT_NOT_FOUND",
    "AGENT_ALREADY_EXISTS",
    "TASK_LIST_NOT_FOUND",
    "AGENT_CALL_NOT_FOUND",
    "INVALID_AGENT_CALL_STATE",
    "INVALID_TASK_FORMAT",
    "VALIDATION_ERROR",
    "AGENT_OFFLINE",
    "INTERNAL_ERROR",
    # 错误响应函数
    "make_error_response",
    # MCP 工具
    "call_agent",
    "assign_tasks_to_team",
    "archive_task_list",
    "check_agent_call",
    # "complete_task",
    # "report_progress",
    "create_group_chat",
    "create_agent",
    "create_loop",
    "start_loop",
    "stop_loop",
    "delete_loop",
    "get_loop_status",
    "list_loops",
    "list_loop_executions",
    "get_memory_context",
    # 飞书管理工具
    "list_group_chats",
    "list_single_chat_history",
    "bind_to_group_chat",
    "bind_to_single_chat",
    "create_single_chat",
    "get_current_binding",
]
