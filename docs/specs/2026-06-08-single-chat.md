---
version: 1.0
created_at: 2026-06-08
updated_at: 2026-06-08
last_updated: 从实现代码和设计文档生成正式 spec
abstract: 单聊通道模块规格，定义用户与单个 Agent 直接对话的轻量级通道，包括三种创建模式、流式消息发送、Session 文件解析和 LRU 消息缓存
id: single-chat
title: 单聊通道模块
status: unstable
module: api/single_chat
sourc_spec: docs/superpowers/specs/2026-06-07-single-chat-design.md
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
| 1.0 | 创建 spec 初稿，基于实现代码和设计文档 |

## Overview

单聊通道是用户与单个 Agent 直接对话的通道，不依赖群聊的编排逻辑（MessageRouter、AgentCallManager、Manager/Worker）。采用**解析器 + 透传层**架构：agents-hub 负责解析平台 session 文件和透传消息，消息内容由底层平台（Claude Code / Codex）管理。

**核心特征**：
- 直接调用 `agent_bridge.execute_stream()`，无需消息队列
- 消息权威源为平台 session 文件（SSOT）
- 索引持久化到 `index.json`，消息通过 LRU 缓存加速访问

**与群聊的区别**：

| 特性 | 群聊 | 单聊 |
|------|------|------|
| 消息投递 | 放入 message_queue | 直接执行 |
| 响应方式 | WebSocket 广播 | SSE 流式返回 |
| 路由逻辑 | MessageRouter | 无需路由 |
| 编排逻辑 | Manager/Worker | 无 |

## Scope

**当前阶段**：
- 单聊 CRUD（创建、查询详情、列出全部）
- 三种创建模式：新建、Fork 群聊会话、继续群聊会话
- 流式消息发送（SSE）
- 消息历史加载（从平台 session 文件解析）
- LRU 消息缓存（最多 15 个单聊）
- Session 文件路径解析（按平台和 work_root）

**不在范围内**：
- 单聊删除
- 单聊配置修改（名称、Agent 等）
- 消息搜索和过滤
- Docker 模式下的单聊（executor 支持 fork_from，但单聊 API 未集成 Docker 路径）

## Core Behavior

### 三种创建模式

**新建（new）**：
- 创建空白单聊，session_id 初始为空
- 首次发送消息时 CLI 返回 session_id，更新索引
- 必填：`single_chat_name`、`agent_name`、`cwd`

**Fork 群聊会话（fork）**：
- 从群聊中某个 Agent 的会话创建分支
- 不继承原 session_id，通过 `fork_from` 参数创建新会话
- 必填：`group_chat_id`
- 首次发送消息时从群聊获取 fork 源 session

**继续群聊会话（continue_group_chat）**：
- 直接继续群聊中某个 Agent 的会话（不 fork）
- 继承原 session_id 和 session_path
- 消息不进入群聊历史（纯私聊）
- 必填：`group_chat_id`

### 消息发送流程

```
POST /single-chats/{id}/messages/stream
  → 加载单聊索引
  → 获取 Role 配置
  → 调用 agent_bridge.execute_stream(prompt, config, session_id, cwd, fork_from)
  → 流式返回 SSE 事件
  → 首次获取 session_id 时更新索引和 session_path
  → 流结束后更新 last_active_at
  → 清除该单聊的 LRU 缓存
```

### 消息历史加载

```
GET /single-chats/{id}/messages
  → 检查 LRU 缓存命中 → 返回缓存
  → 缓存未命中且 session_path 存在 → 解析平台 session 文件
  → 写入 LRU 缓存（超过上限淘汰最久未使用）
  → 缓存未命中且 session_path 为空 → 返回空列表
```

### Session 路径解析

根据 session_id、平台类型和 work_root 查找 session 文件：

- **Claude 平台**：搜索 `work_root/projects/` 目录
- **Codex 平台**：搜索 `work_root/sessions/` 目录
- 搜索方式：递归查找文件名包含 session_id 的 `.jsonl` 文件
- 未找到返回 `None`（不抛异常）

### LRU 缓存策略

- 缓存上限：15 个单聊
- 缓存命中：移到最后（标记为最近使用）
- 缓存满：淘汰最久未使用的
- 消息发送后：清除该单聊缓存（下次加载时重新解析文件）

## Technical Contract

### API 端点

**创建单聊**：
```
POST /api/v1/single-chats
Request: CreateSingleChatRequest
Response: CreateSingleChatResponse
Errors: 404 (agent 不存在), 400 (缺少 group_chat_id), 422 (字段验证失败)
```

**列出单聊**：
```
GET /api/v1/single-chats
Response: SingleChatListResponse（按 last_active_at 降序）
```

**获取单聊详情**：
```
GET /api/v1/single-chats/{single_chat_id}
Response: SingleChatResponse
Errors: 404 (单聊不存在)
```

**发送消息（流式）**：
```
POST /api/v1/single-chats/{single_chat_id}/messages/stream
Request: SendMessageRequest
Response: SSE stream (text/event-stream)
Errors: 404 (单聊不存在)
```

**获取消息历史**：
```
GET /api/v1/single-chats/{single_chat_id}/messages
Response: MessageHistoryResponse
Errors: 404 (单聊不存在)
```

### 数据模型

**SingleChatType**：`new` | `fork` | `continue_group_chat`

**SingleChatIndex**（持久化到 `index.json`）：
- `single_chat_id`: 唯一标识
- `single_chat_name`: 单聊名称
- `type`: 创建类型
- `agent_name`: Agent 名称
- `platform`: 平台类型（claude/codex）
- `session_id`: 平台 session ID（首次对话后更新）
- `session_path`: 平台 session 文件路径
- `group_chat_id`: 来源群聊 ID（可选）
- `cwd`: 工作目录
- `created_at`: 创建时间
- `last_active_at`: 最后活跃时间

**SessionMessage**（从平台 session 文件解析）：
- `id`: 消息唯一标识
- `role`: `user` | `assistant` | `system` | `tool`
- `content`: 消息内容
- `timestamp`: 时间戳
- `model`: 使用的模型（可选）
- `token_usage`: Token 使用情况（可选）

### Session 文件解析规则

**Claude 平台**：
- 消息类型字段：`type`（`user` / `assistant`）
- user 消息：`message.content`（字符串）
- assistant 消息：`message.content`（内容块数组，提取 `type=text` 的块）
- ID 来源：`uuid` 或 `message.id`

**Codex 平台**：
- 消息类型字段：`type`（`response_item`）
- 角色来源：`payload.role`（校验白名单：user/assistant/system/tool）
- 内容来源：`payload.content`（提取 `type=input_text` 或 `type=output_text` 的块）
- 未知角色的消息被跳过

### 持久化路径

- 索引文件：`{config.data_path}/single_chats/index.json`
- Session 文件：由 `RoleConfig.work_root` + 平台类型决定

## Acceptance Notes

- 创建单聊后 index.json 包含新记录
- 发送消息后 session_id 和 session_path 被更新
- 消息历史能从 session 文件正确解析
- LRU 缓存超过 15 个时淘汰最久未使用的
- agent 不存在时返回 404
- fork/continue 类型缺少 group_chat_id 时返回 400
- SSE 事件格式符合规范（多行 data 前缀）

## Out of Spec

- 单聊删除功能（未实现）
- Docker 模式下的单聊执行路径
- 前端 UI 交互（由前端 spec 覆盖）
- agent_bridge 的 fork_from 实现细节（由 agent-bridge spec 覆盖）
- WebSocket 实时推送（单聊使用 SSE，不使用 WebSocket）
