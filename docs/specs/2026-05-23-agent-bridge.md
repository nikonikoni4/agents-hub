---
version: 1.3
created_at: 2026-05-23
updated_at: 2026-05-31
last_updated: AgentBridge 初始化时创建 bare 角色并缓存配置，新增 bare_claude_call() 快速调用接口
abstract: agent_bridge 模块的正式规格定义，描述其作为纯执行层的核心职责、统一事件契约和双接口设计
id: spec-agent-bridge
title: Agent Bridge 模块规格
status: draft
module: agent_bridge
sourc_spec: docs/superpowers/specs/2026-05-23-agent-bridge-design.md
related_plan: null
code_scope:
  - agents_hub/agent_bridge/
contract_refs:
  - agents_hub/agent_bridge/models.py
  - agents_hub/agent_bridge/protocols.py
  - agents_hub/agent_bridge/exceptions.py
  - agents_hub/roles/models.py
  - agents_hub/roles/role_manager.py
---

# Agent Bridge 模块规格

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 从设计文档过滤生成正式 spec 初稿 |
| 1.1 | RoleConfig 增加 claude_config_dir，移除留白字段（permissions、tools） |
| 1.2 | RoleConfig 统一为 work_root，新增 description/role_type/bare；StreamEvent 增加 agent_name/platform/role_type；execute() 返回 AgentResult |
| 1.3 | AgentBridge 初始化时通过 RoleManager 创建 bare 角色并缓存 RoleConfig；新增 bare_claude_call() 接口 |

---

## Overview

agent_bridge 是 agents-hub 系统的**纯执行层模块**，负责调用不同 AI 平台的 CLI 工具（Claude Code、Codex），并将各平台的原始输出解析为统一格式。

模块定位：
- **负责**：启动 CLI 进程、解析原始输出、提供统一调用接口
- **不负责**：业务逻辑、会话持久化、自动错误重试（异常已定义，重试机制留白）

## Scope

### 范围内

- 多平台 CLI 调用的统一抽象
- 流式/非流式/bare 三种接口
- 统一事件格式定义与解析
- 角色配置管理（platform、work_root、role_type）
- bare 角色的初始化与配置缓存
- 会话 ID 的传递与返回

### 范围外

- 会话持久化存储
- 错误重试与恢复机制
- 动态配置变更
- 业务层逻辑（任务管理、权限控制）

## Core Behavior

### 架构模式：扁平化组合

模块采用**执行器-解析器分离**的扁平化架构，通过组合而非继承实现功能复用：

- **Executor（执行器）**：构建 CLI 命令、启动子进程、返回原始输出流
- **Parser（解析器）**：解析原始 JSON 输出、转换为统一事件格式
- **Bridge（桥接器）**：根据平台类型选择对应的 Executor 和 Parser，组装完整流程

每个平台各有一个 Executor 和一个 Parser，新增平台只需添加这两个组件并注册到 Bridge。

### 数据流

```
用户调用 → Bridge.execute_stream()
  → 根据 platform 选择 Executor + Parser
  → Executor 启动 CLI 子进程，返回原始 JSON 流
  → Parser 逐行解析为统一 StreamEvent
  → yield 给调用方
```

### 初始化

`AgentBridge` 在 `__init__` 时完成以下初始化：

1. 创建 Claude/Codex 的 Executor 和 Parser 实例（可复用）
2. 创建 `RoleManager` 实例
3. 通过 `_init_bare_config()` 获取或创建 `bare_claude` 角色，读取其 `RoleConfig` 并设置 `bare=True`，缓存到 `self._bare_config`

bare 角色仅在首次调用时创建（`RoleManager.create_role()`），后续初始化直接复用已有角色（`RoleManager.get_role()`）。配置缓存在实例中，`bare_claude_call()` 直接使用缓存，无文件 I/O。

### 接口设计

模块提供三种调用接口，底层共享同一套流式解析逻辑：

