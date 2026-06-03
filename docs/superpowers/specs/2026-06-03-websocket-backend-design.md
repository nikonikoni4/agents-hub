# WebSocket 后端设计规格

## 设计概述

### 目标
实现 WebSocket 后端功能，当 Agent 需要发送信息给前端时调用，支持实时消息推送。

### 范围
- 当前阶段：只实现 WebSocket 后端，不写入 core 层
- 目标：测试能够正常推送刷新信号
- 未来演进：支持推送完整消息内容

### 技术选择
- **技术栈**：FastAPI 原生 WebSocket
- **房间模式**：多房间（每个 group_chat_id 一个房间）
- **推送内容**：刷新信号（通知前端有新消息，前端调用 API 拉取最新列表）
- **认证机制**：无认证（MVP 阶段，仅本地开发测试）
- **断线重连**：自动重连（前端负责，后端不感知）

### 刷新信号定义
刷新信号是一种通知机制，告知前端有新数据可拉取：
- **信号格式**：固定结构 `{"type": "refresh", "group_chat_id": "...", "timestamp": "..."}`
- **前端响应**：收到信号后调用 `GET /api/v1/group_chats/{group_chat_id}/messages` 拉取最新消息
- **信号类型**：MVP 阶段只有 `refresh` 类型，未来可扩展 `status_change`、`agent_typing` 等

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                   │
│  ┌─────────────────────────────────────────────────────┐│
│  │              WebSocket Manager                      ││
│  │  ┌───────────────────────────────────────────────┐ ││
│  │  │  Connection Pool (rooms: dict[str, list[WS]])  │ ││
│  │  └───────────────────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────┘│
│                         ↑                               │
│                         │                               │
│  ┌─────────────────────────────────────────────────────┐│
│  │              WebSocket Endpoint                     ││
│  │           /ws/group_chat/{group_chat_id}            ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
                         ↑
                         │
    ┌────────────────────┴────────────────────┐
    │                                         │
┌───┴───┐                               ┌─────┴─────┐
│ Agent │                               │  Frontend  │
│  产生  │                               │    监听    │
│  消息  │                               │   消息     │
└───────┘                               └───────────┘
```

### 核心组件

1. **WebSocketManager**：管理连接池和房间，提供广播方法
2. **WebSocket Endpoint**：处理连接、断开、消息接收
3. **API 接口**：供 Agent 调用，触发广播

---

## 组件设计

### 1. WebSocketManager

**职责**：管理 WebSocket 连接池，提供房间管理接口

**位置**：`agents_hub/api/websocket/manager.py`

**设计要点**：
- 全局单例，通过依赖注入共享
- 房间按需创建（有连接时创建，无连接时销毁）
- 内存存储，服务器重启后丢失所有连接（MVP 阶段限制）

**接口设计**：
```python
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket 连接管理器（全局单例）"""

    def __init__(self):
        # 房间映射：group_chat_id -> [WebSocket, ...]
        self.rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, group_chat_id: str):
        """接受连接并加入房间"""
        await websocket.accept()
        self.rooms.setdefault(group_chat_id, []).append(websocket)
        logger.info(f"WebSocket connected to room {group_chat_id}, total connections: {len(self.rooms[group_chat_id])}")

    async def disconnect(self, websocket: WebSocket, group_chat_id: str):
        """断开连接并从房间移除"""
        if group_chat_id in self.rooms and websocket in self.rooms[group_chat_id]:
            self.rooms[group_chat_id].remove(websocket)
            logger.info(f"WebSocket disconnected from room {group_chat_id}, remaining: {len(self.rooms[group_chat_id])}")
            if not self.rooms[group_chat_id]:
                del self.rooms[group_chat_id]
                logger.info(f"Room {group_chat_id} removed (empty)")

    async def broadcast(self, group_chat_id: str, message: dict):
        """向房间内所有连接广播消息"""
        connections = self.rooms.get(group_chat_id, [])
        if not connections:
            logger.warning(f"Broadcast to empty room {group_chat_id}")
            return

        failed_connections = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to connection in room {group_chat_id}: {e}")
                failed_connections.append(connection)

        # 清理失败的连接
        for conn in failed_connections:
            self.rooms[group_chat_id].remove(conn)
```

### 2. 依赖注入

**位置**：`agents_hub/api/websocket/dependencies.py`

**设计要点**：
- `WebSocketManager` 作为全局单例
- 通过 FastAPI 的依赖注入系统共享

**接口设计**：
```python
from agents_hub.api.websocket.manager import WebSocketManager

# 全局单例
_ws_manager: WebSocketManager | None = None


def get_ws_manager() -> WebSocketManager:
    """获取 WebSocketManager 单例"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager
