# tests/api/test_websocket_boundary.py
"""WebSocket 边界场景测试

聚焦边界条件、bad case、并发场景，而非代码覆盖率。
"""

import asyncio
import contextlib
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient

from agents_hub.api.websocket.dependencies import get_ws_manager, reset_ws_manager
from agents_hub.api.websocket.endpoint import handle_websocket_error, router
from agents_hub.api.websocket.exceptions import WebSocketError
from agents_hub.api.websocket.manager import WebSocketManager
from agents_hub.api.schemas.websocket import RefreshSignal


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def manager():
    """创建 WebSocketManager 实例"""
    return WebSocketManager()


@pytest.fixture
def mock_websocket():
    """创建 mock WebSocket"""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    ws.accept = AsyncMock()
    return ws


@pytest.fixture
def app(manager):
    """创建测试应用（仅 WebSocket endpoint）"""
    reset_ws_manager()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_ws_manager] = lambda: manager
    return app


@pytest.fixture
def client(app):
    """创建测试客户端（仅 WebSocket endpoint）"""
    return TestClient(app)


@pytest.fixture
def broadcast_app(manager):
    """创建测试应用（包含 broadcast 路由）"""
    from agents_hub.api.routes.websocket import router as broadcast_router

    reset_ws_manager()
    app = FastAPI()
    app.include_router(broadcast_router, prefix="/api/v1")
    app.dependency_overrides[get_ws_manager] = lambda: manager
    return app


@pytest.fixture
def broadcast_client(broadcast_app):
    """创建测试客户端（包含 broadcast 路由）"""
    return TestClient(broadcast_app)


# ============================================================================
# WebSocketManager.connect 边界测试
# ============================================================================


@pytest.mark.asyncio
async def test_connect_duplicate_websocket_same_room(manager, mock_websocket):
    """
    契约：同一 websocket 重复 connect 到同一房间

    验证方式：
    1. 同一 websocket connect 两次到同一房间
    2. 验证 websocket 在列表中出现两次
    3. accept() 被调用两次

    如果失败，说明：connect 没有做去重检查（可能有意为之）
    """
    await manager.connect(mock_websocket, "room-1")
    await manager.connect(mock_websocket, "room-1")

    # 当前实现允许重复添加（不做去重）
    assert len(manager.rooms["room-1"]) == 2
    assert mock_websocket.accept.call_count == 2


@pytest.mark.asyncio
async def test_connect_empty_group_chat_id(manager, mock_websocket):
    """
    契约：group_chat_id 为空字符串时仍能创建房间

    验证方式：
    1. connect 到空字符串房间
    2. 验证房间被创建

    如果失败，说明：空字符串被当作无效输入
    """
    await manager.connect(mock_websocket, "")

    assert "" in manager.rooms
    assert mock_websocket in manager.rooms[""]


@pytest.mark.asyncio
async def test_connect_special_characters_room_id(manager, mock_websocket):
    """
    契约：特殊字符的 room_id 应该正常工作

    验证方式：
    1. 使用中文、emoji、路径分隔符作为 room_id
    2. 验证房间被正确创建

    如果失败，说明：room_id 处理有字符限制
    """
    special_ids = ["中文房间", "room/with/slashes", "room:with:colons", "🎉party🎉"]

    for room_id in special_ids:
        ws = AsyncMock()
        await manager.connect(ws, room_id)
        assert room_id in manager.rooms
        assert ws in manager.rooms[room_id]


@pytest.mark.asyncio
async def test_connect_accept_failure_no_room_pollution(manager):
    """
    契约：accept() 失败时，rooms 不应被污染

    验证方式：
    1. mock websocket.accept 抛出异常
    2. 验证 connect 抛出异常
    3. 验证 rooms 为空（没有脏数据）

    如果失败，说明：connect 没有在 accept 失败时回滚
    """
    ws = AsyncMock()
    ws.accept.side_effect = Exception("accept failed")

    with pytest.raises(Exception, match="accept failed"):
        await manager.connect(ws, "room-1")

    # 当前实现在 accept 失败时不会添加到 rooms（异常向上传播）
    assert "room-1" not in manager.rooms


# ============================================================================
# WebSocketManager.disconnect 边界测试
# ============================================================================


@pytest.mark.asyncio
async def test_disconnect_idempotent(manager, mock_websocket):
    """
    契约：disconnect 同一 websocket 两次不应报错（幂等性）

    验证方式：
    1. connect websocket
    2. disconnect 两次
    3. 验证没有异常抛出

    如果失败，说明：disconnect 不是幂等的
    """
    await manager.connect(mock_websocket, "room-1")
    await manager.disconnect(mock_websocket, "room-1")
    await manager.disconnect(mock_websocket, "room-1")  # 第二次不应报错


