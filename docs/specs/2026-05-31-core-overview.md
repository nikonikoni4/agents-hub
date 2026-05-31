---
version: 1.0
created_at: 2026-05-31
updated_at: 2026-05-31
last_updated: 初稿
abstract: core 层的总体概览规格，描述分层架构、依赖方向、跨层协作模式和子 spec 索引
id: spec-core-overview
title: Core 层总体概览
status: draft
module: core
sourc_spec: null
related_plan: null
code_scope:
  - agents_hub/core/
contract_refs: []
---

# Core 层总体概览

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |

## Overview

core 是 agents-hub 的**核心业务逻辑层**，位于 MCP Server（上层）和 Agent Bridge（下层）之间。它负责多 Agent 协作的核心机制：消息路由、上下文管理、Agent 执行和群聊编排。

core 采用**严格的分层架构**，遵循单向依赖原则：上层依赖下层，下层不依赖上层。

## 分层结构

```
┌─────────────────────────────────────────────┐
│  orchestration/  (编排层)                    │  → 团队、群聊、MCP 入口
├─────────────────────────────────────────────┤
│  agent/  (Agent 层)                          │  → Agent 执行模型、角色
├─────────────────┬───────────────────────────┤
│  communication/  │  context/                 │  → 消息路由 / 会话管理
├─────────────────┴───────────────────────────┤
│  foundation/  (基础层)                       │  → 数据模型、消息、异常
└─────────────────────────────────────────────┘
```

### 各层职责

| 层 | 一句话职责 | 依赖 |
|----|----------|------|
| foundation | 公共语言：枚举、消息格式、渲染、异常 | 无 |
| communication | 消息投递和调用生命周期管理 | foundation |
| context | 会话状态、上下文压缩、持久化 | foundation |
| agent | Agent 消息循环和执行 | foundation + communication + context |
| orchestration | 群聊编排、团队管理、MCP 入口 | 所有下层 |

### 依赖规则

```
orchestration → agent → communication → foundation
                  ↓           ↓
              context ────────┘
```

**关键约束**：
- `communication/` 和 `context/` 是**同层**，互不依赖
- `agent/` 依赖 `communication/`，但不依赖 `context/`（通过 AgentContext 间接使用）
- `orchestration/` 是唯一可以同时依赖 `agent/` 和 `context/` 的层
- 所有层都可以依赖 `foundation/`

## 跨层协作流程

一次完整的 Agent 间消息交互涉及所有层：

```
1. MCP call_agent()                    [orchestration]
   → GroupChatManager 查找 GroupChat
   → 创建 AgentCall                    [communication]
   → MessageRouter.send_message()      [communication]

2. Agent.run() 消息循环                 [agent]
   → 从队列取出 AgentMessage
   → AgentContext.get_context()        [context - 增量加载]
   → render_for_llm()                  [foundation - 渲染]
   → agent_bridge.execute()            [外部 - LLM 调用]

3. 结果处理                             [agent]
   → agent_call_manager 更新状态       [communication]
   → group_chat_context.add_message()  [context - 持久化]
   → render_for_chat()                 [foundation - 渲染]
   → 如需回复：send_message_to_agent() [communication]
```

## 子 Spec 索引

| spec | 覆盖范围 | 路径 |
|------|---------|------|
| core-foundation | 基础层：枚举、消息格式、渲染契约、异常体系 | `docs/specs/2026-05-31-core-foundation.md` |
| core-communication | 通信层：消息路由、AgentCall 生命周期、清理策略 | `docs/specs/2026-05-31-core-communication.md` |
| core-context | 上下文层：会话管理、增量加载、压缩策略、持久化 | `docs/specs/2026-05-31-core-context.md` |
| core-agent-orchestration | Agent 层 + 编排层：执行模型、角色、群聊编排、MCP 入口 | `docs/specs/2026-05-31-core-agent-orchestration.md` |

## Out of Spec

- core 不涉及 MCP Server 的协议实现（属于 mcp 模块）
- core 不涉及 API Server 和 WebSocket（属于 api 模块）
- core 不涉及 Agent 平台 CLI 调用（属于 agent_bridge 模块）
- core 不涉及 Role 配置管理（属于 roles 模块）
- core 不涉及系统配置管理（属于 config 模块）
