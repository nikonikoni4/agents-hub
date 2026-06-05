"""
FastAPI 应用

集成 MCP Server，提供 HTTP API 接口。
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

# Windows: 必须在导入 FastAPI 之前设置 ProactorEventLoop
# uvicorn 会在启动时检查当前的事件循环策略
if sys.platform == "win32":
    import warnings

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agents_hub.api.routes import (
    config_router,
    group_chats_router,
    roles_router,
    skills_router,
    teams_router,
)
from agents_hub.config.config import config
from agents_hub.exceptions import (
    AgentsHubError,
    ExternalServiceError,
    ResourceNotFoundError,
    StateError,
    ValidationError,
)

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
    from agents_hub.bootstrap import initialize_default_roles, initialize_resources
    from agents_hub.mcp.server import mcp
    from agents_hub.utils import setup_logging

    setup_logging(log_dir=config.data_path / "logs")
    initialize_resources()
    initialize_default_roles()

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

app.include_router(skills_router, prefix="/api/v1")
app.include_router(group_chats_router, prefix="/api/v1")
app.include_router(roles_router, prefix="/api/v1")
app.include_router(teams_router, prefix="/api/v1")
app.include_router(config_router, prefix="/api/v1")


@app.exception_handler(AgentsHubError)
async def agents_hub_error_handler(request: Request, exc: AgentsHubError) -> JSONResponse:
    """处理所有 agents-hub 领域异常"""
    status = _resolve_status(exc)
    return JSONResponse(status_code=status, content=exc.to_dict())


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底：捕获所有未处理异常，防止内部信息泄露"""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    # 开发环境下返回详细错误信息
    import os

    is_dev = os.getenv("ENV", "development") == "development"
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": str(exc) if is_dev else "服务器内部错误",
            "type": "InternalError",
        },
    )


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    # 注意：reload=True 会导致子进程重置事件循环策略
    # 在开发环境中如果需要 reload，使用命令行：uvicorn agents_hub.api.app:app --reload
    # 但这样会导致 Windows 上 subprocess 失败
    uvicorn.run(app, host="0.0.0.0", port=8099, reload=False)
