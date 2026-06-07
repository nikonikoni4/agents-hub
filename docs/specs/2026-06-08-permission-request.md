---
version: 1.0
created_at: 2026-06-08
updated_at: 2026-06-08
last_updated: 创建 spec 初稿
abstract: 权限请求功能规格，定义 Agent 请求用户授权的 MCP 工具、消息内嵌权限卡片、审批 API 和前端交互
id: permission-request
title: 权限请求功能
status: unstable
module: mcp/server, api/group_chat, core/context, frontend/chat
sourc_spec: 无（brainstorming 讨论直接产出）
related_plan: C:\Users\15535\.claude\plans\shimmying-conjuring-river.md
code_scope:
  - agents_hub/mcp/server.py
  - agents_hub/agent_bridge/models.py
  - agents_hub/api/schemas/group_chats.py
  - agents_hub/api/routes/group_chat.py
  - agents_hub/api/services/group_chat_service.py
  - agents_hub/core/context/group_chat_runtime.py
  - agents_hub/core/context/group_chat_session.py
  - frontend/src/shared/types/api-schemas.ts
  - frontend/src/core/api/groupChatApi.ts
  - frontend/src/shared/components/PermissionRequest/
  - frontend/src/layouts/ChatArea/ChatArea.tsx
contract_refs:
  - agents_hub/api/schemas/group_chats.py
  - frontend/src/shared/types/api-schemas.ts
---

# 权限请求功能

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |

## Overview

权限请求功能允许 Agent 在执行敏感操作前向用户发起授权请求。Agent 通过 MCP 工具 `request_permission` 创建一条带 `permission_request` 字段的消息，该消息在群聊时间线中以专用卡片形式渲染，用户可点击"允许"或"拒绝"按钮进行审批。

**核心设计决策**：权限请求是消息的扩展字段，不是独立系统。它复用现有消息存储（JSONL）、WebSocket 刷新机制和群聊时间线，避免引入新的持久化层。

**架构分层**：
- **MCP 层**：`request_permission` 工具创建权限请求消息
- **消息流水线**：`AgentResult.permission_request` → `GroupChatSession.add_message()` → JSONL 持久化 → `GroupChatRuntime.get_message_dicts()` 透传
- **API 层**：`PATCH /messages/{id}/permission` 更新审批状态
- **通知层**：审批结果通过 `AgentCallManager` 以 NOTIFICATION 类型发送给请求方 Agent

## Scope

**当前阶段**：
- Agent 通过 MCP 工具发起权限请求（标题 + 描述）
- 权限请求在群聊时间线中以卡片形式展示
- 用户点击"允许"或"拒绝"进行审批
- 审批结果通知请求方 Agent
- 已审批的卡片显示为已解决状态（半透明 + 状态标签）
- WebSocket 刷新同步审批状态

**不在范围内**：
- 权限请求的过期机制
- 权限请求的批量审批
- 权限请求的撤销（Agent 主动取消）
- 细粒度权限类型（文件读取、命令执行等分类）
- 权限请求的历史审计日志

## Core Behavior

### 权限请求生命周期

```
1. Agent 调用 request_permission MCP 工具
   → 构建 permission_request 数据（uuid4 作为 request_id，status="pending"）
   → 创建 AgentResult，注入 permission_request 字段
   → 写入消息历史（JSONL），广播 WebSocket refresh

2. 前端收到消息列表
   → MessageBubble 检测 msg.permission_request 字段存在
   → 渲染 PermissionRequest 卡片（标题、描述、时间、允许/拒绝按钮）

3. 用户点击"允许"或"拒绝"
   → 前端调用 PATCH /messages/{id}/permission
   → 按钮立即禁用（本地 acted 状态），防止重复提交

4. 后端处理审批
   → 验证 status 合法性（approved/rejected）
   → 更新消息中 permission_request.status 字段
   → 查找请求方 Agent，通过 AgentCallManager 发送 NOTIFICATION
   → 广播 WebSocket refresh

5. 前端收到 refresh
   → 重新拉取消息 → 卡片进入已解决状态（半透明 + "已允许"/"已拒绝"标签）
```

### 消息内嵌设计

权限请求不是独立实体，而是消息的一个可选字段：

- 消息的 `content` 字段显示 `[权限请求] {title}` 文本摘要
- 消息的 `permission_request` 字段携带完整权限数据
- 前端根据 `permission_request` 字段是否存在来决定渲染方式
- 不存在该字段时，消息按普通 Markdown 气泡渲染

