---
version: 1.0
created_at: 2026-06-22
updated_at: 2026-06-22
last_updated: 记录 Claude/Codex/OpenCode 三个平台 CLI 在 fork、系统提示词、MCP、工具禁用四个维度的功能差异与限制
abstract: 各 Agent 平台 CLI 能力不一致导致的实现约束。覆盖 fork 会话分叉、系统提示词注入、MCP 连接、工具禁用四个方面，说明当前实现方式、限制原因和未解决问题。
---

# CLI 平台能力限制

## 概述

agents-hub 通过子进程调用各平台 CLI（Claude Code、Codex、OpenCode）驱动 Agent 执行。各平台 CLI 能力不一致，导致部分功能只能在特定平台实现或需要 workaround。

---

## 1. Fork（会话分叉）

Fork 用于从已有会话创建新会话，保留上下文历史。

| 平台 | 支持程度 | 实现方式 |
|------|---------|---------|
| Claude | 原生支持 | CLI 参数 `--fork-session --resume <session_id>` |
| Codex | workaround | 文件层复制 JSONL + 修改 meta（见下方说明） |
| OpenCode | 不支持 | 降级为普通会话初始化 |

**相关代码**：

- Claude executor: `agents_hub/agent_bridge/executors/claude.py`（`_build_command` 中拼接 fork 参数）
- Codex fork 工具函数: `agents_hub/core/utils/session_fork.py`（`fork_codex_session`）
- Codex executor: `agents_hub/agent_bridge/executors/codex.py`（`fork_from` 参数已弃用，executor 只用 `session_id` 恢复）
- OpenCode executor: `agents_hub/agent_bridge/executors/opencode.py`（不支持 fork）
- 编排层降级处理: `agents_hub/core/orchestration/group_chat.py`

**Codex fork workaround 说明**：Codex CLI 没有原生 fork 参数。当前方案是在文件系统层面复制原会话 JSONL 文件，修改 `session_meta` 中的 `id` 和 `forked_from_id`，生成新的 `session_id`，再通过 `codex exec resume --json <new_session_id>` 恢复。这个方案绕过了 CLI 限制，但依赖 Codex 内部文件格式，存在格式变更风险。

**未解决问题**：OpenCode 的 fork 能力未调研，当前直接降级。

---

## 2. 系统提示词注入

| 平台 | 注入方式 | CLI 参数 | 是否需要文件 |
|------|---------|---------|------------|
| Claude | CLI 参数直接传入 | `--append-system-prompt <text>` | 否 |
| Codex | CLI 配置参数传入 | `-c instructions=<text>` | 否 |
| OpenCode | 文件引用方式 | `--agent <filename>` | 是 |

**相关代码**：

- Claude executor: `agents_hub/agent_bridge/executors/claude.py`
- Codex executor: `agents_hub/agent_bridge/executors/codex.py`（辅助函数 `_sanitize_for_codex_cli` 清理换行符和转义单引号）
- OpenCode executor: `agents_hub/agent_bridge/executors/opencode.py`
- OpenCode 文件写入: `agents_hub/core/agent/base_agent.py`（`_build_opencode_system_prompt` 方法）

**OpenCode 文件注入机制说明**：OpenCode CLI 不支持直接传入 system prompt 字符串。当前方案是将 system prompt 写入 `{work_root}/agents/{agent_name}_{group_chat_id}.md` 文件，然后通过 `--agent <filename>` 参数引用该文件名（不含 `.md` 后缀）。OpenCode 通过环境变量 `OPENCODE_CONFIG_DIR` 指向 `work_root`，从而找到 `agents/` 目录下的 `.md` 文件。

**当前状态**：system prompt 动态生成通道已关闭（`system_prompt = None`），但通道代码保留。

---

## 3. MCP 连接限制

### 3.1 各平台 MCP 连接状态

