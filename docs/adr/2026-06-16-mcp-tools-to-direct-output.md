---
version: 1.0
created_at: 2026-06-16
updated_at: 2026-06-16
abstract: 暂时取消 MCP 工具 complete_task 和 report_progress，改为直接使用 agentbridge 输出作为回复；成功展示改为 XML 标签 + git status 兜底的两步策略
status: decided
---

# MCP 工具到直接输出的决策

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建文档，记录从 MCP 工具到直接输出的决策 |

## 问题界定

### 问题简述

当前系统使用两个 MCP 工具（`complete_task` 和 `report_progress`）来控制 Agent 的输出行为：
- `report_progress`：用于群聊公开发言
- `complete_task`：用于结束需要回复的 AgentCall 并返回结果

然而，经过一段时间的实际使用，发现这两个工具存在以下问题：
1. **平台兼容性**：Codex 目前无法使用当前的 MCP 工具
2. **过度设计**：最初引入这两个工具是担心输出内容太杂会干扰群聊上下文，但实际使用中这个问题并不显著
3. **架构复杂度**：MCP 工具增加了 tool_use 的复杂性，而解析器已经能够排除 tool_use 对群聊的干扰
4. **调用稳定性**：Agent 调用 MCP 工具不稳定，虽然经过改名和函数 docstring 改进后有所提升，但仍然存在 Agent 无法正确调用的问题（主观判断概率不低）

### 讨论范围

- MCP 工具 `complete_task` 和 `report_progress` 的存废
- Agent 输出的默认行为策略
- 成功展示（原绑定在 `complete_task`）的替代方案

### 非讨论范围

- MCP 工具的传输方式（HTTP vs stdio）
- Agent 的其他工具（如 `call_agent`、`assign_tasks_to_team` 等）
- 前端如何渲染群聊消息

## 现状

### 当前架构

1. **MCP 工具层**：`complete_task` 和 `report_progress` 作为 MCP 工具暴露给 Agent
2. **Agent 行为约束**：Agent 被要求通过显式工具调用来公开发言或结束任务
3. **输出解析**：解析器负责从 MCP 工具调用中提取内容，排除 tool_use 对群聊的干扰

### 现有问题

1. **Codex 平台限制**：Codex 无法使用当前的 MCP 工具，导致架构不一致
2. **过度设计**：实际使用中，输出内容干扰群聊上下文的问题并不显著
3. **架构复杂度**：MCP 工具增加了 tool_use 的复杂性，而解析器已经能够处理这个问题
4. **认知成本**：Agent 需要学习和使用额外的工具，增加了 prompt 工程成本
5. **调用稳定性**：Agent 调用 MCP 工具不稳定，虽然经过改名和 docstring 改进后有所提升，但仍存在无法正确调用的问题

## 可选方案

### 方案 A：保持现状（MCP 工具控制输出）

**做法**：继续使用 `complete_task` 和 `report_progress` 作为 MCP 工具。

**优势**：
- 已经实现，无需改动
- 显式控制输出行为，语义清晰

**劣势**：
- Codex 平台无法使用
- 架构复杂度高
- 实际收益不明显

### 方案 B：直接使用 agentbridge 输出（本方案）

**做法**：
1. 暂时取消 `complete_task` 和 `report_progress` 这两个 MCP 工具
2. Agent 的输出直接作为回复，无需显式工具调用
3. 成功展示改为两步策略：
   - 第一步：Agent 在结果中输出 XML 标签（如 `<task_complete>`、`<progress_update>`）
   - 第二步：若没有输出标签，则使用 `git status` 对比前后不同状态的文件作为输出兜底

**优势**：
- 简化架构，减少工具数量
- 解决 Codex 平台兼容性问题
- 降低 Agent 的学习成本
- 解析器已经能够处理 tool_use 的干扰问题

**劣势**：
- 需要依赖 Agent 遵循输出格式约定（XML 标签）
- 需要实现 git status 兜底逻辑
- 可能需要调整现有的解析器逻辑

