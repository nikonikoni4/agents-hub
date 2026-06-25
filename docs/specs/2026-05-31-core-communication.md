---
version: 2.0
created_at: 2026-05-31
updated_at: 2026-06-18
last_updated: 重构为新 spec 规则：移除执行细节，新增 Design Rationale，添加 key_function 标签
abstract: core/communication 层的正式规格，定义消息路由机制、Agent 调用生命周期管理和任务管理的技术契约
---

# Core Communication 层规格

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |
| 1.1 | 新增 Task/TaskList 数据模型和 TaskManager |
| 1.2 | 路径管理改用 group_chat_paths 集中管理 |
| 1.3 | AgentCall 增加显式回复闭环语义 |
| 2.0 | 重构为新 spec 规则：移除执行细节，整合 Technical Contract，新增 Design Rationale，添加 key_function 标签 |

## Overview

**业务问题**：Agent 之间需要可靠的点对点通信机制，以及对异步调用生命周期的全流程追踪能力。系统需要知道"谁在等谁的回复""调用是否超时""任务是否已完成"。

**核心职责**：
1. **消息路由**：提供基于私有队列的点对点消息投递机制
2. **调用追踪**：管理跨 Agent 调用的完整生命周期（PENDING → RUNNING → 终态）
3. **任务协作**：管理团队任务的 CRUD 和持久化

## Scope

### 范围内

- Agent 消息队列的注册、注销和投递
- AgentCall 的生命周期状态管理
- 调用超时检测与自动清理策略
- 调用记录的持久化与恢复
- Task / TaskList 数据模型和 TaskManager 任务管理

### 范围外

- Agent 的执行逻辑（参考 `docs/specs/2026-05-31-core-agent-orchestration.md`）
- 群聊会话和上下文管理（参考 `docs/specs/2026-05-31-core-context.md`）
- 群聊编排和团队管理（参考 `docs/specs/2026-05-31-core-agent-orchestration.md`）
- 消息持久化（由 context 层的 GroupChatRuntime 负责）

## Technical Contract

### MessageRouter

<key_function last_update="2026-06-25T11:30:28+08:00">
- agents_hub/core/communication/message_router.py
  - message_router.MessageRouter.register:26
  - message_router.MessageRouter.unregister:43
  - message_router.MessageRouter.send_message:66
  - message_router.MessageRouter.clear:151
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| register(name, queue) | 注册 Agent 的消息队列 | name 唯一，队列为 asyncio.Queue |
| unregister(name) | 注销 Agent 的消息队列 | 幂等，未注册时不报错 |
| send_message(message) | 投递消息到目标队列 | message 必须有效，send_to 必须已注册 |
| clear() | 清空所有队列并注销所有 Agent | 幂等，可重复调用 |

**消息验证规则**：
- 消息内容不能为空
- 发送者和接收者都必须已注册
- 验证失败抛出 `InvalidMessageError` 或 `AgentNotFoundError`

**投递失败处理**：
- 队列满 → `MessageDeliveryError`
- 目标不存在 → `AgentNotFoundError`
- 其他异常 → `MessageDeliveryError`（包装原始错误）

### AgentCallManager

<key_function last_update="2026-06-18T16:30:00+08:00">
- agents_hub/core/communication/agent_call_manager.py
  - agent_call_manager.AgentCallManager.create_call:62
  - agent_call_manager.AgentCallManager.get_call:108
  - agent_call_manager.AgentCallManager.list_all_calls:128
  - agent_call_manager.AgentCallManager.get_runtime_calls_for_agent:138
  - agent_call_manager.AgentCallManager.update_status:157
  - agent_call_manager.AgentCallManager.set_result:188
  - agent_call_manager.AgentCallManager.set_error:210
  - agent_call_manager.AgentCallManager.mark_agent_response:233
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| create_call(...) | 创建新调用记录 | 返回 AgentCall，立即持久化 |
| get_call(call_id) | 获取调用详情 | 不存在时返回 None |
| list_all_calls() | 获取所有调用记录 | 用于 API 查询 |
| get_runtime_calls_for_agent(name) | 获取需要注入到指定 Agent runtime 的调用列表 | TASK 调用在回复闭环前持续暴露 |
| update_status(call_id, status) | 更新调用状态 | 状态不变时跳过 |
| set_result(call_id, result) | 设置调用结果，状态 → COMPLETED | result 不持久化 |
| set_error(call_id, error, exc) | 设置调用错误，状态 → FAILED | 记录完整 traceback |
| mark_agent_response(call_id, content, success) | 标记接收方已显式回复闭环 | success=True → COMPLETED, False → FAILED |

**AgentCall 数据模型**：

```python
@dataclass
class AgentCall:
    call_id: str              # 唯一标识
    send_from: str            # 发送者名称
    send_to: str              # 接收者名称
    content: str              # 消息内容
    message_type: MessageType # TASK / NOTIFICATION
    status: CallStatus        # PENDING / RUNNING / COMPLETED / FAILED / TIMEOUT
    has_agent_response: bool  # 是否已显式回复闭环
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    timeout_seconds: int | None
    business_task_id: str | None
    result: object | None     # 不持久化
    error: str | None
```

**状态机规则**：

```
创建 → PENDING
       ↓
    RUNNING（execute 之前）
       ↓
    ┌── COMPLETED（成功）
    ├── FAILED（失败）
    └── TIMEOUT（超时）
```

- **状态**：表示调用生命周期
- **闭环标志**（has_agent_response）：表示接收方是否已通过显式工具给出最终回复
- **TASK 调用**：只有显式回复闭环后，才应进入 COMPLETED 或 FAILED 终态
- **NOTIFICATION 调用**：不需要显式回复闭环

