"""
群聊会话

管理群聊的消息历史和元数据。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class AgentContextState:
    """Agent 的上下文加载状态"""

    last_loaded_compact_index: int = 0  # 已加载到第几条压缩历史
    last_loaded_message_index: int = 0  # 已加载到第几条原始消息


@dataclass
class AgentMemberInfo:
    """Agent 的会话信息"""

    main_session: str | None = None  # 主会话 ID
    btw_session: list[str] = field(default_factory=list)  # by the way session 列表
    context_state: AgentContextState = field(default_factory=AgentContextState)  # 上下文加载状态
    token: str = ""  # Agent 的 token，用于 MCP 工具身份验证
    cwd: str = ""  # CLI 命令启动的工作目录路径
    use_docker: bool = False  # 是否使用 Docker 沙箱执行
    status: str = "idle"  # Agent 状态：idle/busy/stopped/error/in_loop
    current_loop_id: str | None = None  # 当前所在循环 ID（IN_LOOP 状态时非空）
    context_usage: int = 0  # 上下文使用量（input_tokens/1000 取整）
    error_info: dict[str, Any] | None = (
        None  # 错误信息：{"type": "...", "message": "...", "exit_code": ..., "stderr": "..."}
    )


@dataclass
class GroupChatSession:
    """
    群聊会话

    用于管理群聊的消息历史，对于每个 agent 的单聊和具体内容由各自的平台管理。
    """

    # TODO 缺乏锁
    group_chat_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = field(default_factory=lambda: f"session_{datetime.now().strftime('%Y%m%d%H%M')}")
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_compacted_loc: int = 0  # 上一次 compact 的位置
    next_message_id: int = 1  # 下一个可用的消息 id

    def add_message(self, agent_result):
        """
        添加消息到历史记录

        Args:
            agent_result: Agent 执行结果（AgentResult）
                需要包含: agent_name, text, timestamp, platform
                可选: cwd, modified_files, git_diff_range
        """
        message = {
            "id": self.next_message_id,
            "agent_name": agent_result.agent_name,
            "content": agent_result.text,
            "timestamp": agent_result.timestamp,
            "platform": agent_result.platform.value,
        }

        # 添加可选字段（如果存在且不为 None）
        if agent_result.cwd is not None:
            message["cwd"] = agent_result.cwd

        if agent_result.modified_files is not None:
            message["modified_files"] = agent_result.modified_files

        if agent_result.git_diff_range is not None:
            message["git_diff_range"] = agent_result.git_diff_range

        if agent_result.permission_request is not None:
            message["permission_request"] = agent_result.permission_request

        if agent_result.web_preview is not None:
            message["web_preview"] = agent_result.web_preview

        if agent_result.files is not None:
            message["files"] = agent_result.files

        self.messages.append(message)
        self.next_message_id += 1

    def get_uncompact_messages(self) -> list[dict]:
        """
        获取未压缩的消息

        Returns:
            list[dict]: 从 last_compacted_loc 到最新的消息列表
        """
        return self.messages[self.last_compacted_loc :]


DEFAULT_MAX_RETRIES = 3


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
