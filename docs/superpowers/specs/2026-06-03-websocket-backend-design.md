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
- **推送内容**：刷新信号
- **认证机制**：无认证（MVP 阶段）
- **断线重连**：自动重连（前端负责）

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

**接口设计**：
```python
class WebSocketManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 房间映射：group_chat_id -> [WebSocket, ...]
        self.rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, group_chat_id: str):
        """接受连接并加入房间"""
        await websocket.accept()
        self.rooms.setdefault(group_chat_id, []).append(websocket)

    async def disconnect(self, websocket: WebSocket, group_chat_id: str):
        """断开连接并从房间移除"""
        self.rooms[group_chat_id].remove(websocket)
        if not self.rooms[group_chat_id]:
            del self.rooms[group_chat_id]

    async def broadcast(self, group_chat_id: str, message: dict):
        """向房间内所有连接广播消息"""
        failed_connections = []
        for connection in self.rooms.get(group_chat_id, []):
            try:
                await connection.send_json(message)
            except Exception:
                failed_connections.append(connection)

        # 清理失败的连接
        for conn in failed_connections:
            self.rooms[group_chat_id].remove(conn)
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

### 3. API 接口

**职责**：供 Agent 调用，触发广播

**位置**：`agents_hub/api/routes/websocket.py`

**接口设计**：
```python
@router.post("/api/v1/ws/broadcast/{group_chat_id}")
async def broadcast_message(
    group_chat_id: str,
    message: dict,
    manager: WebSocketManager = Depends(get_ws_manager)
):
    """广播消息到指定房间"""
    await manager.broadcast(group_chat_id, message)
    return {"status": "ok"}
```

---

## 数据流设计

### 完整消息流

**场景 1：Agent 产生消息，推送前端**

```
1. Agent 执行完成，产生消息
   ↓
2. 调用 API: POST /api/v1/ws/broadcast/{group_chat_id}
   请求体: {"type": "new_message", "group_chat_id": "abc123"}
   ↓
3. API 调用 WebSocketManager.broadcast()
   ↓
4. 遍历 rooms["abc123"] 中的所有连接
   ↓
5. 向每个连接发送 JSON: {"type": "new_message"}
   ↓
6. 前端收到消息，调用 GET /api/v1/messages/{group_chat_id} 拉取最新列表
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

**推送消息（后端 → 前端）**：
```json
{
    "type": "new_message",
    "group_chat_id": "abc123",
    "timestamp": "2026-06-03T10:30:00Z"
}
```

**错误消息（后端 → 前端）**：
```json
{
    "type": "error",
    "error_code": "ROOM_NOT_FOUND",
    "message": "房间不存在",
    "details": {}
}
```

**前端响应（可选）**：
```json
{
    "type": "heartbeat"
}
```

---

## 错误处理

### 异常体系

**WebSocket 专用异常类**：
```python
# agents_hub/api/websocket/exceptions.py

from agents_hub.exceptions import AgentsHubError

class WebSocketError(AgentsHubError):
    """WebSocket 错误基类"""
    pass

class ConnectionError(WebSocketError):
    """连接错误"""
    pass

class RoomNotFoundError(WebSocketError):
    """房间不存在错误"""
    pass

class BroadcastError(WebSocketError):
    """广播错误"""
    pass
```

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

**重连策略**：
```javascript
// 前端伪代码
class WebSocketClient {
    constructor() {
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // 初始延迟 1 秒
    }

    connect(groupChatId) {
        this.ws = new WebSocket(`ws://localhost:8000/ws/group_chat/${groupChatId}`);

        this.ws.onclose = () => {
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                setTimeout(() => {
                    this.reconnectAttempts++;
                    this.reconnectDelay *= 2; // 指数退避
                    this.connect(groupChatId);
                }, this.reconnectDelay);
            }
        };

        this.ws.onopen = () => {
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
        };
    }
}
```

**重连流程**：
```
连接断开
    ↓
等待 1 秒
    ↓
尝试重连
    ↓
成功？ → 重置计数器
    ↓ 失败
等待 2 秒
    ↓
尝试重连
    ↓
... 最多重试 5 次
    ↓
放弃，提示用户刷新页面
```

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

tests/
└── test_websocket.py   # WebSocket 测试
```

### 修改文件

```
agents_hub/api/app.py   # 注册 WebSocket 路由
```

---

## 后续演进

### 阶段 1：MVP（当前）
- 实现 WebSocket 后端
- 推送刷新信号
- 测试验证

### 阶段 2：功能增强
- 推送完整消息内容
- 消息确认机制
- 离线消息补发

### 阶段 3：多端支持
- 多端同步
- 设备配对
- 权限控制
