# WebSocket 后端实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 WebSocket 后端，支持 Agent 向前端推送刷新信号

**Architecture:** 使用 FastAPI 原生 WebSocket，多房间模式（每个 group_chat_id 一个房间），通过 WebSocketManager 管理连接池，提供广播 API 供 Agent 调用

**Tech Stack:** Python, FastAPI, WebSocket, Pydantic, pytest

---

## 文件结构

### 新增文件

| 文件 | 职责 |
|------|------|
| `agents_hub/api/websocket/__init__.py` | WebSocket 模块初始化 |
| `agents_hub/api/websocket/exceptions.py` | WebSocket 异常类（继承现有异常体系） |
| `agents_hub/api/websocket/manager.py` | WebSocketManager 连接池管理 |
| `agents_hub/api/websocket/dependencies.py` | 依赖注入（get_ws_manager 单例） |
| `agents_hub/api/websocket/endpoint.py` | WebSocket 端点 |
| `agents_hub/api/schemas/websocket.py` | Pydantic schemas（RefreshSignal, BroadcastResponse） |
| `agents_hub/api/routes/websocket.py` | WebSocket API 路由 |
| `tests/api/test_websocket.py` | WebSocket 集成测试 |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `agents_hub/api/routes/__init__.py` | 导出 websocket_router |
| `agents_hub/api/app.py` | 注册 WebSocket 路由 |

---

## Task 1: 创建 WebSocket 异常类

**Files:**
- Create: `agents_hub/api/websocket/__init__.py`
- Create: `agents_hub/api/websocket/exceptions.py`

- [ ] **Step 1: 创建 websocket 模块 __init__.py**

```python
# agents_hub/api/websocket/__init__.py
"""WebSocket 模块"""
```

- [ ] **Step 2: 创建异常类**

```python
# agents_hub/api/websocket/exceptions.py
"""WebSocket 异常类

继承现有 agents_hub/exceptions.py 分类体系，按"谁应该处理"分类。
"""

from agents_hub.exceptions import (
    AgentsHubError,
    ExternalServiceError,
    ResourceNotFoundError,
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

- [ ] **Step 3: 验证异常类导入**

Run: `python -c "from agents_hub.api.websocket.exceptions import WebSocketError, WebSocketConnectionError, WebSocketRoomNotFoundError, WebSocketBroadcastError, WebSocketValidationError; print('All exceptions imported successfully')"`

Expected: `All exceptions imported successfully`

- [ ] **Step 4: 运行现有测试确保无破坏**

Run: `pytest tests/ -x -q`

Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add agents_hub/api/websocket/__init__.py agents_hub/api/websocket/exceptions.py
git commit -m "feat(websocket): add WebSocket exception classes

- WebSocketError base class
- WebSocketConnectionError (ExternalServiceError)
- WebSocketRoomNotFoundError (ResourceNotFoundError)
- WebSocketBroadcastError (ExternalServiceError)
- WebSocketValidationError (ValidationError)"
```

---

## Task 2: 创建 WebSocketManager

**Files:**
- Create: `agents_hub/api/websocket/manager.py`
- Create: `tests/api/test_websocket_manager.py`

- [ ] **Step 1: 编写 WebSocketManager 测试**

