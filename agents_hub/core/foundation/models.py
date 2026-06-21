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
    LOOP_MESSAGE = "loop_message"  # 循环内部消息，不自动保存


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


class TaskStatus(str, Enum):
    """任务状态枚举

    - PENDING: 待执行
    - RUNNING: 执行中
    - COMPLETED: 已完成
    - FAILED: 失败
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskListStatus(str, Enum):
    """任务列表状态枚举

    - ACTIVE: 激活（当前使用）
    - ARCHIVED: 已归档
    """

    ACTIVE = "active"
    ARCHIVED = "archived"


class LoopExecutionStatus(str, Enum):
    """Loop 执行实例状态

    Loop 定义本身无状态，只有执行实例（LoopExecution）有状态。

    - CREATED: 已创建，待启动
    - RUNNING: 运行中
    - PAUSED: 已暂停
    - COMPLETED: 已完成
    - FAILED: 失败
    """

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


# 向后兼容别名（将在下一版本移除）
LoopStatus = LoopExecutionStatus


class SystemRoles:
    """系统身份常量

    定义 MessageRouter 中使用的系统级身份名称，
    避免硬编码字符串散布在多个模块中。
    """

    HEARTBEAT = "__HEARTBEAT__"  # 定时唤醒 Manager 的心跳身份
    LOOP = "loop"  # LoopExecutor 向节点投递消息的身份
    SYSTEM = "__SYSTEM__"  # 系统内部消息的发送方身份（哨兵、系统通知）
