# Issue 03: 添加 execute_with_first_response 单元测试

**Status**: ready-for-agent
**Type**: AFK
**Blocked by**: Issue 01
**User stories covered**: 1, 2, 3, 4, 13, 14, 17

---

## Parent

关联 Issue 01

## What to build

为 `execute_with_first_response()` 添加单元测试，覆盖以下场景：

1. **正常流程**：Agent 输出包含文本和工具调用
   - 验证首次响应和最终结果正确发送
   - 验证 `runtime.add_message()` 被调用一次

2. **纯文本输出**：Agent 只输出文本，无工具调用
   - 验证首次响应和最终结果正确

3. **纯工具调用**：Agent 只执行工具，无文本输出
   - 验证不发送首次响应（`runtime.add_message()` 不被调用）

4. **执行失败**：Agent 执行中途失败
   - 验证首次响应仍然发送（已捕获的内容写入群聊历史）

5. **多平台**：分别测试 Claude 和 Codex 平台的首句检测逻辑
   - Claude: 验证 `content_block_stop` + text 类型触发首响
   - Codex: 验证 `item.completed` + `agent_message` 触发首响

## Acceptance criteria

- [ ] 测试正常流程：首次响应和最终结果正确发送
- [ ] 测试纯文本输出：首次响应和最终结果正确
- [ ] 测试纯工具调用：不发送首次响应
- [ ] 测试执行失败：首次响应仍然发送
- [ ] 测试 Claude 平台首句检测逻辑
- [ ] 测试 Codex 平台首句检测逻辑
- [ ] 所有测试通过

## Blocked by

- Issue 01: execute_with_first_response() 方法必须先实现

## Architecture Reference

详见架构约束文件：`.scratch/agent-first-response/architecture.md`
