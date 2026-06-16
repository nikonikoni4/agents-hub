---
version: 1.2
created_at: 2026-06-03
updated_at: 2026-06-16
last_updated: 修正端点路径与广播 API 路径，精简 realtime 重叠内容，补充心跳和边界场景
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

## Overview

WebSocket 后端模块为 Agent 与前端之间提供实时消息推送能力。当 Agent 产生新消息时，通过 WebSocket 向前端推送刷新信号，前端收到信号后主动拉取最新数据。

当前实现将实时连接管理和广播能力归属到 `realtime` 边界（详见 `realtime` spec）。API 侧只负责暴露 WebSocket endpoint 与 HTTP broadcast route；MCP 等非 API 入口可以直接依赖 realtime 广播刷新信号，避免依赖 API 内部模块。

**技术选择**：
- 技术栈：FastAPI 原生 WebSocket
- 房间模式：多房间（每个 group_chat_id 一个房间）
- 推送内容：刷新信号（通知前端有新消息，前端调用 API 拉取最新列表）
- 认证机制：无认证（MVP 阶段，仅本地开发测试）
- 断线重连：前端负责，后端不感知

## Scope

**当前阶段（MVP）**：
- 暴露 WebSocket endpoint 供前端连接
- 暴露 HTTP broadcast route 供 API 调用方触发刷新信号
- 连接管理、房间模型、广播机制由 realtime 模块提供（详见 `realtime` spec）

**不在范围内**：
- 认证与授权机制
- 消息确认与离线补发
- 与 core 层的自动集成
- 直接推送完整 message payload

## Core Behavior

### 连接生命周期

1. 前端发起 WebSocket 连接到 `/api/v1/ws/group_chat/{group_chat_id}`
2. 后端接受连接，将其加入 realtime 对应房间（房间模型详见 `realtime` spec）
3. 连接保持活跃，服务端定期发送心跳
4. 连接断开时（主动关闭或网络异常），从房间移除

### 心跳机制（ping-pong）

- 服务端每 30 秒向客户端发送 `{"type": "ping"}` JSON 消息
- 发送后等待 10 秒超时，若超时则主动断开连接
- 客户端无需回复 pong，服务端仅以发送是否超时作为连接存活判断

### 连接错误处理

- `WebSocketError`：发送错误消息到客户端，**不关闭连接**
- 通用 `Exception`：转换为 `WebSocketError` 发送错误消息，**不关闭连接**
- `WebSocketDisconnect`：触发断开清理（从房间移除连接）

以上均在 `finally` 块中调用 `manager.disconnect` 确保清理。

### 边界场景

- **group_chat_id 格式校验**：endpoint 接受任意字符串，不做 UUID 等格式校验；不存在的 group_chat_id 会创建空房间
- **同一客户端重复连接**：允许同一客户端对同一 group_chat_id 建立多个连接（多 Tab 场景），每个连接独立管理
- **服务端重启后重连**：连接状态仅存于内存，重启后所有连接丢失，前端需自行重连
- **连接数上限**：当前无连接数上限，未来可扩展

### 刷新信号流

```
Agent/MCP/API 入口产生群聊变更
  → 调用 realtime 广播 refresh signal
  → realtime 广播到房间内所有连接
  → 前端收到刷新信号
  → 前端调用 GET /api/v1/group_chats/{group_chat_id}/messages 拉取最新消息
```

## Technical Contract

### WebSocket 端点

| 项目 | 说明 |
|------|------|
| 路径 | `/api/v1/ws/group_chat/{group_chat_id}` |
| 协议 | WebSocket (ws://) |
| 路径参数 | `group_chat_id` - 群聊 ID |
| 连接成功 | 返回 101 状态码，升级为 WebSocket 协议 |

### 广播 API

| 项目 | 说明 |
|------|------|
| 方法 | POST |
| 路径 | `/api/v1/ws/broadcast/{group_chat_id}` |
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

## Interaction / UX Notes

- 前端收到刷新信号后，应调用对应的 REST API 拉取最新数据
- 前端负责断线重连，后端不感知重连过程
- MVP 阶段无认证，任何客户端可连接任何房间

## Acceptance Notes

1. 前端能通过 `/api/v1/ws/group_chat/{group_chat_id}` 建立 WebSocket 连接并收到刷新信号
2. 广播 API 路径 `/api/v1/ws/broadcast/{group_chat_id}` 可正常触发刷新信号
3. 服务端每 30 秒发送 ping，超时 10 秒后断开连接
4. `WebSocketError` 和通用 `Exception` 发送错误消息后不关闭连接
5. 连接断开后房间状态正确清理（由 realtime 模块保证）

## Out of Spec

以下内容不在本 spec 中长期维护：

1. 连接管理、房间模型、广播机制的内部实现（见 `realtime` spec）
2. 认证与授权机制（未来阶段）
3. 消息确认与离线补发机制（未来阶段）
4. 与 core 层的自动集成方式（未来阶段）
5. 前端 WebSocket 客户端实现细节
6. 具体的重连策略参数（指数退避倍数、最大重试次数等）