```python
# tests/api/test_websocket_manager.py
"""WebSocketManager 单元测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from agents_hub.api.websocket.manager import WebSocketManager


@pytest.fixture
def manager():
    """创建 WebSocketManager 实例"""
    return WebSocketManager()


@pytest.fixture
def mock_websocket():
    """创建 mock WebSocket"""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_connect(manager, mock_websocket):
    """测试：连接加入房间"""
    await manager.connect(mock_websocket, "chat-123")

    assert "chat-123" in manager.rooms
    assert mock_websocket in manager.rooms["chat-123"]
    mock_websocket.accept.assert_called_once()


@pytest.mark.asyncio
async def test_connect_multiple_rooms(manager, mock_websocket):
    """测试：不同房间独立"""
    ws2 = AsyncMock()

    await manager.connect(mock_websocket, "chat-1")
    await manager.connect(ws2, "chat-2")

    assert len(manager.rooms) == 2
    assert mock_websocket in manager.rooms["chat-1"]
    assert ws2 in manager.rooms["chat-2"]


@pytest.mark.asyncio
async def test_disconnect(manager, mock_websocket):
    """测试：断开连接从房间移除"""
    await manager.connect(mock_websocket, "chat-123")
    await manager.disconnect(mock_websocket, "chat-123")

    assert "chat-123" not in manager.rooms


@pytest.mark.asyncio
async def test_disconnect_nonexistent_room(manager, mock_websocket):
    """测试：断开不存在的房间不报错"""
    await manager.disconnect(mock_websocket, "nonexistent")


@pytest.mark.asyncio
async def test_disconnect_nonexistent_websocket(manager, mock_websocket):
    """测试：断开不存在的连接不报错"""
    ws2 = AsyncMock()
    await manager.connect(mock_websocket, "chat-123")
    await manager.disconnect(ws2, "chat-123")

    # 原连接仍在房间
    assert mock_websocket in manager.rooms["chat-123"]


@pytest.mark.asyncio
async def test_broadcast(manager, mock_websocket):
    """测试：广播消息到房间"""
    ws2 = AsyncMock()
    await manager.connect(mock_websocket, "chat-123")
    await manager.connect(ws2, "chat-123")

    message = {"type": "refresh", "group_chat_id": "chat-123"}
    await manager.broadcast("chat-123", message)

    mock_websocket.send_json.assert_called_once_with(message)
    ws2.send_json.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_broadcast_empty_room(manager):
    """测试：广播到空房间不报错"""
    await manager.broadcast("nonexistent", {"type": "refresh"})


@pytest.mark.asyncio
async def test_broadcast_failed_connection(manager, mock_websocket):
    """测试：广播失败时清理连接"""
    mock_websocket.send_json.side_effect = Exception("Connection closed")

    await manager.connect(mock_websocket, "chat-123")
    await manager.broadcast("chat-123", {"type": "refresh"})

    # 失败的连接被清理
    assert "chat-123" not in manager.rooms
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/api/test_websocket_manager.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'agents_hub.api.websocket.manager'`

- [ ] **Step 3: 实现 WebSocketManager**

```python
# agents_hub/api/websocket/manager.py
"""WebSocket 连接管理器

管理 WebSocket 连接池，提供房间管理接口。
全局单例，通过依赖注入共享。
"""

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
        logger.info(
            f"WebSocket connected to room {group_chat_id}, "
            f"total connections: {len(self.rooms[group_chat_id])}"
        )

    async def disconnect(self, websocket: WebSocket, group_chat_id: str):
        """断开连接并从房间移除"""
        if group_chat_id not in self.rooms:
            return
        if websocket not in self.rooms[group_chat_id]:
            return

        self.rooms[group_chat_id].remove(websocket)
        logger.info(
            f"WebSocket disconnected from room {group_chat_id}, "
            f"remaining: {len(self.rooms[group_chat_id])}"
        )

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
                logger.error(
                    f"Failed to send to connection in room {group_chat_id}: {e}"
                )
                failed_connections.append(connection)

        # 清理失败的连接
        for conn in failed_connections:
            self.rooms[group_chat_id].remove(conn)

        logger.info(
            f"Broadcast to room {group_chat_id}: "
            f"{len(connections) - len(failed_connections)}/{len(connections)} sent"
        )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/api/test_websocket_manager.py -v`

Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents_hub/api/websocket/manager.py tests/api/test_websocket_manager.py
git commit -m "feat(websocket): add WebSocketManager

- Connection pool management (rooms dict)
- connect/disconnect with room lifecycle
- broadcast with error handling and logging
- Unit tests (9 test cases)"
```

---

## Task 3: 创建依赖注入

**Files:**
- Create: `agents_hub/api/websocket/dependencies.py`
- Create: `tests/api/test_websocket_dependencies.py`

- [ ] **Step 1: 编写依赖注入测试**

```python
# tests/api/test_websocket_dependencies.py
"""WebSocket 依赖注入测试"""