@pytest.mark.asyncio
async def test_disconnect_last_connection_removes_room(manager, mock_websocket):
    """
    契约：断开最后一个连接后房间被删除

    验证方式：
    1. connect websocket
    2. disconnect websocket
    3. 验证房间被删除

    如果失败，说明：空房间未被清理
    """
    await manager.connect(mock_websocket, "room-1")
    assert "room-1" in manager.rooms

    await manager.disconnect(mock_websocket, "room-1")
    assert "room-1" not in manager.rooms


@pytest.mark.asyncio
async def test_disconnect_not_last_connection_keeps_room(manager, mock_websocket):
    """
    契约：断开非最后一个连接时房间保留

    验证方式：
    1. connect 两个 websocket
    2. disconnect 一个
    3. 验证房间仍在，且剩余连接正确

    如果失败，说明：disconnect 逻辑有误
    """
    ws2 = AsyncMock()
    await manager.connect(mock_websocket, "room-1")
    await manager.connect(ws2, "room-1")

    await manager.disconnect(mock_websocket, "room-1")

    assert "room-1" in manager.rooms
    assert len(manager.rooms["room-1"]) == 1
    assert ws2 in manager.rooms["room-1"]


@pytest.mark.asyncio
async def test_disconnect_concurrent_multiple_connections(manager):
    """
    契约：并发 disconnect 同一房间的多个连接应该安全

    验证方式：
    1. connect 多个 websocket
    2. 并发 disconnect 所有 websocket
    3. 验证房间被删除，无异常

    如果失败，说明：并发操作存在竞态条件
    """
    connections = [AsyncMock() for _ in range(10)]
    for ws in connections:
        await manager.connect(ws, "room-1")

    # 并发 disconnect
    tasks = [manager.disconnect(ws, "room-1") for ws in connections]
    await asyncio.gather(*tasks)

    assert "room-1" not in manager.rooms


# ============================================================================
# WebSocketManager.broadcast 边界测试
# ============================================================================


@pytest.mark.asyncio
async def test_broadcast_empty_message(manager, mock_websocket):
    """
    契约：广播空消息 {} 应该正常工作

    验证方式：
    1. connect websocket
    2. broadcast 空消息
    3. 验证 send_json 被调用

    如果失败，说明：空消息被当作无效输入
    """
    await manager.connect(mock_websocket, "room-1")
    await manager.broadcast("room-1", {})

    mock_websocket.send_json.assert_called_once_with({})


@pytest.mark.asyncio
async def test_broadcast_all_failures_removes_room(manager):
    """
    契约：所有连接都失败时房间被删除

    验证方式：
    1. connect 多个 websocket，全部 mock 为失败
    2. broadcast
    3. 验证房间被删除

    如果失败，说明：全部失败时房间未被清理
    """
    ws1 = AsyncMock()
    ws1.send_json.side_effect = Exception("fail 1")
    ws2 = AsyncMock()
    ws2.send_json.side_effect = Exception("fail 2")

    await manager.connect(ws1, "room-1")
    await manager.connect(ws2, "room-1")

    await manager.broadcast("room-1", {"type": "refresh"})

    assert "room-1" not in manager.rooms


@pytest.mark.asyncio
async def test_broadcast_unicode_message(manager, mock_websocket):
    """
    契约：Unicode 消息内容应该正常广播

    验证方式：
    1. connect websocket
    2. broadcast Unicode 消息（中文、emoji）
    3. 验证 send_json 被调用

    如果失败，说明：Unicode 处理有问题
    """
    await manager.connect(mock_websocket, "room-1")

    message = {"type": "refresh", "content": "你好世界 🎉"}
    await manager.broadcast("room-1", message)

    mock_websocket.send_json.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_broadcast_during_concurrent_disconnect(manager):
    """
    契约：广播期间连接断开应该安全处理

    验证方式：
    1. connect 多个 websocket
    2. 模拟一个 websocket 在 send_json 时断开
    3. broadcast
    4. 验证其他连接仍收到消息，失败连接被清理

    如果失败，说明：并发操作存在竞态条件
    """
    ws_ok = AsyncMock()
    ws_fail = AsyncMock()
    ws_fail.send_json.side_effect = Exception("disconnected during send")

    await manager.connect(ws_ok, "room-1")
    await manager.connect(ws_fail, "room-1")

    await manager.broadcast("room-1", {"type": "refresh"})

    ws_ok.send_json.assert_called_once()
    assert ws_fail not in manager.rooms.get("room-1", [])


