---
version: 1.3
created_at: 2026-05-31
updated_at: 2026-06-03
last_updated: AgentCall 增加显式回复闭环语义
abstract: core/communication 层的正式规格，定义消息路由机制、Agent 调用生命周期管理和显式回复闭环语义
id: spec-core-communication
title: Core Communication 层规格
status: draft
module: core/communication
sourc_spec: null
related_plan: null
code_scope:
  - agents_hub/core/communication/
contract_refs:
  - agents_hub/core/communication/message_router.py
  - agents_hub/core/communication/agent_call.py
  - agents_hub/core/communication/agent_call_manager.py
  - agents_hub/core/communication/task.py
  - agents_hub/core/communication/task_manager.py
  - agents_hub/core/foundation/models.py
  - agents_hub/core/foundation/message.py
  - agents_hub/core/foundation/paths.py
---

# Core Communication 层规格

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |
| 1.1 | 新增 Task/TaskList 数据模型和 TaskManager |
| 1.2 | 路径管理改用 group_chat_paths 集中管理 |
| 1.3 | AgentCall 增加显式回复闭环语义 |

## Overview

communication 层是 core 的**消息基础设施**，负责两件事：

1. **消息路由**（MessageRouter）：Agent 之间的消息投递，基于私有队列的点对点通信
2. **调用管理**（AgentCallManager）：跟踪每次跨 Agent 调用的完整生命周期，支持超时检测、自动清理和持久化

communication 只依赖 foundation 层，不依赖 context、agent 或 orchestration。

## Scope

### 范围内

- Agent 消息队列的注册、注销和投递
- AgentCall 的生命周期状态管理
- 调用超时检测与自动清理策略
- 调用记录的持久化与恢复
- Task / TaskList 数据模型和 TaskManager 任务管理

### 范围外

- Agent 的执行逻辑（属于 agent 层）
- 群聊会话和上下文管理（属于 context 层）
- 群聊编排和团队管理（属于 orchestration 层）

## Core Behavior

### 消息路由模型

MessageRouter 实现基于**私有 asyncio.Queue** 的点对点消息投递：

- 每个 Agent 启动时注册自己的消息队列（register）
- Agent 退出时注销队列（unregister）
- 发送消息时，路由器将消息放入目标 Agent 的队列（send_message）

**消息验证规则**：
- 消息内容不能为空
- 发送者和接收者都必须已注册
- 验证失败抛出对应的 foundation 异常（InvalidMessageError / AgentNotFoundError）

**投递失败处理**：
- 队列满 → MessageDeliveryError
- 目标不存在 → AgentNotFoundError
- 其他异常 → MessageDeliveryError（包装原始错误）

**资源清理**：clear() 方法清空所有队列中的消息并注销所有 Agent，幂等可重复调用。

### AgentCall 生命周期

每次跨 Agent 调用（无论是 MCP Tool 调用还是群聊中 @Agent）都会创建一个 AgentCall 记录，跟踪完整生命周期。

AgentCall 同时记录"调用是否已被接收方显式回复闭环"。该闭环标志与状态不同：
- 状态表示调用生命周期（PENDING / RUNNING / COMPLETED / FAILED / TIMEOUT）
- 闭环标志表示接收方是否已经通过显式工具给出最终回复
- TASK 调用只有显式回复闭环后，才应进入 COMPLETED 或 FAILED 终态
- NOTIFICATION 调用不需要显式回复闭环

**状态转换**：

```
创建 → PENDING
       ↓
    RUNNING（execute 之前）
       ↓
    ┌── COMPLETED（成功）
    ├── FAILED（失败）
    └── TIMEOUT（超时）
```

**触发场景**：
- MCP Tool `call_agent` 调用时创建
- User 在群聊中 @Agent 时创建
- MessageType 为 TASK 时，接收方需要通过显式回复工具结束调用

**超时判断**：
- 基于 elapsed > timeout_seconds
- 仅对非终态（PENDING / RUNNING）生效
- timeout_seconds 为 None 表示无超时限制

### 清理策略

AgentCallManager 后台定期清理过期调用记录，释放内存：

