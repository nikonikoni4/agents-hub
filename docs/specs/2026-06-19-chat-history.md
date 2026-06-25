---
version: 1.0
created_at: 2026-06-19
updated_at: 2026-06-19
last_updated: 创建 spec 初稿
abstract: 聊天历史记录模块规格，定义群聊聚合消息和成员个人历史的存储模型、检索接口、数据结构和分页策略
id: chat-history
title: 聊天历史记录
status: draft
module: core/context, api/services, utils
source_spec: 无
code_scope:
  - agents_hub/core/context/group_chat_session.py
  - agents_hub/core/context/group_chat_runtime.py
  - agents_hub/core/context/group_chat_repository.py
  - agents_hub/core/foundation/paths.py
  - agents_hub/utils/session_parser.py
  - agents_hub/api/services/group_chat_service.py
  - agents_hub/api/services/single_chat_service.py
  - agents_hub/api/schemas/group_chats.py
  - agents_hub/api/schemas/single_chat.py
contract_refs:
  - agents_hub/api/schemas/group_chats.py
  - agents_hub/api/schemas/single_chat.py
---

# 聊天历史记录

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |

## Overview

**业务问题**：系统中存在两种不同来源的聊天历史——群聊聚合消息（所有成员的对话汇总）和成员个人历史（单个 Agent 与平台的原始对话记录）。需要统一的存储、检索和展示机制，让前端能够按需获取不同粒度的历史记录。

**核心职责**：
- 管理群聊聚合消息的持久化和检索（JSONL 文件存储）
- 管理成员个人历史的解析和检索（平台 session 文件）
- 提供游标分页和缓存策略，支持前端无限滚动
- 定义统一的消息数据结构，屏蔽不同来源的差异

**不做什么**：
- 不负责消息的写入和投递（参考 `message-flow-and-persistence` spec）
- 不负责消息的搜索和过滤（未来功能）
- 不负责消息的压缩和上下文管理（参考 `core-context` spec）
- 不负责单聊通道的创建和管理（参考 `single-chat` spec）

## Scope

### 范围内

- 群聊聚合消息的存储模型（JSONL 文件）
- 成员个人历史的解析机制（Claude/Codex session 文件）
- 消息检索接口（get_messages、get_member_history）
- 游标分页策略
- 单聊消息历史的 LRU 缓存
- 消息数据结构定义（MessageInfo、MemberHistoryMessage、SessionMessage）

### 范围外

- 消息写入和投递机制 → 参考 `message-flow-and-persistence` spec
- 消息搜索和高级过滤 → 未来功能
- 上下文压缩和增量加载 → 参考 `core-context` spec
- 单聊通道生命周期管理 → 参考 `single-chat` spec
- 前端消息展示和交互 → 参考 `frontend-features` spec

## Technical Contract

### 存储模型

系统中存在两种独立的历史记录存储：

| 类型 | 存储位置 | 格式 | 数据来源 |
|------|---------|------|---------|
| 群聊聚合消息 | `{data_path}/teams/<project>/<id>/<id>.jsonl` | JSONL | GroupChatRuntime.add_message() |
| 成员个人历史 | Agent work_root 下的 session 文件 | JSONL（平台格式） | Claude/Codex 平台原生 |

**为什么分离存储？**
- 群聊聚合消息是系统组装的视图，包含所有成员的对话汇总
- 成员个人历史是平台原始记录，包含 user/assistant 完整交互
- 两者数据结构不同，用途不同，不应合并

### 群聊聚合消息

<key_function last_update="2026-06-25T19:37:44+08:00">
- agents_hub/core/context/group_chat_runtime.py
  - group_chat_runtime.GroupChatRuntime.get_message_dicts:130
- agents_hub/core/context/group_chat_session.py
  - group_chat_session.GroupChatSession.add_message:55