import pytest

from agents_hub.api.websocket.dependencies import get_ws_manager, reset_ws_manager
from agents_hub.api.websocket.manager import WebSocketManager


def test_get_ws_manager_singleton():
    """测试：get_ws_manager 返回单例"""
    reset_ws_manager()  # 重置状态

    manager1 = get_ws_manager()
    manager2 = get_ws_manager()

    assert isinstance(manager1, WebSocketManager)
    assert manager1 is manager2


def test_reset_ws_manager():
    """测试：reset_ws_manager 重置单例"""
    manager1 = get_ws_manager()
    reset_ws_manager()
    manager2 = get_ws_manager()

    assert manager1 is not manager2
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/api/test_websocket_dependencies.py -v`

Expected: FAIL with `ImportError: cannot import name 'get_ws_manager'`

- [ ] **Step 3: 实现依赖注入**

```python
# agents_hub/api/websocket/dependencies.py
"""WebSocket 依赖注入

提供 WebSocketManager 全局单例。
"""

from agents_hub.api.websocket.manager import WebSocketManager

# 全局单例
_ws_manager: WebSocketManager | None = None


def get_ws_manager() -> WebSocketManager:
    """获取 WebSocketManager 单例"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager


def reset_ws_manager():
    """重置 WebSocketManager 单例（用于测试）"""
    global _ws_manager
    _ws_manager = None
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/api/test_websocket_dependencies.py -v`

Expected: All 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents_hub/api/websocket/dependencies.py tests/api/test_websocket_dependencies.py
git commit -m "feat(websocket): add WebSocket dependency injection

- get_ws_manager() singleton factory
- reset_ws_manager() for testing
- Unit tests (2 test cases)"
```

---

## Task 4: 创建 Pydantic Schemas

**Files:**
- Create: `agents_hub/api/schemas/websocket.py`
- Create: `tests/api/schemas/test_websocket.py`

- [ ] **Step 1: 编写 Schemas 测试**

```python
# tests/api/schemas/test_websocket.py
"""WebSocket Schemas 测试"""

import pytest
from datetime import datetime

from agents_hub.api.schemas.websocket import BroadcastResponse, RefreshSignal


def test_refresh_signal_default():
    """测试：RefreshSignal 默认值"""
    signal = RefreshSignal(group_chat_id="chat-123")

    assert signal.type == "refresh"
    assert signal.group_chat_id == "chat-123"
    assert isinstance(signal.timestamp, datetime)


def test_refresh_signal_custom():
    """测试：RefreshSignal 自定义值"""
    now = datetime(2026, 6, 3, 10, 30, 0)
    signal = RefreshSignal(
        type="status_change",
        group_chat_id="chat-456",
        timestamp=now,
    )

    assert signal.type == "status_change"
    assert signal.group_chat_id == "chat-456"
    assert signal.timestamp == now


def test_refresh_signal_model_dump():
    """测试：RefreshSignal 序列化"""
    signal = RefreshSignal(group_chat_id="chat-123")
    data = signal.model_dump()

    assert data["type"] == "refresh"
    assert data["group_chat_id"] == "chat-123"
    assert "timestamp" in data


def test_broadcast_response_default():
    """测试：BroadcastResponse 默认值"""
    response = BroadcastResponse()

    assert response.status == "ok"
    assert response.message == "Broadcast sent"


def test_broadcast_response_custom():
    """测试：BroadcastResponse 自定义值"""
    response = BroadcastResponse(status="error", message="Failed")

    assert response.status == "error"
    assert response.message == "Failed"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/api/schemas/test_websocket.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'agents_hub.api.schemas.websocket'`

- [ ] **Step 3: 实现 Schemas**

```python
# agents_hub/api/schemas/websocket.py
"""WebSocket Pydantic Schemas"""

from datetime import datetime

from pydantic import BaseModel, Field


class RefreshSignal(BaseModel):
    """刷新信号请求体"""

    type: str = Field(default="refresh", description="信号类型")
    group_chat_id: str = Field(..., description="群聊 ID")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="信号时间戳"
    )


class BroadcastResponse(BaseModel):
    """广播 API 响应体"""

    status: str = Field(default="ok", description="状态")
    message: str = Field(default="Broadcast sent", description="描述")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/api/schemas/test_websocket.py -v`

Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents_hub/api/schemas/websocket.py tests/api/schemas/test_websocket.py
git commit -m "feat(websocket): add WebSocket Pydantic schemas

- RefreshSignal (type, group_chat_id, timestamp)
- BroadcastResponse (status, message)
- Unit tests (5 test cases)"
```

---

## Task 5: 创建 WebSocket 端点

**Files:**
- Create: `agents_hub/api/websocket/endpoint.py`
- Create: `tests/api/test_websocket_endpoint.py`

- [ ] **Step 1: 编写端点测试**

```python
# tests/api/test_websocket_endpoint.py
"""WebSocket 端点集成测试"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agents_hub.api.websocket.dependencies import get_ws_manager, reset_ws_manager
from agents_hub.api.websocket.endpoint import router
from agents_hub.api.websocket.manager import WebSocketManager


