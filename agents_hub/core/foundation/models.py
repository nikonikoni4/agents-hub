"""
基础数据模型

定义系统中使用的枚举类型和状态，零依赖。
"""

from enum import Enum


class SessionType(Enum):
    """会话类型"""

    MAIN = "main"  # 主会话（群聊）
    BTW = "btw"  # 单聊会话（by the way）


class MessageType(Enum):
    """消息类型，用于判断 agent 是否需要默认回复"""

    TASK = "task"  # 需要回复的任务
    NOTIFICATION = "notification"  # 不需要回复的通知


class CallStatus(Enum):
    """Agent 调用状态跟踪"""

    PENDING = "pending"  # 已创建，等待执行
    RUNNING = "running"  # 正在执行
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"  # 执行失败
    TIMEOUT = "timeout"  # 执行超时


class GroupChatType(Enum):
    """群聊类型"""

    SEQUENCE_EXECUTE = "sequence_execute"  # 流水线顺序执行
    MANAGER_ORCHESTRATE = "manager_orchestrate"  # 由 Team manager 动态决定安排
