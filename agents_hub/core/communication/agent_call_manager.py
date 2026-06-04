"""
Agent 调用管理器

统一管理所有跨 Agent 的异步调用。
"""

import asyncio
import contextlib
import json
from datetime import datetime

from agents_hub.core.foundation import CallStatus, MessageType, group_chat_paths
from agents_hub.utils.logger import get_specialized_logger

from .agent_call import AgentCall


class AgentCallManager:
    """统一管理所有跨 Agent 的异步调用"""

    def __init__(
        self,
        group_chat_id: str,
        project_path: str,
        cleanup_interval: int = 60,
        retention_config: dict[str, int] | None = None,
    ):
        """
        初始化 AgentCallManager

        Args:
            group_chat_id: 群聊 ID
            project_path: 项目路径
            cleanup_interval: 清理检查间隔（秒），默认 60 秒
            retention_config: 自定义保留时间配置（秒），格式见 AgentCall.can_be_deleted()
        """
        self._calls: dict[str, AgentCall] = {}  # call_id -> AgentCall
        self._calls_by_receiver: dict[str, list[str]] = {}  # agent_name -> call_id list
        self._cleanup_task: asyncio.Task | None = None
        self._running = False
        self._cleanup_interval = cleanup_interval
        self._retention_config = retention_config

        # 创建专用logger：每个群聊有独立的日志目录
        log_dir = group_chat_paths.base_dir(group_chat_id, project_path)
        self.logger = get_specialized_logger(
            name=f"agent_call_manager.{group_chat_id}",
            log_filename="agent_calls.log",
            also_to_global=True,
            log_dir=log_dir,
        )

        # 持久化路径
        self._persistence_path = group_chat_paths.agent_calls_data(group_chat_id, project_path)
        self._persistence_path.parent.mkdir(parents=True, exist_ok=True)

        # 加载历史调用记录
        self._load_from_persistence()

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
        self._index_call(call)
        self.logger.info(
            f"创建调用 {call.call_id}: {send_from} -> {send_to}, "
            f"类型={message_type.value}, 超时={timeout_seconds}s"
        )

        # 立即持久化
        self._persist_call(call)

        return call

    def get_call(self, call_id: str) -> AgentCall | None:
        """
        获取调用详情

        Args:
            call_id: 调用 ID

        Returns:
            AgentCall | None: 调用记录，不存在则返回 None
        """
        if call := self._calls.get(call_id):
            return call

        # 查询不到，记录警告日志
        self.logger.warning(f"调用 {call_id} 不存在，可能已被清理或系统重启导致数据丢失")
        return None

    def get_runtime_calls_for_agent(self, agent_name: str) -> list[AgentCall]:
        """
        获取需要注入到指定接收方 runtime 的调用列表。

        TASK 调用在接收方显式回复闭环前持续暴露；NOTIFICATION 调用只在完成前暴露。
        """
        calls: list[AgentCall] = []
        for call_id in self._calls_by_receiver.get(agent_name, []):
            call = self._calls.get(call_id)
            if call is None:
                continue
            if self._should_include_in_runtime(call):
                calls.append(call)
        return calls

    def update_status(self, call_id: str, status: CallStatus):
        """
        更新调用状态

        Args:
            call_id: 调用 ID
            status: 新状态
        """
        if call := self._calls.get(call_id):
            old_status = call.status
            call.status = status
            if status == CallStatus.RUNNING:
                call.started_at = datetime.now()
            elif status in (CallStatus.COMPLETED, CallStatus.FAILED, CallStatus.TIMEOUT):
                call.completed_at = datetime.now()

            self.logger.info(f"调用 {call_id} 状态变更: {old_status.value} -> {status.value}")

            # 更新持久化
            self._persist_call(call)

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
            self.logger.info(f"调用 {call_id} 完成，结果类型: {type(result).__name__}")

            # 更新持久化
            self._persist_call(call)

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
            self.logger.error(f"调用 {call_id} 失败: {error}")

            # 更新持久化
            self._persist_call(call)

    def mark_agent_response(self, call_id: str, content: str, success: bool = True):
        """
        标记调用已被接收方 Agent 显式回复闭环。

        Args:
            call_id: 调用 ID
            content: Agent 对调用方的最终回复内容
            success: True 表示任务完成，False 表示任务失败或无法继续
        """
        if call := self._calls.get(call_id):
            call.has_agent_response = True
            if success:
                call.result = content
                call.status = CallStatus.COMPLETED
                call.error = None
            else:
                call.error = content
                call.status = CallStatus.FAILED
            call.completed_at = datetime.now()
            self.logger.info(
                f"调用 {call_id} 已显式回复闭环: status={call.status.value}, success={success}"
            )
            self._persist_call(call)

    def _load_from_persistence(self):
        """从持久化文件加载历史调用记录"""
        if not self._persistence_path.exists():
            self.logger.info("持久化文件不存在，跳过加载")
            return

        try:
            call_records = {}  # call_id -> 最新记录

            with open(self._persistence_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    data = json.loads(line)
                    call_id = data["call_id"]
                    # 后面的记录覆盖前面的（取最新）
                    call_records[call_id] = data

            # 反序列化
            for call_id, data in call_records.items():
                call = self._deserialize_call(data)
                self._calls[call_id] = call
                self._index_call(call)

            self.logger.info(f"从持久化文件加载了 {len(call_records)} 个历史调用记录")

        except Exception as e:
            self.logger.error(f"加载持久化文件失败: {e}", exc_info=True)

    def _deserialize_call(self, data: dict) -> AgentCall:
        """从字典反序列化 AgentCall"""
        return AgentCall(
            call_id=data["call_id"],
            send_from=data["send_from"],
            send_to=data["send_to"],
            content=data["content"],
            message_type=MessageType(data["message_type"]),
            status=CallStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=(
                datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
            ),
            error=data.get("error"),
            has_agent_response=data.get("has_agent_response", False),
            business_task_id=data.get("business_task_id"),
            timeout_seconds=data.get("timeout_seconds"),
            # result 不持久化，重启后为 None
            result=None,
        )

    def _persist_call(self, call: AgentCall):
        """持久化单个调用记录（追加模式）"""
        try:
            data = {
                "call_id": call.call_id,
                "send_from": call.send_from,
                "send_to": call.send_to,
                "content": call.content,
                "message_type": call.message_type.value,
                "status": call.status.value,
                "created_at": call.created_at.isoformat(),
                "started_at": call.started_at.isoformat() if call.started_at else None,
                "completed_at": (call.completed_at.isoformat() if call.completed_at else None),
                "error": call.error,
                "has_agent_response": call.has_agent_response,
                "business_task_id": call.business_task_id,
                "timeout_seconds": call.timeout_seconds,
                # result 不持久化（可能很大，且重启后无法恢复）
            }

            with open(self._persistence_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")

        except Exception as e:
            self.logger.error(f"持久化调用记录失败: {e}", exc_info=True)

    async def _cleanup_loop(self):
        """
        后台清理循环

        定期执行以下任务：
        1. 检查并删除可以删除的 AgentCall
        2. 检查并更新超时的 AgentCall
        """
        self.logger.info(f"启动清理循环，检查间隔: {self._cleanup_interval}秒")

        while self._running:
            try:
                await asyncio.sleep(self._cleanup_interval)

                # 1. 检查超时
                timeout_count = self._check_timeouts()
                if timeout_count > 0:
                    self.logger.warning(f"检测到 {timeout_count} 个超时调用")

                # 2. 清理可删除的调用
                deleted_count = self._cleanup_deletable_calls()
                if deleted_count > 0:
                    self.logger.info(
                        f"清理完成，删除 {deleted_count} 个调用，当前剩余 {len(self._calls)} 个调用"
                    )

            except asyncio.CancelledError:
                self.logger.info("清理循环被取消")
                break
            except Exception as e:
                self.logger.error(f"清理循环发生错误: {e}", exc_info=True)

    def _check_timeouts(self) -> int:
        """
        检查并更新超时的调用

        Returns:
            int: 超时调用的数量
        """
        timeout_count = 0
        for call_id, call in list(self._calls.items()):
            if call.is_timeout():
                self.update_status(call_id, CallStatus.TIMEOUT)
                timeout_count += 1
        return timeout_count

    def _cleanup_deletable_calls(self) -> int:
        """
        清理可删除的调用

        Returns:
            int: 删除的调用数量
        """
        deleted_count = 0
        for call_id, call in list(self._calls.items()):
            if call.can_be_deleted(self._retention_config):
                self.logger.debug(
                    f"删除调用 {call_id}: {call.send_from} -> {call.send_to}, "
                    f"状态={call.status.value}, 类型={call.message_type.value}"
                )
                del self._calls[call_id]
                self._unindex_call(call)
                deleted_count += 1

        # 如果删除了记录，压缩持久化文件
        if deleted_count > 0:
            self._compact_persistence()

        return deleted_count

    def _compact_persistence(self):
        """
        压缩持久化文件

        重写持久化文件，只保留内存中的调用记录，去除已删除的记录
        """
        try:
            # 临时文件
            temp_path = self._persistence_path.with_suffix(".tmp")

            # 写入当前内存中的所有调用
            with open(temp_path, "w", encoding="utf-8") as f:
                for call in self._calls.values():
                    data = {
                        "call_id": call.call_id,
                        "send_from": call.send_from,
                        "send_to": call.send_to,
                        "content": call.content,
                        "message_type": call.message_type.value,
                        "status": call.status.value,
                        "created_at": call.created_at.isoformat(),
                        "started_at": (call.started_at.isoformat() if call.started_at else None),
                        "completed_at": (
                            call.completed_at.isoformat() if call.completed_at else None
                        ),
                        "error": call.error,
                        "has_agent_response": call.has_agent_response,
                        "business_task_id": call.business_task_id,
                        "timeout_seconds": call.timeout_seconds,
                    }
                    f.write(json.dumps(data, ensure_ascii=False) + "\n")

            # 替换原文件
            temp_path.replace(self._persistence_path)
            self.logger.debug("持久化文件已压缩")

        except Exception as e:
            self.logger.error(f"压缩持久化文件失败: {e}", exc_info=True)

    def start_cleanup(self):
        """启动后台清理任务"""
        if self._running:
            self.logger.warning("清理任务已在运行")
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.logger.info("后台清理任务已启动")

    async def stop_cleanup(self):
        """停止后台清理任务"""
        if not self._running:
            return

        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None
        self.logger.info("后台清理任务已停止")

    def get_stats(self) -> dict:
        """
        获取统计信息

        Returns:
            dict: 统计信息，包括各状态的调用数量
        """
        stats: dict[str, int | dict[str, int]] = {
            "total": len(self._calls),
            "by_status": {},
            "by_message_type": {},
        }

        for call in self._calls.values():
            # 按状态统计
            status_key = call.status.value
            by_status = stats["by_status"]
            assert isinstance(by_status, dict)
            by_status[status_key] = by_status.get(status_key, 0) + 1

            # 按消息类型统计
            type_key = call.message_type.value
            by_message_type = stats["by_message_type"]
            assert isinstance(by_message_type, dict)
            by_message_type[type_key] = by_message_type.get(type_key, 0) + 1

        return stats

    def _index_call(self, call: AgentCall):
        """维护 send_to -> call_id 索引。"""
        call_ids = self._calls_by_receiver.setdefault(call.send_to, [])
        if call.call_id not in call_ids:
            call_ids.append(call.call_id)

    def _unindex_call(self, call: AgentCall):
        """从 send_to -> call_id 索引移除调用。"""
        call_ids = self._calls_by_receiver.get(call.send_to)
        if not call_ids:
            return
        with contextlib.suppress(ValueError):
            call_ids.remove(call.call_id)
        if not call_ids:
            del self._calls_by_receiver[call.send_to]

    def _should_include_in_runtime(self, call: AgentCall) -> bool:
        """判断调用是否应出现在接收方 runtime prompt 中。"""
        if call.status in (CallStatus.FAILED, CallStatus.TIMEOUT):
            return False
        if call.message_type == MessageType.TASK:
            return not call.has_agent_response
        if call.message_type == MessageType.NOTIFICATION:
            return call.status != CallStatus.COMPLETED
        return False  # type: ignore[unreachable]