**清理策略**：

| 条件 | 保留时间 | 说明 |
|------|----------|------|
| PENDING / RUNNING | 不删除 | 进行中的调用 |
| 有 business_task_id | 不删除 | 由业务任务管理器决定 |
| NOTIFICATION + COMPLETED | 5 分钟 | 通知类调用，完成后快速清理 |
| TASK + COMPLETED | 1 小时 | 任务类调用，保留更久供查询 |
| FAILED / TIMEOUT | 24 小时 | 失败调用保留较久，便于调试 |

**持久化设计**：
- **文件格式**：append-only JSONL（`agent_calls.jsonl`）
- **容错设计**：同一 call_id 的多条记录取最新一条
- **result 不持久化**：执行结果可能很大且重启后无法恢复

### TaskManager

<key_function last_update="2026-06-18T16:30:00+08:00">
- agents_hub/core/communication/task_manager.py
  - task_manager.TaskManager.get_active_task_list:58
  - task_manager.TaskManager.assign_tasks:81
  - task_manager.TaskManager.archive_task_list:113
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| get_active_task_list(group_chat_id) | 获取当前活跃任务列表 | 不存在时返回 None |
| assign_tasks(group_chat_id, tasks, created_by) | 覆盖式更新任务 | 返回 {created, updated, unchanged} |
| archive_task_list(group_chat_id) | 归档当前任务列表 | 状态 ACTIVE → ARCHIVED，返回 {archived_count, archived_at} |

**数据模型**：

```python
@dataclass
class Task:
    task_id: str
    owner: str
    content: str
    status: TaskStatus  # PENDING / IN_PROGRESS / COMPLETED / DELETED
    group_chat_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime

@dataclass
class TaskList:
    list_id: str
    group_chat_id: str
    status: str  # ACTIVE / ARCHIVED
    tasks: list[Task]
    created_at: datetime
    updated_at: datetime
```

**持久化设计**：
- **文件格式**：append-only JSONL（`tasks.jsonl`）
- **容错设计**：同 list_id 取最新记录

### 跨层依赖

**依赖方向**：
- communication 依赖 foundation 层（`AgentMessage`、`CallStatus`、`MessageType`、异常类、`group_chat_paths`）
- agent 层通过 `GroupChat.send_message_to_agent()` 间接使用 `MessageRouter`
- orchestration 层的 GroupChat 创建并持有 MessageRouter、AgentCallManager、TaskManager 实例

## Design Rationale

**为什么选择私有队列而非共享队列？**
- **隔离性**：每个 Agent 有独立的消息队列，避免相互干扰
- **背压控制**：队列满时可以阻塞发送方，防止消息积压导致 OOM
- **清理简单**：Agent 退出时只需清理自己的队列，不影响其他 Agent

**为什么需要 AgentCall 独立于消息？**
- **生命周期追踪**：消息投递是瞬时的，但调用是有生命周期的（可能跨多轮对话）
- **超时检测**：需要在后台定期检查哪些调用超时，消息本身没有这个能力
- **持久化需求**：调用记录需要持久化以支持系统重启恢复，而消息队列是内存的

**为什么 TASK 调用需要显式回复闭环？**
- **明确的任务完成语义**：Agent 执行完成 ≠ 任务完成，需要 Agent 显式告知调用方"我已经完成你交给我的任务"
- **支持多轮协作**：Agent 可能需要多轮思考才能完成任务，不能在第一轮就进入终态
- **区分执行完成和任务完成**：执行完成是技术概念，任务完成是业务概念

**为什么 result 不持久化？**
- **体积问题**：执行结果可能包含大量 LLM 输出、工具调用结果，持久化会占用大量磁盘空间
- **恢复无意义**：系统重启后，Agent 状态已经丢失，result 无法被使用
- **查询场景少**：result 主要在运行时使用，很少需要从磁盘读取历史 result

**为什么使用覆盖式更新任务？**
- **对齐 Claude Code TodoWrite 语义**：用户习惯"给一个新列表覆盖旧列表"而非增量更新
- **避免冲突**：多个 Agent 同时更新任务时，增量更新容易产生冲突，覆盖式更简单

**有哪些约束？**
- **单群聊单 AgentCallManager**：每个群聊有独立的 AgentCallManager，不能跨群聊查询调用记录
- **清理策略不可配置**：保留时间目前是硬编码的，未来可能支持配置
- **无事务保证**：持久化是 append-only，没有事务保证，依赖"后写覆盖前写"的容错机制

**有哪些已知限制？**
- **内存占用**：所有调用记录都在内存中，长时间运行的群聊可能占用较多内存（通过清理策略缓解）
- **无分布式支持**：当前设计是单机的，无法支持分布式部署（多个进程共享同一个群聊）
- **持久化延迟**：持久化是同步 IO，在高频调用场景下可能成为瓶颈（未来可考虑异步写入）

**相关 ADR**：
- 暂无（未来如果有重大架构决策，在此链接）

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **消息持久化**：`docs/specs/2026-05-31-core-context.md` - 由 GroupChatRuntime 负责
- **Agent 执行逻辑**：`docs/specs/2026-05-31-core-agent-orchestration.md` - 由 agent 层和 agent_bridge 负责
- **群聊编排**：`docs/specs/2026-05-31-core-agent-orchestration.md` - 由 GroupChat 和 GroupChatManager 负责
- **MCP 工具设计**：`docs/specs/2026-05-31-mcp-tools-design.md` - 定义如何通过 MCP 工具操作 communication 层