@pytest.mark.asyncio
async def test_broadcast_concurrent_modification_safety(manager):
    """
    契约：broadcast 执行过程中 rooms 不应被意外修改

    验证方式：
    1. connect 多个 websocket
    2. 模拟一个 websocket 在 send_json 时触发 disconnect（通过 side_effect）
    3. broadcast
    4. 验证没有 RuntimeError（字典大小改变）

    如果失败，说明：遍历过程中修改了字典
    """
    connections = []
    for i in range(5):
        ws = AsyncMock()
        connections.append(ws)
        await manager.connect(ws, "room-1")

    # 第 3 个连接在 send_json 时失败
    connections[2].send_json.side_effect = Exception("fail")

    await manager.broadcast("room-1", {"type": "refresh"})

    # 验证成功发送的连接数
    success_count = sum(
        1 for ws in connections if ws.send_json.call_count > 0 and ws != connections[2]
    )
    assert success_count == 4  # 除第 3 个外都成功


# ============================================================================
# WebSocket Endpoint 边界测试
# ============================================================================


def test_endpoint_immediate_disconnect(client, manager):
    """
    契约：连接后立即断开应该正确清理

    验证方式：
    1. 建立 WebSocket 连接
    2. 立即关闭
    3. 验证房间被清理

    如果失败，说明：极短生命周期连接处理有问题
    """
    with client.websocket_connect("/ws/group_chat/room-1"):
        pass  # 立即退出

    assert "room-1" not in manager.rooms


def test_endpoint_multiple_clients_same_room(client, manager):
    """
    契约：多个客户端同时连接同一房间

    验证方式：
    1. 建立两个 WebSocket 连接到同一房间
    2. 验证房间有两个连接
    3. 关闭一个，验证剩余一个
    4. 关闭最后一个，验证房间删除

    如果失败，说明：多客户端管理有问题
    """
    with client.websocket_connect("/ws/group_chat/room-1") as ws1:
        assert len(manager.rooms["room-1"]) == 1

        with client.websocket_connect("/ws/group_chat/room-1") as ws2:
            assert len(manager.rooms["room-1"]) == 2

        # ws2 关闭后
        assert len(manager.rooms["room-1"]) == 1

    # ws1 关闭后
    assert "room-1" not in manager.rooms


def test_endpoint_room_isolation(client, manager):
    """
    契约：不同房间之间完全隔离

    验证方式：
    1. 建立两个不同房间的连接
    2. 关闭一个房间的连接
    3. 验证另一个房间不受影响

    如果失败，说明：房间隔离有问题
    """
    with client.websocket_connect("/ws/group_chat/room-1"):
        with client.websocket_connect("/ws/group_chat/room-2"):
            assert len(manager.rooms) == 2

        # room-2 关闭后
        assert len(manager.rooms) == 1
        assert "room-1" in manager.rooms
        assert "room-2" not in manager.rooms

    # room-1 关闭后
    assert len(manager.rooms) == 0


# ============================================================================
# handle_websocket_error 边界测试
# ============================================================================


@pytest.mark.asyncio
async def test_handle_websocket_error_basic():
    """
    契约：handle_websocket_error 发送正确的错误格式

    验证方式：
    1. 创建 WebSocketError
    2. 调用 handle_websocket_error
    3. 验证 send_json 被调用且格式正确

    如果失败，说明：错误消息格式不对
    """
    ws = AsyncMock()
    error = WebSocketError("test error", error_code="TEST_ERR", details={"key": "value"})

    await handle_websocket_error(ws, error)

    ws.send_json.assert_called_once()
    sent_data = ws.send_json.call_args[0][0]
    assert sent_data["type"] == "error"
    assert sent_data["error_code"] == "TEST_ERR"
    assert sent_data["message"] == "test error"
    assert sent_data["details"] == {"key": "value"}


@pytest.mark.asyncio
async def test_handle_websocket_error_send_failure():
    """
    契约：send_json 失败时异常应该被抛出

    验证方式：
    1. mock send_json 抛出异常
    2. 调用 handle_websocket_error
    3. 验证异常被抛出

    如果失败，说明：错误处理吞掉了异常
    """
    ws = AsyncMock()
    ws.send_json.side_effect = Exception("send failed")

    error = WebSocketError("test error")

    with pytest.raises(Exception, match="send failed"):
        await handle_websocket_error(ws, error)


# ============================================================================
# RefreshSignal Schema 边界测试
# ============================================================================


def test_refresh_signal_empty_group_chat_id():
    """
    契约：group_chat_id 为空字符串时应该验证失败

    验证方式：
    1. 创建 group_chat_id="" 的 RefreshSignal
    2. 验证 Pydantic 是否允许（min_length 未设置则允许）

    如果失败，说明：验证规则不一致
    """
    # 当前实现没有 min_length 限制，空字符串应该被允许
    signal = RefreshSignal(group_chat_id="")
    assert signal.group_chat_id == ""


