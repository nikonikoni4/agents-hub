"""
FastAPI 应用

集成 MCP Server，提供 HTTP API 接口。
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agents_hub.config.config import config
from agents_hub.exceptions import (
    AgentsHubError,
    ExternalServiceError,
    ResourceNotFoundError,
    StateError,
    ValidationError,
)

from .routes import group_chats_router, router

logger = logging.getLogger(__name__)


_STATUS_MAP: dict[type[AgentsHubError], int] = {
    ValidationError: 400,
    ResourceNotFoundError: 404,
    StateError: 409,
    ExternalServiceError: 502,
}


def _resolve_status(exc: AgentsHubError) -> int:
    """根据异常类型映射 HTTP 状态码（子类优先匹配）"""
    for exc_cls, status in _STATUS_MAP.items():
        if isinstance(exc, exc_cls):
            return status
    return 500


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    from agents_hub.mcp.server import mcp

    mcp_task = asyncio.create_task(
        mcp.run_async(
            transport="http",
            host="localhost",
            port=config.mcp_port,
        )
    )
    yield
    mcp_task.cancel()


app = FastAPI(title="Agents Hub API", version="0.1.0", lifespan=lifespan)

# 注册路由
app.include_router(router, prefix="/api/v1")
app.include_router(group_chats_router, prefix="/api/v1")


@app.exception_handler(AgentsHubError)
async def agents_hub_error_handler(request: Request, exc: AgentsHubError) -> JSONResponse:
    """处理所有 agents-hub 领域异常"""
    status = _resolve_status(exc)
    return JSONResponse(status_code=status, content=exc.to_dict())


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底：捕获所有未处理异常，防止内部信息泄露"""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
            "type": "InternalError",
        },
    )


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok"}
