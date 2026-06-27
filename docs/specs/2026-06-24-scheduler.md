---
version: 1.0
created_at: 2026-06-24
updated_at: 2026-06-24
last_updated: 创建 scheduler spec 初稿
abstract: 定时记忆助手调度系统规格，定义 SchedulerService、StateManager、MemoryTask 的职责边界、状态文件设计和定时触发机制
id: scheduler
title: 定时记忆助手调度系统
status: draft
module: scheduler
source_spec:
related_plan:
code_scope: agents_hub/scheduler/
contract_refs: agents_hub/scheduler/scheduler_service.py, agents_hub/scheduler/state_manager.py, agents_hub/scheduler/task/memory_task.py
---

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |

## Overview

**业务问题**：记忆助手需要定期收集群聊对话内容并更新记忆文件，手动触发不可靠且遗漏率高。系统需要一个自动化的定时调度机制，确保所有活跃群聊的记忆定期更新。

**核心职责**：
- 以 Cron 表达式定时触发记忆收集任务
- 遍历所有活跃群聊，对需要更新的群聊执行记忆收集
- 服务重启后自动补偿错过的任务
- 管理调度状态和群聊记忆索引的持久化

## Scope

### 范围内

- SchedulerService：APScheduler 封装、定时触发、补偿执行
- StateManager：调度状态文件（`.schedule_state.json`、`memory/index.json`、`memory/result.json`）读写
- MemoryTask：单个群聊的记忆收集执行逻辑
- MCP 工具 `get_memory_context`：为记忆助手提供群聊上下文数据

### 范围外

- 记忆助手 Agent 的具体记忆生成逻辑（由记忆助手角色自身负责）
- 群聊消息的存储和管理（由 core/context 层负责）
- APScheduler 库的内部实现细节

## Technical Contract

### SchedulerService

<key_function last_update="2026-06-27T23:39:49+08:00">
- agents_hub/scheduler/scheduler_service.py
  - scheduler_service.SchedulerService.start:42
  - scheduler_service.SchedulerService.shutdown:101
  - scheduler_service.SchedulerService._execute_memory_task:117
  - scheduler_service.SchedulerService._run_compensation:88
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| `start()` | 启动调度器 | 幂等：已启动时跳过。应在 FastAPI lifespan startup 中调用 |
| `shutdown()` | 关闭调度器 | 幂等：未启动时跳过。应在 FastAPI lifespan shutdown 中调用 |

**容错策略**：
- 单群聊执行失败时，记录错误到 `result.json`，跳过该群聊继续处理下一个
- 只有在所有群聊都处理完毕后，才更新 `.schedule_state.json`
- 补偿任务引用保存到实例变量，添加 `add_done_callback` 监控异常

**并发保护**：
- `start()` 幂等，已启动时直接返回
- `_execute_memory_task` 内部使用状态标志防止重入

### StateManager

<key_function last_update="2026-06-24T10:00:00+08:00">
- agents_hub/scheduler/state_manager.py
  - state_manager.StateManager.load_schedule_state:18
  - state_manager.StateManager.save_schedule_state:25
  - state_manager.StateManager.load_memory_index:32
  - state_manager.StateManager.save_memory_index:39
  - state_manager.StateManager.should_execute_today:46
  - state_manager.StateManager.append_results:55
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| `load_schedule_state()` | 加载 `.schedule_state.json` | 文件不存在时返回空 dict |
| `save_schedule_state(state)` | 保存 `.schedule_state.json` | OSError 自然传播，不做静默捕获 |
| `load_memory_index()` | 加载 `memory/index.json` | 文件不存在时返回空 dict |
| `save_memory_index(index)` | 保存 `memory/index.json` | OSError 自然传播 |
| `should_execute_today()` | 判断今天是否需要执行 | 比较 `.schedule_state.json` 中 memory_task 日期与今天 |
| `append_results(results)` | 批量追加执行结果到 `result.json` | 保留最近 10 条 |

### MemoryTask

<key_function last_update="2026-06-24T10:00:00+08:00">
- agents_hub/scheduler/task/memory_task.py
  - memory_task.MemoryTask.execute:15
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| `execute(group_chat_id, last_updated)` | 执行单个群聊的记忆更新 | 内部捕获异常，返回结果文本而非抛出 |

### MCP 工具：get_memory_context

<key_function last_update="2026-06-25T14:30:00+08:00">
- agents_hub/mcp/server.py
  - server.get_memory_context:1469
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| `get_memory_context(agent_token, group_chat_id, last_updated)` | 获取群聊上下文 | 使用 `config.memory_assistant_token` 验证身份，不依赖群聊 token 机制 |

**返回值**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `group_chat_id` | str | 群聊 ID |
| `last_updated` | str | 上次更新时间 |
| `history_summary` | str | 历史总结内容（从 `history.jsonl` 最后一行读取） |
| `new_messages` | str | 新消息内容（通过 `get_group_chat_messages` 获取） |
| `context` | str | 拼接后的完整上下文 |

### 数据模型

#### .schedule_state.json

```json
{
  "memory_task": "2026-06-24T10:00:00Z"
}
```

#### memory/index.json

```json
{
  "<group_chat_id>": {
    "last_updated": "2026-06-24T10:00:00Z"
  }
}
```

#### memory/result.json

记录每次记忆任务的执行结果，保留最近 10 条，用于调试。

```json
[
  {
    "timestamp": "2026-06-24T10:00:05Z",
    "group_chat_id": "ba8e155a-...",
    "success": true,
    "result": "记忆收集完成，已更新 4 份文件"
  }
]
```

### 配置项

| 字段名 | 类型 | 默认值 | 语义 |
|--------|------|--------|------|
| `memory_task_cron_hour` | int | 10 | 记忆任务执行小时（0-23） |
| `memory_task_cron_minute` | int | 0 | 记忆任务执行分钟（0-59） |

详见 [Config Spec](2026-06-06-config.md) 中的配置项定义。

## Design Rationale

**为什么这样设计？**
- **APScheduler 封装**：成熟的定时任务库，支持 Cron 表达式和 AsyncIOScheduler，与 FastAPI 的 async 生命周期兼容
- **补偿执行**：服务可能在定时任务执行窗口内重启，补偿机制确保不遗漏
- **结果记录**：`result.json` 保留最近 10 条执行结果，用于调试和监控
- **容错隔离**：单群聊失败不影响其他群聊，错误记录到 result 而非阻断整个任务

**有哪些约束？**
- 每天只执行一次记忆任务，通过 `.schedule_state.json` 的日期字段防重
- 记忆助手 Agent 通过 `agent_platform_client.execute` 直接执行，不创建 GroupChat
- Token 使用 `config.memory_assistant_token`（记忆助手专用 token，独立于群聊 token 机制）

**有哪些已知限制？**
- 当前不支持按群聊自定义执行时间
- 补偿执行仅检查当天是否已执行，不支持跨天补偿
- APScheduler CronTrigger 精度为分钟级

**相关 ADR**：
- 无

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **Config 模块**：配置项定义和路径策略（见 `config` spec）
- **Core Agent Orchestration**：Agent 执行模型和 MCP 工具入口（见 `core-agent-orchestration` spec）
- **记忆助手角色**：记忆生成的具体逻辑（由角色 prompt 和 skill 定义）
