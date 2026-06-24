# PRD: 群聊 Agent 流式首响

**标签**: `ready-for-agent`
**创建时间**: 2026-06-24
**状态**: 待开发

---

## Problem Statement

在群聊场景中，用户 @agent 发送任务后，Agent 需要执行较长时间（可能涉及多轮工具调用）才能返回结果。当前实现是等待 Agent 完全执行完成后才一次性发送结果，期间用户无法得知 Agent 是否在工作，体验上像是"卡住了"。这导致用户焦虑，甚至重复发送消息或误以为系统故障。

## Solution

将 Agent 的一次性输出拆分为两次消息：
1. **首次响应（即时）**：Agent 收到任务后，立即发送第一句完整的话，让用户知道 Agent 已开始工作
2. **最终结果（完成时）**：Agent 执行完成后，发送剩余内容整合

这种"伪流式"方案既解决了交互体验问题，又不会因为过于频繁的消息而干扰用户。

## User Stories

1. As a 群聊用户, I want 在 @agent 后立即看到 Agent 的响应, so that 我知道 Agent 已收到任务并在工作中
2. As a 群聊用户, I want 首次响应是 Agent 输出的第一句完整的话, so that 我能了解 Agent 的初步理解和工作方向
3. As a 群聊用户, I want 最终结果包含完整的执行结果, so that 我能获取完整的任务执行结果
4. As a 群聊用户, I want 首次响应和最终结果是两条独立的消息, so that 我能清晰区分中间状态和最终结果
5. As a 系统管理员, I want 新功能与现有逻辑解耦, so that 出现问题时可以快速回滚
6. As a 开发者, I want 复用现有的 `execute_stream()` 能力, so that 不需要重复造轮子
7. As a 开发者, I want 新方法作为 `execute_stream()` 的二次包装, so that 逻辑清晰且易于维护
8. As a 系统, I want 支持 Claude 和 Codex 两个平台, so that 所有 Agent 角色都能使用此功能
9. As a Claude 平台, I want 通过检测第一个 `content_block_stop` (type=text) 来识别首句完成, so that 准确捕获第一个完整文本块
10. As a Codex 平台, I want 通过检测第一个 `item.completed` (type=agent_message) 来识别首句完成, so that 准确捕获 Agent 的第一条消息
11. As a 群聊系统, I want 首次响应写入群聊历史并触发前端刷新, so that 用户能实时看到响应
12. As a 群聊系统, I want 最终结果写入群聊历史并触发前端刷新, so that 用户能看到完整结果
13. As a 系统, I want 首次响应不影响最终结果的完整性, so that 最终结果仍然是完整的执行输出
14. As a 系统, I want 如果 Agent 输出没有文本内容（只有工具调用）, 则不发送首次响应, so that 避免发送空消息
15. As a 系统, I want 首次响应的消息格式与普通消息一致, so that 前端不需要额外处理
16. As a 开发者, I want 新增的 `execute_with_first_response()` 方法签名与 `execute()` 兼容, so that 调用方改动最小
17. As a 系统, I want 如果流式执行中途失败，仍然发送已捕获的首次响应, so that 用户至少能看到 Agent 的初步输出
18. As a 系统, I want 最终结果包含首次响应之后的所有内容, so that 不会丢失任何输出

## Implementation Decisions

### 1. 新增 `execute_with_first_response()` 方法

在 `base_agent.py` 中新增方法，作为 `execute_stream()` 的二次包装：

- 方法签名与 `execute()` 兼容，接收相同的参数
- 内部调用 `agent_platform_client.execute_stream()` 获取流式事件
- 检测首句完成条件，发送首次响应消息
- 继续收集剩余内容，最终发送完整结果
- 返回 `AgentResult` 与原 `execute()` 一致

### 2. 首句检测逻辑

**Claude 平台**：
- 遍历流式事件，累积 `TEXT_DELTA` 类型事件的内容
- 当收到 `content_block_stop` 且该块是文本类型时，判定为首句完成
- 发送累积的文本内容作为首次响应

**Codex 平台**：
- 遍历流式事件
- 当收到第一个 `item.completed` 且 `item.type == "agent_message"` 时，判定为首句完成
- 发送 `item.text` 作为首次响应

### 3. 消息发送机制

- 首次响应：调用 `runtime.add_message()` 写入群聊历史，触发前端刷新
- 最终结果：复用现有的 `_fallback_close_task()` 逻辑，确保消息正确保存
- 两次消息使用不同的标记区分，便于前端展示

### 4. 回滚方案

- 在 `_process_message()` 中，只需将 `execute_with_first_response()` 替换回 `execute()` 即可回滚
- 新方法完全独立，不影响现有 `execute()` 和 `execute_stream()` 方法

### 5. 复用现有能力

- 复用 `agent_platform_client.execute_stream()` 获取流式事件
- 复用 `runtime.add_message()` 写入群聊历史
- 复用 `_fallback_close_task()` 处理最终结果

## Testing Decisions

### 测试边界（Seams）

1. **Parser 层**：ClaudeParser 和 CodexParser 的事件解析
   - 已有测试：`tests/unit/agent_bridge/parsers/`
   - 验证：首句检测条件是否正确触发

2. **Bridge 层**：`execute_stream()` 的流式输出
   - 已有测试：`tests/unit/agent_bridge/`
   - 验证：流式事件是否正确传递

3. **Agent 层**：`execute_with_first_response()` 的业务逻辑
   - 新增测试：验证首次响应和最终结果的发送
   - 验证：消息格式、发送时机、异常处理

### 测试场景

1. **正常流程**：Agent 输出包含文本和工具调用，验证首次响应和最终结果正确发送
2. **纯文本输出**：Agent 只输出文本，无工具调用，验证首次响应和最终结果正确
3. **纯工具调用**：Agent 只执行工具，无文本输出，验证不发送首次响应
4. **执行失败**：Agent 执行中途失败，验证首次响应仍然发送
5. **多平台**：分别测试 Claude 和 Codex 平台的首句检测逻辑

## Out of Scope

1. **前端修改**：前端不需要改动，复用现有的消息展示逻辑
2. **实时逐字输出**：本方案是"伪流式"，不是真正的逐字实时输出
3. **工具调用过程展示**：首次响应只包含文本，不包含工具调用状态
4. **消息编辑/撤回**：首次响应发送后不可修改
5. **其他平台支持**：本期只支持 Claude 和 Codex，不包含 OpenCode

## Further Notes

### 性能考虑

- 首次响应的检测逻辑是轻量级的，不会增加明显的性能开销
- 流式事件的遍历是异步的，不会阻塞主线程

### 后续优化方向

- 如果用户反馈首次响应太慢（第一个文本块太长），可以考虑按句子分割
- 如果需要展示工具调用状态，可以在后续版本中增加 `TOOL_USE` 事件的处理
- 可以考虑增加首次响应的样式区分（如添加"正在思考中..."的标记）

---

**PRD 完成时间**: 2026-06-24
**需求来源**: 群聊用户交互体验优化
**关联文档**: `docs/temp/研究报告/CLI_AND_SDK/claude-codex-cli-output-analysis.md`
