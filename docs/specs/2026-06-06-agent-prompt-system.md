---
version: 1.2
created_at: 2026-06-06
updated_at: 2026-06-16
last_updated: Runtime 注入机制重写（移至 user message）、XML 结构修正、Task 闭环提醒标注 deprecated
abstract: Agent 提示词系统规格，定义发送给 Agent 的所有提示词来源、注入机制、渲染规则和平台标识
id: spec-agent-prompt-system
title: Agent 提示词系统规格
status: draft
module: core/agent, core/foundation, core/orchestration
source_spec: null
related_plan: null
code_scope:
  - agents_hub/core/agent/base_agent.py
  - agents_hub/core/agent/manager.py
  - agents_hub/core/agent/worker.py
  - agents_hub/core/foundation/renderer.py
  - agents_hub/core/orchestration/group_chat.py
  - agents_hub/core/context/agent_context.py
contract_refs:
  - agents_hub/core/foundation/renderer.py
  - agents_hub/core/agent/base_agent.py
---

# Agent 提示词系统规格

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |
| 1.1 | `<AGENT_RUNTIME>` 新增 `<pinned_messages>` 区块，Pin 消息通过 runtime 注入而非 prompt 拼接 |
| 1.2 | AgentContext 按角色差异化交付（Worker 不接收 raw messages）；工具提示词重构为 ROLE_INSTRUCTIONS 类变量；收窄 report_progress 语义；新增阻塞判定规则 |

## Overview

Agent 提示词系统负责构造发送给 LLM 的所有输入。提示词有四个来源，按注入时机分为两类：

- **启动时加载**：CLAUDE.md / AGENTS.md 作为 system_prompt，由 CLI 自动读取
- **每条消息处理前动态注入**：工具使用说明写入 CLAUDE.md / AGENTS.md（`<TOOL_USAGE>` 标记）
- **每次执行时构造**：Runtime 信息、入站消息渲染、上下文拼接，三段拼接为 user message
- **定时/事件触发**：Heartbeat、Task 未闭环提醒（Task 未闭环提醒已 deprecated）

## Scope

### 范围内

- 提示词的四个来源及其触发时机
- `<runtime>` XML 内容结构和 `build_user_prompt()` 三段拼接逻辑
- `<TOOL_USAGE>` 的内容结构（通过 system_prompt 加载）
- `render_for_llm` 的输出格式和平台标识
- AgentContext 上下文构造规则
- Heartbeat 提示词内容
- Manager 与 Worker 的提示词差异

### 范围外

- CLI 如何读取 CLAUDE.md 作为 system_prompt（属于 agent_bridge）
- Agent 的 LLM 调用实现（属于 agent_bridge）
- 提示词的具体措辞优化（属于运行时调优）

## Core Behavior

### 1. 提示词来源全景

Agent 收到的完整 prompt 由以下部分组成：

```
┌─────────────────────────────────────────────┐
│ System Prompt（CLI 自动加载 CLAUDE.md）       │
│  └─ <TOOL_USAGE>     工具使用说明              │
├─────────────────────────────────────────────┤
│ User Prompt（build_user_prompt 三段拼接）      │
│  ├─ <runtime>        身份/团队/任务/调用状态/Pin消息 │
│  ├─ <group_chat_history>  历史摘要            │
│  ├─ <recent_messages>     最近群聊消息        │
│  └─ <incoming_message>    当前入站消息         │
└─────────────────────────────────────────────┘
```

### 2. Runtime 信息构造（`<runtime>`）

**触发时机**：Agent 处理每条 MAIN 会话消息时，作为 `build_user_prompt()` 的第一段。

**构造机制**：通过 `_build_runtime()` 构造 XML 字符串，作为 user message 的一部分传给 LLM。不再注入到 CLAUDE.md / AGENTS.md 文件。

**内容结构**：

| 区块 | 条件 | 内容 |
|------|------|------|
| `<type>` | 始终 | 会话类型（群聊/单聊） |
| `<agent_token>` | 始终 | Agent 身份令牌 |
| `<group_chat_id>` | 始终 | 当前群聊 ID |
| `<team_members>` | 始终 | 团队成员列表（排除自己，带 description） |
| `<agent_call>` | 始终 | 当前消息的 call 信息（call_id、from、content_head、need_response） |
| `<team_workboard>` | 仅 Manager + task_manager 存在 | 当前任务列表及状态 |
| `<user_pin_message>` | 有 Pin 消息时 | 用户置顶的重要消息，按 pinned_at 升序排列 |

**`<agent_call>` 语义说明**：该区块描述的是当前正在处理的这条消息的调用信息，而非多个待处理的调用列表。属性包含 `call_id`、`from`（调用来源）、`content_head`（请求内容前 20 字）、`need_response`（TASK 类型为 true，其余为 false）。

