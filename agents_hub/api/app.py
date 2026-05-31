"""
FastAPI 应用

集成 MCP Server，提供 HTTP API 接口。
"""

import asyncio

from fastapi import FastAPI

app = FastAPI(title="Agents Hub API", version="0.1.0")


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok"}


@app.on_event("startup")
async def startup_mcp():
    """启动 MCP Server"""
    from agents_hub.mcp.server import mcp

    # FastMCP 使用 HTTP 传输，在独立任务中运行
    asyncio.create_task(mcp.run_async(transport="http", host="localhost", port=8001))
