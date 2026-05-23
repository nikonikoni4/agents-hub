---
version: 1.0
created_at: 2026-05-23
updated_at: 2026-05-24
last_updated: RoleConfig 增加 claude_config_dir，移除留白字段
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
  - agents_hub/agent_bridge/parsers/base.py
  - agents_hub/agent_bridge/protocols.py
  - agents_hub/agent_bridge/config.py
---

# Agent Bridge 模块规格

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 从设计文档过滤生成正式 spec 初稿 |
| 1.1 | RoleConfig 增加 claude_config_dir，移除留白字段（permissions、tools） |

---

## Overview

agent_bridge 是 agents-hub 系统的**纯执行层模块**，负责调用不同 AI 平台的 CLI 工具（Claude Code、Codex），并将各平台的原始输出解析为统一格式。

模块定位：
- **负责**：启动 CLI 进程、解析原始输出、提供统一调用接口
- **不负责**：业务逻辑、会话持久化、错误重试（留白）

## Scope

### 范围内

- 多平台 CLI 调用的统一抽象
- 流式/非流式双接口
- 统一事件格式定义与解析
- 角色配置管理（platform、system_prompt、skills）
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
  → Parser 逐行解析为统一 AgentEvent
  → yield 给调用方
```

### 双接口设计

模块提供两种调用接口，底层共享同一套流式解析逻辑：

| 接口 | 用途 | 返回方式 |
|------|------|---------|
| `execute_stream()` | 人机交互场景（实时显示） | 逐事件 yield |
| `execute()` | A2A 调用场景（主 Agent 调用子 Agent） | 拼接所有文本后返回单个 RESULT 事件 |

`execute()` 是 `execute_stream()` 的薄包装，内部拼接所有 `text_delta` 事件文本，收集 `usage` 统计，最终返回一个 `RESULT` 类型事件。

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
| `platform` | AgentPlatform | 是 | 目标平台类型 |
| `system_prompt` | str | 是 | 系统提示词内容 |
| `skills` | list[str] | 是 | skill 标识列表 |
| `codex_home` | str? | 否 | Codex 专用配置目录路径（注入 `CODEX_HOME` 环境变量） |
| `claude_config_dir` | str? | 否 | Claude 专用配置目录路径（注入 `CLAUDE_CONFIG_DIR` 环境变量） |

### 统一事件格式（AgentEvent）

所有平台的输出统一转换为以下事件结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | AgentEventType | 事件类型 |
| `data` | dict | 事件数据 |
| `session_id` | str | 会话标识 |
| `timestamp` | str | 时间戳 |

### 事件类型（AgentEventType）

| 类型 | 含义 | data 内容 |
|------|------|----------|
| `INIT` | 会话开始元数据 | `model`、`tools` 等平台信息 |
| `TEXT_DELTA` | 文本增量（流式主要内容） | `text` |
| `TOOL_USE` | 工具调用 | `command`、`output`、`exit_code`、`status` |
| `TURN_COMPLETE` | 回合完成 | `usage`（token 统计） |
| `RESULT` | 完整结果（非流式返回） | `text`（拼接后全文）、`usage` |

### 协议接口

模块通过 Protocol 定义两个核心接口契约：

- **Executor 协议**：接收 prompt、config、session_id，返回原始 JSON 字符串的异步迭代器
- **Parser 协议**：接收单行原始 JSON 字符串，返回可选的统一 AgentEvent

### CLI 命令参数

#### Claude CLI

核心参数：`--print`（非交互）、`--verbose`（详细输出）、`--output-format stream-json`（流式 JSON）、`--include-partial-messages`（逐字输出）、`--append-system-prompt`（追加系统提示词）

会话恢复：`--resume <session_id>`

环境变量：通过 `CLAUDE_CONFIG_DIR` 指定角色配置目录

#### Codex CLI

核心参数：`exec`（执行命令）、`--json`（JSON 输出）

会话恢复：`exec resume --json <session_id>`

环境变量：通过 `CODEX_HOME` 指定角色配置目录

## Acceptance Notes

1. 支持 Claude 和 Codex 两个平台的 CLI 调用
2. 流式输出能逐事件返回给调用方
3. 非流式输出能正确拼接完整文本
4. session_id 能从返回事件中正确提取
5. 恢复会话时能正确传递 session_id 给 CLI
6. Parser 能正确忽略无法解析的原始行（返回 None）
7. Executor 和 Parser 均可独立测试

## Out of Spec

以下内容不在本 spec 中长期维护：

1. **CLI 命令的完整参数列表**：仅记录核心参数，具体参数随 CLI 版本变化
2. **错误处理与重试策略**：当前为留白，后续单独定义
3. **性能优化方案**：连接池、缓存、并发控制等
4. **动态配置变更机制**：配置当前固定，作为参数传入
5. **具体的代码实现**：函数签名、类名、变量名、目录结构等
