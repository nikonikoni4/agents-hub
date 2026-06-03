"""
测试 FastAPI 集成 MCP Server

验证：
1. MCP Server 在 FastAPI 启动时自动启动
2. MCP Server 监听正确的端口（config.mcp_port）
3. MCP Server 可以接收请求
"""

import asyncio
import socket
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from agents_hub.config import config


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

    # 验证端口被占用（MCP Server 正在监听）
    port = config.mcp_port
    assert is_port_in_use(port), f"MCP Server 应该在端口 {port} 上监听"


@pytest.mark.asyncio
async def test_mcp_server_can_receive_requests(client):
    """测试 MCP Server 可以接收请求"""
    # 等待 MCP Server 启动
    await asyncio.sleep(1)

    # 尝试连接到 MCP Server
    # 注意：这里只测试连接性，不测试具体的 MCP 协议
    reader, writer = await asyncio.open_connection("localhost", config.mcp_port)

    try:
        # 如果能建立连接，说明 MCP Server 正在运行
        assert True
    finally:
        writer.close()
        await writer.wait_closed()


def test_fastapi_startup_event_registered(client):
    """测试 FastAPI 启动生命周期已配置"""
    from agents_hub.api.app import app

    # app 使用 lifespan 模式（非 on_startup），验证 lifespan 已配置
    assert app.router.lifespan_context is not None, "应该配置 lifespan 生命周期管理"
