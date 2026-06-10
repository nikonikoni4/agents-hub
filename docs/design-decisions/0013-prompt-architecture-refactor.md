---
version: 1.0
created_at: 2026-06-10
updated_at: 2026-06-10
last_updated: 2026-06-10
abstract: 将 runtime 信息从 system prompt 移到 user message，解决 Agent 找不到 call_id 和身份信息缺失的问题
status: decided
---

# 提示词架构重构

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建文档初稿 |

## 问题界定

### 问题简述

Agent 在处理消息时找不到 call_id，需要通过系统提醒才能获得，导致多次无效工具调用。同时 Agent 缺少身份信息（role description），无法了解自己的职责。

### 讨论范围

- runtime 信息的传递位置（system prompt vs user message）
- call_id 的可见性
- 身份信息的注入方式
- CLAUDE/AGENTS.md 的写入时机

### 非讨论范围

- 压缩算法本身的优化
- LLM 模型的 context window 限制

### 问题深度

涉及 Agent 架构的核心设计：提示词结构和信息传递方式，影响所有 Agent 的行为和 token 消耗。

## 现状

### Bug 1: 缺少身份信息

Agent 只知道自己的名字，不知道自己的角色职责描述。`role.json` 中的 `description` 字段没有被注入到 system prompt 中。

### Bug 2: call_id 位置错误

call_id 被写入 system prompt 的 `active_agent_calls`，但 Agent 在 incoming_message 中看不到。Agent 需要通过 `__SYSTEM__` 消息提醒才能获得 call_id，出现 Agent 猜测 call_id 的现象。

**从分析文件（docs\temp\a59faa03-9d2c-4a28-b67e-e70a57398284_analysis.md）看到的问题行为**：
- Agent 使用 `check_agent_call` 猜测 call_id
- 等待系统提醒才获得正确的 call_id
- 多次无效的工具调用

## 可选方案

### 方案 A: 保持现状，修复 call_id 传递

在 `render_for_llm` 中添加 call_id，保持其他结构不变。

**优势**
- 改动最小

**劣势**
- 不解决身份信息缺失问题
- runtime 信息仍在 system prompt，与 CLAUDE/AGENTS.md 内容重复

### 方案 B: 将 runtime 信息移到 user message

将所有 runtime 信息（agent_token, group_chat_id, team_members, agent_call 等）从 system prompt 移到 user message。system prompt 不再动态生成，CLAUDE/AGENTS.md 在 role 创建时写入。

**优势**
- 解决 call_id 可见性问题
- 解决身份信息缺失问题
- 减少 system prompt 的动态生成复杂度
- CLAUDE/AGENTS.md 内容稳定，不随消息变化

**劣势**
- 需要修改多个文件
- 需要实现 `build_user_prompt` 方法

### 方案 C: 只重构代码组织，不改信息传递

将提示词模板提取到 `prompt_file.py`，但保持 system prompt 动态生成。

**优势**
- 代码组织更清晰

**劣势**
- 不解决核心问题（call_id 和身份信息）

## 最终决策

选择 **方案 B: 将 runtime 信息移到 user message**。

## 决策原因

1. **call_id 必须在 incoming_message 中可见**：Agent 处理消息时需要立即知道 call_id，不能依赖系统提醒。这是核心问题。

2. **身份信息应该在 CLAUDE/AGENTS.md 中**：role 的 description 和工具说明是静态的，应该在 role 创建时写入，而不是每次消息都动态生成。

3. **system prompt 应该保持稳定**：动态生成 system prompt 增加了复杂度，而且内容与 CLAUDE/AGENTS.md 重复。保留通道但不使用，后续可能有用。

4. **runtime 信息适合放在 user message**：agent_token、group_chat_id、team_members 等信息是每次消息都需要的，放在 user message 的 `<runtime>` 标签中更合理。

## 后续影响

### 代码修改

1. `renderer.py`: `render_for_llm()` 添加 call_id 和 message_type
2. `agent_context.py`: 实现 `build_user_prompt()`，组装 runtime + context + incoming_message
3. `base_agent.py`: 简化 `_process_message()`，移除动态 system prompt 生成
4. `role_manager.py`: `create_role()` 调用 `prompt_file.py` 写入 CLAUDE/AGENTS.md
5. `prompt_file.py`: 新增模板定义

### 解决的问题

- Agent 找不到 call_id（现在在 incoming_message 中）
- 身份信息未注入（现在在 CLAUDE/AGENTS.md 中）
- 工具说明硬编码（现在在 prompt_file.py 中）

### 后续重构

1. **role 的 system prompt 输入**：增加 role 的 system prompt 输入，用于区分身份信息和职责表述。Manager 需要知道每个 Worker 的职责和身份描述，但要写进 Manager 的工作面板，所以不能太长。

2. **CLAUDE/AGENTS.md 更新时机**：应该由 role 管理，当 role 配置变更时同步更新。

3. **custom_prompt 字段**：role.json 增加 custom_prompt 字段，用于自定义提示词。