```

### 2. WebSocket Endpoint

**职责**：处理 WebSocket 连接生命周期

**位置**：`agents_hub/api/websocket/endpoint.py`

**接口设计**：
```python
@router.websocket("/ws/group_chat/{group_chat_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    group_chat_id: str,
    manager: WebSocketManager = Depends(get_ws_manager)
):
    """WebSocket 端点"""
    try:
        await manager.connect(websocket, group_chat_id)
        while True:
            # 保持连接，接收前端消息（如心跳）
            data = await websocket.receive_text()
            # 可选：处理前端消息
    except WebSocketDisconnect:
        await manager.disconnect(websocket, group_chat_id)
    except WebSocketError as e:
        await handle_websocket_error(websocket, e)
        await manager.disconnect(websocket, group_chat_id)
    except Exception as e:
        # 未知错误，转换为 WebSocketError
        ws_error = WebSocketError(
            message=str(e),
            error_code="UNKNOWN_ERROR",
            cause=e
        )
        await handle_websocket_error(websocket, ws_error)
        await manager.disconnect(websocket, group_chat_id)
```

### 3. Pydantic Schemas

**位置**：`agents_hub/api/schemas/websocket.py`

**接口设计**：
```python
from datetime import datetime
from pydantic import BaseModel, Field


class RefreshSignal(BaseModel):
    """刷新信号请求体"""
    type: str = Field(default="refresh", description="信号类型")
    group_chat_id: str = Field(..., description="群聊 ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="信号时间戳")


class BroadcastResponse(BaseModel):
    """广播 API 响应体"""
    status: str = Field(default="ok", description="状态")
    message: str = Field(default="Broadcast sent", description="描述")
```

### 4. API 接口

**职责**：供 Agent 调用，触发广播

**位置**：`agents_hub/api/routes/websocket.py`

**触发时机**：
- Agent 执行完成并产生新消息后，由 `GroupChatManager` 或 `MessageRouter` 调用
- 当前 MVP 阶段：手动调用 API 测试，不集成到 core 层

**接口设计**：
```python
from fastapi import APIRouter, Depends
from agents_hub.api.websocket.dependencies import get_ws_manager
from agents_hub.api.websocket.manager import WebSocketManager
from agents_hub.api.schemas.websocket import RefreshSignal, BroadcastResponse

router = APIRouter(tags=["websocket"])


@router.post(
    "/ws/broadcast/{group_chat_id}",
    response_model=BroadcastResponse,
    summary="广播刷新信号到指定房间",
)
async def broadcast_message(
    group_chat_id: str,
    signal: RefreshSignal,
    manager: WebSocketManager = Depends(get_ws_manager),
):
    """广播刷新信号到指定房间

    - **group_chat_id**: 群聊 ID
    - **signal**: 刷新信号内容

    前端收到信号后应调用 GET /api/v1/group_chats/{group_chat_id}/messages 拉取最新消息
    """
    # 确保 signal 中的 group_chat_id 与路径参数一致
    signal.group_chat_id = group_chat_id
    await manager.broadcast(group_chat_id, signal.model_dump())
    return BroadcastResponse()
```

---

## 数据流设计

### 完整消息流

**场景 1：Agent 产生消息，推送前端**

```
1. Agent 执行完成，产生消息，写入消息存储
   ↓
2. 调用 API: POST /api/v1/ws/broadcast/{group_chat_id}
   请求体: {"type": "refresh", "group_chat_id": "abc123", "timestamp": "..."}
   ↓
3. API 验证请求体（Pydantic schema）
   ↓
4. API 调用 WebSocketManager.broadcast()
   ↓
5. 遍历 rooms["abc123"] 中的所有连接
   ↓
6. 向每个连接发送 JSON: {"type": "refresh", "group_chat_id": "abc123", "timestamp": "..."}
   ↓
7. 前端收到刷新信号，调用 GET /api/v1/group_chats/abc123/messages 拉取最新列表
```

**场景 2：前端连接 WebSocket**

```
1. 前端发起连接: ws://localhost:8000/ws/group_chat/abc123
   ↓
2. WebSocket endpoint 接收连接
   ↓
3. 调用 WebSocketManager.connect()
   ↓
4. 将连接加入 rooms["abc123"]
   ↓
5. 保持连接，等待消息
```

**场景 3：前端断开连接**

```
1. 前端关闭页面或网络断开
   ↓
2. WebSocket endpoint 捕获 WebSocketDisconnect 异常
   ↓
3. 调用 WebSocketManager.disconnect()
   ↓
4. 从 rooms["abc123"] 移除连接
   ↓
5. 如果房间为空，删除房间
```

### 消息格式

**刷新信号（后端 → 前端）**：
```json
{
    "type": "refresh",
    "group_chat_id": "abc123",
    "timestamp": "2026-06-03T10:30:00Z"
}
```

**错误消息（后端 → 前端）**：
```json
{
    "type": "error",
    "error_code": "WebSocketRoomNotFoundError",
    "message": "房间不存在",
    "details": {}
}
```

---

## 错误处理

### 异常体系

WebSocket 异常继承现有 `agents_hub/exceptions.py` 分类体系，按"谁应该处理"分类：

```python
# agents_hub/api/websocket/exceptions.py

from agents_hub.exceptions import (
    AgentsHubError,
    ExternalServiceError,
    ResourceNotFoundError,
    StateError,
    ValidationError,
)


class WebSocketError(AgentsHubError):
    """WebSocket 错误基类"""
    pass


class WebSocketConnectionError(WebSocketError, ExternalServiceError):
    """WebSocket 连接错误（网络层问题）"""
    pass


class WebSocketRoomNotFoundError(WebSocketError, ResourceNotFoundError):
    """房间不存在错误"""
    pass


class WebSocketBroadcastError(WebSocketError, ExternalServiceError):
    """广播错误（发送失败）"""
    pass


class WebSocketValidationError(WebSocketError, ValidationError):
    """WebSocket 消息验证错误"""
    pass
```

**设计原则**：
- `WebSocketError` 作为 WebSocket 模块的基类
- 具体异常同时继承 `WebSocketError` 和对应的通用异常分类
- 这样既保持模块内聚，又与全局异常体系一致

### 错误处理机制

HTTP 和 WebSocket 错误处理方式不同：

| 类型 | 处理方式 | 返回格式 |
|------|---------|---------|
| HTTP | 返回 JSONResponse | `{"error_code": "...", "message": "..."}` |
| WebSocket | 通过连接发送错误消息 | `{"type": "error", "error_code": "...", "message": "..."}` |

**WebSocket 错误处理器**：
```python
async def handle_websocket_error(websocket: WebSocket, error: WebSocketError):
    """处理 WebSocket 错误，通过连接发送错误消息"""
    error_message = {
        "type": "error",
        "error_code": error.error_code,
        "message": error.message,
        "details": error.details,
    }
    await websocket.send_json(error_message)
```

### 断线重连机制（前端负责）

> **注意**：以下为前端实现参考，不属于后端设计范围。详见前端设计文档。

**重连策略**（前端参考）：
- 指数退避：1s → 2s → 4s → 8s → 16s
- 最大重试次数：5 次
- 重连成功后重置计数器

**后端行为**：
- 后端不感知前端重连
- 每次连接都是新连接，加入房间
- 无需补发离线消息（MVP 阶段）

---

## 测试方案

### 测试目标

验证 WebSocket 后端能够：
1. 接受前端连接
2. 管理多房间
3. 推送刷新信号
4. 处理断线和重连

### 测试用例

| 测试项 | 测试步骤 | 预期结果 |
|--------|---------|---------|
| 连接测试 | 建立 WebSocket 连接 | 连接成功，返回 101 状态码 |
| 多房间测试 | 建立两个不同房间的连接 | 各自独立，互不影响 |
| 广播测试 | 建立连接后调用广播 API | 连接收到广播消息 |
| 断线测试 | 关闭连接后重新连接 | 自动重连成功 |
| 错误测试 | 发送无效 group_chat_id | 返回错误消息 |

### 测试脚本

**Python 测试脚本**：
```python
# tests/test_websocket.py
import asyncio
import websockets

async def test_websocket_connection():
    """测试 WebSocket 连接"""
    uri = "ws://localhost:8000/ws/group_chat/test123"
    async with websockets.connect(uri) as websocket:
        # 连接成功
        print("Connected")

        # 接收消息（如果有）
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
            print(f"Received: {message}")
        except asyncio.TimeoutError:
            print("No message received (expected)")

async def test_broadcast():
    """测试广播功能"""
    import aiohttp

    # 先建立 WebSocket 连接
    uri = "ws://localhost:8000/ws/group_chat/test123"
    async with websockets.connect(uri) as websocket:
        # 调用广播 API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/api/v1/ws/broadcast/test123",
                json={"type": "new_message"}
            ) as resp:
                print(f"Broadcast API status: {resp.status}")

        # 接收广播消息
        message = await websocket.recv()
        print(f"Received broadcast: {message}")
