---
version: 2.0
created_at: 2026-05-31
updated_at: 2026-06-18
last_updated: 按照新 spec 规则重构：聚焦业务意图、技术契约、设计决策
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
  - agents_hub/core/context/group_chat_runtime.py
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
| 1.4 | 修正持有关系描述：GroupChatContext 持有 Runtime，Runtime 持有 Repository |
| 1.5 | 移除 GroupChatContext 中间层，Agent 直接持有 GroupChatRuntime |
| 2.0 | 按照新 spec 规则重构：聚焦业务意图、技术契约、设计决策 |

## Overview

**业务问题**：群聊场景需要管理多个 Agent 的会话状态、消息历史和上下文，需要一个统一的状态管理层来处理这些职责。

**核心职责**：
1. **会话状态管理**（GroupChatSession）：管理群聊的消息历史和元数据
2. **运行时协调**（GroupChatRuntime）：协调消息管理、session 管理和上下文压缩
3. **持久化**（GroupChatRepository）：文件读写、路径记录和并发控制
4. **增量加载**（AgentContext）：为每个 Agent 提供个性化的增量上下文

**边界**：context 只依赖 foundation 层，与 communication 层同级、互不依赖。

## Scope

### 范围内

- 群聊消息历史的存储和检索
- Agent session ID 的映射管理
- 上下文压缩策略（何时压缩、如何压缩）
- Agent 上下文的增量加载机制
- 持久化文件的读写和并发控制

### 范围外

- 消息路由和投递（属于 communication 层，参见 `docs/specs/2026-05-31-core-communication.md`）
- Agent 执行逻辑（属于 agent 层）
- 群聊编排和团队管理（属于 orchestration 层）

## Technical Contract

### GroupChatRuntime（运行时 Facade）

<key_function last_update="2026-06-20T14:08:10+08:00">
- agents_hub/core/context/group_chat_runtime.py
  - group_chat_runtime.GroupChatRuntime.load:56
  - group_chat_runtime.GroupChatRuntime.add_message:319
  - group_chat_runtime.GroupChatRuntime.save_agent_members:438
  - group_chat_runtime.GroupChatRuntime.compact_messages:493
  - group_chat_runtime.GroupChatRuntime.update_agent_session:397
  - group_chat_runtime.GroupChatRuntime.close:642
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| `load()` | 从持久化层加载所有状态到内存 | 返回 GroupChatRuntimeState |
| `add_message(agent_result)` | 添加消息到群聊历史 | 内部加锁保护并发写入 |
| `save_agent_members(context)` | 持久化所有 agent 成员信息 | 内部加锁保护并发写入 |
| `compact_messages(agent_info)` | 压缩群聊消息历史 | 调用 LLM 生成摘要 |
| `update_agent_session(agent_result)` | 根据 Agent 执行结果更新会话信息 | 内部加锁保护并发写入 |
| `close()` | 关闭 Runtime，释放资源 | 幂等可重复调用 |

**数据模型**：

| 模型 | 说明 |
|------|------|
| GroupChatSession | 群聊会话，包含 messages 列表和 last_compacted_loc |
| AgentMemberInfo | Agent 会话信息，包含 main_session、btw_session、context_state、token、cwd、use_docker |
| GroupMetadata | 群聊元数据，包含 group_chat_id、group_chat_name、project_path、created_at、group_type |

**消息格式说明**：

- `ChatMessage`（持久化格式）：agent_name、content、timestamp、platform
- `AgentMessage`（通信格式）：call_id、content、send_from、send_to、session_type、message_type

两者是不同的数据结构，`add_message()` 接收 Agent 执行结果并转换为 `ChatMessage` 格式存储。

### AgentContext（Agent 上下文）

<key_function last_update="2026-06-18T10:00:00+08:00">
- agents_hub/core/context/agent_context.py
  - agent_context.AgentContext.get_context:38
  - agent_context.AgentContext.build_user_prompt:180
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| `get_context()` | 获取 Agent 的增量上下文 | 返回 XML 标签包裹的上下文字符串，无新内容时返回空串 |
| `build_user_prompt(msg)` | 构建完整的 user message | 包含 runtime + context + incoming_message |

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