| 平台 | 配置文件 | 配置格式 | 连接状态 |
|------|---------|---------|---------|
| Claude | `.mcp.json` | JSON（`mcpServers`） | 正常 |
| Codex | `config.toml` | TOML（`mcp_servers`） | 不可用（HTTP bug） |
| OpenCode | `opencode.json` | JSON（`mcp`） | 未验证（前端已禁用） |

**相关代码**：

- MCP 配置生成: `agents_hub/roles/role_manager.py`（`_init_agents_hub_mcp` 方法，按平台分支生成配置）
- 环境变量设置: 各 executor 的 `_build_env` 方法

**环境变量**：各平台通过环境变量将 `work_root` 设为配置目录，实现角色隔离：

| 平台 | 环境变量 |
|------|---------|
| Claude | `CLAUDE_CONFIG_DIR` |
| Codex | `CODEX_HOME` |
| OpenCode | `OPENCODE_CONFIG_DIR` |

### 3.2 Codex MCP 连接问题

Codex CLI 对 HTTP 传输的 MCP 存在 bug，无法正常接收 MCP 消息。曾尝试切换到 stdio 模式，但发现根本性问题：agents-hub 的 MCP Server 与主 API Server 运行在同一进程内，共享内存状态（`GroupChatManager` 单例、token 注册表、WebSocket 连接）。stdio 模式下 MCP Server 作为独立子进程，导致：

1. **内存隔离**：子进程有独立的 `GroupChatManager` 单例副本，token 验证全部失败
2. **通信断裂**：子进程中的 `send_message_to_agent()` 只影响自身内存副本，主进程 agent 无法接收消息

最终决定回归 HTTP 传输模式。详见 [ADR-0012](../ADR/0012-mcp-transport-and-platform-migration.md)。

### 3.3 MCP 必须项目级配置（未解决问题）

由于各平台通过环境变量改变了配置数据路径，全局添加的 MCP 配置在各角色的隔离环境中不可见。因此 MCP 配置必须写在每个角色的 `work_root` 下（项目级别）。

各平台项目级 MCP 配置路径：

| 平台 | 配置文件路径 |
|------|------------|
| Claude | `{work_root}/.mcp.json` |
| Codex | `{work_root}/config.toml`（格式较复杂） |
| OpenCode | `{work_root}/opencode.json` |

**影响**：MCP 限制导致 manager 角色当前只能使用 Claude 平台（唯一 MCP 连接正常的平台）。bootstrap.py 中 manager 默认创建为 Claude 平台。

---

## 4. 工具禁用

| 平台 | 支持程度 | 机制 |
|------|---------|------|
| Claude | 支持 | `--disallowedTools=Tool1,Tool2` 黑名单参数 |
| Codex | 不支持 | CLI 无工具过滤参数 |
| OpenCode | 不支持 | CLI 无工具过滤参数 |

**相关代码**：

- Claude executor: `agents_hub/agent_bridge/executors/claude.py`、`agents_hub/agent_bridge/executors/docker_claude.py`
- 配置定义: `agents_hub/roles/models.py`（`disabled_tools` 字段）
- 初始化: `agents_hub/bootstrap.py`（`MANAGER_DISABLED_TOOLS`、`ASSISTANT_ENABLED_TOOLS`）
- Worker 自动禁用: `agents_hub/roles/role_manager.py`（`WORKER_DISABLED_TOOLS`，Leader 专属工具不对 Worker 开放）

**为什么只做了 Claude**：只有 Claude CLI 提供 `--disallowedTools` 参数。`--allowedTools`（白名单）经调研无法阻止 sub-agent 调用，不可靠，因此采用黑名单方案。Codex 和 OpenCode 的 `RoleConfig.disabled_tools` 字段虽然存在，但在 executor 的 `_build_command` 中完全被忽略。

**API 层处理**：前端发送 `enabled_tools`（白名单），后端在 `agents_hub/api/services/role_service.py` 通过取反计算出 `disabled_tools` 存储。
