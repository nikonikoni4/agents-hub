---
version: 2.0
created_at: 2026-06-08
updated_at: 2026-06-18
last_updated: 按新 spec 规则重构：移除执行细节，补充 key_function 标签和 Design Rationale
abstract: 单聊通道模块规格，定义用户与单个 Agent 直接对话的轻量级通道，包括三种创建模式、流式消息发送、Session 文件解析和 LRU 消息缓存
id: single-chat
title: 单聊通道模块
status: unstable
module: api/single_chat
source_spec: docs/superpowers/specs/2026-06-07-single-chat-design.md
related_plan: 无
code_scope:
  - agents_hub/api/routes/single_chat.py
  - agents_hub/api/services/single_chat_service.py
  - agents_hub/api/schemas/single_chat.py
  - agents_hub/utils/session_parser.py
contract_refs:
  - agents_hub/api/schemas/single_chat.py
---

# 单聊通道模块

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 2.0 | 按新 spec 规则重构：移除执行细节，补充 key_function 标签和 Design Rationale |
| 1.0 | 创建 spec 初稿，基于实现代码和设计文档 |

## Overview

**业务问题**：用户需要与单个 Agent 进行直接对话，不依赖群聊的编排逻辑（MessageRouter、AgentCallManager、Manager/Worker）。群聊通道的消息路由和编排机制对单聊场景过于重量级。

**核心职责**：提供轻量级的单聊通道，采用**解析器 + 透传层**架构——agents-hub 负责解析平台 session 文件和透传消息，消息内容由底层平台（Claude Code / Codex）管理。

**与群聊的区别**：

| 特性 | 群聊 | 单聊 |
|------|------|------|
| 消息投递 | 放入 message_queue | 直接执行 |
| 响应方式 | WebSocket 广播 | SSE 流式返回 |
| 路由逻辑 | MessageRouter | 无需路由 |
| 编排逻辑 | Manager/Worker | 无 |

## Scope

### 范围内

- 单聊 CRUD（创建、查询详情、列出全部）
- 三种创建模式：新建、Fork 群聊会话、继续群聊会话
- 流式消息发送（SSE）
- 消息历史加载（从平台 session 文件解析）
- LRU 消息缓存（最多 15 个单聊）
- Session 文件路径解析（按平台和 work_root）

### 范围外

- 单聊删除
- 单聊配置修改（名称、Agent 等）
- 消息搜索和过滤
- Docker 模式下的单聊（executor 支持 fork_from，但单聊 API 未集成 Docker 路径）

## Technical Contract

### API 端点

<key_function last_update="2026-06-22T20:27:51+08:00">
- agents_hub/api/routes/single_chat.py
  - single_chat.list_single_chats:25
  - single_chat.get_single_chat:33
  - single_chat.send_message_stream:42
  - single_chat.get_messages:78
</key_function>

| 端点 | 方法 | 说明 | 路由处理函数 | 错误码 |
|------|------|------|-------------|--------|
| `/api/v1/single-chats` | GET | 列出所有单聊（按 last_active_at 降序） | `list_single_chats` | - |
| `/api/v1/single-chats/{single_chat_id}` | GET | 获取单聊详情 | `get_single_chat` | 404 |
| `/api/v1/single-chats/messages/stream` | POST | 发送消息（SSE 流式） | `send_message_stream` | 404 |
| `/api/v1/single-chats/{single_chat_id}/messages` | GET | 获取消息历史 | `get_messages` | 404 |

**发送消息端点特殊行为**：当 `single_chat_id` 为空时，自动创建单聊（需 `agent_name`），响应头 `X-Single-Chat-Id` 返回真实 ID。

### 创建模式

**SingleChatType**：`new` | `fork` | `continue_group_chat`

| 模式 | 行为 | 必填参数 | 可选参数 |
|------|------|---------|---------|
| `new` | 创建空白单聊，session_id 首次对话后更新 | `single_chat_name`、`agent_name`、`cwd` | - |
| `fork` | 从群聊中某个 Agent 的会话创建分支，不继承原 session_id | `group_chat_id` | `agent_name`、`cwd` |
| `continue_group_chat` | 直接继续群聊中某个 Agent 的会话（不 fork），继承原 session_id | `group_chat_id` | `agent_name`、`cwd` |

### 数据模型

**SingleChatIndex**（持久化到 `index.json`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `single_chat_id` | `str` | 唯一标识 |
| `single_chat_name` | `str` | 单聊名称 |
| `type` | `SingleChatType` | 创建类型 |
| `agent_name` | `str` | Agent 名称 |
| `platform` | `AgentPlatform` | 平台类型（claude/codex） |
| `session_id` | `str \| None` | 平台 session ID（首次对话后更新） |
| `session_path` | `str \| None` | 平台 session 文件路径 |
| `group_chat_id` | `str \| None` | 来源群聊 ID（可选） |
| `cwd` | `str` | 工作目录 |
| `created_at` | `str` | 创建时间（ISO 8601） |
| `last_active_at` | `str` | 最后活跃时间（ISO 8601） |

**SessionMessage**（从平台 session 文件解析）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `str` | 消息唯一标识 |
| `role` | `str` | `user` \| `assistant` \| `system` \| `tool` |
| `content` | `str` | 消息内容 |
| `timestamp` | `str` | 时间戳 |
| `model` | `str \| None` | 使用的模型（可选） |
| `token_usage` | `object \| None` | Token 使用情况（可选） |
| `tool_calls` | `list[ToolCallInfo] \| None` | AI 工具调用记录（可选） |

