---
version: 2.1
created_at: 2026-05-23
updated_at: 2026-06-24
last_updated: 新增首响支持：FIRST_RESPONSE 事件、execute_with_first_response 接口、FirstResponseResult 数据类
abstract: agent_bridge 模块的规格定义，描述其作为纯执行层的核心职责、统一事件契约和多接口设计
id: spec-agent-bridge
title: Agent Bridge 模块规格
status: draft
module: agent_bridge
source_spec: docs/superpowers/specs/2026-05-23-agent-bridge-design.md
code_scope:
  - agents_hub/agent_bridge/
  - agents_hub/roles/
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
| 2.0 | 按照新 spec 规则重构，移除执行细节，添加 Design Rationale 和 key_function 标签 |
| 2.1 | 新增首响支持：FIRST_RESPONSE 事件、execute_with_first_response 接口、FirstResponseResult 数据类 |

---

## Overview

**业务问题**：agents-hub 系统需要调用不同 AI 平台的 CLI 工具（Claude Code、Codex），各平台的命令格式、输出格式、会话管理方式各不相同，上层模块需要一个统一的调用接口。

**核心职责**：agent_bridge 是系统的**纯执行层模块**，负责：
- 封装多平台 CLI 调用的差异，提供统一的调用接口
- 将各平台的原始输出解析为统一事件格式
- 管理角色配置，支持 bare 模式的快速调用

**不负责**：业务逻辑、会话持久化、自动错误重试（异常已定义，重试机制留白）

## Scope

### 范围内

- 多平台 CLI 调用的统一抽象
- 流式/非流式/bare 三种调用接口
- 统一事件格式定义与解析
- 角色配置管理（platform、work_root、role_type、bare）
- 异常类型定义

### 范围外

- 会话持久化存储 → 参考会话管理相关 spec
- 错误重试与恢复机制 → 异常类型已定义，重试策略留白
- 动态配置变更 → 配置作为参数传入
- 业务层逻辑（任务管理、权限控制） → 参考业务层 spec

## Technical Contract

### 对外接口

<key_function last_update="2026-06-26T18:23:55+08:00">
- agents_hub/agent_bridge/bridge.py
  - bridge.AgentBridge.execute_stream:130
  - bridge.AgentBridge.execute:262
  - bridge.AgentBridge.execute_with_first_response:351
  - bridge.AgentBridge.bare_claude_call:458
- agents_hub/agent_bridge/models.py
  - models.StreamEvent
  - models.AgentResult
  - models.FirstResponseResult
  - models.AgentEventType:13
- agents_hub/roles/role_manager.py
  - role_manager.RoleManager.create_role:266
  - role_manager.RoleManager.get_role:211
</key_function>

**接口说明**：

| 接口 | 用途 | 返回方式 | 参数 |
|------|------|---------|------|
| `execute_stream()` | 人机交互场景（实时显示） | 逐事件 yield StreamEvent | prompt, config: RoleConfig, session_id? |
| `execute()` | A2A 调用场景（主 Agent 调用子 Agent） | 返回 AgentResult | prompt, config: RoleConfig, session_id? |
| `execute_with_first_response()` | 群聊场景（首句快速响应） | 返回 FirstResponseResult | prompt, config: RoleConfig, session_id?, cwd?, system_prompt? |
| `bare_claude_call()` | 内部快速 LLM 调用（不涉及角色业务） | 返回 AgentResult | prompt, session_id? |

**接口关系**：
- `execute()` 是 `execute_stream()` 的包装，内部拼接所有 `text_delta` 事件文本，收集 `usage` 统计
- `execute_with_first_response()` 是 `execute_stream()` 的包装，检测 `FIRST_RESPONSE` 事件，返回首句文本和完整结果
- `bare_claude_call()` 是 `execute()` 的包装，使用初始化时缓存的 bare 角色配置

### 平台枚举

支持的 AI 平台：
- `CLAUDE` - Claude Code CLI
- `CODEX` - Codex CLI

### 角色配置（RoleConfig）

调用时需传入的角色配置，完整定义见 `docs/specs/2026-05-24-agents-role.md` 的 RoleConfig 章节。

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
| `RESULT` | 完整结果（非流式输出） | 完整结果数据 |
| `FIRST_RESPONSE` | 首句完成（用于群聊首响） | 空 dict |

### 完整结果格式（AgentResult）

