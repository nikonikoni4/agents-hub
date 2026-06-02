"""
FastAPI 应用

集成 MCP Server，提供 HTTP API 接口。
"""

import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agents_hub.core.orchestration import GroupChatManager
from agents_hub.exceptions import (
    AgentsHubError,
    ExternalServiceError,
    ResourceNotFoundError,
    StateError,
    ValidationError,
)

from .routes import router

logger = logging.getLogger(__name__)

# 全局单例（模块级变量）
_group_chat_manager_singleton = GroupChatManager()


def get_group_chat_manager() -> GroupChatManager:
    """获取全局 GroupChatManager 单例

    Returns:
        GroupChatManager: 全局唯一的 GroupChatManager 实例
    """
    return _group_chat_manager_singleton


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


app = FastAPI(title="Agents Hub API", version="0.1.0")

# 注册路由
app.include_router(router)


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


@app.on_event("startup")
async def startup_mcp():
    """启动 MCP Server"""
    from agents_hub.mcp.server import mcp

    # FastMCP 使用 HTTP 传输，在独立任务中运行
    asyncio.create_task(mcp.run_async(transport="http", host="localhost", port=8001))
