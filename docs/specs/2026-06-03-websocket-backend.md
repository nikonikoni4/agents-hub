---
version: 2.0
created_at: 2026-06-03
updated_at: 2026-06-18
last_updated: 按照新 spec 规则重构，移除执行细节，添加 key_function 标签和 Design Rationale
abstract: WebSocket 后端模块的正式规格，定义 WebSocket endpoint、HTTP broadcast route、错误消息格式等 API 侧特有内容
id: websocket-backend
title: WebSocket 后端模块
status: draft
module: api/websocket, realtime
source_spec: docs/superpowers/specs/2026-06-03-websocket-backend-design.md
related_plan: docs/superpowers/plans/2026-06-03-websocket-backend-implementation.md
code_scope:
  - agents_hub/realtime/
  - agents_hub/api/websocket/
  - agents_hub/api/routes/websocket.py
  - agents_hub/api/schemas/websocket.py
contract_refs:
  - agents_hub/realtime/events.py
  - agents_hub/realtime/exceptions.py
  - agents_hub/api/schemas/websocket.py
  - agents_hub/api/websocket/exceptions.py
---

# WebSocket 后端模块

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |
| 1.1 | WebSocket 连接管理与广播能力迁移到 realtime 边界，API 保留 endpoint 和 HTTP route |
| 1.2 | 修正端点路径和广播 API 路径，精简 realtime 重叠内容，补充心跳机制和边界场景 |
| 2.0 | 按照新 spec 规则重构，移除执行细节，添加 key_function 标签和 Design Rationale |

## Overview

**业务问题**：Agent 与前端之间需要实时消息推送能力。当 Agent 产生新消息时，需要通知前端刷新数据，而不是让前端轮询。

**核心职责**：
- 暴露 WebSocket endpoint 供前端连接，接收刷新信号
- 暴露 HTTP broadcast route 供 API 调用方触发刷新信号
- 连接管理、房间模型、广播机制由 realtime 模块提供（详见 `realtime` spec）

**技术选择**：
- 技术栈：FastAPI 原生 WebSocket
- 房间模式：多房间（每个 group_chat_id 一个房间）
- 推送内容：刷新信号（通知前端有新消息，前端调用 API 拉取最新列表）
- 认证机制：无认证（MVP 阶段，仅本地开发测试）
- 断线重连：前端负责，后端不感知

## Scope

### 范围内

- WebSocket endpoint：前端连接入口
- HTTP broadcast route：触发刷新信号的 API
- 错误消息格式：WebSocket 错误的 JSON 结构
- 异常体系：API 侧的异常兼容性导出

### 范围外

- 连接管理、房间模型、广播机制的内部实现（见 `realtime` spec）
- 认证与授权机制（未来阶段）
- 消息确认与离线补发机制（未来阶段）
- 与 core 层的自动集成方式（未来阶段）
- 前端 WebSocket 客户端实现细节

## Technical Contract

### API 端点总览

<key_function last_update="2026-06-21T07:52:42+08:00">
- agents_hub/api/websocket/endpoint.py
  - endpoint.websocket_endpoint:34
- agents_hub/api/routes/websocket.py
  - websocket.broadcast_message:20
</key_function>

| 方法 | 路径 | 说明 | 路由处理函数 |
|------|------|------|-------------|
| WebSocket | `/api/v1/ws/group_chat/{group_chat_id}` | WebSocket 连接入口 | `websocket_endpoint` |
| POST | `/api/v1/ws/broadcast/{group_chat_id}` | 触发刷新信号广播 | `broadcast_message` |

**WebSocket 端点详情**：

| 项目 | 说明 |
|------|------|
| 路径参数 | `group_chat_id` - 群聊 ID（任意字符串，不做 UUID 格式校验） |
| 连接成功 | 返回 101 状态码，升级为 WebSocket 协议 |
| 心跳 | 服务端每 30 秒发送 `{"type": "ping"}`，超时 10 秒断开 |
| 多连接 | 允许同一客户端对同一 group_chat_id 建立多个连接（多 Tab 场景） |
| 重启影响 | 连接状态仅存于内存，重启后所有连接丢失，前端需自行重连 |