### 3. 工具使用说明（`<TOOL_USAGE>`）

**注入机制**：`_inject_tool_usage_to_files()` 已 deprecated。`<TOOL_USAGE>` 通过 CLI 自动读取 CLAUDE.md / AGENTS.md 作为 system_prompt 的一部分传递给 LLM。

**架构**：工具提示词通过子类 `ROLE_INSTRUCTIONS` 类变量定义，基类 `Agent.SHARED_RULES` 定义共享规则，`_generate_tool_usage_content()` 只做编排拼接。

| 类 | 变量 | 内容 |
|------|------|------|
| `Manager` | `ROLE_INSTRUCTIONS` | 工具列表、工作流程、派活要求、阻塞处理流程 |
| `Worker` | `ROLE_INSTRUCTIONS` | 工具列表、工作流程、阻塞判定规则、回报要求 |
| `Agent` | `SHARED_RULES` | 群聊消息显示规则 |

**角色差异**：

| 角色 | 工具范围 |
|------|---------|
| Manager | 全部 6 个工具：call_agent、assign_tasks_to_team、archive_task_list、check_agent_call、report_progress、complete_task |
| Worker | 2 个工具：report_progress、complete_task |

**工具语义**：

| 工具 | 用途 |
|------|------|
| report_progress | 任务汇报，让 user 和 manager 知道当前进展 |
| complete_task | 闭环 AgentCall，汇报成果（成功/失败/阻塞） |

**complete_task 的角色差异说明**：

| 角色 | 何时闭环 | 说明 |
|------|---------|------|
| Manager | 安排完任务后立即闭环 | 不需要等待 Worker 执行结果，Worker 完成后会通过新的 AgentCall 重新激活 |
| Worker | 完成实际工作后闭环 | Worker 不委派，闭环即表示工作完成 |

**Worker 阻塞判定规则**：

遇到以下情况，Worker 用 complete_task 标记失败（success=false）：

| 类型 | 判断标准 |
|------|----------|
| 跨模块依赖 | 问题涉及其他模块且改动范围超出当前任务边界（小 bug 直接修） |
| 对外接口不明 | 需要暴露的接口、关键数据模型与其他模块未对齐 |
| 需求冲突 | 任务要求与现有代码逻辑矛盾，修改会影响其他模块 |
| 执行路径需协调 | 方案选择会影响其他并行任务（如 schema 变更、公共配置修改） |

核心原则：阻塞只针对影响范围超出任务边界的情况，内部实现细节自行判断。

**Manager 阻塞处理流程**：

Worker 报告阻塞时，Manager 根据情况处理：
1. 自己能判断的，直接决策并重新派活
2. 需要专业判断的（需求澄清、架构决策），派给群里对应的专业成员
3. 都无法解决的，向 user 汇报

两个角色均需说明：忘记闭环会被系统自动停止，如果之前忘记调用需要立即补一个。

### 4. 入站消息渲染（`render_for_llm`）

**触发时机**：Agent 处理每条消息时。

**输出格式**：

```xml
<incoming_message>
[Agents Hub 平台消息]
call_id: {call_id}
来自：{send_from}
发送给：{send_to}（你）
类型：{message_type}
内容：{content}

[附件]
- {file_name} ({file_type}, {file_size}B): {absolute_file_path}
</incoming_message>
```

**附件**：仅当消息携带附件（`msg.files` 非空）时才输出 `[附件]` 区块。

**平台标识**：`[Agents Hub 平台消息]` 用于让 Agent 识别消息来源平台，与 MCP 工具对应。

**约束**：`msg.content` 在 Agent 之间投递时始终是原始内容，渲染只发生在 LLM 出口。

### 5. 上下文构造（AgentContext）

**触发时机**：Agent 处理 MAIN 会话消息时。

**角色差异化交付**：

| 角色 | compact history | raw messages |
|------|----------------|-------------|
| Manager | 接收 | 接收（增量，过滤自己和 @ 自己的） |
| Worker | 接收 | 不接收 |

Worker 不接收 raw messages，因为 Worker 的工作模式是「接任务 → 执行 → 报告」，通过 AgentMessage.content 已经拿到任务详情，compact history 提供团队进展摘要。无论角色，都更新 `last_loaded_message_index` 避免积压。

**内容结构**：

| 区块 | 条件 | 内容 |
|------|------|------|
| `<group_chat_history>` | 有新压缩历史时 | 压缩历史摘要，含 `<overall_summary>`（全体）和 `<summary_for_you>`（针对当前 Agent） |
| `<recent_messages>` | 仅 Manager + 有新消息时 | 最近群聊消息列表，格式为 `[发送者]: 内容` |

**过滤规则**（仅 Manager）：
- 排除自己发送的消息
- 排除 @ 自己的消息（已在 incoming_message 中）

