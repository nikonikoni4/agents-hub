---
version: 1.0
created_at: 2026-06-25
updated_at: 2026-06-25
last_updated: 创建私聊功能 spec 初稿
abstract: 群聊内私聊功能规格，定义用户在群聊中与单个 Agent 进行私聊对话的能力，包括状态管理、消息拦截、操作限制和前端 UI
id: private-chat
title: 群聊内私聊功能
status: unstable
module: core/orchestration, api/services, frontend/private-chat
source_spec: 无
related_plan: 无
code_scope:
  - agents_hub/core/orchestration/group_chat.py
  - agents_hub/api/services/group_chat_service.py
  - agents_hub/api/routes/group_chat.py
  - frontend/src/features/private-chat/
contract_refs:
  - agents_hub/api/schemas/group_chat.py
---

# 群聊内私聊功能

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |

## Overview

**业务问题**：用户在群聊场景下，需要与某个 Agent 进行一对一的私密对话，而不让其他 Agent 看到消息内容。这在调试、测试或需要隔离对话时非常有用。

**核心职责**：在群聊内提供私聊通道，通过状态标记和消息拦截实现对话隔离。

**与单聊的区别**：

| 特性 | 单聊 (Single Chat) | 私聊 (Private Chat) |
|------|---------------------|---------------------|
| 会话独立性 | 独立会话，不关联群聊 | 复用群聊会话 |
| 消息路由 | 直接执行，无路由 | 通过 MessageRouter，但拦截其他 Agent |
| 生命周期 | 独立管理 | 跟随群聊，3 分钟超时自动退出 |
| 状态标记 | 无特殊标记 | Agent 状态变为 `in_private_chat` |

## Scope

### 范围内

- 进入/退出私聊（状态变更）
- 消息拦截：私聊中只投递给目标 Agent，其他 Agent 收到 NOTIFICATION 自动回复
- 操作限制：私聊中的 Agent 不能被停止、重置、压缩
- Manager 限制：Manager 角色禁止进入私聊
- 前端 UI：退出按钮、3 分钟超时计时器

### 范围外

- 私聊消息持久化（复用群聊消息）
- 私聊历史查询
- 多 Agent 同时私聊

## Technical Contract

### 状态定义

Agent 成员状态扩展为：

| 状态 | 说明 |
|------|------|
| `idle` | 空闲，可接收任务 |
| `busy` | 忙碌，正在执行任务 |
| `stopped` | 已停止 |
| `in_private_chat` | 私聊中，不可被停止/重置/压缩 |
| `in_loop` | 循环中 |

### API 端点

<key_function last_update="2026-06-28T09:38:27+08:00">
- agents_hub/api/routes/group_chat.py
  - group_chat.start_private_chat
  - group_chat.stop_private_chat
</key_function>

| 端点 | 方法 | 说明 | 错误码 |
|------|------|------|--------|
| `/api/v1/group-chats/{group_chat_id}/members/{agent_name}/start-private-chat` | POST | 进入私聊 | 404, 409 |
| `/api/v1/group-chats/{group_chat_id}/members/{agent_name}/stop-private-chat` | POST | 退出私聊 | 404, 409 |

### 响应 Schema

```python
class PrivateChatResponse(BaseModel):
    agent_name: str
    status: str  # "in_private_chat" 或 "idle"
    main_session_id: str | None = None
```

### 消息拦截规则

在 `send_message_to_agent` 中实现拦截逻辑：

1. 检查目标 Agent 是否处于 `in_private_chat` 状态
2. 如果是，且发送方不是正在私聊的用户，则：
   - 不投递消息给目标 Agent
   - 创建一条 NOTIFICATION 类型的自动回复发送给发送方
   - 自动回复内容："{agent_name} 正在单聊中，请稍后再试"
3. 如果发送方是正在私聊的用户，则正常投递

### 操作限制规则

| 操作 | in_private_chat 状态 | 错误信息 |
|------|---------------------|----------|
| `stop_member` | 禁止 | "Agent {name} 正在单聊中，无法停止" |
| `reset_member` | 禁止 | "Agent {name} 正在单聊中，无法重置" |
| `compress_agent_context` | 跳过 | 日志警告，不报错 |
| `compress_all_agents` | 跳过 | 日志警告，不报错 |

### Manager 限制

- `start_private_chat` 时检查目标 Agent 是否为 Manager
- 如果是 Manager，抛出 StateError："Manager 不允许进入私聊"

## Frontend Module

### 目录结构

```
frontend/src/features/private-chat/
├── hooks/
│   └── usePrivateChat.ts    # 业务逻辑 hook
├── store/
│   └── privateChatStore.ts  # 状态管理
└── index.ts                 # 统一导出
```

### Store 接口

```typescript
interface PrivateChatState {
  activeGroupChatId: string | null;
  activeAgentName: string | null;
  lastActivityTime: number | null;

  startPrivateChat: (groupChatId: string, agentName: string) => void;
  stopPrivateChat: () => void;
  updateActivity: () => void;
}
```

### Hook 接口

```typescript
function usePrivateChat(): {
  isPrivateChat: boolean;
  activeGroupChatId: string | null;
  activeAgentName: string | null;
  startPrivateChat: (groupChatId: string, agentName: string) => void;
  stopPrivateChat: () => Promise<boolean>;
  startTimer: (onTimeout: () => void) => void;
  resetTimer: (onTimeout: () => void) => void;
  clearTimer: () => void;
  handleTimeout: () => Promise<void>;
}
```

## Design Rationale

### 为什么复用群聊会话而不是创建新会话？

私聊的目的是在群聊上下文中与单个 Agent 对话，而不是创建一个全新的对话。复用群聊会话可以：
- 保持上下文连续性
- 避免会话数量膨胀
- 简化实现

### 为什么限制 3 分钟超时？

防止用户忘记退出私聊，导致 Agent 长时间处于 `in_private_chat` 状态，无法被其他操作（停止、重置、压缩）使用。

### 为什么 Manager 禁止私聊？

Manager 是群聊的编排者，负责分配任务和协调 Agent。如果 Manager 进入私聊，会影响群聊的正常运行。
