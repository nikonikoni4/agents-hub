# agents_hub/exceptions.py
"""
agents-hub 顶层异常基类
所有模块的异常都继承自这里

设计原则：
1. 所有异常继承自 AgentsHubError
2. 按"谁应该处理"分类（验证/资源/状态/外部服务/系统）
3. 携带足够的上下文信息（error_code, details, cause）
4. 支持转换为 JSON 响应（to_dict）
"""

from typing import Any


class AgentsHubError(Exception):
    """所有 agents-hub 异常的基类

    设计要点：
    1. 提供统一的错误信息格式
    2. 支持错误码（用于 API/MCP 响应）
    3. 携带上下文信息（便于调试和日志）
    4. 保留原始异常链
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        """
        Args:
            message: 人类可读的错误信息
            error_code: 错误码（用于 API 响应），默认为类名
            details: 上下文信息字典（用于调试和日志）
            cause: 原始异常（用于异常链）
        """
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause
        super().__init__(message)

    def __str__(self) -> str:
        """人类可读的错误信息"""
        base = f"[{self.error_code}] {self.message}"
        if self.details:
            base += f" | Details: {self.details}"
        if self.cause:
            base += f" | Caused by: {type(self.cause).__name__}: {self.cause}"
        return base

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于 JSON 响应）"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "type": self.__class__.__name__
        }


# ==================== 通用异常分类（按"谁应该处理"分类） ====================

class ValidationError(AgentsHubError):
    """验证错误

    特征：输入参数不符合要求
    处理策略：返回详细的错误信息，帮助调用者修正

    示例：
    - 参数缺失或格式错误
    - 数据不符合约束
    - 消息内容为空
    """
    pass


class ResourceNotFoundError(AgentsHubError):
    """资源不存在错误

    特征：请求的资源不存在
    处理策略：返回 404 类错误，提示可用资源

    示例：
    - Agent 不存在
    - GroupChat 不存在
    - Role 不存在
    """
    pass


class StateError(AgentsHubError):
    """状态错误

    特征：在错误的状态下执行操作
    处理策略：返回当前状态和期望状态，提示正确的操作顺序

    示例：
    - 无效的状态转换（PENDING → COMPLETED，跳过 RUNNING）
    - Agent 未就绪时调用
    - 重复操作（已完成的任务再次执行）
    """
    pass


class ExternalServiceError(AgentsHubError):
    """外部服务错误

    特征：外部服务调用失败
    处理策略：区分可恢复和不可恢复错误，可恢复的自动重试

    示例：
    - LLM API 错误（限流、超时、无效响应）
    - 文件系统错误（权限不足、磁盘满）
    - Agent Bridge 错误（平台不支持、CLI 执行失败）
    """
    pass


# ==================== 可恢复错误标记 ====================

class RecoverableError(AgentsHubError):
    """可恢复错误（用于重试逻辑）

    特征：系统可以自动重试解决
    处理策略：自动重试（带指数退避）

    示例：
    - API 限流（429 错误）
    - 临时网络故障
    - 队列临时满

    注意：具体的可恢复错误应该继承自 ExternalServiceError 和 RecoverableError
    """

    def __init__(self, message: str, retry_after: float = 1.0, **kwargs):
        """
        Args:
            message: 错误信息
            retry_after: 建议的重试延迟（秒）
            **kwargs: 传递给 AgentsHubError 的其他参数
        """
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
