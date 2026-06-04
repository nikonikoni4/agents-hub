---
version: 1.0
created_at: 2026-06-04
updated_at: 2026-06-04
last_updated: 创建实时通信边界设计，明确 API 与 MCP 共同依赖 realtime 模块
abstract: 设计 WebSocket 从 API 内部模块迁移为独立 realtime 能力，当前只广播 refresh 信号，同时为未来直接推送消息 payload 预留事件边界。
---

# Realtime Boundary Design

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建设计初稿 |

## 背景

当前 WebSocket 连接管理位于 `agents_hub/api/websocket/`。这在只由 API 路由调用时可以工作，但 MCP Server 的 `speak_in_group_chat` 和 `finish_agent_call` 在写入群聊消息后也需要通知前端刷新。如果 MCP 直接依赖 API WebSocket 模块，会形成 `mcp -> api` 的依赖方向，使 API、MCP、WebSocket 三者的职责边界混在一起，并增加循环依赖风险。

本设计的核心目标是把实时通知从 API transport 中抽离出来，使 API 和 MCP 都依赖一个独立的 realtime 模块。

## 设计目标

- WebSocket 连接管理不再属于 API 内部实现，而是独立的 realtime 能力。
- API 仍负责 WebSocket endpoint、HTTP route 和 FastAPI 依赖注入。
- MCP 工具在写入群聊历史后可以触发前端刷新，但不依赖 API 模块。
- 当前只发送 refresh signal，前端继续通过 REST API 拉取消息。
- 模块边界为未来直接推送消息 payload 预留位置，但本轮不实现 payload 推送。

## 非目标

- 不实现跨进程或分布式广播。
- 不实现离线补发、ack、消息确认或重放。
- 不改变前端当前的“收到 refresh 后拉取消息”模式。
- 不让 core 层直接依赖 realtime。
- 不重构 MCP tool 的业务语义。

## 推荐方案

新增 `agents_hub/realtime/` 作为实时通信边界：

- `manager`：管理 WebSocket 连接、房间和广播。
- `dependencies` 或 registry：提供进程内共享的 realtime manager。
- `events`：定义稳定事件类型，至少包含 refresh；未来可扩展 message payload。
- `exceptions`：承载 realtime/WebSocket 广播相关异常。

依赖方向：

```text
api ───────┐
           ├──> realtime
mcp ───────┘

realtime 不依赖 api / mcp / core
core 不依赖 realtime
```

## 行为设计

### 当前行为：refresh signal

1. MCP tool 完成业务写入：
   - `speak_in_group_chat` 写入公开群聊消息。
   - `finish_agent_call` 更新 AgentCall 并写入最终群聊回复。
2. MCP 调用 realtime 广播群聊刷新信号。
3. WebSocket 房间内所有连接收到 refresh 事件。
4. 前端收到 refresh 后调用群聊消息 REST API 拉取最新消息。

### 未来行为：message payload

realtime 事件模型允许未来新增“直接推送新增消息 payload”的事件，但当前不启用。未来是否启用由前端数据一致性、消息体 schema 稳定性和离线补偿策略共同决定。

## 方案对比

### 方案 A：独立 realtime 模块（采纳）

API endpoint 和 MCP tool 都依赖 realtime。realtime 只管理实时连接与广播，不承载群聊业务状态。

优势：

- 立即消除 MCP 依赖 API 的风险。
- 改动范围小，能复用现有 WebSocketManager 行为。
- 依赖方向清晰，符合 API 是 transport、MCP 是 tool ingress、realtime 是通知服务的边界。

劣势：

- 仍是进程内 singleton，不支持多进程部署。
- MCP tool 仍需要显式调用广播，业务写入与通知之间存在调用约定。

### 方案 B：事件总线

MCP 或业务层发布领域事件，WebSocket 作为订阅者广播。

优势：

- 更适合未来多类事件和多订阅者。
- 业务写入与通知分发解耦更彻底。

劣势：

- 当前项目没有事件总线，MVP 阶段实现成本偏高。
- 会引入事件生命周期、订阅顺序和错误处理等新问题。

### 方案 C：core 写入时自动广播

在 core 的消息写入逻辑中直接触发 WebSocket 通知。

优势：

- 调用方最省心，不容易漏发 refresh。

劣势：

- core 会依赖 realtime 或 API，破坏现有 core 分层。
- 群聊持久化行为和前端实时通知耦合，后续测试和复用成本更高。

## 推荐理由

选择方案 A。当前真正的问题是 API/MCP/WebSocket 的模块边界，而不是缺少完整事件总线。独立 realtime 模块可以用最小改动解决依赖方向问题，同时保留未来升级到 payload 推送或事件总线的空间。

这个选择也符合当前项目偏好的 SSOT、SRP 和最小改动原则：群聊消息仍由 core/context 持久化，realtime 只负责通知，API 和 MCP 只是不同入口。

## 测试关注点

- API WebSocket endpoint 仍能连接指定 group chat 房间。
- HTTP broadcast route 仍能广播 refresh。
- MCP 的 `speak_in_group_chat` 写入消息后触发 refresh。
- MCP 的 `finish_agent_call` 写入最终回复后触发 refresh。
- realtime 模块不 import API 或 MCP。
- core 模块不 import realtime。

## 待确认风险

- 当前广播是进程内状态，若未来 FastAPI 使用多 worker，需要升级为跨进程 pub/sub。
- 如果未来直接推送 message payload，需要确认 payload schema、前端去重和离线补偿策略。