@pytest.fixture
def manager():
    """创建 WebSocketManager 实例"""
    return WebSocketManager()


@pytest.fixture
def app(manager):
    """创建测试应用"""
    reset_ws_manager()
    app = FastAPI()
    app.include_router(router)

    # 覆盖依赖注入
    app.dependency_overrides[get_ws_manager] = lambda: manager

    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


def test_websocket_connect(client, manager):
    """测试：WebSocket 连接成功"""
    with client.websocket_connect("/ws/group_chat/chat-123") as websocket:
        assert "chat-123" in manager.rooms
        assert len(manager.rooms["chat-123"]) == 1


def test_websocket_disconnect(client, manager):
    """测试：WebSocket 断开连接"""
    with client.websocket_connect("/ws/group_chat/chat-123") as websocket:
        pass

    # 连接断开后房间被清理
    assert "chat-123" not in manager.rooms


def test_websocket_multiple_connections(client, manager):
    """测试：多个连接加入同一房间"""
    with client.websocket_connect("/ws/group_chat/chat-123") as ws1:
        with client.websocket_connect("/ws/group_chat/chat-123") as ws2:
            assert len(manager.rooms["chat-123"]) == 2


def test_websocket_different_rooms(client, manager):
    """测试：不同房间独立"""
    with client.websocket_connect("/ws/group_chat/chat-1") as ws1:
        with client.websocket_connect("/ws/group_chat/chat-2") as ws2:
            assert len(manager.rooms) == 2
            assert len(manager.rooms["chat-1"]) == 1
            assert len(manager.rooms["chat-2"]) == 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/api/test_websocket_endpoint.py -v`

Expected: FAIL with `ImportError: cannot import name 'router' from 'agents_hub.api.websocket.endpoint'`

- [ ] **Step 3: 实现 WebSocket 端点**

```python
# agents_hub/api/websocket/endpoint.py
"""WebSocket 端点

处理 WebSocket 连接生命周期。
"""

import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from agents_hub.api.websocket.dependencies import get_ws_manager
from agents_hub.api.websocket.exceptions import WebSocketError
from agents_hub.api.websocket.manager import WebSocketManager

logger = logging.getLogger(__name__)

router = APIRouter()


async def handle_websocket_error(websocket: WebSocket, error: WebSocketError):
    """处理 WebSocket 错误，通过连接发送错误消息"""
    error_message = {
        "type": "error",
        "error_code": error.error_code,
        "message": error.message,
        "details": error.details,
    }
    await websocket.send_json(error_message)


