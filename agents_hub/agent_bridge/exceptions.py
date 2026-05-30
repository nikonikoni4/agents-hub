"""Agent Bridge 模块的自定义异常

所有异常继承自顶层 agents_hub.exceptions，遵循统一的错误处理规范。
"""

from agents_hub.exceptions import ExternalServiceError, ValidationError, RecoverableError


class AgentBridgeError(ExternalServiceError):
    """Agent Bridge 错误基类

    特征：Agent 平台调用失败
    处理策略：区分可恢复和不可恢复错误
    """
    pass


class CLINotFoundError(AgentBridgeError):
    """CLI 命令不存在

    特征：找不到 Claude CLI 或 Codex CLI 可执行文件
    处理策略：返回详细错误信息，提示安装对应平台

    示例：
    - claude 命令不在 PATH 中
    - codex 命令不在 PATH 中
    """

    def __init__(self, platform: str, command: str):
        super().__init__(
            message=f"{platform} CLI 不存在: {command}",
            error_code="CLI_NOT_FOUND",
            details={
                "platform": platform,
                "command": command
            }
        )


class CLIExecutionError(AgentBridgeError):
    """CLI 执行失败

    特征：CLI 进程启动失败或异常退出
    处理策略：返回详细错误信息，包含退出码和错误输出

    示例：
    - CLI 进程返回非零退出码
    - CLI 进程被信号终止
    """

    def __init__(self, platform: str, exit_code: int, stderr: str):
        super().__init__(
            message=f"{platform} CLI 执行失败 (exit code: {exit_code})",
            error_code="CLI_EXECUTION_ERROR",
            details={
                "platform": platform,
                "exit_code": exit_code,
                "stderr": stderr
            }
        )


class ParseError(AgentBridgeError):
    """解析错误

    特征：无法解析 CLI 输出
    处理策略：记录原始输出，返回解析错误信息

    示例：
    - JSON 格式错误
    - 缺少必需字段
    - 数据类型不匹配
    """

    def __init__(self, platform: str, raw_line: str, reason: str):
        super().__init__(
            message=f"{platform} 输出解析失败: {reason}",
            error_code="PARSE_ERROR",
            details={
                "platform": platform,
                "raw_line": raw_line[:200],  # 只保留前 200 字符
                "reason": reason
            }
        )


class PlatformNotSupportedError(ValidationError):
    """平台不支持

    特征：请求的平台类型不支持
    处理策略：返回支持的平台列表

    示例：
    - 请求未知的平台类型
    """

    def __init__(self, platform: str, supported_platforms: list[str]):
        super().__init__(
            message=f"平台 '{platform}' 不支持",
            error_code="PLATFORM_NOT_SUPPORTED",
            details={
                "platform": platform,
                "supported_platforms": supported_platforms
            }
        )


class AgentTimeoutError(AgentBridgeError, RecoverableError):
    """Agent 执行超时

    特征：Agent 执行超过指定时间
    处理策略：可以重试，建议增加超时时间

    示例：
    - Agent 执行时间过长
    - 网络延迟导致超时
    """

    def __init__(self, platform: str, timeout_seconds: float):
        AgentBridgeError.__init__(
            self,
            message=f"{platform} Agent 执行超时 ({timeout_seconds}秒)",
            error_code="AGENT_TIMEOUT",
            details={
                "platform": platform,
                "timeout_seconds": timeout_seconds
            }
        )
        RecoverableError.__init__(
            self,
            message=f"{platform} Agent 执行超时 ({timeout_seconds}秒)",
            retry_after=5.0
        )
