"""
Agent 调用记录

记录一次 Agent 调用的完整信息，包括状态、结果、错误等。
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from agents_hub.core.foundation import CallStatus, MessageType


@dataclass
class AgentCall:
    """
    Agent 调用记录

    生命周期：
    1. 创建：
       - MCP Tool 调用 call_agent 时创建
       - User 在群聊中 @agent 时创建
       - MessageType 是 TASK 类型时，完成后系统主动返回信息给发送者

    2. 状态变更：
       - 创建时：PENDING
       - execute 之前：RUNNING
       - 运行完成：COMPLETED（成功）/ FAILED（失败）/ TIMEOUT（超时）

    3. 删除：
       - 为减小内存占用，需要删除无用的调用信息
       - 删除逻辑依赖于 message_type（待实现）
    """

    send_from: str
    send_to: str
    content: str
    message_type: MessageType
    call_id: str = field(default_factory=lambda: str(uuid4())[:8])
    status: CallStatus = field(default=CallStatus.PENDING)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: object | None = None  # 执行结果（AgentResult，避免循环依赖暂用 object）
    error: str | None = None  # 错误信息
    has_agent_response: bool = False  # Agent 是否已通过显式工具回复并闭环
    business_task_id: str | None = None  # 关联的业务任务 ID（可选）
    timeout_seconds: int | None = None  # 超时阈值（秒），None 表示无超时限制

    def is_timeout(self) -> bool:
        """
        判断是否超时

        Returns:
            bool: 是否超时
        """
        # 已完成的调用不会超时
        if self.status in (CallStatus.COMPLETED, CallStatus.FAILED, CallStatus.TIMEOUT):
            return False

        # 无超时限制
        if self.timeout_seconds is None:
            return False

        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > self.timeout_seconds

    def can_be_deleted(self, retention_config: dict[str, int] | None = None) -> bool:
        """
        判断是否可以删除

        删除策略：
        1. 运行中的调用（PENDING/RUNNING）：不删除
        2. 有业务任务关联的调用：不删除（由业务任务管理器决定）
        3. NOTIFICATION 类型 + COMPLETED：完成后 5 分钟可删除
        4. TASK 类型 + COMPLETED：完成后 1 小时可删除
        5. FAILED/TIMEOUT：完成后 24 小时可删除（用于调试）

        Args:
            retention_config: 自定义保留时间配置（秒），格式：
                {
                    "notification_completed": 300,  # NOTIFICATION 完成后保留 5 分钟
                    "task_completed": 3600,         # TASK 完成后保留 1 小时
                    "failed": 86400,                # 失败后保留 24 小时
                }

        Returns:
            bool: 是否可以删除
        """
        # 默认保留时间配置（秒）
        default_retention = {
            "notification_completed": 300,  # 5 分钟
            "task_completed": 3600,  # 1 小时
            "failed": 86400,  # 24 小时
        }
        retention = retention_config or default_retention

        # 1. 运行中的调用不删除
        if self.status in (CallStatus.PENDING, CallStatus.RUNNING):
            return False

        # 2. 有业务任务关联的调用不删除
        if self.business_task_id is not None:
            return False

        # 3. 必须有完成时间才能判断
        if self.completed_at is None:
            return False

        # 计算完成后经过的时间
        elapsed_since_completion = (datetime.now() - self.completed_at).total_seconds()

        # 4. 根据状态和消息类型判断
        if self.status == CallStatus.COMPLETED:
            if self.message_type == MessageType.NOTIFICATION:
                # NOTIFICATION 完成后 5 分钟可删除
                return elapsed_since_completion > retention["notification_completed"]
            elif self.message_type == MessageType.TASK:
                # TASK 完成后 1 小时可删除
                return elapsed_since_completion > retention["task_completed"]

        elif self.status in (CallStatus.FAILED, CallStatus.TIMEOUT):
            # 失败/超时后 24 小时可删除
            return elapsed_since_completion > retention["failed"]

        # 默认不删除
        return False