```

### 测试环境

**启动后端**：
```bash
# 启动 FastAPI 应用
uvicorn agents_hub.api.app:app --reload --port 8000
```

**运行测试**：
```bash
# 运行 WebSocket 测试
pytest tests/test_websocket.py -v
```

---

## 文件结构

### 新增文件

```
agents_hub/api/websocket/
├── __init__.py
├── manager.py          # WebSocketManager 实现
├── endpoint.py         # WebSocket 端点
├── exceptions.py       # WebSocket 异常类
└── dependencies.py     # 依赖注入（get_ws_manager）

agents_hub/api/routes/
└── websocket.py        # WebSocket API 路由

agents_hub/api/schemas/
└── websocket.py        # WebSocket Pydantic schemas

tests/
└── test_websocket.py   # WebSocket 测试
```

### 修改文件

```
agents_hub/api/app.py           # 注册 WebSocket 路由
agents_hub/api/routes/__init__.py  # 导出 websocket_router
```

---

## 与现有架构集成

### 路由注册

在 `agents_hub/api/app.py` 中注册 WebSocket 路由：

```python
from agents_hub.api.routes import websocket_router

app.include_router(websocket_router, prefix="/api/v1")
```

在 `agents_hub/api/routes/__init__.py` 中导出：

```python
from .websocket import router as websocket_router

