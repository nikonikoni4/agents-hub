---
version: 1.0
created_at: 2026-05-31
updated_at: 2026-05-31
last_updated: 初稿
abstract: core/foundation 层的正式规格，定义系统共享的基础数据模型、消息格式、渲染契约和异常体系
id: spec-core-foundation
title: Core Foundation 层规格
status: draft
module: core/foundation
sourc_spec: null
related_plan: null
code_scope:
  - agents_hub/core/foundation/
contract_refs:
  - agents_hub/core/foundation/models.py
  - agents_hub/core/foundation/message.py
  - agents_hub/core/foundation/renderer.py
  - agents_hub/core/foundation/exceptions.py
  - agents_hub/core/foundation/constants.py
---

# Core Foundation 层规格

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |

## Overview

foundation 是 core 的**最底层**，零外部依赖。它定义了整个 core 层共享的基础数据模型、消息格式、渲染契约和异常体系。其他所有层（communication、context、agent、orchestration）都依赖 foundation，但 foundation 不依赖任何其他层。

**定位**：foundation 是 core 层的"公共语言"——所有跨层传递的数据结构、枚举、常量都在此定义。

## Scope

### 范围内

- 基础枚举类型（会话类型、消息类型、调用状态、群聊类型）
- Agent 间消息的数据结构定义
- 消息渲染的三个边界契约（入口、LLM 出口、UI 出口）
- 异常体系（统一基类 + 模块专属异常）
- 系统常量和持久化格式定义

### 范围外

- 具体的持久化实现（属于 context 层）
- 消息路由逻辑（属于 communication 层）
- Agent 执行逻辑（属于 agent 层）

## Core Behavior

### 枚举模型

foundation 定义四个核心枚举，构成系统的状态词汇表：

| 枚举 | 用途 | 值域 |
|------|------|------|
| SessionType | 区分群聊会话与单聊会话 | MAIN（群聊）、BTW（单聊） |
| MessageType | 区分是否需要自动回复 | TASK（需要回复）、NOTIFICATION（不需要回复） |
| CallStatus | Agent 调用的生命周期状态 | PENDING → RUNNING → COMPLETED / FAILED / TIMEOUT |
| GroupChatType | 群聊的编排模式 | SEQUENCE_EXECUTE（流水线）、MANAGER_ORCHESTRATE（动态编排） |

**状态转换规则**（CallStatus）：
- 一次调用的生命周期：PENDING → RUNNING → 终态（COMPLETED / FAILED / TIMEOUT）
- 终态不可逆：到达 COMPLETED / FAILED / TIMEOUT 后不再变更
- 超时判断基于 elapsed > timeout_seconds，仅对非终态生效

### 消息格式（AgentMessage）

Agent 间传递的消息结构，核心字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| call_id | str | 调用链 ID，关联 AgentCall |
| content | str | 原始消息内容，投递时不可变 |
| send_from | str | 发送者名称 |
| send_to | str | 接收者名称 |
| session_type | SessionType | MAIN 或 BTW |
| message_type | MessageType | TASK 或 NOTIFICATION |

**关键约束**：`content` 在 Agent 之间投递时始终是原始内容，渲染只发生在边界处（见渲染契约）。

### 渲染契约

渲染只发生在三个边界，不在中间环节改写 content：

| 边界 | 函数 | 方向 | 说明 |
|------|------|------|------|
| 入口 | parse_chat_input | 前端 → (send_to, content) | 解析 @xxx 格式，失败抛 InvalidMessageError |
| LLM 出口 | render_for_llm | AgentMessage → LLM prompt | 用 `<incoming_message>` 标签包裹 |
| UI 出口 | render_for_chat | Agent 输出 → 群聊记录 | 生成 `@xxx content` 格式 |

**XML 标签常量**（Tag 类）：预定义的 prompt 结构标签，用于 LLM 上下文的结构化输入：

| 标签 | 用途 |
|------|------|
| group_chat_history | 历史群聊摘要块 |
| recent_messages | 群聊最新消息块 |
| incoming_message | 当前传入的消息 |
| overall_summary | 摘要中的整体内容 |
| summary_for_you | 摘要中针对当前 Agent 的内容 |

### 异常体系

采用**统一基类 + 模块专属异常**的设计：

- `AgentsHubError`：所有异常基类，包含 message、error_code、details，提供 `to_mcp_response()` 转换方法
- 各模块继承基类，定义专属错误码

异常分类：

| 类别 | 异常 | error_code |
|------|------|------------|
| 业务错误 | AgentNotFoundError | AGENT_NOT_FOUND |
| 业务错误 | GroupChatNotFoundError | GROUP_CHAT_NOT_FOUND |
| 业务错误 | MessageDeliveryError | MESSAGE_DELIVERY_FAILED |
| 业务错误 | AgentExecutionError | AGENT_EXECUTION_FAILED |
| 业务错误 | AgentTimeoutError | AGENT_TIMEOUT |
| 验证错误 | InvalidMessageError | INVALID_MESSAGE |
| 系统错误 | FileSystemError | FILE_SYSTEM_ERROR |
| 系统错误 | CompactionError | COMPACTION_FAILED |

### 常量与持久化格式

- `MAX_TOKEN`：压缩阈值（当前 1000 token），用于判断是否需要压缩群聊历史
- `LOCAL_DATA_PATH`：本地数据存储根路径

持久化文件格式定义（详见 constants.py 注释）：
- `<group_chat_id>.jsonl`：群聊消息历史，首行为 meta_data
- `agent_session_state.json`：Agent session 映射 + 上下文加载状态
- `compact_history.jsonl`：压缩历史，每条包含 summary 和 per-agent 关键信息

## Technical Contract

### 跨层依赖契约

foundation 的数据结构是所有 core 层的共享契约：

- `AgentMessage`：communication 层的消息路由、agent 层的消息处理、orchestration 层的群聊管理都依赖此结构
- `CallStatus`：communication 层的 AgentCall 状态管理依赖此枚举
- `SessionType` / `MessageType`：agent 层的消息处理逻辑依赖这两个枚举做分支判断
- `render_for_llm` / `render_for_chat`：agent 层的 run() 循环使用这两个函数做渲染

### MCP 响应契约

所有 foundation 异常都支持 `to_mcp_response()` 转换，返回格式：

```json
{
  "success": false,
  "error_code": "<ERROR_CODE>",
  "message": "<人类可读错误信息>",
  "details": {}
}
```

## Out of Spec

- foundation 不涉及任何业务逻辑实现
- 不涉及持久化的具体读写操作（属于 context/group_chat_repository）
- 不涉及消息路由和投递机制（属于 communication/message_router）
- 不涉及 LLM 调用和 Agent 执行（属于 agent_bridge）