- agents_hub/core/context/group_chat_repository.py
  - group_chat_repository.GroupChatRepository.load_group_chat_session:54
  - group_chat_repository.GroupChatRepository.save_group_chat_session:110
- agents_hub/core/foundation/paths.py
  - paths.GroupChatPaths.messages_file:55
</key_function>

**数据结构**（内存模型 `GroupChatSession.messages`）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | int | 是 | 消息唯一标识（自增） |
| agent_name | str | 是 | 发送者名称（agent 角色名或 "user"） |
| content | str | 是 | 消息内容 |
| timestamp | str | 是 | ISO 8601 时间戳 |
| platform | str | 是 | 来源平台（claude/codex） |
| cwd | str | 否 | 消息产生时的工作目录 |
| modified_files | list[str] | 否 | 关联的修改文件列表 |
| git_diff_range | str | 否 | Git diff 范围 |
| permission_request | dict | 否 | 权限请求信息 |
| web_preview | dict | 否 | Web 预览信息 |
| files | list | 否 | 关联文件列表 |

**检索接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| get_message_dicts(limit, before) | 获取消息字典列表 | 游标分页，返回 before 时间戳之前的消息；limit<=0 返回全部 |

**分页策略**：
- 使用 `before` 时间戳作为游标（严格小于）
- 返回末尾 `limit` 条消息（最新的）
- 支持 `limit=0` 返回全部消息

### 成员个人历史

<key_function last_update="2026-06-19T00:00:00+08:00">
- agents_hub/utils/session_parser.py
  - session_parser.parse_session_file:120
  - session_parser.resolve_session_path:141
- agents_hub/api/services/group_chat_service.py
  - group_chat_service.GroupChatService.get_member_history:922
</key_function>

**数据结构**（`MemberHistoryMessage` / `SessionMessage`）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | str | 是 | 消息 ID（平台生成的 UUID） |
| role | str | 是 | 角色（user/assistant/system/tool） |
| content | str | 是 | 消息内容 |
| timestamp | str | 是 | 时间戳 |
| model | str | 否 | 使用的模型名称 |
| token_usage | dict | 否 | Token 使用量 |
| tool_calls | list[ToolCallInfo] | 否 | AI 工具调用记录 |

**ToolCallInfo 结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | 工具调用 ID |
| name | str | 工具名称 |
| input | dict | 输入参数 |

**Session 文件解析规则**：

| 平台 | 搜索目录 | 文件匹配 | 工具调用提取方式 |
|------|---------|---------|-----------------|
| Claude | `{work_root}/projects/` | `*{session_id}*.jsonl`（递归搜索） | 从 assistant message 的 content block 中提取 `tool_use` 块 |
| Codex/OpenCode | `{work_root}/sessions/` | `*{session_id}*.jsonl`（递归搜索） | 从顶层 `function_call` response_item 提取，通过 `call_id` 关联 |

**检索流程**：
1. 通过 `agent_member.json` 获取 Agent 的 `main_session` ID
2. 通过 `resolve_session_path()` 查找 session 文件路径
3. 通过 `parse_session_file()` 解析平台原生格式
4. 返回统一的 `MemberHistoryMessage` 列表

### 单聊消息历史

<key_function last_update="2026-06-19T00:00:00+08:00">
- agents_hub/api/services/single_chat_service.py
  - single_chat_service.SingleChatManager.get_messages:348
  - single_chat_service.SingleChatManager.get_messages_response:384
</key_function>

**数据结构**（`SessionMessageResponse`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | 消息 ID |
| role | str | 角色（user/assistant/system/tool） |
| content | str | 消息内容 |
| timestamp | str | 时间戳 |
| model | str | 使用的模型名称 |
| tool_calls | list[ToolCallInfo] | AI 工具调用记录 |

**缓存策略**：
- 使用 LRU 缓存，上限 15 个单聊
- 缓存命中时直接返回，不重新解析文件
- 发送消息后清除对应缓存，下次读取重新加载