### 方案 C：混合方案（部分保留 MCP 工具）

**做法**：保留 `complete_task` 用于任务闭环，取消 `report_progress`，Agent 的普通输出直接作为回复。

**优势**：
- 保留任务闭环的显式控制
- 简化普通发言的流程

**劣势**：
- 仍然存在 Codex 平台兼容性问题
- 架构仍然较复杂

## 最终决策

选择**方案 B：直接使用 agentbridge 输出**。

## 决策原因

### 原因 1：解决平台兼容性问题

Codex 目前无法使用当前的 MCP 工具，这导致架构不一致。直接使用输出可以解决这个问题，为未来支持更多平台奠定基础。

### 原因 2：实际收益不明显

经过一段时间的使用，发现输出内容干扰群聊上下文的问题并不显著。最初引入 MCP 工具是基于对解析器的不了解，现在解析器已经能够排除 tool_use 的干扰。

### 原因 3：MCP 工具调用不稳定

Agent 调用 MCP 工具存在稳定性问题。虽然经过改名和函数 docstring 改进后调用稳定性有所提升，但仍然存在 Agent 无法正确调用的情况。根据使用经验主观判断，这个概率并不低。直接输出可以完全规避这个风险。

### 原因 4：简化架构

MCP 工具增加了 tool_use 的复杂性，而直接输出可以简化架构，降低 Agent 的学习成本和 prompt 工程成本。

### 原因 4：两步策略提供兜底

成功展示改为 XML 标签 + git status 兜底的两步策略，确保每次 Agent 修改都能有产出物展示，同时不依赖显式工具调用。

## 实施细节

### 第一步：取消 MCP 工具

1. 从 `agents_hub/mcp/server.py` 中移除 `complete_task` 和 `report_progress` 工具
2. 更新相关文档和配置

### 第二步：调整 Agent 输出行为

1. Agent 的输出直接作为回复，无需显式工具调用
2. 在 Agent 的 system prompt 中说明输出格式约定

### 第三步：实现成功展示的两步策略

1. **XML 标签策略**：
   - Agent 在结果中输出 XML 标签来标识任务状态
   - 示例：`<task_complete>任务完成</task_complete>`、`<progress_update>处理中...</progress_update>`

2. **git status 兜底策略**：
   - 若 Agent 没有输出 XML 标签，则使用 `git status` 对比任务前后的文件状态
   - 将变更的文件列表作为成功展示的兜底

### 第四步：调整解析器

1. 更新解析器以支持新的输出格式
2. 确保解析器能够正确处理 XML 标签和 git status 兜底

## 后续影响

### 对当前架构的影响

1. **MCP 工具层**：移除 `complete_task` 和 `report_progress`，减少工具数量
2. **Agent 行为**：Agent 不再需要显式调用工具来输出结果
3. **解析器**：需要支持新的输出格式（XML 标签 + git status 兜底）

### 对未来 spec 的影响

1. 需要更新 `core-agent-orchestration` spec 中关于 Agent 输出行为的描述
2. 需要更新 `core-communication` spec 中关于群聊发言的描述

### 风险与缓解

1. **风险**：Agent 可能不遵循 XML 标签约定
   - **缓解**：通过 system prompt 明确说明输出格式，并在解析器中实现兜底逻辑

2. **风险**：git status 兜底可能不准确
   - **缓解**：在解析器中实现智能匹配，优先使用 XML 标签，git status 作为最后手段

## 与其他决策的关联

- **ADR 0006（显式群聊发言）**：本决策是对 0006 的调整，从显式工具调用改为直接输出
- **ADR 0011（Agent 工具语义与阻塞判定规则）**：本决策简化了工具语义，减少了阻塞判定的复杂性
- **ADR 0012（MCP 传输与平台迁移）**：本决策解决了 Codex 平台兼容性问题，与平台迁移目标一致
