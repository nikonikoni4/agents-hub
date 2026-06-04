---
version: 1.1
created_at: 2026-06-03
updated_at: 2026-06-04
last_updated: 对齐 realtime 边界迁移，明确 API 负责 endpoint，realtime 负责连接管理和广播
abstract: WebSocket 后端模块的正式规格，定义 API endpoint、realtime 连接管理、房间模型、广播机制和异常体系
id: websocket-backend
title: WebSocket 后端模块
status: draft
module: api/websocket, realtime
sourc_spec: docs/superpowers/specs/2026-06-03-websocket-backend-design.md
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

## Overview

WebSocket 后端模块为 Agent 与前端之间提供实时消息推送能力。当 Agent 产生新消息时，通过 WebSocket 向前端推送刷新信号，前端收到信号后主动拉取最新数据。

当前实现将实时连接管理和广播能力归属到 `realtime` 边界。API 侧只负责暴露 WebSocket endpoint 与 HTTP broadcast route；MCP 等非 API 入口可以直接依赖 realtime 广播刷新信号，避免依赖 API 内部模块。

**技术选择**：
- 技术栈：FastAPI 原生 WebSocket
- 房间模式：多房间（每个 group_chat_id 一个房间）
- 推送内容：刷新信号（通知前端有新消息，前端调用 API 拉取最新列表）
- 认证机制：无认证（MVP 阶段，仅本地开发测试）
- 断线重连：前端负责，后端不感知

## Scope

**当前阶段（MVP）**：
- 实现 WebSocket 连接管理和房间机制
- 实现刷新信号广播
- API route 和 MCP tool 均可触发刷新信号
- 不让 core 层直接依赖 realtime

**不在范围内**：
- 认证与授权机制
- 消息确认与离线补发
- 与 core 层的自动集成
- 直接推送完整 message payload

## Core Behavior

### 连接生命周期

1. 前端发起 WebSocket 连接到 `/ws/group_chat/{group_chat_id}`
2. 后端接受连接，将其加入对应房间
3. 连接保持活跃，等待前端消息（如心跳）
4. 连接断开时（主动关闭或网络异常），从房间移除
5. 房间内无连接时，房间自动销毁

### 房间模型

- 房间以 `group_chat_id` 为键，每个房间持有多个 WebSocket 连接
- 支持同一 group_chat_id 的多客户端连接（多设备场景）
- 房间按需创建（首次连接时），自动销毁（最后连接断开时）
- 连接状态仅存于内存，服务器重启后丢失

### 广播机制

- API 或 MCP 等入口通过 realtime 广播能力，触发向指定房间推送消息
- 广播遍历房间内所有连接，逐个发送 JSON 消息
- 单个连接发送失败不影响其他连接，失败连接在广播后自动清理
- 空房间广播时静默返回，不报错

### 刷新信号流

```
Agent/MCP/API 入口产生群聊变更
  → 写入群聊状态或验证 HTTP 请求体
  → 调用 realtime 广播 refresh signal
  → realtime 广播到房间内所有连接
  → 前端收到刷新信号
  → 前端调用 GET /api/v1/group_chats/{group_chat_id}/messages 拉取最新消息
```

## Technical Contract

### WebSocket 端点

| 项目 | 说明 |
|------|------|
| 路径 | `/ws/group_chat/{group_chat_id}` |
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

WebSocket 异常继承项目通用异常分类体系，采用双重继承：

| 异常类 | 继承自 | 场景 |
|--------|--------|------|
| WebSocketError | AgentsHubError | WebSocket 模块基类 |
| WebSocketConnectionError | WebSocketError, ExternalServiceError | 网络层连接失败 |
| WebSocketRoomNotFoundError | WebSocketError, ResourceNotFoundError | 房间不存在 |
| WebSocketBroadcastError | WebSocketError, ExternalServiceError | 广播发送失败 |
| WebSocketValidationError | WebSocketError, ValidationError | 消息验证错误 |

## Interaction / UX Notes

- 前端收到刷新信号后，应调用对应的 REST API 拉取最新数据
- 前端负责断线重连，后端不感知重连过程
- MVP 阶段无认证，任何客户端可连接任何房间

## Acceptance Notes

1. 前端能成功建立 WebSocket 连接并收到刷新信号
2. 多房间连接互相隔离，广播不跨房间
3. 连接断开后房间状态正确清理
4. 广播失败的连接被自动移除，不影响其他连接
5. 空房间广播不报错

## Out of Spec

以下内容不在本 spec 中长期维护：

1. 认证与授权机制（未来阶段）
2. 消息确认与离线补发机制（未来阶段）
3. 与 core 层的自动集成方式（未来阶段）
4. 前端 WebSocket 客户端实现细节
5. 具体的重连策略参数（指数退避倍数、最大重试次数等）
