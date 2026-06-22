---
version: 2.0
created_at: 2026-06-06
updated_at: 2026-06-18
last_updated: 按新 spec 规则重构：移除执行细节，添加 key_function 和 Design Rationale
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
| 2.0 | 按新 spec 规则重构：移除执行细节，添加 key_function 和 Design Rationale |

## Overview

**业务问题**：Agent 系统需要将身份、团队、任务状态、工具规则等信息注入 LLM 的输入，不同角色（Manager/Worker）需要差异化的内容交付。提示词的来源分散、注入时机各异，需要统一的规格来约束各模块的职责边界。

**核心职责**：
- 定义提示词的四个来源（System Prompt、Runtime、Context、Heartbeat）及其触发时机
- 定义 `<runtime>` XML 的内容结构和 `build_user_prompt()` 的三段拼接规则
- 定义 `<TOOL_USAGE>` 的内容结构和角色差异化（Manager/Worker）
- 定义消息渲染格式（`render_for_llm` / `render_for_chat`）
- 定义 AgentContext 的角色差异化交付规则

## Scope

### 范围内

- 提示词的四个来源及其触发时机
- `<runtime>` XML 内容结构和 `build_user_prompt()` 三段拼接逻辑
- `<TOOL_USAGE>` 的内容结构（通过 system_prompt 加载）
- `render_for_llm` 的输出格式和平台标识
- AgentContext 上下文构造规则和角色差异化
- Heartbeat 提示词内容
- Manager 与 Worker 的提示词差异

### 范围外

- CLI 如何读取 CLAUDE.md 作为 system_prompt（属于 agent_bridge）
- Agent 的 LLM 调用实现（属于 agent_bridge）
- 提示词的具体措辞优化（属于运行时调优）
- 上下文压缩的具体算法（属于 core/context）

## Technical Contract

### 提示词构造层次

| 层次 | 构造内容 | 目标 |
|------|---------|------|
| System Prompt | CLI 自动加载 CLAUDE.md / AGENTS.md（含 `<TOOL_USAGE>`） | LLM system message |
| User Prompt | `build_user_prompt()` 三段拼接：`<runtime>` + 上下文 + `<incoming_message>` | LLM user message |

### 提示词来源全景

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

### 对外接口

<key_function last_update="2026-06-22T20:27:51+08:00">
- agents_hub/core/agent/base_agent.py
  - base_agent.Agent.SHARED_RULES:38
- agents_hub/core/agent/manager.py
  - manager.Manager.ROLE_INSTRUCTIONS:15
- agents_hub/core/agent/worker.py
  - worker.Worker.ROLE_INSTRUCTIONS:15
- agents_hub/core/foundation/renderer.py
  - renderer.render_for_llm:49
  - renderer.render_for_chat:69
- agents_hub/core/context/agent_context.py
  - agent_context.AgentContext.get_context:38
  - agent_context.AgentContext.build_user_prompt:180
</key_function>

| 接口 | 说明 | 约束 |
|------|------|------|
| `build_user_prompt(msg)` | 三段拼接构造 LLM user message | 按 runtime + context + incoming_message 顺序，`"\n\n"` 分隔 |
| `render_for_llm(msg)` | 将消息渲染为 `<incoming_message>` XML 片段 | 输出必须包含 `[Agents Hub 平台消息]` 标识、`call_id`、`类型` |
| `render_for_chat(send_from, send_to, content, is_loop_message?, loop_iteration?)` | 格式化消息写入群聊记录 | 非循环消息：`@{send_to} {content}`；循环消息：`[循环-节点{send_from}-第{loop_iteration}轮] @{send_to} {content}` |
| `SHARED_RULES` (Agent) | 共享规则类变量 | 群聊消息显示规则 |
| `ROLE_INSTRUCTIONS` (Manager) | Manager 工具指令类变量 | 工具列表、工作流程、派活要求、阻塞处理流程 |
| `ROLE_INSTRUCTIONS` (Worker) | Worker 工具指令类变量 | 工具列表、工作流程、阻塞判定规则、回报要求 |
| `AgentContext.get_context()` | 获取上下文区块（history + recent_messages） | 按角色差异化交付，见下方规则 |

### Runtime 信息结构（`<runtime>`）

`<runtime>` XML 作为 `build_user_prompt()` 的第一段，包含以下区块：

| 区块 | 条件 | 内容 |
|------|------|------|
| `<type>` | 始终 | 会话类型（群聊/单聊） |
| `<agent_token>` | 始终 | Agent 身份令牌 |
| `<group_chat_id>` | 始终 | 当前群聊 ID |
| `<team_members>` | 始终 | 团队成员列表（排除自己，带 description） |
| `<agent_call>` | 始终 | 当前消息的调用信息（call_id、from、content_head、need_response） |
| `<team_workboard>` | 仅 Manager + task_manager 存在 | 当前任务列表及状态 |
| `<user_pin_message>` | 有 Pin 消息时 | 用户置顶的重要消息，按 pinned_at 升序排列 |

**`<agent_call>` 语义约束**：描述的是当前正在处理的这条消息的调用信息，而非多个待处理的调用列表。

### 入站消息渲染格式（`render_for_llm`）

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

