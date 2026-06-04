---
version: 1.3
created_at: 2026-05-31
updated_at: 2026-06-04
last_updated: 对齐现有 GroupChatContext 创建 Repository、metadata 持久化和 AgentMemberInfo 字段
abstract: core/context 层的正式规格，定义群聊会话管理、Agent 上下文增量加载、消息压缩策略和持久化机制
id: spec-core-context
title: Core Context 层规格
status: draft
module: core/context
sourc_spec: null
related_plan: null
code_scope:
  - agents_hub/core/context/
contract_refs:
  - agents_hub/core/context/group_chat_session.py
  - agents_hub/core/context/group_chat_context.py
  - agents_hub/core/context/group_chat_repository.py
  - agents_hub/core/context/agent_context.py
  - agents_hub/core/foundation/constants.py
  - agents_hub/core/foundation/paths.py
---

# Core Context 层规格

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |
| 1.1 | AgentMemberInfo 新增 token 字段 |
| 1.2 | 路径管理改用 group_chat_paths 集中管理 |
| 1.3 | 对齐现有 GroupChatContext 创建 Repository、metadata 持久化和 AgentMemberInfo 字段 |

## Overview

context 层是 core 的**状态管理层**，负责群聊会话的生命周期管理。核心职责：

1. **会话状态**（GroupChatSession）：管理群聊的消息历史和元数据
2. **上下文管理**（GroupChatContext）：协调消息管理、session 管理和上下文压缩，并在当前实现中创建和持有 GroupChatRepository
3. **持久化**（GroupChatRepository）：文件读写、路径记录和并发控制
4. **增量加载**（AgentContext）：为每个 Agent 提供个性化的增量上下文

context 只依赖 foundation 层，与 communication 层同级、互不依赖。

## Scope

### 范围内

- 群聊消息历史的存储和检索
- Agent session ID 的映射管理
- 上下文压缩策略（何时压缩、如何压缩）
- Agent 上下文的增量加载机制
- 持久化文件的读写和并发控制

### 范围外

- 消息路由和投递（属于 communication 层）
- Agent 执行逻辑（属于 agent 层）
- 群聊编排和团队管理（属于 orchestration 层）

## Core Behavior

### 会话状态模型

GroupChatSession 管理群聊的消息历史，核心数据：

| 字段 | 说明 |
|------|------|
| group_chat_id | 群聊唯一标识 |
| messages | 消息列表，每条包含 agent_name、content、timestamp、platform |
| last_compacted_loc | 上一次压缩的位置（消息列表索引） |
| created_at / updated_at | 时间戳 |

**消息追加**：Agent 执行完成后，通过 add_message() 将结果追加到 messages 列表。

**未压缩消息**：`messages[last_compacted_loc:]` 即为尚未被压缩的消息。

### Agent Session 管理

每个 Agent 在群聊中有独立的 session 映射：

- `main_session`：主会话 ID（群聊场景）
- `btw_session`：单聊会话 ID 列表（by the way 场景）
- `context_state`：上下文加载状态（已加载到第几条压缩历史和原始消息）
- `token`：Agent Token，用于 MCP 工具身份验证（由 orchestration 层在 start/load 时生成或恢复）
- `cwd`：Agent CLI 执行时使用的工作目录；为空时可由群聊项目路径作为默认值
- `use_docker`：是否启用 Docker 沙箱执行

**Session 更新规则**：
- 首次出现的 Agent → 创建新的 AgentMemberInfo
- session_id 与 main_session 相同 → 不处理
- session_id 不同且不在 btw_session 中 → 追加到 btw_session

### 上下文压缩策略

当未压缩消息的估算 token 数超过阈值（MAX_TOKEN = 1000）时，触发压缩：

**触发条件**：估算 token 数 = 总字符数 / 4 >= MAX_TOKEN

**压缩流程**：
1. 获取 `messages[last_compacted_loc:]` 的未压缩消息
2. 构建消息历史文本 + Agent 职责描述
3. 调用 LLM（bare_claude_call）生成结构化摘要
4. 输出格式：`{summary: "...", agent_specific: {agent_name: "..."}}`
5. 追加到 compact_history.jsonl
6. 更新 last_compacted_loc

**压缩产物**：
- `summary`：所有 Agent 共享的整体对话摘要
- `agent_specific`：为每个 Agent 提取与其职责相关的关键信息