### 审批通知机制

审批结果复用现有 `AgentCallManager` 通知体系：

- 审批操作完成后，查找消息中 `permission_request.requested_by` 字段
- 如果请求方不是 user，创建一个 `NOTIFICATION` 类型的 AgentCall
- 通知内容包含审批结果和权限标题
- 请求方 Agent 在下一轮消息处理时收到通知

## Technical Contract

### 端点总览

| 方法 | 路径 | 说明 |
|------|------|------|
| PATCH | `/api/v1/group-chats/{group_chat_id}/messages/{message_id}/permission` | 更新权限请求状态 |

### Schema 定义

**PermissionRequestInfo**（嵌入 MessageInfo 中）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| request_id | str | 是 | 权限请求唯一 ID（uuid4） |
| title | str | 是 | 权限请求标题 |
| content | str | 是 | 权限请求详细描述 |
| status | str | 否 | 请求状态，默认 "pending"，可选 approved/rejected |
| requested_by | str | 是 | 请求发起者名称（Agent 角色名） |

**PermissionUpdateRequest**（PATCH 请求体）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | str | 是 | 新状态：approved 或 rejected |

**PermissionUpdateResponse**（PATCH 响应）：

| 字段 | 类型 | 说明 |
|------|------|------|
| ok | bool | 操作是否成功 |
| message_id | int | 更新的消息 ID |
| new_status | str | 更新后的状态 |

### MCP 工具

**request_permission**：

| 参数 | 类型 | 说明 |
|------|------|------|
| agent_token | str | 调用者的身份令牌 |
| title | str | 权限请求标题 |
| content | str | 权限请求详细描述 |

返回：`{"request_id": str, "status": "pending"}` 或错误响应。

### 消息流水线透传

权限请求数据沿现有 `AgentResult → Message → API` 流水线透传：

1. `AgentResult.permission_request`：agent_bridge 层数据模型
2. `GroupChatSession.add_message()`：写入消息 dict，持久化到 JSONL
3. `GroupChatRuntime.get_message_dicts()`：从消息 dict 透传到 API 响应

### 异常处理

| HTTP 状态码 | 触发场景 |
|-------------|----------|
| 404 | 群聊或消息不存在 |
| 422 | 无效的状态值（非 approved/rejected） |

## Interaction / UX Notes

### 权限请求卡片

- 在群聊时间线中，带 `permission_request` 的消息渲染为专用卡片
- 卡片包含：锁图标、标题、请求方 Agent 名称（标签）、时间、描述内容、允许/拒绝按钮
- 卡片左侧有强调色竖条（`border-left: 3px solid var(--accent-color)`）
- 卡片最大宽度为 50%，左对齐（与 Agent 消息一致）

### 审批交互

- 点击"允许"或"拒绝"后，按钮立即禁用（本地状态），防止重复提交
- API 调用完成后，等待 WebSocket refresh 更新卡片状态
- 已审批的卡片进入已解决状态：半透明（opacity: 0.55）、按钮隐藏、显示"已允许"或"已拒绝"标签
- 已解决状态的卡片不可交互（pointer-events: none）

### 消息操作栏

- 权限请求卡片底部仍有置顶和引用按钮，与普通消息一致
- 置顶和引用操作不受权限状态影响

## Acceptance Notes

1. Agent 调用 `request_permission` 后，群聊中出现权限请求卡片
2. 卡片正确显示标题、描述、时间和请求方 Agent 名称
3. 点击"允许"按钮后，按钮立即禁用，卡片最终变为"已允许"状态
4. 点击"拒绝"按钮后，按钮立即禁用，卡片最终变为"已拒绝"状态
5. 审批后请求方 Agent 收到 NOTIFICATION 通知
6. 已审批的卡片不可再次操作
7. 不同会话的权限请求互相隔离

## Out of Spec

以下内容不在本 spec 中长期维护：

1. 权限请求的过期机制（后续迭代）
2. 权限请求的批量审批
3. 权限请求的撤销（Agent 主动取消）
4. 细粒度权限类型分类
5. 权限请求的历史审计日志
6. WebSocket 事件的具体实现细节（由 realtime spec 处理）
7. 前端组件的具体实现（TypeScript 类型、状态管理、样式代码）
