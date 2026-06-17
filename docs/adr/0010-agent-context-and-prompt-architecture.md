---
version: 1.0
created_at: 2026-06-08
updated_at: 2026-06-08
last_updated: 2026-06-08
abstract: Agent Context 按角色差异化交付（Worker 不接收 raw messages），工具提示词从 base_agent 提取到子类作为 ROLE_INSTRUCTIONS 类变量
status: decided
---

# Agent Context 差异化与提示词架构

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建文档初稿 |

## 问题界定

### 问题简述

Agent context 占用过多上下文 token，原因有两个：(1) 每个 Agent 在群聊里发出内容太多 (2) 原始未压缩聊天记录直接交给 Agent。同时，工具提示词全部硬编码在 base_agent 的 `_generate_tool_usage_content()` 中，80+ 行 if/else 分支，修改某个角色的提示词需要在大函数中定位，新增角色需要改 base_agent。

### 讨论范围

- AgentContext 如何按角色差异化交付上下文
- 工具提示词的代码组织方式
- Worker 输出约束的方式

### 非讨论范围

- 压缩算法本身的优化
- LLM 模型的 context window 限制

### 问题深度

涉及 Agent 架构的核心设计：context 交付策略和提示词管理方式，影响所有 Agent 的行为和 token 消耗。

## 现状

- `AgentContext.get_context()` 对 Manager 和 Worker 交付完全相同的上下文（compact history + raw messages）
- Manager 和 Worker 都是 Agent 的空子类，无行为差异
- `_generate_tool_usage_content()` 在 base_agent 中通过 `if LEADER ... else ...` 硬编码全部工具提示词
- Worker 输出无长度约束，导致群聊消息膨胀

## 可选方案

### 方案 A：减小压缩窗口

减小 Group Context 的 Compact 窗口（如 1000→500），让每次发给 Agent 的消息更少。

**优势**
- 改动最小，只改一个常量

**劣势**
- 压缩频率太高，增加 LLM 调用成本
- 压缩对活跃 Agent 帮助有限（每次拿到的是增量 raw messages）

### 方案 B：AgentContext 按角色差异化 + 提示词提取到子类

Worker 不接收 raw messages（只接收 compact history），Manager 保持原样。工具提示词从 base_agent 提取到子类作为类变量。

**优势**
- Worker context 直接砍掉 raw messages，减少 50-70% token
- 提示词职责清晰：子类定义角色专属内容，基类只做编排
- 修改某个角色的提示词不需要改 base_agent

**劣势**
- 需要将 role_type 传入 AgentContext

### 方案 C：只做提示词提取，不改 context 交付

只重构代码组织，不改变 context 交付策略。

**优势**
- 改动范围小

**劣势**
- 不解决 context token 过大的核心问题

## 最终决策

选择 **方案 B：AgentContext 按角色差异化 + 提示词提取到子类**。

## 决策原因

1. **Worker 不需要 raw messages**：Worker 的工作模式是「接任务 → 执行 → 报告」，通过 AgentMessage.content 已经拿到任务详情，compact history 提供团队进展摘要。raw messages 里的中间对话对 Worker 执行具体任务没有帮助。
2. **仍需更新 message_index**：虽然 Worker 跳过 raw messages，但必须更新 last_loaded_message_index，避免积压。
3. **类变量优于函数内硬编码**：ROLE_INSTRUCTIONS 作为类变量，修改时直接改子类文件，不需要在 base_agent 的大函数中定位分支。编排函数只负责拼接。
4. **共享规则留在基类**：群聊消息显示规则是所有角色共享的，作为 Agent.SHARED_RULES 类变量。

## 后续影响

- AgentContext 构造函数新增 role_type 参数，所有实例化点需要同步
- 新增角色只需在子类定义 ROLE_INSTRUCTIONS，不需要改 base_agent
- Worker 的 context token 消耗预计减少 50-70%
- 需要监控 Worker 是否因缺少 raw messages 而丢失关键上下文