- `[附件]` 区块仅当消息携带附件（`msg.files` 非空）时输出
- `[Agents Hub 平台消息]` 用于让 Agent 识别消息来源平台
- `msg.content` 在 Agent 之间投递时始终是原始内容，渲染只发生在 LLM 出口

### 上下文构造规则（AgentContext）

**角色差异化交付**：

| 角色 | compact history | raw messages |
|------|----------------|-------------|
| Manager | 接收 | 接收（增量，过滤自己和 @ 自己的） |
| Worker | 接收 | 不接收 |

**上下文内容结构**：

| 区块 | 条件 | 内容 |
|------|------|------|
| `<group_chat_history>` | 有新压缩历史时 | 压缩历史摘要，含 `<overall_summary>`（全体）和 `<summary_for_you>`（针对当前 Agent） |
| `<recent_messages>` | 仅 Manager + 有新消息时 | 最近群聊消息列表，格式为 `[发送者]: 内容` |

**Manager 过滤规则**：排除自己发送的消息；排除 @ 自己的消息（已在 incoming_message 中）。

### 工具体系

**角色工具范围**：

| 角色 | 工具 |
|------|------|
| Manager | call_agent、assign_tasks_to_team、archive_task_list、check_agent_call、report_progress、complete_task |
| Worker | report_progress、complete_task |

**关键工具语义**：

| 工具 | 用途 | 角色差异 |
|------|------|---------|
| report_progress | 任务汇报，让 user 和 manager 知道当前进展 | 通用 |
| complete_task | 闭环 AgentCall，汇报成果（成功/失败/阻塞） | Manager 安排完任务后立即闭环；Worker 完成实际工作后闭环 |

**Worker 阻塞判定规则**：遇到以下情况，Worker 用 complete_task 标记失败（success=false）：

| 类型 | 判断标准 |
|------|----------|
| 跨模块依赖 | 问题涉及其他模块且改动范围超出当前任务边界（小 bug 直接修） |
| 对外接口不明 | 需要暴露的接口、关键数据模型与其他模块未对齐 |
| 需求冲突 | 任务要求与现有代码逻辑矛盾，修改会影响其他模块 |
| 执行路径需协调 | 方案选择会影响其他并行任务（如 schema 变更、公共配置修改） |

核心原则：阻塞只针对影响范围超出任务边界的情况，内部实现细节自行判断。

### Heartbeat 提示词

**触发条件**：每 20 分钟定时发给 Manager。

**正常心跳**：`[Heartbeat] 定时检查：请查看当前任务进度。`

**有 Worker 停止时**：`[Heartbeat] 以下成员已因连续执行失败自动停止: {成员列表}。当前没有自动重启机制，请通过 report_progress 向 user 说明情况。`

消息类型为 `NOTIFICATION`。

### 触发时机汇总

| 提示词类型 | 触发时机 | 目标 |
|-----------|---------|------|
| `<TOOL_USAGE>` | 启动时加载 | CLAUDE.md / AGENTS.md（system_prompt） |
| `<runtime>` | MAIN 会话消息处理时 | LLM user message（第一段） |
| `<incoming_message>` | 每条消息处理时 | LLM user message（末段） |
| AgentContext | MAIN 会话消息处理时 | LLM user message（中间段） |
| Heartbeat | 每 20 分钟 | Manager 消息队列 |

## Design Rationale

**为什么采用四来源模型？**
- 提示词来源性质不同：系统级规则（System Prompt） vs 运行时状态（Runtime） vs 对话上下文（Context） vs 定时事件（Heartbeat）。混合注入会导致职责不清，分离后各模块独立演进。

**为什么 Runtime 注入到 user message 而非 system_prompt？**
- Runtime 内容（身份、团队、任务状态）每条消息都变化，注入 system_prompt 会破坏 prompt caching 命中率。作为 user message 的一部分，可以在保持 system_prompt 稳定的同时动态更新。

**为什么 Worker 不接收 raw messages？**
- Worker 的工作模式是「接任务 -> 执行 -> 报告」，通过 AgentMessage.content 已经拿到任务详情，compact history 提供团队进展摘要。raw messages 会增加 Worker 的认知负担且无实际收益。

**为什么工具提示词通过类变量（ROLE_INSTRUCTIONS）而非运行时注入？**
- 工具规则在 Agent 生命周期内不变，通过类变量定义在编译期确定，避免每次消息处理时重复构造。

**为什么 complete_task 在 Manager 和 Worker 间有不同语义？**
- Manager 是编排者，安排完任务后不需要等待 Worker 结果即可闭环，Worker 完成后通过新的 AgentCall 重新激活。Worker 是执行者，闭环即表示工作完成。

**已知限制**：
- Heartbeat 固定 20 分钟间隔，无法按任务紧急程度动态调整
- Task 未闭环提醒已 deprecated，由 `_fallback_close_task()` 兜底，连续未闭环阈值固定（默认 30 次）

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **agent_bridge**：CLI 如何从 CLAUDE.md 读取 system_prompt、Agent 的 LLM 调用参数和模型选择
- **core/context**：上下文压缩的具体算法和实现
- **运行时调优**：提示词的具体措辞和 prompt engineering 技巧
