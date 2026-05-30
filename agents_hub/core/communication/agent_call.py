"""
Agent 调用记录

记录一次 Agent 调用的完整信息，包括状态、结果、错误等。
"""
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from agents_hub.core.foundation import AgentMessage, CallStatus


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
    to_agent_message: AgentMessage  # 复用 AgentMessage，避免重复定义
    call_id: str = field(default_factory=lambda: str(uuid4())[:8])
    status: CallStatus = field(default=CallStatus.PENDING)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: object | None = None  # 执行结果（AgentResult，避免循环依赖暂用 object）
    error: str | None = None  # 错误信息
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

    def can_be_deleted(self) -> bool:
        """
        判断是否可以删除

        TODO: 删除逻辑未确认，需要根据以下因素决定：
        1. 已完成且超过一定时间（如 1 小时）？
        2. NOTIFICATION 类型的消息完成后立即删除？
        3. TASK 类型的消息需要保留更久？
        4. 是否需要考虑 business_task_id 关联？
        5. 是否需要持久化到磁盘以便审计和恢复？

        Returns:
            bool: 是否可以删除
        """
        return False
