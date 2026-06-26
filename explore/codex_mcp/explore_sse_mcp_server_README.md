# Explore: SSE MCP Server 连通性测试

用于验证 Codex CLI 是否能通过 SSE 传输连接 FastMCP。

## 启动服务

```bash
# 默认端口 8800
python explore/codex_mcp/explore_sse_mcp_server.py

# 自定义端口
python explore/codex_mcp/explore_sse_mcp_server.py --port 8900
```

## 注册到 Codex

```bash
codex mcp add explore-sse --url http://127.0.0.1:8800/sse
```

## 验证连接

在 Codex 中调用 `health_check` 工具，预期返回：

```json
{
  "status": "ok",
  "server_name": "AgentsHub Explore SSE MCP Server",
  "transport": "sse",
  "time": "2026-06-26T..."
}
```

## 对比测试

| 传输模式 | URL 格式 | Codex 支持 |
|---------|----------|-----------|
| Streamable HTTP | `http://localhost:8765/mcp` | 待确认（当前失败） |
| SSE | `http://127.0.0.1:8800/sse` | 本测试验证中 |
