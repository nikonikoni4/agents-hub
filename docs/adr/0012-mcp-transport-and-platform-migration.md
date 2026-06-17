# MCP 传输模式与平台迁移决策

- updated_at: 2026-06-09
- 状态：decided
- 触发规则：当设计或修改 MCP 传输模式、Agent 平台选型时阅读

## 背景

### 阶段一：Codex 不支持 HTTP MCP

最初 MCP Server 使用 HTTP 传输模式（`http://localhost:8765/mcp`）。但 Codex 平台不支持 HTTP 传输的 MCP 协议，只支持 stdio 模式。为了兼容 Codex，决定将 MCP 传输从 HTTP 切换到 stdio。

### 阶段二：Stdio 跨进程隔离问题

切换到 stdio 后发现根本性问题：

1. **内存隔离**：MCP Server 作为独立子进程运行（`python -m agents_hub.mcp.server`），与主进程（API Server）拥有各自独立的 `GroupChatManager` 单例实例。Token 注册在主进程内存中，MCP 子进程的 `_tokens` 字典为空，导致所有 token 验证失败。

2. **通信断裂**：MCP 子进程中的 `send_message_to_agent()`、`broadcast_group_chat_refresh()` 等操作只影响自身的内存副本，主进程的 agent 完全无法接收消息。`finish_agent_call` 等工具的核心功能（闭环通知、群聊刷新）在 stdio 模式下全部失效。

3. **架构不兼容**：当前架构依赖进程内共享状态（内存队列、WebSocket 连接、单例注册表），stdio 模式要求每个操作都能跨进程工作，改造成本过高。

### 阶段三：回归 HTTP

综合评估后决定回归 HTTP 传输模式。HTTP 模式下 MCP Server 与主进程在同一进程内运行，共享内存状态，不存在跨进程隔离问题。

## 决策

1. **MCP 传输模式**：回归 HTTP，放弃 stdio
2. **Agent 平台**：放弃 Codex，改用 OpenCode

## 原因

- stdio 的跨进程隔离问题与当前架构根本不兼容，改造成本远超收益
- HTTP 模式天然适配进程内共享状态的架构
- OpenCode 替代 Codex，不再需要为兼容 Codex 而选择 stdio

## 影响

- `.mcp.json` 中 agents-hub 配置从 stdio 改回 HTTP
- `GroupChat._init_mcp_for_all_agents()` 需要适配 HTTP 模式
- Codex 相关的 executor、parser、MCP 配置代码可逐步移除