`execute()` 和 `bare_claude_call()` 的返回值结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | str | 拼接后的完整文本 |
| `session_id` | str | 会话标识 |
| `timestamp` | str | 时间戳 |
| `agent_name` | str | agent 名称 |
| `platform` | AgentPlatform | 平台类型 |
| `role_type` | RoleType | 角色类型 |
| `usage` | Usage? | token 使用统计 |
| `cwd` | str? | Agent 工作目录（绝对路径） |
| `modified_files` | FileMetadata[]? | 修改的文件列表元数据 |
| `git_diff_range` | str? | Git diff 范围（格式：start..end） |
| `permission_request` | dict? | 权限请求数据 |
| `web_preview` | dict? | 网页预览数据 `{"url": "...", "title": "..."}` |
| `files` | list[dict]? | 上传文件列表 |

### 首响结果格式（FirstResponseResult）

`execute_with_first_response()` 的返回值结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| `first_text` | str | 首句文本（可能为空，如纯工具调用或首句未检测到） |
| `result` | AgentResult | 完整结果（包含首句 + 剩余内容） |

**首句检测机制**：
- Claude：检测 `content_block_stop` 事件（text block 结束）
- Codex：检测 `item.completed` 事件（agent_message 完成）
- 纯工具调用（无文本）：`first_text` 为空字符串

#### FileMetadata 类型

| 字段 | 类型 | 说明 |
|------|------|------|
| `path` | str | 文件路径 |
| `status` | str | 文件状态（如 modified、added、deleted） |
| `additions` | int | 新增行数 |
| `deletions` | int | 删除行数 |
| `snapshot_id` | str | 快照 ID |
| `diff_available` | bool | 是否有可用的 diff |
| `diff_error` | str? | diff 获取错误信息 |

#### Usage 类型

| 字段 | 类型 | 说明 |
|------|------|------|
| `input_tokens` | int | 输入 token 数（默认 0） |
| `cache_read_input_tokens` | int | 缓存读取的输入 token 数（默认 0） |
| `max_context_window` | int | 模型最大上下文窗口（仅 Claude 提供，默认 0） |

### 协议接口

模块通过 Protocol 定义两个核心接口契约：

- **Executor 协议**：接收 prompt、config（RoleConfig）、session_id，返回原始 JSON 字符串的异步迭代器
- **Parser 协议**：接收单行原始 JSON 字符串，返回可选的统一 StreamEvent

### 异常类型

| 异常 | 触发场景 | 继承关系 |
|------|----------|----------|
| CLINotFoundError | CLI 可执行文件不在 PATH 中 | AgentBridgeError |
| CLIExecutionError | CLI 进程返回非零退出码 | AgentBridgeError |
| ParseError | 无法解析 CLI 输出的 JSON | AgentBridgeError |
| PlatformNotSupportedError | 请求的平台类型不在已注册的 Executor 中 | ValidationError |
| AgentTimeoutError | Agent 执行超时（可恢复，建议重试） | AgentBridgeError, RecoverableError |

所有 `AgentBridgeError` 继承自 `ExternalServiceError`。

## Design Rationale

**为什么采用执行器-解析器分离的架构？**
- 各平台 CLI 的命令格式和输出格式差异大，但都需要转换为统一事件
- 分离后每个平台只需实现 Executor（构建命令）和 Parser（解析输出），新增平台成本低
- Bridge 根据 platform 类型选择对应的 Executor 和 Parser，组装完整流程

**为什么需要 bare 模式？**
- 内部快速 LLM 调用场景不需要 hooks/LSP/plugin sync 等功能
- bare 模式跳过这些初始化，减少开销，提高响应速度
- 通过 `RoleConfig.bare` 字段控制，与角色配置统一管理

**为什么角色配置不在 RoleConfig 中包含 system_prompt 和 skills？**
- system_prompt 和 skills 由 CLI 从角色目录自动加载（Claude 从 `CLAUDE.md`，Codex 从 `AGENTS.md`）
- 这样配置文件与角色目录绑定，便于版本控制和独立管理
- `work_root` 同时作为环境变量注入源，统一了配置路径

**有哪些约束？**
- CLI 工具必须在 PATH 中可用，否则抛出 CLINotFoundError
- 会话恢复依赖 CLI 工具的 session_id 机制
- bare 模式仅适用于 Claude CLI

**有哪些已知限制？**
- 错误重试机制留白，当前异常类型已定义但未实现自动重试
- 性能优化（连接池、缓存、并发控制）未涉及
- 动态配置变更未支持，配置作为参数传入

**相关 ADR**：
- 参考 `docs/superpowers/specs/2026-05-23-agent-bridge-design.md` 获取原始设计文档

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **会话持久化**：会话管理相关 spec
- **业务层逻辑**：任务管理、权限控制等业务层 spec
- **CLI 命令完整参数**：仅记录核心参数，具体参数随 CLI 版本变化
- **具体实现细节**：函数签名、类名、变量名、目录结构等 → 参考 Flow 文档