### GroupChatRepository（持久化层）

<key_function last_update="2026-06-18T10:00:00+08:00">
- agents_hub/core/context/group_chat_repository.py
  - group_chat_repository.GroupChatRepository.load_group_chat_session:54
  - group_chat_repository.GroupChatRepository.save_group_chat_session:110
  - group_chat_repository.GroupChatRepository.load_agent_member_infos:154
  - group_chat_repository.GroupChatRepository.save_agent_member:217
  - group_chat_repository.GroupChatRepository.load_compact_history:270
  - group_chat_repository.GroupChatRepository.save_compact_history:300
  - group_chat_repository.GroupChatRepository.save_group_metadata:329
  - group_chat_repository.GroupChatRepository.load_group_metadata:354
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| `load_group_chat_session()` | 从文件加载群聊会话 | 无锁，读操作 |
| `save_group_chat_session(session)` | 保存 GroupChatSession 到文件 | 加锁，写操作 |
| `load_agent_member_infos()` | 加载 agent session 状态 | 无锁，读操作 |
| `save_agent_member(state)` | 保存 agent session 状态到文件 | 加锁，写操作 |
| `load_compact_history()` | 加载压缩历史记录 | 无锁，读操作 |
| `save_compact_history(history)` | 保存压缩历史记录到文件 | 加锁，写操作 |
| `save_group_metadata(metadata)` | 保存群聊元数据 | 加锁，写操作 |
| `load_group_metadata()` | 加载群聊元数据 | 无锁，读操作 |

**持久化文件结构**：

| 文件 | 格式 | 锁 | 说明 |
|------|------|-----|------|
| `<id>.jsonl` | JSONL | _session_lock | 消息历史，首行为 meta_data |
| `agent_member.json` | JSON | _agent_state_lock | Agent session 映射 |
| `memory/compact_history.jsonl` | JSONL | _compact_lock | 压缩历史 |
| `group_metadata.json` | JSON | _metadata_lock | 群聊元数据 |

### 状态机规则

**Agent Session 更新规则**：
- 首次出现的 Agent → 创建新的 AgentMemberInfo
- session_id 与 main_session 相同 → 不处理
- session_id 不同且不在 btw_session 中 → 追加到 btw_session

**上下文压缩触发条件**：
- 估算 token 数 = 总字符数 / 4 >= MAX_TOKEN（1000）
- 压缩产物包含 summary（共享摘要）和 agent_specific（Agent 专属摘要）

**增量加载规则**：
- 每个 Agent 独立追踪 last_loaded_compact_index 和 last_loaded_message_index
- 只加载未加载的压缩历史和原始消息
- 加载后自动更新加载状态

## Design Rationale

**为什么这样设计？**
- **分层架构**：context 层只依赖 foundation 层，保持依赖方向单向
- **增量加载**：避免重复加载已读内容，减少 token 消耗
- **压缩机制**：当消息历史过长时自动压缩，控制上下文大小
- **并发控制**：使用 asyncio.Lock 保护写操作，防止并发写入导致数据损坏

**有哪些约束？**
- 压缩功能依赖 LLM 调用（`bare_claude_call`），通过可注入接口（CompactionLLM protocol）解耦
- 路径管理使用 foundation 层的 `group_chat_paths` 单例集中管理
- 文件不存在时返回空数据（首次创建场景）

**有哪些已知限制？**
- 压缩策略的具体参数（MAX_TOKEN 值、压缩 prompt）可能随版本调整
- 当前使用 asyncio.Lock，未来可能需要文件锁支持多进程场景

**相关 ADR**：
- 无

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **communication 层**：`docs/specs/2026-05-31-core-communication.md` - 消息路由和投递机制
- **agent 层**：Agent 执行逻辑和 LLM 调用细节
- **orchestration 层**：群聊编排和团队管理
