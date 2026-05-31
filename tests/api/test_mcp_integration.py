"""
测试 FastAPI 集成 MCP Server

验证：
1. MCP Server 在 FastAPI 启动时自动启动
2. MCP Server 监听正确的端口（8001）
3. MCP Server 可以接收请求
"""

import asyncio
import socket
from contextlib import closing

import pytest
from fastapi.testclient import TestClient


def is_port_in_use(port: int) -> bool:
    """检查端口是否被占用"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        return sock.connect_ex(("localhost", port)) == 0


@pytest.fixture(scope="module")
def client():
    """创建 FastAPI 测试客户端（模块级别，所有测试共享）"""
    from agents_hub.api.app import app

    with TestClient(app) as c:
        yield c


def test_fastapi_app_exists(client):
    """测试 FastAPI 应用存在且可以响应"""
    response = client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_mcp_server_starts_with_fastapi(client):
    """测试 MCP Server 在 FastAPI 启动时自动启动"""
    # 等待 MCP Server 启动
    await asyncio.sleep(1)

    # 验证端口 8001 被占用（MCP Server 正在监听）
    assert is_port_in_use(8001), "MCP Server 应该在端口 8001 上监听"


@pytest.mark.asyncio
async def test_mcp_server_can_receive_requests(client):
    """测试 MCP Server 可以接收请求"""
    # 等待 MCP Server 启动
    await asyncio.sleep(1)

    # 尝试连接到 MCP Server
    # 注意：这里只测试连接性，不测试具体的 MCP 协议
    reader, writer = await asyncio.open_connection("localhost", 8001)

    try:
        # 如果能建立连接，说明 MCP Server 正在运行
        assert True
    finally:
        writer.close()
        await writer.wait_closed()


def test_fastapi_startup_event_registered(client):
    """测试 FastAPI 启动事件已注册"""
    from agents_hub.api.app import app

    # 检查是否有 startup 事件处理器
    assert len(app.router.on_startup) > 0, "应该至少有一个 startup 事件处理器"
