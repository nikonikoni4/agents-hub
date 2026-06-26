"""探索性 SSE MCP Server（仅用于 Codex 连通性测试）

提供一个最小 SSE MCP Server，默认只暴露 health_check 工具，
用于验证 Codex CLI 是否能通过 SSE 传输连接 FastMCP。

使用方式：
    python explore/codex_mcp/explore_sse_mcp_server.py
    # 默认监听 http://127.0.0.1:8800/sse

自定义端口：
    python explore/codex_mcp/explore_sse_mcp_server.py --port 8900

注册到 Codex：
    codex mcp add explore-sse --url http://127.0.0.1:8800/sse
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from fastmcp import FastMCP


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="启动用于探索的 SSE MCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址，默认 127.0.0.1")
    parser.add_argument("--port", type=int, default=8800, help="监听端口，默认 8800")
    return parser.parse_args()


def create_server() -> FastMCP:
    """创建仅包含 health check 的 FastMCP 实例。"""
    server = FastMCP(
        name="AgentsHub Explore SSE MCP Server",
        instructions="探索性 SSE MCP Server，用于测试 Codex 对 SSE 传输的连接能力。",
        version="0.0.1",
    )

    @server.tool()
    def health_check() -> dict[str, object]:
        """返回当前 SSE MCP Server 的健康状态。"""
        return {
            "status": "ok",
            "server_name": server.name,
            "transport": "sse",
            "time": datetime.now(timezone.utc).isoformat(),
        }

    return server


def main() -> None:
    args = _parse_args()
    server = create_server()
    print(f"[explore] SSE MCP Server 启动: http://{args.host}:{args.port}/sse")
    server.run(transport="sse", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