| 接口 | 用途 | 返回方式 |
|------|------|---------|
| `execute_stream()` | 人机交互场景（实时显示） | 逐事件 yield StreamEvent |
| `execute()` | A2A 调用场景（主 Agent 调用子 Agent） | 返回 AgentResult 数据对象 |
| `bare_claude_call()` | 内部快速 LLM 调用（不涉及角色业务） | 返回 AgentResult 数据对象 |

`execute()` 是 `execute_stream()` 的薄包装，内部拼接所有 `text_delta` 事件文本，收集 `usage` 统计，最终返回一个 `AgentResult` 对象。

`bare_claude_call()` 是 `execute()` 的薄包装，使用初始化时缓存的 bare 角色配置（`bare=True`），适用于一次性快速 LLM 调用场景。角色在 `__init__` 时通过 `RoleManager` 创建或获取，配置缓存在实例中，避免每次调用的文件 I/O。

### 会话管理

- **新建会话**：不传 `session_id`，CLI 工具自动生成
- **恢复会话**：传入已有 `session_id`，CLI 工具恢复对应会话
- **session_id 获取**：从返回事件中读取，调用方在首次调用完成后记录

## Technical Contract

### 平台枚举

支持的 AI 平台：
- `CLAUDE` - Claude Code CLI
- `CODEX` - Codex CLI

### 角色配置（RoleConfig）

调用时需传入的角色配置包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | str | 是 | 角色名称，用于标识和事件填充 |
| `platform` | AgentPlatform | 是 | 目标平台类型 |
| `description` | str? | 否 | 角色职责描述 |
| `work_root` | str? | 否 | 角色工作目录路径，注入 `CLAUDE_CONFIG_DIR` 或 `CODEX_HOME` 环境变量 |
| `role_type` | RoleType | 是 | 角色类型（leader / team_member），默认 team_member |
| `bare` | bool | 否 | Claude CLI 极简模式：跳过 hooks/LSP/plugin sync/auto-memory/CLAUDE.md 自动发现 |

**注**：`system_prompt` 和 `skills` 不在 RoleConfig 中——由 CLI 从角色目录自动加载（Claude 从 `CLAUDE.md`，Codex 从 `AGENTS.md`；skills 从 `work_root/skills/`）。`work_root` 同时作为环境变量注入源（Claude → `CLAUDE_CONFIG_DIR`，Codex → `CODEX_HOME`）。

### 统一事件格式（StreamEvent）

所有平台的输出统一转换为以下事件结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | AgentEventType | 事件类型 |
| `content` | dict | 事件数据（文本、工具调用、usage 等） |
| `session_id` | str | 会话标识 |
| `timestamp` | str | 时间戳 |
| `agent_name` | str | 当前 agent 名称（由 Bridge 从 RoleConfig 填充） |
| `platform` | AgentPlatform | agent 所属平台（由 Bridge 从 RoleConfig 填充） |
| `role_type` | RoleType | 角色类型（由 Bridge 从 RoleConfig 填充） |

### 事件类型（AgentEventType）

| 类型 | 含义 | content 内容 |
|------|------|----------|
| `INIT` | 会话开始元数据 | `model`、`tools` 等平台信息 |
| `TEXT_DELTA` | 文本增量（流式主要内容） | `text` |
| `TOOL_USE` | 工具调用 | `command`、`output`、`exit_code`、`status` |
| `TURN_COMPLETE` | 回合完成 | `usage`（token 统计） |

**注**：`execute()` 不使用 `RESULT` 事件类型，而是直接返回 `AgentResult` 数据对象。

### 完整结果格式（AgentResult）

