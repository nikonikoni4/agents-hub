# Issue 01: 实现 execute_with_first_response() 方法

**Status**: ready-for-agent
**Type**: AFK
**Blocked by**: None - 可立即开始
**User stories covered**: 1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18

---

## Parent

无 - 这是根切片

## What to build

在 `base_agent.py` 中新增 `execute_with_first_response()` 方法，作为 `execute_stream()` 的二次包装。

**核心逻辑**：
1. 内部调用 `agent_platform_client.execute_stream()` 获取流式事件
2. 遍历事件流，累积文本内容到 `first_text_buffer`
3. 检测首句完成条件：
   - Claude: `event.type == content_block_stop` 且 `block.type == text`
   - Codex: `event.type == item.completed` 且 `item.type == agent_message`
4. 首句完成时 → 立即调用 `runtime.add_message()` 写入群聊历史，触发前端刷新
5. 继续收集剩余内容到 `remaining_text`
6. 所有事件处理完毕 → 返回 `AgentResult(text=first_text + remaining_text)`

**边界情况处理**：
- 纯工具调用（无文本）：不发送首次响应
- 执行中途失败：仍发送已捕获的首次响应

**接口签名**：
```python
async def execute_with_first_response(
    self,
    prompt: str,
    use_docker: bool = False,
    group_chat_id: str | None = None,
    system_prompt: str | None = None,
) -> AgentResult:
```

## Acceptance criteria

- [ ] 方法签名与 `execute()` 兼容（相同的参数类型和返回类型）
- [ ] 复用 `execute_stream()` 获取流式事件，不重复造轮子
- [ ] 正确检测 Claude 平台首句完成条件（content_block_stop + text 类型）
- [ ] 正确检测 Codex 平台首句完成条件（item.completed + agent_message）
- [ ] 首句完成时调用 `runtime.add_message()` 写入群聊历史
- [ ] 返回的 `AgentResult.text` 包含首次响应 + 剩余内容（完整结果）
- [ ] 纯工具调用（无文本）时不发送首次响应
- [ ] 执行中途失败时仍发送已捕获的首次响应

## Blocked by

None - 可立即开始

## Architecture Reference

详见架构约束文件：`.scratch/agent-first-response/architecture.md`