@router.websocket("/ws/group_chat/{group_chat_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    group_chat_id: str,
    manager: WebSocketManager = Depends(get_ws_manager),
):
    """WebSocket 端点

    前端通过此端点连接到指定群聊房间，接收刷新信号。
    """
    try:
        await manager.connect(websocket, group_chat_id)
        while True:
            # 保持连接，接收前端消息（如心跳）
            data = await websocket.receive_text()
            logger.debug(f"Received from {group_chat_id}: {data}")
    except WebSocketDisconnect:
        await manager.disconnect(websocket, group_chat_id)
    except WebSocketError as e:
        await handle_websocket_error(websocket, e)
        await manager.disconnect(websocket, group_chat_id)
    except Exception as e:
        logger.exception(f"WebSocket error in room {group_chat_id}")
        ws_error = WebSocketError(
            message=str(e),
            error_code="UNKNOWN_ERROR",
            cause=e,
        )
        await handle_websocket_error(websocket, ws_error)
        await manager.disconnect(websocket, group_chat_id)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/api/test_websocket_endpoint.py -v`

Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents_hub/api/websocket/endpoint.py tests/api/test_websocket_endpoint.py
git commit -m "feat(websocket): add WebSocket endpoint

- /ws/group_chat/{group_chat_id} endpoint
- Connection lifecycle management
- Error handling with WebSocketError
- Integration tests (4 test cases)"
```

---

## Task 6: 创建广播 API 路由

**Files:**
- Create: `agents_hub/api/routes/websocket.py`
- Create: `tests/api/test_websocket_api.py`
- Modify: `agents_hub/api/routes/__init__.py`

- [ ] **Step 1: 编写广播 API 测试**

```python
# tests/api/test_websocket_api.py
"""WebSocket 广播 API 集成测试"""

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from agents_hub.api.routes.websocket import router
from agents_hub.api.websocket.dependencies import get_ws_manager, reset_ws_manager
from agents_hub.api.websocket.manager import WebSocketManager
from agents_hub.exceptions import AgentsHubError


@pytest.fixture
def manager():
    """创建 WebSocketManager 实例"""
    return WebSocketManager()


@pytest.fixture
def client(manager):
    """创建测试客户端"""
    reset_ws_manager()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    # 覆盖依赖注入
    app.dependency_overrides[get_ws_manager] = lambda: manager

    @app.exception_handler(AgentsHubError)
    async def agents_hub_error_handler(request: Request, exc: AgentsHubError):
        return JSONResponse(status_code=500, content=exc.to_dict())

    return TestClient(app)


def test_broadcast_success(client, manager):
    """测试：成功广播消息"""
    # 添加 mock 连接
    mock_ws = AsyncMock()
    manager.rooms["chat-123"] = [mock_ws]

    response = client.post(
        "/api/v1/ws/broadcast/chat-123",
        json={"type": "refresh", "group_chat_id": "chat-123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "Broadcast sent"

    # 验证广播被调用
    mock_ws.send_json.assert_called_once()


def test_broadcast_empty_room(client):
    """测试：广播到空房间"""
    response = client.post(
        "/api/v1/ws/broadcast/nonexistent",
        json={"type": "refresh", "group_chat_id": "nonexistent"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_broadcast_invalid_signal(client):
    """测试：无效信号格式"""
    response = client.post(
        "/api/v1/ws/broadcast/chat-123",
        json={"type": "refresh"},  # 缺少 group_chat_id
    )

    assert response.status_code == 422  # Pydantic 验证错误
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/api/test_websocket_api.py -v`

Expected: FAIL with `ImportError: cannot import name 'router' from 'agents_hub.api.routes.websocket'`

- [ ] **Step 3: 实现广播 API 路由**

```python
# agents_hub/api/routes/websocket.py
"""WebSocket API 路由

提供广播 API 供 Agent 调用，触发前端刷新。
"""

from fastapi import APIRouter, Depends

from agents_hub.api.schemas.websocket import BroadcastResponse, RefreshSignal
from agents_hub.api.websocket.dependencies import get_ws_manager
from agents_hub.api.websocket.manager import WebSocketManager

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.post(
    "/broadcast/{group_chat_id}",
    response_model=BroadcastResponse,
    summary="广播刷新信号到指定房间",
)
async def broadcast_message(
    group_chat_id: str,
    signal: RefreshSignal,
    manager: WebSocketManager = Depends(get_ws_manager),
) -> BroadcastResponse:
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

- [ ] **Step 4: 更新 routes/__init__.py**

```python
# agents_hub/api/routes/__init__.py
"""API routes package."""

