# Issue 02: 集成 execute_with_first_response 到消息处理流程

**Status**: ready-for-agent
**Type**: AFK
**Blocked by**: Issue 01
**User stories covered**: 1, 5, 16

---

## Parent

关联 Issue 01

## What to build

在 `_process_message()` 的 MAIN 会话分支（base_agent.py line 339-344），将 `self.execute()` 调用替换为 `self.execute_with_first_response()`。

**修改位置**：
```python
# 修改前
result = await self.execute(
    full_prompt,
    use_docker=use_docker,
    group_chat_id=self.runtime.group_chat_id,
    system_prompt=system_prompt,
)

# 修改后
result = await self.execute_with_first_response(
    full_prompt,
    use_docker=use_docker,
    group_chat_id=self.runtime.group_chat_id,
    system_prompt=system_prompt,
)
```

**回滚方案**：只需将 `execute_with_first_response()` 改回 `execute()` 即可恢复原行为。

## Acceptance criteria

- [ ] `_process_message()` 中 MAIN 会话分支调用 `execute_with_first_response()`
- [ ] 参数传递与原 `execute()` 调用完全一致
- [ ] BTW 会话分支（line 351）不受影响，仍调用 `btw_execute()`
- [ ] 回滚方案可行：改回 `execute()` 即可恢复原行为

## Blocked by

- Issue 01: execute_with_first_response() 方法必须先实现

## Architecture Reference

详见架构约束文件：`.scratch/agent-first-response/architecture.md`
