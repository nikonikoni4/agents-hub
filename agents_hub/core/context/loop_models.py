"""Loop 数据模型。

定义 Loop 循环执行功能的核心数据结构，包括：
- LoopNodeType: 节点类型枚举（普通节点/结束节点）
- LoopNode: 循环节点定义，包含节点类型、Agent 名称、职责描述、输出格式要求
- Loop: 循环定义（可复用模板），包含节点列表、最大迭代次数
- LoopExecution: 循环执行实例（一次性），包含初始任务、状态、迭代计数等

设计决策：
- Loop 定义与执行实例分离，Loop 作为可复用模板，LoopExecution 作为一次性执行
- initial_task 从 Loop 移到 LoopExecution，作为执行参数而非定义属性
- 支持同一 Loop 定义多次启动，每次传入不同的 initial_task
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

DEFAULT_MAX_RETRIES = 3
"""默认输出校验失败的最大重试次数。"""


class LoopNodeType(str, Enum):
    """Loop 节点类型枚举。

    定义循环中节点的两种类型：
    - NORMAL: 普通节点，执行具体任务
    - TERMINATOR: 结束节点，判断循环是否继续

    Attributes:
        NORMAL: 普通节点类型，用于执行具体任务（如代码实现、文档撰写）。
        TERMINATOR: 结束节点类型，用于判断循环是否继续，必须输出 <loop_decision> 标签。
    """

    NORMAL = "normal"
    TERMINATOR = "terminator"


@dataclass
class LoopNode:
    """Loop 节点定义。

    表示循环中的一个执行单元，包含节点类型、执行 Agent、职责描述和输出格式要求。
    每个节点对应一个 Agent，Agent 根据 role_description 和 output_schema_prompt 执行任务。

    Attributes:
        node_type: 节点类型，取值为 "normal" 或 "terminator"。
        agent_name: 执行该节点的 Agent 名称，必须在 RoleManager 中存在。
        role_description: 节点职责描述，包含角色、输入、输出、职责，发送给 Agent 作为上下文。
        output_schema_prompt: 输出格式提示词，Markdown 格式，告诉 Agent 应该如何格式化输出。
        output_schema_fields: 必需字段列表，用于校验 Agent 输出是否符合格式要求。
        max_retries: 输出校验失败的最大重试次数，默认为 3。
        node_id: 节点唯一标识，自动生成 UUID。
    """

    node_type: str  # "normal" or "terminator"
    agent_name: str  # 执行节点的 Agent 名称
    role_description: str  # 节点职责描述（对应 PRD 的 node_prompt）
    output_schema_prompt: str | None = None  # 输出格式提示词（给 LLM 看的 Markdown）
    output_schema_fields: list[str] | None = None  # 必需字段列表（用于校验）
    max_retries: int = DEFAULT_MAX_RETRIES  # 输出校验失败的最大重试次数
    node_id: str = field(default_factory=lambda: str(uuid4()))  # 节点唯一标识

    def to_dict(self) -> dict[str, Any]:
        """将 LoopNode 序列化为字典。

        序列化逻辑：
        - 将所有属性转换为可 JSON 序列化的格式
        - node_id、node_type、agent_name 等字符串字段直接复制
        - output_schema_prompt 和 output_schema_fields 可能为 None
        - max_retries 使用默认值 3

        Returns:
            包含所有节点属性的字典，用于 JSON 持久化。
        """
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "agent_name": self.agent_name,
            "role_description": self.role_description,
            "output_schema_prompt": self.output_schema_prompt,
            "output_schema_fields": self.output_schema_fields,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LoopNode":
        """从字典反序列化为 LoopNode。

        反序列化逻辑：
        - 检查必需字段（node_type、agent_name、role_description）是否存在
        - 如果缺失必需字段，抛出 ValueError 并列出缺失字段
        - 使用 data.get() 为可选字段提供默认值
        - node_id 如果不存在则自动生成 UUID
        - max_retries 如果不存在则使用 DEFAULT_MAX_RETRIES（3）

        Args:
            data: 包含节点属性的字典，必须包含 node_type、agent_name、role_description。

        Returns:
            反序列化后的 LoopNode 实例。

        Raises:
            ValueError: 缺失必需字段（node_type、agent_name、role_description）。
        """
        required = ("node_type", "agent_name", "role_description")
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(
                f"LoopNode 反序列化失败: 缺失必需字段 {missing}, 已有字段={list(data.keys())}"
            )
        return cls(
            node_id=data.get("node_id", str(uuid4())),
            node_type=data["node_type"],
            agent_name=data["agent_name"],
            role_description=data["role_description"],
            output_schema_prompt=data.get("output_schema_prompt"),
            output_schema_fields=data.get("output_schema_fields"),
            max_retries=data.get("max_retries", DEFAULT_MAX_RETRIES),
        )


@dataclass
class Loop:
    """Loop 循环定义（可复用模板）。

    表示一个可复用的循环定义，包含节点列表和最大迭代次数。
    Loop 定义由 Manager 创建后，可以多次启动，每次启动创建一个新的 LoopExecution 实例。

    Attributes:
        loop_id: 循环定义唯一标识，自动生成 UUID。
        group_chat_id: 所属群聊 ID。
        nodes: 节点列表，至少 2 个节点，有且仅有 1 个 TERMINATOR 节点。
        max_iterations: 最大循环次数，防止死循环。
        created_at: 创建时间。
        updated_at: 最后更新时间。
    """

    loop_id: str  # UUID
    group_chat_id: str  # 所属群聊
    nodes: list[LoopNode]  # 节点列表
    max_iterations: int  # 最大循环次数
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """将 Loop 序列化为字典。

        将循环定义及其所有节点序列化为可 JSON 持久化的字典格式。
        datetime 字段使用 ISO 8601 格式。

        序列化逻辑：
        - 调用每个 LoopNode 的 to_dict() 方法序列化节点列表
        - 使用 datetime.isoformat() 将 datetime 转换为 ISO 8601 字符串

        Returns:
            包含所有循环定义属性的字典，用于 JSON 持久化。
        """
        return {
            "loop_id": self.loop_id,
            "group_chat_id": self.group_chat_id,
            "nodes": [node.to_dict() for node in self.nodes],
            "max_iterations": self.max_iterations,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Loop":
        """从字典反序列化为 Loop。

        反序列化逻辑：
        - 直接从字典读取必需字段（loop_id、group_chat_id、nodes、max_iterations）
        - 调用 LoopNode.from_dict() 反序列化节点列表
        - 使用 datetime.fromisoformat() 将 ISO 8601 字符串转换为 datetime

        兼容性处理：
        - 如果字典包含旧版本的执行状态字段（status, current_iteration 等），忽略它们
        - 这样可以从旧的 loops.jsonl 文件加载为新的 Loop 定义

        Args:
            data: 包含循环定义属性的字典，必须包含 loop_id、group_chat_id、nodes、max_iterations。

        Returns:
            反序列化后的 Loop 实例。
        """
        return cls(
            loop_id=data["loop_id"],
            group_chat_id=data["group_chat_id"],
            nodes=[LoopNode.from_dict(n) for n in data["nodes"]],
            max_iterations=data["max_iterations"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


@dataclass
class LoopExecution:
    """Loop 执行实例（一次性）。

    表示 Loop 定义的一次具体执行，包含初始任务、状态、迭代计数等执行状态。
    每次调用 start_loop() 时创建一个新的 LoopExecution 实例。

    状态机转换规则：
    - CREATED -> RUNNING（启动执行）
    - RUNNING -> PAUSED / COMPLETED / FAILED（暂停/正常完成/失败）
    - PAUSED -> RUNNING / FAILED（恢复/失败）

    Attributes:
        execution_id: 执行实例唯一标识，自动生成 UUID。
        loop_id: 关联的 Loop 定义 ID。
        initial_task: 本次执行的初始任务描述，发送给第一个节点。
        status: 执行状态，取值为 "created"/"running"/"paused"/"completed"/"failed"。
        current_iteration: 当前循环轮次，从 1 开始。
        current_node_index: 当前节点索引，指向 Loop.nodes 列表中的位置。
        created_at: 创建时间。
        updated_at: 最后更新时间。
        error_message: 错误信息，仅在 FAILED 状态时有值。
    """

    execution_id: str  # UUID
    loop_id: str  # 关联的 Loop 定义 ID
    initial_task: str  # 本次执行的初始任务
    status: str  # "created"/"running"/"paused"/"completed"/"failed"
    current_iteration: int  # 当前循环轮次
    current_node_index: int  # 当前节点索引
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None  # 失败原因

    def to_dict(self) -> dict[str, Any]:
        """将 LoopExecution 序列化为字典。

        将执行实例序列化为可 JSON 持久化的字典格式。
        datetime 字段使用 ISO 8601 格式。

        序列化逻辑：
        - 使用 datetime.isoformat() 将 datetime 转换为 ISO 8601 字符串
        - error_message 可能为 None，直接复制

        Returns:
            包含所有执行实例属性的字典，用于 JSON 持久化。
        """
        return {
            "execution_id": self.execution_id,
            "loop_id": self.loop_id,
            "initial_task": self.initial_task,
            "status": self.status,
            "current_iteration": self.current_iteration,
            "current_node_index": self.current_node_index,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LoopExecution":
        """从字典反序列化为 LoopExecution。

        反序列化逻辑：
        - 直接从字典读取必需字段（execution_id、loop_id、initial_task、status 等）
        - 使用 datetime.fromisoformat() 将 ISO 8601 字符串转换为 datetime
        - error_message 使用 data.get() 提供默认值 None

        Args:
            data: 包含执行实例属性的字典，必须包含 execution_id、loop_id、initial_task、status 等字段。

        Returns:
            反序列化后的 LoopExecution 实例。
        """
        return cls(
            execution_id=data["execution_id"],
            loop_id=data["loop_id"],
            initial_task=data["initial_task"],
            status=data["status"],
            current_iteration=data["current_iteration"],
            current_node_index=data["current_node_index"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            error_message=data.get("error_message"),
        )