### Agent 上下文增量加载

AgentContext 为每个 Agent 提供**增量加载**的上下文，避免重复加载已读内容：

**加载逻辑**：
1. 读取 Agent 的 `last_loaded_compact_index` 和 `last_loaded_message_index`
2. 加载新的压缩历史：`compact_history[last_loaded_compact_index:]`
3. 加载新的原始消息：`messages[last_loaded_message_index:]`
4. 更新加载状态（两个 index 推进到最新位置）

**输出格式**（XML 标签包裹）：

```
<group_chat_history>
  <overall_summary>
    1. 摘要一
    2. 摘要二
  </overall_summary>
  <summary_for_you>
    1. 与你相关的关键信息
  </summary_for_you>
</group_chat_history>
<recent_messages>
  [AgentA]: 消息内容
  [AgentB]: 消息内容
</recent_messages>
```

**空内容处理**：如果没有新的压缩历史和消息，返回空串。

### 持久化机制

GroupChatRepository 由 GroupChatContext 创建并持有，负责群聊相关文件的读写，使用独立的 asyncio.Lock 保护写操作：

| 文件 | 格式 | 锁 | 说明 |
|------|------|-----|------|
| `<id>.jsonl` | JSONL | _session_lock | 消息历史，首行为 meta_data |
| `agent_member.json` | JSON | _agent_state_lock | Agent session 映射（含 context_state、token、cwd、use_docker 字段） |
| `memory/compact_history.jsonl` | JSONL | _compact_lock | 压缩历史 |
| `group_metadata.json` | JSON | _metadata_lock | 群聊元数据，包含 group_chat_id、group_chat_name、project_path、created_at、group_type |

**并发控制策略**：
- 读操作不加锁（asyncio 单线程模型下安全）
- 写操作加锁（防止并发写入导致数据损坏）
- 文件不存在时返回空数据（首次创建场景）

**路径管理**：
- 使用 foundation 层的 `group_chat_paths` 单例集中管理路径
- 路径规则：`local_data/teams/<sanitized_project_path>/<group_chat_id>/`
- project_path 中的 `/ : \` 转换为 `-`，连续 `-` 合并为单个

**路径获取方式**：
```python
from agents_hub.core.foundation import group_chat_paths

# 获取群聊基础目录
base_dir = group_chat_paths.base_dir(group_chat_id, project_path)

# 获取具体文件路径
messages_file = group_chat_paths.messages_file(group_chat_id, project_path)
agent_member_file_path = group_chat_paths.agent_member_file_path(group_chat_id, project_path)
compact_history_file = group_chat_paths.compact_history_file(group_chat_id, project_path)
metadata_file = group_chat_paths.metadata_file(group_chat_id, project_path)
```

## Technical Contract

### 跨层依赖

- context 依赖 foundation 的 `MAX_TOKEN`、`StateError`、`Tag`、`wrap_xml`
- context 依赖 agent_bridge 的 `bare_claude_call`（压缩时调用 LLM）
- agent 层通过 `AgentContext.get_context()` 获取增量上下文
- agent 层通过 `GroupChatContext.add_message()` 写入消息
- orchestration 层的 GroupChat 创建并持有 GroupChatContext 实例；当前实现中，Repository 由 GroupChatContext 内部创建并通过 context 暴露给部分编排逻辑使用

### 与 Agent 的协作模式

```
Agent._process_message():
  1. history = await agent_context.get_context()  ← 增量加载上下文
  2. full_prompt = history + render_for_llm(msg)   ← 拼接上下文和新消息
  3. result = await execute(full_prompt)            ← 执行
  4. await group_chat_context.add_message(result)   ← 写回消息
  5. await group_chat_context.update_agent_member_info(result)  ← 更新 session
```

### 资源清理

GroupChatContext.close() 负责释放资源：
- 关闭 Repository（预留接口，当前 asyncio.Lock 不需要显式释放）
- 清空内存引用（group_chat_session、agent_member_info）
- 幂等可重复调用

## Out of Spec

- context 不涉及消息路由和投递机制
- context 不涉及 Agent 执行和 LLM 调用细节
- context 不涉及群聊编排和团队管理
- 压缩策略的具体参数（MAX_TOKEN 值、压缩 prompt）可能随版本调整
