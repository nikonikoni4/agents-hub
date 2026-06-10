---
version: 1.0
created_at: 2026-06-08
updated_at: 2026-06-08
last_updated: 2026-06-08
abstract: 收窄 speak_in_group_chat 为任务汇报工具，所有成果/问题/风险通过 complete_task 汇报；阻塞判定标准为"影响范围是否超出任务边界"
status: decided
---

# Agent 工具语义与阻塞判定规则

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建文档初稿 |

## 问题界定

### 问题简述

speak_in_group_chat 的使用边界不清晰，容易被 Agent 滥用（长篇汇报、频繁进度更新），导致群聊消息膨胀。同时缺乏阻塞判定标准，Worker 遇到问题时不知道应该自己处理还是上报。

### 讨论范围

- speak_in_group_chat 和 complete_task 的语义边界
- Worker 什么情况下算"阻塞"
- Manager 收到阻塞报告后的处理流程

### 非讨论范围

- 工具的技术实现（参数、返回值）
- Agent 中断机制（当前不存在）

### 问题深度

涉及 Agent 协作行为设计：工具语义决定 Agent 的行为模式，阻塞判定规则决定系统熵增的控制策略。

## 现状

- speak_in_group_chat 定义为"在群聊中公开发言"，过于宽泛
- Worker 没有明确的阻塞判定标准
- Manager 收到 Worker 失败后的处理流程未定义
- Agent 能力强但行为发散，不约束会导致系统熵增严重

## 可选方案

### 方案 A：保持现状，通过输出约束控制

保持两个工具的当前语义，只在 ROLE_INSTRUCTIONS 中加字数限制。

**优势**
- 改动最小

**劣势**
- 不解决根本问题：工具语义模糊导致 Agent 行为不可控
- 字数限制是表面约束，不改变 Agent 的使用决策

### 方案 B：收窄 speak_in_group_chat + 阻塞判定规则

将 speak_in_group_chat 收窄为"任务汇报"工具，所有成果/问题/风险通过 complete_task 汇报。定义明确的阻塞判定标准。

**优势**
- 语义清晰，Agent 不需要在两个工具之间纠结
- complete_task 成为唯一的信息汇总出口，Manager 不需要同时关注两个渠道
- 阻塞规则给 Worker 提供明确的行为边界

**劣势**
- speak_in_group_chat 的使用场景变得很窄
- 需要在提示词中详细说明阻塞判定规则

### 方案 C：去掉 speak_in_group_chat，只保留 complete_task

完全移除 speak_in_group_chat，所有输出都通过 complete_task。

**优势**
- 最简化，Agent 只需要记住一个出口

**劣势**
- 丢失了任务执行过程中的轻量汇报能力（如"收到任务"）
- complete_task 需要 call_id，不是所有场景都有

## 最终决策

选择 **方案 B：收窄 speak_in_group_chat + 阻塞判定规则**。

## 决策原因

1. **没有中断机制**：即使 speak_in_group_chat 通知了 Manager，Manager 也无法实时阻止 Worker（延迟问题）。所以执行过程中的通知对任务控制没有实际作用。
2. **complete_task 是唯一可靠的信息汇总出口**：它携带 call_id，能激活原调用方，有明确的状态标记（success/failed）。所有成果、问题、风险都应通过这个渠道汇报。
3. **阻塞判定的核心原则是"影响范围"**：内部实现细节 agent 自行判断，只有影响范围超出任务边界的情况才算阻塞。这约束的是接口和执行路径，不是执行本身。
4. **Manager 处理阻塞的三种路径**：自己判断 → 派给专业成员 → 向 user 汇报。群里可能有专门做需求或架构的 Worker，Manager 不需要事事亲力亲为。

## 阻塞判定标准

Worker 遇到以下情况，用 complete_task 标记失败（success=false）：

| 类型 | 判断标准 | 示例 |
|------|----------|------|
| 跨模块依赖 | 问题涉及其他模块且改动范围超出当前任务边界（小 bug 直接修） | 依赖链 A→B→C，做 B 时发现 C 有大量问题 |
| 对外接口不明 | 需要暴露的接口、关键数据模型与其他模块未对齐 | API schema 需要和前端协商 |
| 需求冲突 | 任务要求与现有代码逻辑矛盾，修改会影响其他模块 | 新需求和现有架构冲突 |
| 执行路径需协调 | 方案选择会影响其他并行任务 | 数据库 schema 变更、公共配置修改 |

## 后续影响

- MCP 工具 docstring 需要同步更新
- Worker 的 ROLE_INSTRUCTIONS 需要包含阻塞判定规则
- Manager 的工作流程需要包含阻塞处理步骤
- 需要监控 Worker 是否因规则过于保守而频繁阻塞
- 后续可能需要细化"什么算阻塞"的判断规则，取决于实际运行中的阻塞模式
