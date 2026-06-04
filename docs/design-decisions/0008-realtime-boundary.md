---
version: 1.0
created_at: 2026-06-04
updated_at: 2026-06-04
last_updated: 决定将 WebSocket 连接管理从 API 内部抽离为 realtime 模块
abstract: 为避免 MCP Server 依赖 API WebSocket 模块导致循环依赖和职责混乱，决定将实时广播能力抽离为独立 realtime 边界，API 与 MCP 共同依赖该边界。
status: decided
---

# Realtime 边界决策

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建文档初稿 |

## 问题界定

### 问题简述

当前 WebSocket 连接管理位于 API 文件夹中。随着 MCP Server 新增 `speak_in_group_chat` 和 `finish_agent_call`，MCP tool 在结束时需要通知前端群聊有新消息。如果 MCP 直接导入 API WebSocket 模块，就会出现 `mcp -> api` 的依赖方向。

这会让 API transport、MCP tool ingress 和实时通知服务混在一起。未来 API 路由、MCP Server、WebSocket manager 之间更容易形成循环依赖，也会让 WebSocket 这个本应独立的实时能力被误认为 API 的内部细节。

### 讨论范围

- WebSocket 连接管理和广播能力的模块归属。
- MCP tool 写入群聊消息后的前端刷新通知方式。
- API、MCP、realtime、core 之间的依赖方向。
- 当前 refresh signal 与未来 message payload 推送之间的边界。

### 非讨论范围

- 不讨论前端渲染方式重构。
- 不讨论 MCP tool 的业务语义重构。
- 不讨论跨进程 pub/sub 或分布式部署。
- 不讨论离线补发、ack 和消息确认机制。

### 模糊信息的明确定义

- `realtime`：进程内实时通知能力，当前承载 WebSocket 连接管理、房间广播和实时事件结构。
- `refresh signal`：只通知前端“群聊有变化”，不携带完整消息内容；前端收到后通过 REST API 拉取最新消息。
- `message payload`：未来可能直接通过 WebSocket 推送的新增消息内容；本次只预留边界，不实现。

### 问题深度

这是一个架构边界决策。它不仅决定文件移动位置，也决定 API、MCP、core 和实时通知服务之间谁可以依赖谁。

## 现状

现有 WebSocket 模块在 API 目录中，连接管理器由 API dependency 提供。WebSocket 后端 spec 当前定义的是 MVP 模式：Agent 产生消息后广播 refresh，前端再拉取最新消息。

新增显式群聊发言与 AgentCall 闭环后，MCP Server 的 `speak_in_group_chat` 和 `finish_agent_call` 成为新的消息写入入口。它们在写入群聊历史后，也需要触发同样的 refresh 通知。

不能忽略的风险是：如果 MCP 直接依赖 `agents_hub.api.websocket`，API 将不再只是前端通信入口，而变成 MCP 的运行时依赖。这个方向与模块职责不匹配。

## 可选方案

### 方案 A：抽离独立 realtime 模块

将 WebSocket 连接管理、房间广播和实时事件结构移动到独立 `realtime` 模块。API endpoint 依赖 realtime 管理连接，MCP tool 依赖 realtime 发送 refresh。

**优势**

- 消除 MCP 直接依赖 API 的风险。
- 保持 core 不依赖 realtime，维护现有 core 分层。
- 当前实现改动小，可复用已有 WebSocket manager 行为。
- 为未来直接推送 message payload 预留事件边界。

**劣势**

- 仍然是进程内 singleton，不适合多 worker 部署。
- MCP 写入消息后需要显式调用 refresh，存在调用约定。

### 方案 B：引入事件总线

业务入口发布领域事件，WebSocket 作为订阅者监听并广播。

**优势**

- 业务写入与通知分发解耦更彻底。
- 未来支持更多实时事件和订阅者时扩展性更好。

**劣势**

- 当前项目没有事件总线，引入成本高。
- 会新增事件生命周期、订阅顺序和错误处理复杂度。

### 方案 C：core 写入时自动广播

在群聊消息写入逻辑中直接触发实时广播。

**优势**

- 调用方不需要关心通知，较难漏发 refresh。

**劣势**

- core 会依赖 realtime 或 API，破坏现有分层。
- 持久化写入和前端通知耦合，降低 core 可复用性。

## 最终决策

选择 `方案 A：抽离独立 realtime 模块`。

当前只实现 refresh signal：前端收到通知后继续通过 REST API 拉取消息。模块和事件边界允许未来扩展 message payload 推送，但本次不启用。

## 决策原因

- 原因 1：MCP 不应该依赖 API。MCP 是 Agent tool ingress，API 是前端 transport，两者应该共同依赖更底层的 realtime 能力。
- 原因 2：core 不应该承担前端实时通知职责。core 负责群聊状态和持久化，realtime 负责投影通知，两者保持分离。
- 原因 3：事件总线当前过重。项目现阶段只需要在消息写入后广播 refresh，引入完整事件总线会超出当前问题范围。
- 原因 4：refresh 先行符合现有 WebSocket spec。前端继续拉取消息，避免提前稳定 message payload schema 和去重策略。

## 后续影响

- `agents_hub/api/websocket` 中的连接管理能力应迁移到 `agents_hub/realtime`。
- API WebSocket endpoint 保留在 API 侧，但只负责连接生命周期入口。
- MCP 的 `speak_in_group_chat` 和 `finish_agent_call` 在写入群聊消息后触发 realtime refresh。
- 测试需要覆盖 MCP 写入后 refresh 被广播，以及 realtime 不依赖 API/MCP。
- 如果未来启用多 worker 或分布式部署，需要将进程内 realtime 升级为 pub/sub。