### 前端 API 接口

<key_function last_update="2026-06-19T00:00:00+08:00">
- frontend/src/core/api/groupChatApi.ts
  - groupChatApi.getMessages:647
  - groupChatApi.getMemberHistory:937
</key_function>

| 函数 | API 路径 | 说明 |
|------|---------|------|
| `getMessages(chatId, limit, before?)` | `GET /group-chats/{chatId}/messages` | 群聊聚合消息，游标分页 |
| `getMemberHistory(chatId, agentName)` | `GET /group-chats/{chatId}/members/{agentName}/history` | 成员个人历史 |

### 响应 Schema

**MessageInfo**（群聊聚合消息响应）：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 消息唯一标识 |
| speaker | str | 发送者名称 |
| content | str | 消息内容 |
| timestamp | str | 时间戳 |
| platform | str | 来源平台 |
| cwd | str | 工作目录 |
| modified_files | list[str] | 修改文件列表 |
| git_diff_range | str | Git diff 范围 |
| permission_request | dict | 权限请求信息 |
| web_preview | dict | Web 预览信息 |
| files | list | 关联文件列表 |

**MemberHistoryResponse**（成员个人历史响应）：

| 字段 | 类型 | 说明 |
|------|------|------|
| agent_name | str | Agent 名称 |
| main_session_id | str | 主会话 ID |
| messages | list[MemberHistoryMessage] | 消息列表 |

**MemberHistoryMessage**：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | 消息 ID |
| role | str | 角色 |
| content | str | 消息内容 |
| timestamp | str | 时间戳 |
| model | str | 模型名称 |
| tool_calls | list[ToolCallInfo] | AI 工具调用记录 |

## Design Rationale

**为什么群聊消息使用 JSONL 格式？**
- JSONL 支持追加写入，不需要读取整个文件
- 每行一条记录，便于流式读取和增量加载
- 与平台 session 文件格式一致，降低解析复杂度

**为什么成员个人历史从 session 文件解析而不另存一份？**
- 遵循 SSOT 原则：session 文件是平台原生记录，是唯一真实来源
- 避免数据冗余和同步问题
- Agent 重启后 session 文件仍然存在，不依赖系统内存状态

**为什么使用游标分页而非偏移量分页？**
- 消息列表实时变化，偏移量分页会导致重复或遗漏
- 游标分页保证一致性，支持无限滚动
- 时间戳作为游标语义清晰，不需要维护额外状态

**为什么单聊使用 LRU 缓存？**
- session 文件解析是 IO 密集操作，频繁读取影响性能
- 用户通常在短时间内多次查看同一单聊的历史
- LRU 策略自动淘汰不活跃的缓存，控制内存使用

**有哪些约束？**
- 群聊聚合消息的 `id` 是自增整数，仅在单个群聊内唯一
- 成员个人历史依赖 `agent_member.json` 中的 `main_session` 字段，未分配 session 时返回空列表
- session 文件搜索使用 `rglob`，在大量文件时可能有性能问题

**有哪些已知限制？**
- 不支持消息搜索和全文检索
- 不支持按类型（如只看 user 消息）过滤
- 成员个人历史不支持分页，一次性返回全部消息
- 群聊聚合消息的分页基于内存中的消息列表，大量消息时内存占用较高

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **消息写入和投递**：`docs/specs/2026-06-05-message-flow-and-persistence.md` - 消息如何保存到群聊历史
- **群聊 API 端点**：`docs/specs/2026-06-03-group-chat-api.md` - HTTP 接口定义和路由处理
- **上下文压缩**：`docs/specs/2026-05-31-core-context.md` - 消息压缩和增量加载机制
- **单聊通道**：`docs/specs/2026-06-08-single-chat.md` - 单聊生命周期和流式消息
- **前端展示**：`docs/specs/2026-06-06-frontend-features.md` - ChatHistoryPanel 组件和 useChatHistory hook
