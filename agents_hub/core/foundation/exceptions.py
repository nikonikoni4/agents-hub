"""
异常类定义

定义 agents-hub 中使用的所有异常类，提供统一的错误处理机制。
"""


class AgentsHubError(Exception):
    """所有 agents-hub 错误的基类"""

    def __init__(self, message: str, error_code: str, details: dict | None = None):
        self.message = message
        self.error_code = error_code  # 用于 MCP Tool 返回
        self.details = details or {}
        super().__init__(message)

    def to_mcp_response(self) -> dict:
        """转换为 MCP Tool 的错误响应格式"""
        return {
            "success": False,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


# ==================== 业务错误 ====================

class AgentNotFoundError(AgentsHubError):
    """Agent 不存在"""

    def __init__(self, agent_name: str):
        super().__init__(
            message=f"Agent '{agent_name}' 不存在，请检查 agent 名称是否正确",
            error_code="AGENT_NOT_FOUND",
            details={"agent_name": agent_name}
        )


class GroupChatNotFoundError(AgentsHubError):
    """GroupChat 不存在"""

    def __init__(self, group_chat_id: str):
        super().__init__(
            message=f"GroupChat '{group_chat_id}' 不存在",
            error_code="GROUP_CHAT_NOT_FOUND",
            details={"group_chat_id": group_chat_id}
        )


class MessageDeliveryError(AgentsHubError):
    """消息投递失败"""

    def __init__(self, reason: str, send_from: str, send_to: str):
        super().__init__(
            message=f"消息投递失败: {reason}",
            error_code="MESSAGE_DELIVERY_FAILED",
            details={"send_from": send_from, "send_to": send_to, "reason": reason}
        )


class AgentExecutionError(AgentsHubError):
    """Agent 执行失败"""

    def __init__(self, agent_name: str, reason: str):
        super().__init__(
            message=f"Agent '{agent_name}' 执行失败: {reason}",
            error_code="AGENT_EXECUTION_FAILED",
            details={"agent_name": agent_name, "reason": reason}
        )


class AgentTimeoutError(AgentsHubError):
    """Agent 执行超时"""

    def __init__(self, agent_name: str, timeout_seconds: int):
        super().__init__(
            message=f"Agent '{agent_name}' 执行超时（{timeout_seconds}秒）",
            error_code="AGENT_TIMEOUT",
            details={"agent_name": agent_name, "timeout_seconds": timeout_seconds}
        )


# ==================== 验证错误 ====================

class InvalidMessageError(AgentsHubError):
    """消息格式错误"""

    def __init__(self, reason: str):
        super().__init__(
            message=f"消息格式错误: {reason}",
            error_code="INVALID_MESSAGE",
            details={"reason": reason}
        )


# ==================== 系统错误 ====================

class FileSystemError(AgentsHubError):
    """文件系统错误"""

    def __init__(self, operation: str, path: str, reason: str):
        super().__init__(
            message=f"文件系统错误: {operation} '{path}' 失败 - {reason}",
            error_code="FILE_SYSTEM_ERROR",
            details={"operation": operation, "path": path, "reason": reason}
        )


class CompactionError(AgentsHubError):
    """压缩失败"""

    def __init__(self, reason: str):
        super().__init__(
            message=f"消息压缩失败: {reason}",
            error_code="COMPACTION_FAILED",
            details={"reason": reason}
        )