**广播 API 详情**：

| 项目 | 说明 |
|------|------|
| 路径参数 | `group_chat_id` - 群聊 ID |
| 请求体 | `RefreshSignal` schema |
| 响应体 | `BroadcastResponse` schema |

注意：请求体 `RefreshSignal` 中的 `group_chat_id` 字段会被路径参数覆盖，以路径参数为准。

### Schema 定义

**RefreshSignal**（请求体）：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| type | string | 否 | "refresh" | 信号类型 |
| group_chat_id | string | 是 | - | 群聊 ID |
| timestamp | datetime | 否 | 当前时间 | 信号时间戳 |

**BroadcastResponse**（响应体）：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| status | string | "ok" | 状态 |
| message | string | "Broadcast sent" | 描述 |

### 错误消息格式

WebSocket 错误通过连接发送 JSON：

| 字段 | 类型 | 说明 |
|------|------|------|
| type | string | 固定为 "error" |
| error_code | string | 错误码 |
| message | string | 错误描述 |
| details | object | 错误详情 |

### 认证状态

**当前（MVP）**：无认证，裸连。任何客户端可直接连接任意房间，无需 Token 或身份验证。

**未来演进**：需要实现基于 Token 的连接认证，在 WebSocket 握手阶段验证客户端身份和房间访问权限。

### 异常体系

异常的实际定义在 `realtime/exceptions.py`。`api/websocket/exceptions.py` 是兼容性导出层，将 realtime 异常重新导出供 API 模块使用。

异常继承结构详见 `realtime` spec。核心异常类：

| 异常类 | 场景 |
|--------|------|
| WebSocketError | WebSocket 模块基类 |
| WebSocketConnectionError | 网络层连接失败 |
| WebSocketRoomNotFoundError | 房间不存在 |
| WebSocketBroadcastError | 广播发送失败 |
| WebSocketValidationError | 消息验证错误 |

## Design Rationale

**为什么将连接管理和广播能力归属到 realtime 边界？**
- API 侧只负责暴露 endpoint 和 route，保持职责单一
- realtime 模块提供通用的实时能力，MCP 等非 API 入口可以直接依赖，避免依赖 API 内部模块
- 便于未来扩展其他实时协议（如 SSE、gRPC streaming）

**为什么推送刷新信号而不是完整消息？**
- 前端已有 REST API 获取消息列表，WebSocket 只需通知"有新数据"
- 避免 WebSocket 和 REST API 之间的数据一致性问题
- 前端可以按需拉取，支持分页、过滤等已有能力

**为什么允许同一客户端建立多个连接？**
- 支持多 Tab 场景，每个 Tab 独立接收刷新信号
- 每个连接独立管理，断开时不影响其他连接

**为什么连接状态仅存于内存？**
- MVP 阶段简化实现，避免引入外部存储依赖
- 重启后前端自动重连即可恢复，用户体验可接受
- 未来如需持久化，可引入 Redis 等外部存储

**已知限制**：
- 无连接数上限，高并发场景可能需要扩展
- 无认证机制，仅适用于本地开发测试
- 无消息确认与离线补发，断线期间的消息会丢失

## Interaction / UX Notes

- 前端收到刷新信号后，应调用对应的 REST API 拉取最新数据
- 前端负责断线重连，后端不感知重连过程
- MVP 阶段无认证，任何客户端可连接任何房间

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **realtime 模块**：[2026-06-06-realtime.md](2026-06-06-realtime.md) - 连接管理、房间模型、广播机制的内部实现
- **前端 WebSocket 客户端**：[2026-06-06-frontend-core.md](2026-06-06-frontend-core.md) - 前端连接、重连、消息处理实现
- **认证机制**：未来阶段实现，当前 MVP 不包含
- **消息确认与离线补发**：未来阶段实现，当前 MVP 不包含
