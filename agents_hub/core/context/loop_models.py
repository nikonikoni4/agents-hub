"""Loop 数据模型。"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

DEFAULT_MAX_RETRIES = 3


class LoopNodeType(str, Enum):
    """Loop 节点类型"""

    NORMAL = "normal"
    TERMINATOR = "terminator"


@dataclass
class LoopNode:
    """Loop 节点定义"""

    node_type: str  # "normal" or "terminator"
    agent_name: str  # 执行节点的 Agent 名称
    role_description: str  # 节点职责描述（对应 PRD 的 node_prompt）
    output_schema_prompt: str | None = None  # 输出格式提示词（给 LLM 看的 Markdown）
    output_schema_fields: list[str] | None = None  # 必需字段列表（用于校验）
    max_retries: int = DEFAULT_MAX_RETRIES  # 输出校验失败的最大重试次数
    node_id: str = field(default_factory=lambda: str(uuid4()))  # 节点唯一标识

    def to_dict(self) -> dict[str, Any]:
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
    """Loop 循环定义"""

    loop_id: str  # UUID
    group_chat_id: str  # 所属群聊
    nodes: list[LoopNode]  # 节点列表
    status: str  # "created"/"running"/"paused"/"completed"/"failed"
    max_iterations: int  # 最大循环次数
    current_iteration: int  # 当前循环轮次
    current_node_index: int  # 当前节点索引
    initial_task: str  # 初始任务描述
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None  # 失败原因

    def to_dict(self) -> dict[str, Any]:
        return {
            "loop_id": self.loop_id,
            "group_chat_id": self.group_chat_id,
            "nodes": [node.to_dict() for node in self.nodes],
            "status": self.status,
            "max_iterations": self.max_iterations,
            "current_iteration": self.current_iteration,
            "current_node_index": self.current_node_index,
            "initial_task": self.initial_task,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Loop":
        return cls(
            loop_id=data["loop_id"],
            group_chat_id=data["group_chat_id"],
            nodes=[LoopNode.from_dict(n) for n in data["nodes"]],
            status=data["status"],
            max_iterations=data["max_iterations"],
            current_iteration=data["current_iteration"],
            current_node_index=data["current_node_index"],
            initial_task=data["initial_task"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            error_message=data.get("error_message"),
        )
