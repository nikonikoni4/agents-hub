---
version: 2.0
created_at: 2026-06-08
updated_at: 2026-06-18
last_updated: 按照新 spec 规则重构：移除执行细节，添加 key_function 标签和 Design Rationale
abstract: 权限请求功能规格，定义 Agent 请求用户授权的 MCP 工具、消息内嵌权限卡片、审批 API 和前端交互
---

# 权限请求功能

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 2.0 | 按照新 spec 规则重构 |
| 1.0 | 创建 spec 初稿 |

## Overview

**业务问题**：Agent 在执行敏感操作（如文件写入、命令执行）前需要获得用户授权，但现有群聊系统缺乏结构化的权限请求与审批机制。

**核心职责**：
- 提供 MCP 工具 `request_permission`，允许 Agent 发起权限请求
- 权限请求以消息扩展字段形式存在，复用现有消息存储和 WebSocket 机制
- 提供审批 API，用户可批准或拒绝请求
- 审批结果通过 `AgentCallManager` 通知请求方 Agent

**关键设计**：权限请求是消息的扩展字段（`permission_request`），不是独立实体。它复用 JSONL 持久化和 WebSocket 刷新，避免引入新的持久化层。

## Scope

### 范围内

- Agent 通过 MCP 工具发起权限请求（标题 + 描述）
- 权限请求在群聊时间线中以卡片形式展示
- 用户点击"允许"或"拒绝"进行审批
- 审批结果通知请求方 Agent
- 已审批的卡片显示为已解决状态
- WebSocket 刷新同步审批状态

### 范围外

- 权限请求的过期机制
- 权限请求的批量审批
- 权限请求的撤销（Agent 主动取消）
- 细粒度权限类型（文件读取、命令执行等分类）
- 权限请求的历史审计日志
- WebSocket 事件的具体实现细节（参见 realtime spec）

## Technical Contract

### MCP 工具

<key_function last_update="2026-06-22T20:27:51+08:00">
- agents_hub/mcp/server.py
  - server.request_permission:863
</key_function>

**request_permission**：

| 参数 | 类型 | 说明 |
|------|------|------|
| agent_token | str | 调用者的身份令牌 |
| title | str | 权限请求标题 |
| content | str | 权限请求详细描述 |

返回：`{"request_id": str, "status": "pending"}` 或错误响应。

### API 端点

<key_function last_update="2026-06-18T10:00:00+08:00">
- agents_hub/api/routes/group_chat.py
  - group_chat.update_permission_status:295
</key_function>

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

### 数据模型

<key_function last_update="2026-06-18T10:00:00+08:00">
- agents_hub/agent_bridge/models.py
  - models.AgentResult:47
</key_function>

权限请求通过 `AgentResult.permission_request` 字段承载，沿 `AgentResult → Message → API` 流水线透传到前端。

### 状态机规则

```
pending → approved
pending → rejected
```

- 状态转换为单向，不可回退
- 每条权限请求只能审批一次

### 异常处理

| HTTP 状态码 | 触发场景 |
|-------------|----------|
| 404 | 群聊或消息不存在 |
| 422 | 无效的状态值（非 approved/rejected） |

## Design Rationale

**为什么权限请求是消息扩展字段而非独立实体？**
- 复用现有 JSONL 持久化、WebSocket 刷新和群聊时间线渲染
- 避免引入新的持久化层和独立的 UI 列表
- 权限请求天然附着于群聊上下文，作为消息的一部分更符合用户心智模型

**为什么审批结果通过 AgentCallManager 通知？**
- 复用现有的 Agent 间通信机制，避免引入新的通知通道
- NOTIFICATION 类型的 AgentCall 与现有消息处理流程一致

**有哪些约束？**
- 权限请求依赖群聊消息系统，无法脱离群聊使用
- 审批状态不可回退，不支持撤销操作

**有哪些已知限制？**
- 不支持权限请求过期机制
- 不支持批量审批
- 不支持细粒度权限类型分类

## Interaction / UX Notes

### 权限请求卡片

- 带 `permission_request` 的消息渲染为专用卡片，包含锁图标、标题、请求方 Agent 名称、时间、描述、允许/拒绝按钮
- 卡片左侧有强调色竖条，最大宽度 50%，左对齐
- 已审批卡片进入已解决状态：半透明、按钮隐藏、显示"已允许"/"已拒绝"标签
- 已解决状态不可交互（pointer-events: none）

### 审批交互

- 点击按钮后立即禁用（本地状态），防止重复提交
- 等待 WebSocket refresh 更新最终状态
- 置顶和引用操作不受权限状态影响

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **消息持久化**：JSONL 存储和读取逻辑（参见 group_chat_session spec）
- **WebSocket 实时更新**：事件广播和前端刷新机制（参见 realtime spec）
- **Agent 间通知**：AgentCallManager 的 NOTIFICATION 处理（参见 agent_call spec）
- **前端组件实现**：PermissionRequest 组件的具体代码（TypeScript 类型、状态管理、样式）
