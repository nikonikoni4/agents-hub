"""
Agent 调用管理器

统一管理所有跨 Agent 的异步调用。
"""

from datetime import datetime

from agents_hub.core.foundation import CallStatus, MessageType

from .agent_call import AgentCall


class AgentCallManager:
    """统一管理所有跨 Agent 的异步调用"""

    def __init__(self):
        self._calls: dict[str, AgentCall] = {}  # call_id -> AgentCall

        # TODO: 未实现的功能
        # 1. 与 util 统一的 logger，但 agentCall 单独保存一份
        #    需要一个 logger 的变体类独立用于 AgentCallManager
        # 2. 轮询线程，用于判断是否需要删除已经完成的 AgentCall
        # 3. 超时检查：定期调用 AgentCall.is_timeout() 检查超时

    def create_call(
        self,
        send_from: str,
        send_to: str,
        content: str,
        message_type: MessageType,
        timeout_seconds: int | None = None,
        business_task_id: str | None = None,
    ) -> AgentCall:
        """
        创建新调用

        Args:
            send_from: 发送者名称
            send_to: 接收者名称
            content: 消息内容
            message_type: 消息类型（TASK/NOTIFICATION）
            timeout_seconds: 超时阈值（秒），None 表示无超时限制
            business_task_id: 关联的业务任务 ID（可选）

        Returns:
            AgentCall: 创建的调用记录
        """
        call = AgentCall(
            send_from=send_from,
            send_to=send_to,
            content=content,
            message_type=message_type,
            timeout_seconds=timeout_seconds,
            business_task_id=business_task_id,
        )
        self._calls[call.call_id] = call
        return call

    def get_call(self, call_id: str) -> AgentCall | None:
        """
        获取调用详情

        Args:
            call_id: 调用 ID

        Returns:
            AgentCall | None: 调用记录，不存在则返回 None
        """
        return self._calls.get(call_id)

    def update_status(self, call_id: str, status: CallStatus):
        """
        更新调用状态

        Args:
            call_id: 调用 ID
            status: 新状态
        """
        if call := self._calls.get(call_id):
            call.status = status
            if status == CallStatus.RUNNING:
                call.started_at = datetime.now()
            elif status in (CallStatus.COMPLETED, CallStatus.FAILED, CallStatus.TIMEOUT):
                call.completed_at = datetime.now()

    def set_result(self, call_id: str, result: object):
        """
        设置调用结果

        Args:
            call_id: 调用 ID
            result: 执行结果（AgentResult）
        """
        if call := self._calls.get(call_id):
            call.result = result
            call.status = CallStatus.COMPLETED
            call.completed_at = datetime.now()

    def set_error(self, call_id: str, error: str):
        """
        设置调用错误

        Args:
            call_id: 调用 ID
            error: 错误信息
        """
        if call := self._calls.get(call_id):
            call.error = error
            call.status = CallStatus.FAILED
            call.completed_at = datetime.now()