**拼接方式**：`build_user_prompt()` 按顺序拼接三段，用 `"\n\n"` 分隔：runtime（`_build_runtime()`） + context（`get_context()`） + incoming_message（`render_for_llm(msg)`）

### 6. Heartbeat 提示词

**触发条件**：每 20 分钟定时发给 Manager。

**正常心跳**：
```
[Heartbeat] 定时检查：请查看当前任务进度。
```

**有 Worker 停止时**：
```
[Heartbeat] 以下成员已因连续执行失败自动停止: {成员列表}。
当前没有自动重启机制，请通过 report_progress 向 user 说明情况。
```

**消息属性**：消息类型为 `NOTIFICATION`，不触发 Task 未闭环提醒。

### 7. Task 未闭环提醒（deprecated）

> **已废弃**：`_needs_complete_task_reminder()` 和 `_enqueue_complete_task_reminder()` 均标记为 deprecated，相关逻辑在 `_run_loop()` 中已注释。当前由 `_fallback_close_task()` 兜底处理未闭环的 TASK。

**触发条件**：Agent 处理 TASK 类型消息后未调用 `complete_task` 闭环。

**基础提醒内容**：
```
系统提醒：你刚刚处理了来自 [{send_from}] 的 TASK 调用（call_id={call_id}），
原始请求：{content 截断 100 字}。
该调用尚未闭环，请调用 complete_task，传入对应的 call_id，
并用 content 说明任务完成、失败或无法继续的结果。
```

**Manager 额外说明**：
```
你可以在安排完任务后立即闭环，无需等待 Worker 执行结果。
如果忘记调用，请立即补一个。连续未闭环会被系统自动停止。
```

**自动停止机制**：连续未闭环次数达到阈值（默认 30 次）时，Agent 自动停止。

### 8. 消息格式化（`render_for_chat`）

**用途**：Agent 输出写入群聊记录时格式化。

**格式**：`@{send_to} {content}`

**去重规则**：如果消息已以 `@{send_to}` 开头，则不重复添加。

## Technical Contract

### 提示词构造层次

| 层次 | 构造内容 | 目标 |
|------|---------|------|
| System Prompt | CLI 自动加载 CLAUDE.md / AGENTS.md（含 `<TOOL_USAGE>`） | LLM system message |
| User Prompt | `build_user_prompt()` 三段拼接：`<runtime>` + 上下文 + `<incoming_message>` | LLM user message |

### Runtime 构造

`_build_runtime()` 输出 `<runtime>` XML，包含：`<type>`、`<agent_token>`、`<group_chat_id>`、`<team_members>`、`<agent_call>`、`<team_workboard>`（仅 Manager）、`<user_pin_message>`（有 Pin 时）。

`build_user_prompt()` 按顺序拼接：runtime + context + incoming_message，用 `"\n\n"` 分隔。

### 渲染函数职责

| 函数 | 输出 | 用途 |
|------|------|------|
| `render_for_llm` | `<incoming_message>` XML | 喂给 LLM 的 user prompt 片段 |
| `render_for_chat` | `@xxx content` | 写入群聊记录 |

### 触发时机汇总

| 提示词类型 | 触发时机 | 目标 |
|-----------|---------|------|
| `<TOOL_USAGE>` | 启动时加载 | CLAUDE.md / AGENTS.md（system_prompt） |
| `<runtime>` | MAIN 会话消息处理时 | LLM user message（第一段） |
| `<incoming_message>` | 每条消息处理时 | LLM user message（末段） |
| AgentContext | MAIN 会话消息处理时 | LLM user message（中间段） |
| Heartbeat | 每 20 分钟 | Manager 消息队列 |
| Task 未闭环提醒 | deprecated | — |

## Acceptance Notes

- Manager 和 Worker 的 ROLE_INSTRUCTIONS 内容必须有差异
- render_for_llm 输出必须包含 `[Agents Hub 平台消息]` 标识、`call_id` 和 `类型`
- Worker 的 AgentContext 不得包含 `<recent_messages>`
- Worker 的 ROLE_INSTRUCTIONS 必须包含阻塞判定规则
- Manager 的 ROLE_INSTRUCTIONS 必须包含阻塞处理流程
- `build_user_prompt()` 必须按 runtime + context + incoming_message 顺序拼接
- `<agent_call>` 描述的是当前消息的调用信息，不是待处理列表

## Out of Spec

- CLI 如何从 CLAUDE.md 读取 system_prompt（属于 agent_bridge）
- 提示词的具体措辞和 prompt engineering 技巧
- Agent 的 LLM 调用参数和模型选择
- 上下文压缩的具体算法（属于 core/context）
- Task 未闭环提醒的具体实现（已 deprecated）
