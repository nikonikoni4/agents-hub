"""
MCP 层

提供 MCP (Model Context Protocol) 相关的工具和服务。
"""

from agents_hub.mcp.errors import (
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
    # 错误响应函数
    make_error_response,
)
from agents_hub.mcp.server import (
    archive_task_list,
    assign_tasks_to_team,
    call_agent,
    check_agent_call,
    create_agent,
    create_group_chat,
    finish_agent_call,
    speak_in_group_chat,
)

__all__ = [
    # 错误码常量
    "INVALID_TOKEN",
    "PERMISSION_DENIED",
    "GROUP_CHAT_NOT_FOUND",
    "AGENT_NOT_FOUND",
    "TASK_LIST_NOT_FOUND",
    "AGENT_CALL_NOT_FOUND",
    "INVALID_AGENT_CALL_STATE",
    "INVALID_TASK_FORMAT",
    "AGENT_OFFLINE",
    "INTERNAL_ERROR",
    # 错误响应函数
    "make_error_response",
    # MCP 工具
    "call_agent",
    "assign_tasks_to_team",
    "archive_task_list",
    "check_agent_call",
    "finish_agent_call",
    "speak_in_group_chat",
    "create_group_chat",
    "create_agent",
]