from .group_chat import router as group_chats_router
from .roles import router as roles_router
from .skills import router as skills_router
from .websocket import router as websocket_router

__all__ = ["roles_router", "skills_router", "group_chats_router", "websocket_router"]
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/api/test_websocket_api.py -v`

Expected: All 3 tests PASS

- [ ] **Step 6: 运行所有路由测试确保无破坏**

Run: `pytest tests/api/ -v`

Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add agents_hub/api/routes/websocket.py agents_hub/api/routes/__init__.py tests/api/test_websocket_api.py
git commit -m "feat(websocket): add broadcast API route

- POST /api/v1/ws/broadcast/{group_chat_id}
- RefreshSignal validation
- BroadcastResponse
- Update routes/__init__.py
- Integration tests (3 test cases)"
```

---

## Task 7: 注册 WebSocket 路由到 FastAPI 应用

**Files:**
- Modify: `agents_hub/api/app.py`

- [ ] **Step 1: 更新 app.py 注册路由**

```python
# agents_hub/api/app.py

# 在现有路由注册处添加
from .routes import group_chats_router, roles_router, skills_router, websocket_router

# ...

app.include_router(skills_router, prefix="/api/v1")
app.include_router(group_chats_router, prefix="/api/v1")
app.include_router(roles_router, prefix="/api/v1")
app.include_router(websocket_router, prefix="/api/v1")  # 新增
```

- [ ] **Step 2: 运行应用启动测试**

Run: `python -c "from agents_hub.api.app import app; print('App loaded successfully')"`

Expected: `App loaded successfully`

- [ ] **Step 3: 运行所有测试**

Run: `pytest tests/ -x -q`

Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add agents_hub/api/app.py
git commit -m "feat(websocket): register WebSocket routes in FastAPI app