`execute()` 的返回值结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | str | 拼接后的完整文本 |
| `session_id` | str | 会话标识 |
| `timestamp` | str | 时间戳 |
| `agent_name` | str | agent 名称 |
| `platform` | AgentPlatform | 平台类型 |
| `role_type` | RoleType | 角色类型 |
| `usage` | dict? | token 使用统计 |
| `cwd` | str? | Agent 工作目录（绝对路径） |
| `modified_files` | FileMetadata[]? | 修改的文件列表元数据 |
| `git_diff_range` | str? | Git diff 范围（格式：start..end） |

#### FileMetadata 类型

`modified_files` 数组中每个元素的结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| `path` | str | 文件路径 |
| `status` | str | 文件状态（如 modified、added、deleted） |
| `additions` | int | 新增行数 |
| `deletions` | int | 删除行数 |
| `snapshot_id` | str | 快照 ID |
| `diff_available` | bool | 是否有可用的 diff |
| `diff_error` | str? | diff 获取错误信息 |

### 协议接口

模块通过 Protocol 定义两个核心接口契约：

- **Executor 协议**：接收 prompt、config（RoleConfig）、session_id，返回原始 JSON 字符串的异步迭代器
- **Parser 协议**：接收单行原始 JSON 字符串，返回可选的统一 StreamEvent

### CLI 命令参数

#### Claude CLI

核心参数：`--print`（非交互）、`--verbose`（详细输出）、`--output-format stream-json`（流式 JSON）、`--include-partial-messages`（逐字输出）

极简模式：`--bare`（跳过 hooks/LSP/plugin sync/auto-memory/CLAUDE.md 自动发现）

会话恢复：`--resume <session_id>`

环境变量：通过 `CLAUDE_CONFIG_DIR`（取自 `RoleConfig.work_root`）指定角色配置目录。system_prompt 由 CLI 从 `CLAUDE.md` 自动加载，无需通过参数传递。

#### Codex CLI

核心参数：`exec`（执行命令）、`--json`（JSON 输出）

会话恢复：`exec resume --json <session_id>`

环境变量：通过 `CODEX_HOME`（取自 `RoleConfig.work_root`）指定角色配置目录。system_prompt 由 CLI 从 `AGENTS.md` 自动加载。

### 异常类型

| 异常 | 触发场景 | 继承关系 |
|------|----------|----------|
| CLINotFoundError | CLI 可执行文件不在 PATH 中 | AgentBridgeError |
| CLIExecutionError | CLI 进程返回非零退出码 | AgentBridgeError |
| ParseError | 无法解析 CLI 输出的 JSON | AgentBridgeError |
| PlatformNotSupportedError | 请求的平台类型不在已注册的 Executor 中 | ValidationError |
| AgentTimeoutError | Agent 执行超时（可恢复，建议重试） | AgentBridgeError, RecoverableError |

所有 `AgentBridgeError` 继承自 `ExternalServiceError`。

## Acceptance Notes

1. 支持 Claude 和 Codex 两个平台的 CLI 调用
2. 流式输出能逐事件返回给调用方
3. 非流式输出能正确拼接完整文本
4. session_id 能从返回事件中正确提取
5. 恢复会话时能正确传递 session_id 给 CLI
6. Parser 无法解析时抛出 ParseError，由 Bridge 捕获并跳过该行继续处理
7. Executor 和 Parser 均可独立测试
8. execute() 返回的 AgentResult 包含拼接文本、session_id 和 usage 统计
9. AgentBridge 初始化时自动创建或获取 bare_claude 角色，配置缓存在实例中
10. bare_claude_call() 使用缓存的 bare 配置调用 execute()，无额外文件 I/O

## Out of Spec

以下内容不在本 spec 中长期维护：

1. **CLI 命令的完整参数列表**：仅记录核心参数，具体参数随 CLI 版本变化
2. **错误重试策略**：异常类型已定义，但自动重试机制留白
3. **性能优化方案**：连接池、缓存、并发控制等
4. **动态配置变更机制**：配置当前固定，作为参数传入
5. **具体的代码实现**：函数签名、类名、变量名、目录结构等
