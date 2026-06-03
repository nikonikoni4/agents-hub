"""
MCP 错误响应工具

提供统一的错误码和错误响应格式，用于 MCP 工具的错误处理。
错误信息包含足够的上下文，帮助 LLM 自纠。
"""

# ============================================================================
# 错误码常量
# ============================================================================

# 身份令牌无效或已过期
INVALID_TOKEN = "INVALID_TOKEN"

# 权限不足（非 Leader 调用 Leader-only 工具）
PERMISSION_DENIED = "PERMISSION_DENIED"

# 群聊不存在
GROUP_CHAT_NOT_FOUND = "GROUP_CHAT_NOT_FOUND"

# Agent 不存在
AGENT_NOT_FOUND = "AGENT_NOT_FOUND"

# 任务列表不存在
TASK_LIST_NOT_FOUND = "TASK_LIST_NOT_FOUND"

# AgentCall 不存在
AGENT_CALL_NOT_FOUND = "AGENT_CALL_NOT_FOUND"

# AgentCall 当前状态不允许执行该操作
INVALID_AGENT_CALL_STATE = "INVALID_AGENT_CALL_STATE"

# 任务格式错误
INVALID_TASK_FORMAT = "INVALID_TASK_FORMAT"

# Agent 离线或不可用
AGENT_OFFLINE = "AGENT_OFFLINE"

# 内部错误
INTERNAL_ERROR = "INTERNAL_ERROR"


# ============================================================================
# 错误响应函数
# ============================================================================


def make_error_response(code: str, message: str, details: dict | None = None) -> dict:
    """
    生成统一格式的错误响应

    Args:
        code: 错误码（使用上面定义的常量）
        message: 错误消息（应包含足够的上下文帮助 LLM 自纠）
        details: 可选的详细信息字典

    Returns:
        错误响应字典，格式为：
        {
            "error": {
                "code": "INVALID_TOKEN",
                "message": "身份令牌无效或已过期，请检查 <AGENT_RUNTIME> 块中的 token",
                "details": {...}  # 可选
            }
        }

    Examples:
        >>> make_error_response(INVALID_TOKEN, "身份令牌无效")
        {'error': {'code': 'INVALID_TOKEN', 'message': '身份令牌无效'}}

        >>> make_error_response(
        ...     AGENT_NOT_FOUND,
        ...     "Agent 不存在",
        ...     details={"agent_id": "agent_123", "available_agents": ["agent_1"]}
        ... )
        {'error': {'code': 'AGENT_NOT_FOUND', 'message': 'Agent 不存在', 'details': {...}}}
    """
    error_dict: dict[str, str | dict] = {
        "code": code,
        "message": message,
    }

    # 只有当 details 不为 None 时才添加 details 字段
    if details is not None:
        error_dict["details"] = details

    return {"error": error_dict}