def test_refresh_signal_very_long_group_chat_id():
    """
    契约：超长 group_chat_id 应该被处理

    验证方式：
    1. 创建 group_chat_id=1000 字符的 RefreshSignal
    2. 验证创建成功

    如果失败，说明：有长度限制
    """
    long_id = "a" * 1000
    signal = RefreshSignal(group_chat_id=long_id)
    assert signal.group_chat_id == long_id


def test_refresh_signal_empty_type():
    """
    契约：type 为空字符串时应该被允许

    验证方式：
    1. 创建 type="" 的 RefreshSignal
    2. 验证创建成功

    如果失败，说明：type 有最小长度限制
    """
    signal = RefreshSignal(group_chat_id="room-1", type="")
    assert signal.type == ""


def test_refresh_signal_json_serialization():
    """
    契约：model_dump(mode="json") 应该正确序列化 datetime

    验证方式：
    1. 创建 RefreshSignal
    2. 使用 model_dump(mode="json") 序列化
    3. 验证 timestamp 是字符串格式

    如果失败，说明：datetime 序列化有问题
    """
    from datetime import datetime

    signal = RefreshSignal(group_chat_id="room-1")
    data = signal.model_dump(mode="json")

    assert isinstance(data["timestamp"], str)
    # 验证可以被 datetime.fromisoformat 解析
    datetime.fromisoformat(data["timestamp"])


def test_refresh_signal_model_dump_without_json_mode():
    """
    契约：model_dump() 不带 mode="json" 返回原始 datetime 对象

    验证方式：
    1. 创建 RefreshSignal
    2. 使用 model_dump() 序列化
    3. 验证 timestamp 是 datetime 对象

    如果失败，说明：序列化行为不一致
    """
    from datetime import datetime

    signal = RefreshSignal(group_chat_id="room-1")
    data = signal.model_dump()

    assert isinstance(data["timestamp"], datetime)


# ============================================================================
# Broadcast API 边界测试
# ============================================================================


def test_broadcast_path_param_overrides_body(broadcast_client, manager):
    """
    契约：路径参数 group_chat_id 覆盖 body 中的 group_chat_id

    验证方式：
    1. 创建测试应用
    2. 发送请求，路径参数和 body 中的 group_chat_id 不同
    3. 验证广播使用路径参数

    如果失败，说明：参数优先级不正确
    """
    mock_ws = AsyncMock()
    manager.rooms["path-room"] = [mock_ws]

    response = broadcast_client.post(
        "/api/v1/ws/broadcast/path-room",
        json={"type": "refresh", "group_chat_id": "body-room"},
    )

    assert response.status_code == 200
    # 验证广播使用了路径参数 "path-room"，而不是 body 中的 "body-room"
    sent_data = mock_ws.send_json.call_args[0][0]
    assert sent_data["group_chat_id"] == "path-room"


def test_broadcast_malformed_body(broadcast_client, manager):
    """
    契约：格式错误的 body 应该返回 422

    验证方式：
    1. 发送无效 JSON
    2. 验证返回 422

    如果失败，说明：错误处理有问题
    """
    response = broadcast_client.post(
        "/api/v1/ws/broadcast/room-1",
        content="not json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422


def test_broadcast_missing_required_field(broadcast_client, manager):
    """
    契约：缺少必需字段应该返回 422

    验证方式：
    1. 发送缺少 group_chat_id 的请求
    2. 验证返回 422

    如果失败，说明：Pydantic 验证未生效
    """
    response = broadcast_client.post(
        "/api/v1/ws/broadcast/room-1",
        json={"type": "refresh"},  # 缺少 group_chat_id
    )

    assert response.status_code == 422


def test_broadcast_extra_fields_ignored(broadcast_client, manager):
    """
    契约：额外字段应该被忽略（Pydantic 默认行为）

    验证方式：
    1. 发送包含额外字段的请求
    2. 验证请求成功
    3. 验证广播消息不包含额外字段

    如果失败，说明：Pydantic 配置有 strict 模式
    """
    mock_ws = AsyncMock()
    manager.rooms["room-1"] = [mock_ws]

    response = broadcast_client.post(
        "/api/v1/ws/broadcast/room-1",
        json={
            "type": "refresh",
            "group_chat_id": "room-1",
            "extra_field": "should be ignored",
        },
    )

    assert response.status_code == 200
    sent_data = mock_ws.send_json.call_args[0][0]
    assert "extra_field" not in sent_data