__all__ = ["websocket_router", ...]
```

### 与 GroupChat 生命周期的关系

- **房间创建**：前端连接时自动创建，无需与 GroupChat 同步
- **房间销毁**：最后一个连接断开时自动销毁
- **GroupChat 删除**：不影响 WebSocket 房间（房间会因无连接自然销毁）
- **设计原则**：WebSocket 房间是前端连接的抽象，与 GroupChat 生命周期解耦

### 与 core 层的关系（未来集成）

当前 MVP 阶段不集成到 core 层，未来集成点：
- `MessageRouter.send_message()` 完成后调用广播 API
- `GroupChatManager` 管理群聊生命周期时通知 WebSocket

### 日志规范

使用 Python 标准 `logging` 模块：
- 连接建立：`logger.info`
- 连接断开：`logger.info`
- 广播失败：`logger.error`
- 房间创建/销毁：`logger.info`

---

## 后续演进

### 阶段 1：MVP（当前）
- 实现 WebSocket 后端
- 推送刷新信号
- 测试验证

### 阶段 2：功能增强
- **推送完整消息内容**：扩展 `RefreshSignal` 为 `WebSocketMessage`，支持 `refresh`、`new_message`、`status_change` 等类型
- **消息确认机制**：前端收到消息后发送 ACK，后端确认送达
- **离线消息补发**：前端重连时携带 `last_message_id`，后端补发缺失消息
- **集成到 core 层**：在 `MessageRouter.send_message()` 完成后自动调用广播

### 阶段 3：多端支持
- **多端同步**：一个 group_chat_id 支持多个客户端连接
- **设备配对**：移动端通过 QR 码配对，获取桌面端 IP 和端口
- **权限控制**：基于 group_chat_id 的连接权限验证
