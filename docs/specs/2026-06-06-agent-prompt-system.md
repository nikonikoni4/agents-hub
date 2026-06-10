---
version: 1.0
created_at: 2026-06-06
updated_at: 2026-06-08
last_updated: AgentContext 差异化交付、ROLE_INSTRUCTIONS 重构、阻塞判定规则
abstract: Agent 提示词系统规格，定义发送给 Agent 的所有提示词来源、注入机制、渲染规则和平台标识
id: spec-agent-prompt-system
title: Agent 提示词系统规格
status: draft
module: core/agent, core/foundation, core/orchestration
sourc_spec: null
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
| 1.2 | AgentContext 按角色差异化交付（Worker 不接收 raw messages）；工具提示词重构为 ROLE_INSTRUCTIONS 类变量；收窄 speak_in_group_chat 语义；新增阻塞判定规则 |

## Overview

Agent 提示词系统负责构造发送给 LLM 的所有输入。提示词有四个来源，按注入时机分为两类：

- **启动时加载**：CLAUDE.md / AGENTS.md 作为 system_prompt，由 CLI 自动读取
- **每条消息处理前动态注入**：Runtime 信息和工具使用说明写入 CLAUDE.md / AGENTS.md
- **每次执行时构造**：入站消息渲染、上下文拼接
- **定时/事件触发**：Heartbeat、Task 未闭环提醒

## Scope

### 范围内

- 提示词的四个来源及其触发时机
- `<AGENT_RUNTIME>` 和 `<TOOL_USAGE>` 的注入机制和内容结构
- `render_for_llm` 的输出格式和平台标识
- AgentContext 上下文构造规则
- Heartbeat 和 Task 未闭环提醒的提示词内容
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
│  ├─ <AGENT_RUNTIME>  身份/团队/任务/调用状态/Pin消息 │
│  └─ <TOOL_USAGE>     工具使用说明              │
├─────────────────────────────────────────────┤
│ User Prompt（代码构造后传给 CLI）              │
│  ├─ <group_chat_history>  历史摘要            │
│  ├─ <recent_messages>     最近群聊消息        │
│  └─ <incoming_message>    当前入站消息         │
└─────────────────────────────────────────────┘
```

### 2. Runtime 注入（`<AGENT_RUNTIME>`）

**触发时机**：Agent 从队列取出每条消息时，在 `run()` 循环中调用。

**注入目标**：`work_root/CLAUDE.md` 和 `work_root/AGENTS.md` 的 `<AGENT_RUNTIME>` 标记。

**注入机制**：使用 `markdown_injector.replace_marked_section` 替换标记之间的内容，保证幂等。

**内容结构**：

| 区块 | 条件 | 内容 |
|------|------|------|
| `<identity>` | 始终 | Agent 名字、群聊 ID、身份令牌 |
| `<team>` | 始终 | 团队成员列表（排除自己）、前端用户名、user 不可调用提示 |
| `<team_workboard>` | 仅 Manager + task_manager 存在 | 当前任务列表及状态 |
| `<active_agent_calls>` | 有待处理 AgentCall 时 | call_id、来源、类型、状态、请求内容 |
| `<pinned_messages>` | 有 Pin 消息时 | 用户置顶的重要消息，按 pinned_at 升序排列 |

### 3. 工具使用说明注入（`<TOOL_USAGE>`）

**触发时机**：与 Runtime 注入相同，在 `run()` 循环中调用。

**注入目标**：`work_root/CLAUDE.md` 和 `work_root/AGENTS.md` 的 `<TOOL_USAGE>` 标记。

**架构**：工具提示词通过子类 `ROLE_INSTRUCTIONS` 类变量定义，基类 `Agent.SHARED_RULES` 定义共享规则，`_generate_tool_usage_content()` 只做编排拼接。

| 类 | 变量 | 内容 |
|------|------|------|
| `Manager` | `ROLE_INSTRUCTIONS` | 工具列表、工作流程、派活要求、阻塞处理流程 |
| `Worker` | `ROLE_INSTRUCTIONS` | 工具列表、工作流程、阻塞判定规则、回报要求 |
| `Agent` | `SHARED_RULES` | 群聊消息显示规则 |

**角色差异**：

| 角色 | 工具范围 |
|------|---------|
| Manager | 全部 6 个工具：call_agent、assign_tasks_to_team、archive_task_list、check_agent_call、speak_in_group_chat、complete_task |
| Worker | 2 个工具：speak_in_group_chat、complete_task |

**工具语义**：

| 工具 | 用途 |
|------|------|
| speak_in_group_chat | 任务汇报，让 user 和 manager 知道当前进展 |
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
来自：{send_from}
发送给：{send_to}（你）
内容：{content}
</incoming_message>
```

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

**拼接方式**：`full_prompt = history + "\n" + render_for_llm(msg)`

### 6. Heartbeat 提示词

**触发条件**：每 20 分钟定时发给 Manager。

**正常心跳**：
```
[Heartbeat] 定时检查：请查看当前任务进度。
```

**有 Worker 停止时**：
```
[Heartbeat] 以下成员已因连续执行失败自动停止: {成员列表}。
当前没有自动重启机制，请通过 speak_in_group_chat 向 user 说明情况。
```

**消息属性**：消息类型为 `NOTIFICATION`，不触发 Task 未闭环提醒。

### 7. Task 未闭环提醒

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

### 注入标记

| 标记 | 内容 | 注入位置 |
|------|------|---------|
| `<AGENT_RUNTIME>` | 身份、团队、任务、调用状态 | CLAUDE.md, AGENTS.md |
| `<TOOL_USAGE>` | 工具使用说明 | CLAUDE.md, AGENTS.md |

### 渲染函数职责

| 函数 | 输入 | 输出 | 用途 |
|------|------|------|------|
| `render_for_llm` | AgentMessage | `<incoming_message>` XML | 喂给 LLM 的 prompt |
| `render_for_chat` | send_from, send_to, content | `@xxx content` | 写入群聊记录 |

### 触发时机汇总

| 提示词类型 | 触发时机 | 目标 |
|-----------|---------|------|
| AGENT_RUNTIME 注入 | 每条消息处理前 | CLAUDE.md / AGENTS.md |
| TOOL_USAGE 注入 | 每条消息处理前 | CLAUDE.md / AGENTS.md |
| render_for_llm | 每条消息处理时 | LLM prompt |
| AgentContext | MAIN 会话消息处理时 | LLM prompt |
| Heartbeat | 每 20 分钟 | Manager 消息队列 |
| Task 未闭环提醒 | TASK 消息未闭环时 | Agent 自身消息队列 |

## Acceptance Notes

- 注入函数必须幂等：多次注入不会产生重复的标记块
- Manager 和 Worker 的 ROLE_INSTRUCTIONS 内容必须有差异
- render_for_llm 输出必须包含 `[Agents Hub 平台消息]` 标识
- Task 未闭环提醒必须包含 call_id 和原始请求摘要
- Manager 的 complete_task 说明必须强调"安排后即可闭环"
- Worker 的 AgentContext 不得包含 `<recent_messages>`
- Worker 的 ROLE_INSTRUCTIONS 必须包含阻塞判定规则
- Manager 的 ROLE_INSTRUCTIONS 必须包含阻塞处理流程

## Out of Spec

- CLI 如何从 CLAUDE.md 读取 system_prompt（属于 agent_bridge）
- 提示词的具体措辞和 prompt engineering 技巧
- Agent 的 LLM 调用参数和模型选择
- 上下文压缩的具体算法（属于 core/context）