**ToolCallInfo 结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `str` | 工具调用 ID |
| `name` | `str` | 工具名称 |
| `input` | `dict` | 输入参数 |

### API Request/Response Schema

**CreateSingleChatRequest**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | `SingleChatType` | 是 | 创建类型 |
| `single_chat_name` | `str` | 是 | 单聊名称 |
| `agent_name` | `str` | 是 | Agent 名称 |
| `group_chat_id` | `str` | 否 | 来源群聊 ID（fork/continue 时必填） |
| `cwd` | `str` | 否 | 工作目录 |

**CreateSingleChatResponse**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `single_chat_id` | `str` | 创建的单聊 ID |
| `single_chat_name` | `str` | 单聊名称 |
| `type` | `SingleChatType` | 创建类型 |

**SendMessageRequest**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `content` | `str` | 是 | 消息内容 |
| `single_chat_id` | `str` | 否 | 为空时自动创建单聊 |
| `single_chat_name` | `str` | 否 | 自动创建时的名称 |
| `agent_name` | `str` | 否 | 自动创建时的 Agent（single_chat_id 为空时必填） |
| `type` | `SingleChatType` | 否 | 自动创建时的类型（默认 NEW） |
| `group_chat_id` | `str` | 否 | fork/continue 时使用 |

**SingleChatResponse**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `single_chat_id` | `str` | 单聊 ID |
| `single_chat_name` | `str` | 单聊名称 |
| `type` | `SingleChatType` | 创建类型 |
| `agent_name` | `str` | Agent 名称 |
| `platform` | `AgentPlatform` | 平台类型 |
| `session_id` | `str \| None` | 平台 session ID |
| `group_chat_id` | `str \| None` | 来源群聊 ID |
| `cwd` | `str` | 工作目录 |
| `created_at` | `str` | 创建时间 |
| `last_active_at` | `str` | 最后活跃时间 |

**MessageHistoryResponse**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `messages` | `list[SessionMessageResponse]` | 消息列表 |

**SessionMessageResponse**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `str` | 消息 ID |
| `role` | `str` | 角色 |
| `content` | `str` | 内容 |
| `timestamp` | `str` | 时间戳 |
| `model` | `str \| None` | 模型名 |
| `tool_calls` | `list[ToolCallInfo] \| None` | AI 工具调用记录（可选） |

### Session 文件解析规则

解析器从平台 session 文件（JSONL 格式）提取消息，输出 `SessionMessage` 列表。各平台解析差异如下：

| 平台 | 支持角色 | 内容提取方式 | 工具调用提取 |
|------|---------|-------------|-------------|
| Claude | user, assistant | 字符串或内容块数组（提取 text 块） | 从 assistant message 的 content block 中提取 `tool_use` 块（id、name、input） |
| Codex | user, assistant, system, tool | 内容块数组（提取 input_text/output_text 块），未知角色跳过 | 从顶层 `function_call` response_item 提取（call_id、name、arguments），通过 `call_id` 关联 `function_call_output` |

**Codex 工具调用特殊格式**：
- 工具调用是独立的顶层 `response_item`（`payload.type = "function_call"`），不是 assistant message 的 content block
- 参数是 JSON string（`payload.arguments`），需要 `json.loads()` 反序列化
- 通过 `call_id` 关联 `function_call` 和 `function_call_output`
- 一个 assistant 消息可能对应多个 `function_call`（并行调用多个工具）

### 缓存策略

- 缓存上限：15 个单聊
- 缓存命中：移到最后（标记为最近使用）
- 缓存满：淘汰最久未使用的
- 消息发送后：清除该单聊缓存（下次加载时重新解析文件）

### 持久化路径

- 索引文件：`{config.data_path}/single_chats/index.json`
- Session 文件：由 `RoleConfig.work_root` + 平台类型决定

## Design Rationale

**为什么采用解析器 + 透传层架构？**
- 单聊不需要群聊的 MessageRouter 和 AgentCallManager 编排逻辑
- 消息内容由底层平台（Claude Code / Codex）的 session 文件管理，agents-hub 只做解析和透传
- 避免重复实现消息存储，符合 SSOT 原则

**为什么使用 LRU 缓存？**
- Session 文件解析是 I/O 密集操作（递归查找 + JSONL 解析）
- 用户在短时间内可能反复查看同一单聊的消息历史
- 15 个单聊上限平衡了内存占用和命中率
- 发送消息后清除缓存确保下次读取拿到最新数据

**为什么支持自动创建单聊？**
- 前端可以在发送首条消息时一并创建单聊，减少用户操作步骤
- `SendMessageRequest.single_chat_id` 为空时触发自动创建，通过响应头 `X-Single-Chat-Id` 返回 ID

**已知限制**：
- LRU 缓存仅在单进程内有效，多进程部署下各进程缓存独立
- Session 文件解析依赖特定的 JSONL 格式，平台格式变化会导致解析失败
- fork 模式仅支持 Claude 和 Codex 平台

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **群聊编排**：[docs/specs/2026-06-03-group-chat-api.md] - MessageRouter、AgentCallManager 等编排逻辑
- **Agent Bridge**：[docs/specs/2026-05-31-core-communication.md] - agent_bridge.execute_stream 的实现细节
- **前端 UI**：由前端 spec 覆盖单聊的界面交互
- **Session 解析器实现**：[docs/flows/] - session_parser 的完整解析链路