| 条件 | 保留时间 | 说明 |
|------|----------|------|
| PENDING / RUNNING | 不删除 | 进行中的调用 |
| 有 business_task_id | 不删除 | 由业务任务管理器决定 |
| NOTIFICATION + COMPLETED | 5 分钟 | 通知类调用，完成后快速清理 |
| TASK + COMPLETED | 1 小时 | 任务类调用，保留更久供查询 |
| FAILED / TIMEOUT | 24 小时 | 失败调用保留较久，便于调试 |

清理间隔默认 60 秒，保留时间可通过 retention_config 自定义。

### 持久化机制

AgentCallManager 在每个群聊的数据目录下维护 `agent_calls.jsonl` 持久化文件：

- **写入时机**：创建调用、状态变更、设置结果/错误时立即追加写入
- **加载时机**：AgentCallManager 初始化时自动加载历史记录
- **压缩时机**：清理过期调用后重写文件，只保留内存中的有效记录
- **容错设计**：同一条 call_id 的多条记录取最新一条（后写覆盖前写）
- **result 不持久化**：执行结果可能很大且重启后无法恢复，不写入文件

**路径管理**：
- 使用 foundation 层的 `group_chat_paths` 单例集中管理路径
- 日志路径：`group_chat_paths.base_dir(group_chat_id, project_path)`
- 数据路径：`group_chat_paths.agent_calls_data(group_chat_id, project_path)`

### 任务管理（TaskManager）

TaskManager 管理团队任务的 CRUD 和持久化（设计详见 `2026-05-31-mcp-tools-design.md` §4）。

**数据模型**：

- `Task`：单个任务，字段包括 `task_id`、`owner`、`content`、`status`（TaskStatus）、`group_chat_id`、`created_by`、时间戳
- `TaskList`：任务列表，状态机 ACTIVE → ARCHIVED，包含 `tasks: list[Task]`

**核心接口**：

```python
class TaskManager:
    def __init__(self, group_chat_id: str, project_path: str): ...
    def get_active_task_list(self, group_chat_id: str) -> TaskList | None: ...
    def assign_tasks(self, group_chat_id: str, tasks: list[dict], created_by: str) -> dict: ...
    def archive_task_list(self, group_chat_id: str) -> dict: ...
```

- `assign_tasks`：覆盖式更新语义（参照 Claude Code TodoWrite），返回 `{created, updated, unchanged}`
- `archive_task_list`：ACTIVE → ARCHIVED，返回 `{archived_count, archived_at}`

**持久化**：append-only JSONL（`tasks.jsonl`），同 `list_id` 取最新记录。

**路径管理**：
- 使用 foundation 层的 `group_chat_paths` 单例集中管理路径
- 日志路径：`group_chat_paths.base_dir(group_chat_id, project_path)`
- 数据路径：`group_chat_paths.tasks_data(group_chat_id, project_path)`

## Technical Contract

### 跨层依赖

- communication 依赖 foundation 的 `AgentMessage`、`CallStatus`、`MessageType`、异常类
- agent 层通过 `MessageRouter.send_message()` 投递消息
- agent 层通过 `AgentCallManager` 跟踪调用状态
- orchestration 层的 GroupChat 创建并持有 MessageRouter 和 AgentCallManager 实例

### 与 Agent 的协作模式

```
Agent.run() 循环：
  1. await message_queue.get()  ← 从 MessageRouter 投递的队列取消息
  2. render_for_llm(msg)        ← 渲染为 LLM prompt
  3. agent_call_manager.update_status(RUNNING)
  4. execute(prompt)             ← 调用 agent_bridge
  5. 非 TASK 调用执行完成后可进入 COMPLETED
  6. TASK 调用等待显式回复闭环后进入 COMPLETED / FAILED
```

## Out of Spec

- MessageRouter 不负责消息持久化（持久化由 context 层的 GroupChatContext 负责）
- AgentCallManager 不负责 Agent 执行（执行由 agent_bridge 负责）
- 清理策略的具体实现细节（保留时间配置等）可能随版本调整
