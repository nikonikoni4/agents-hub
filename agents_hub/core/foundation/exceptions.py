"""
异常类定义

定义 agents-hub 中使用的所有异常类，提供统一的错误处理机制。
"""

from agents_hub.exceptions import AgentsHubError as _TopLevelAgentsHubError

__all__ = [
    "AgentsHubError",
    "AgentNotFoundError",
    "GroupChatNotFoundError",
    "MessageDeliveryError",
    "AgentExecutionError",
    "AgentTimeoutError",
    "ValidationError",
    "ExternalServiceError",
    "InvalidMessageError",
    "FileSystemError",
    "CompactionError",
    "DockerConfigError",
    "DockerNotAvailableError",
    "DockerStartError",
]


class AgentsHubError(_TopLevelAgentsHubError):
    """所有 agents-hub 错误的基类（继承顶层 AgentsHubError，统一异常层级）"""

    def __init__(self, message: str, error_code: str, details: dict | None = None):
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
        )

    def to_mcp_response(self) -> dict:
        """转换为 MCP Tool 的错误响应格式"""
        return {
            "success": False,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# ==================== 业务错误 ====================


class AgentNotFoundError(AgentsHubError):
    """Agent 不存在"""

    def __init__(self, agent_name: str):
        super().__init__(
            message=f"Agent '{agent_name}' 不存在，请检查 agent 名称是否正确",
            error_code="AGENT_NOT_FOUND",
            details={"agent_name": agent_name},
        )


class GroupChatNotFoundError(AgentsHubError):
    """GroupChat 不存在"""

    def __init__(self, group_chat_id: str):
        super().__init__(
            message=f"GroupChat '{group_chat_id}' 不存在",
            error_code="GROUP_CHAT_NOT_FOUND",
            details={"group_chat_id": group_chat_id},
        )


class MessageDeliveryError(AgentsHubError):
    """消息投递失败"""

    def __init__(self, reason: str, send_from: str, send_to: str):
        super().__init__(
            message=f"消息投递失败: {reason}",
            error_code="MESSAGE_DELIVERY_FAILED",
            details={"send_from": send_from, "send_to": send_to, "reason": reason},
        )


class AgentExecutionError(AgentsHubError):
    """Agent 执行失败"""

    def __init__(self, agent_name: str, reason: str, session_id: str, platform: str):
        super().__init__(
            message=f"Agent '{agent_name}' 执行失败: {reason} session_id:{session_id},platform:{platform}",
            error_code="AGENT_EXECUTION_FAILED",
            details={"agent_name": agent_name, "reason": reason},
        )


class AgentTimeoutError(AgentsHubError):
    """Agent 执行超时"""

    def __init__(self, agent_name: str, timeout_seconds: int):
        super().__init__(
            message=f"Agent '{agent_name}' 执行超时（{timeout_seconds}秒）",
            error_code="AGENT_TIMEOUT",
            details={"agent_name": agent_name, "timeout_seconds": timeout_seconds},
        )


# ==================== 通用异常分类 ====================


class ValidationError(AgentsHubError):
    """验证错误：输入参数不符合要求"""

    pass


class ExternalServiceError(AgentsHubError):
    """外部服务错误：外部服务调用失败"""

    pass


# ==================== 验证错误 ====================


class InvalidMessageError(AgentsHubError):
    """消息格式错误"""

    def __init__(self, reason: str):
        super().__init__(
            message=f"消息格式错误: {reason}",
            error_code="INVALID_MESSAGE",
            details={"reason": reason},
        )


# ==================== 系统错误 ====================


class FileSystemError(AgentsHubError):
    """文件系统错误"""

    def __init__(self, operation: str, path: str, reason: str):
        super().__init__(
            message=f"文件系统错误: {operation} '{path}' 失败 - {reason}",
            error_code="FILE_SYSTEM_ERROR",
            details={"operation": operation, "path": path, "reason": reason},
        )


class CompactionError(AgentsHubError):
    """压缩失败"""

    def __init__(self, reason: str):
        super().__init__(
            message=f"消息压缩失败: {reason}",
            error_code="COMPACTION_FAILED",
            details={"reason": reason},
        )


# ==================== Docker 异常 ====================


class DockerConfigError(ValidationError):
    """Docker 配置不合理"""

    def __init__(self, agent_name: str, group_chat_id: str, reason: str):
        self.agent_name = agent_name
        self.group_chat_id = group_chat_id
        self.reason = reason
        message = (
            f"Agent '{agent_name}' 在群聊 '{group_chat_id}' 中的 Docker 配置不合理：\n{reason}"
        )
        super().__init__(
            message=message,
            error_code="DOCKER_CONFIG_ERROR",
            details={"agent_name": agent_name, "group_chat_id": group_chat_id, "reason": reason},
        )


class DockerNotAvailableError(ExternalServiceError):
    """Docker Engine 不可用"""

    def __init__(self, agent_name: str, group_chat_id: str, message: str):
        self.agent_name = agent_name
        self.group_chat_id = group_chat_id
        super().__init__(
            message=message,
            error_code="DOCKER_NOT_AVAILABLE",
            details={"agent_name": agent_name, "group_chat_id": group_chat_id},
        )


class DockerStartError(ExternalServiceError):
    """Docker 容器启动失败"""

    def __init__(self, container_name: str, reason: str):
        self.container_name = container_name
        super().__init__(
            message=f"容器 '{container_name}' 启动失败：{reason}",
            error_code="DOCKER_START_FAILED",
            details={"container_name": container_name, "reason": reason},
        )