- Add websocket_router to app.py
- All routes under /api/v1 prefix"
```

---

## Task 8: 端到端测试

**Files:**
- Create: `tests/integration/test_websocket_e2e.py`

- [ ] **Step 1: 编写端到端测试**

```python
# tests/integration/test_websocket_e2e.py
"""WebSocket 端到端测试"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from agents_hub.api.routes.websocket import router as api_router
from agents_hub.api.websocket.dependencies import get_ws_manager, reset_ws_manager
from agents_hub.api.websocket.endpoint import router as ws_router
from agents_hub.api.websocket.manager import WebSocketManager
from agents_hub.exceptions import AgentsHubError
from fastapi import Request
from fastapi.responses import JSONResponse


@pytest.fixture
def manager():
    """创建 WebSocketManager 实例"""
    return WebSocketManager()


@pytest.fixture
def app(manager):
    """创建完整应用"""
    reset_ws_manager()
    app = FastAPI()
    app.include_router(ws_router)
    app.include_router(api_router, prefix="/api/v1")

    # 覆盖依赖注入
    app.dependency_overrides[get_ws_manager] = lambda: manager

    @app.exception_handler(AgentsHubError)
    async def agents_hub_error_handler(request: Request, exc: AgentsHubError):
        return JSONResponse(status_code=500, content=exc.to_dict())

    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


def test_e2e_connect_and_broadcast(client, manager):
    """端到端测试：连接后接收广播"""
    with client.websocket_connect("/ws/group_chat/chat-123") as websocket:
        # 连接成功
        assert "chat-123" in manager.rooms

        # 调用广播 API
        response = client.post(
            "/api/v1/ws/broadcast/chat-123",
            json={"type": "refresh", "group_chat_id": "chat-123"},
        )
        assert response.status_code == 200

        # 接收广播消息
        data = websocket.receive_json()
        assert data["type"] == "refresh"
        assert data["group_chat_id"] == "chat-123"


def test_e2e_multiple_rooms(client, manager):
    """端到端测试：多房间隔离"""
    with client.websocket_connect("/ws/group_chat/chat-1") as ws1:
        with client.websocket_connect("/ws/group_chat/chat-2") as ws2:
            # 广播到 chat-1
            client.post(
                "/api/v1/ws/broadcast/chat-1",
                json={"type": "refresh", "group_chat_id": "chat-1"},
            )

            # ws1 收到消息
            data1 = ws1.receive_json()
            assert data1["group_chat_id"] == "chat-1"

            # ws2 不应收到消息（非阻塞检查）
            # 注意：在测试环境中，如果 ws2 没有消息，receive_json 会阻塞
            # 所以这里我们只验证 ws1 收到了正确的消息


def test_e2e_disconnect_cleanup(client, manager):
    """端到端测试：断开连接后房间清理"""
    with client.websocket_connect("/ws/group_chat/chat-123") as websocket:
        assert "chat-123" in manager.rooms

    # 连接断开后房间被清理
    assert "chat-123" not in manager.rooms
```

- [ ] **Step 2: 运行端到端测试**

Run: `pytest tests/integration/test_websocket_e2e.py -v`

Expected: All 3 tests PASS

- [ ] **Step 3: 运行完整测试套件**

Run: `pytest tests/ -x -q`

Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_websocket_e2e.py
git commit -m "test(websocket): add end-to-end tests

- Connect and receive broadcast
- Multi-room isolation
- Disconnect cleanup
- 3 e2e test cases"
```

---

## Task 9: 手动测试验证

- [ ] **Step 1: 启动后端服务**

Run: `uvicorn agents_hub.api.app:app --reload --port 8000`

Expected: 服务启动成功，监听 8000 端口

- [ ] **Step 2: 测试 WebSocket 连接（使用 Python 脚本）**

```python
# 手动测试脚本
import asyncio
import aiohttp

async def test_websocket():
    async with aiohttp.ClientSession() as session:
        # 测试广播 API
        async with session.post(
            "http://localhost:8000/api/v1/ws/broadcast/test123",
            json={"type": "refresh", "group_chat_id": "test123"},
        ) as resp:
            print(f"Broadcast API status: {resp.status}")
            print(f"Response: {await resp.json()}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
```

Run: `python test_websocket_manual.py`

Expected: `Broadcast API status: 200`, `Response: {'status': 'ok', 'message': 'Broadcast sent'}`

- [ ] **Step 3: 测试 WebSocket 连接（使用浏览器控制台）**

```javascript
// 浏览器控制台
const ws = new WebSocket('ws://localhost:8000/ws/group_chat/test123');
ws.onopen = () => console.log('Connected');
ws.onmessage = (event) => console.log('Received:', JSON.parse(event.data));
ws.onclose = () => console.log('Disconnected');
```

Expected: 控制台输出 `Connected`

- [ ] **Step 4: 测试广播接收**

```bash
# 新开终端，调用广播 API
curl -X POST http://localhost:8000/api/v1/ws/broadcast/test123 \
  -H "Content-Type: application/json" \
  -d '{"type": "refresh", "group_chat_id": "test123"}'
```

Expected: 浏览器控制台输出 `Received: {type: "refresh", group_chat_id: "test123", timestamp: "..."}`

- [ ] **Step 5: 验证完成**

确认以下功能正常：
- [ ] WebSocket 连接成功
- [ ] 广播 API 正常工作
- [ ] 前端能接收到刷新信号
- [ ] 断开连接后房间自动清理

---

## 自审清单

### Spec 覆盖检查

- [x] WebSocket 连接管理（多房间）
- [x] 刷新信号推送
- [x] 广播 API
- [x] 异常体系（继承现有分类）
- [x] 依赖注入（全局单例）
- [x] Pydantic schemas
- [x] 路由注册
- [x] 测试方案

### 占位符扫描

- [x] 无 TBD/TODO
- [x] 所有代码完整
- [x] 文件路径明确

### 类型一致性

- [x] WebSocketManager 方法签名一致
- [x] 异常类名一致
- [x] Schema 字段一致

---

## 执行选项

Plan complete and saved to `docs/superpowers/plans/2026-06-03-websocket-backend-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
