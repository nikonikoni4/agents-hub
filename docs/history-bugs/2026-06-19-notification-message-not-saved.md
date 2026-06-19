---
version: 1.0
created_at: 2026-06-19
abstract: NOTIFICATION 消息在接收方不保存到群聊历史 - 设计漏洞
status: known_issue
---

# NOTIFICATION 消息在接收方不保存到群聊历史

## 问题描述

当 Agent（Worker）完成任务后发送 NOTIFICATION 给调用方（Manager）时，Manager 收到 NOTIFICATION 后不会将消息保存到群聊历史。

## 触发条件

所有 Agent 间通过 NOTIFICATION 通信的场景。

## 根因分析

### 完整消息流程

```
Manager → TASK (call_agent 保存) → Worker
    → Worker 处理消息
    → complete_task 或兜底 保存消息 + 发送 NOTIFICATION → Manager
    → Manager 收到 NOTIFICATION
    → _fallback_close_task 检查 msg.message_type != TASK → return
    → 消息不保存 ❌
```

### 代码位置

`agents_hub/core/agent/base_agent.py` `_fallback_close_task` 方法：

```python
async def _fallback_close_task(self, msg: AgentMessage, result: AgentResult | None) -> None:
    if msg.message_type != MessageType.TASK:
        return  # ← NOTIFICATION 在这里被跳过
    ...
```

### 设计漏洞

这是一个一开始就存在的设计漏洞：

1. **complete_task 只能回应 TASK**：complete_task 工具只能处理 TASK 类型的 AgentCall，不能回应 NOTIFICATION
2. **report_progress 已被禁用**：report_progress 原本可以用于汇报消息，但已被禁用（ADR 2026-06-16）
3. **兜底策略只处理 TASK**：`_fallback_close_task` 只处理 TASK 类型消息，NOTIFICATION 被直接跳过

## 变量分析

| 场景 | msg.type | has_agent_response | complete_task | 行为 |
|------|----------|-------------------|---------------|------|
| A | TASK | True | 存在且被使用 | 不进入兜底，complete_task 已保存 ✅ |
| B | TASK | False | 不存在或未使用 | 进入兜底，保存消息 ✅ |
| C | NOTIFICATION | - | - | 当前：不保存 ❌ |

## 影响

- Manager 收到 Worker 的 NOTIFICATION 后，消息不会出现在群聊历史中
- 用户无法在群聊中看到 NOTIFICATION 消息
- 但 Worker 的执行结果已经通过 `_fallback_close_task` 保存到群聊历史

## 修复方向

在 `_fallback_close_task` 或 `run()` 中增加对 NOTIFICATION 消息的保存逻辑。需要考虑：

1. 什么条件下 NOTIFICATION 需要保存？
2. 如何避免重复保存（Worker 已经保存了一次）？
3. 如何区分"兜底策略产生的 NOTIFICATION"和"complete_task 产生的 NOTIFICATION"？

## 相关文档

- ADR：`docs/adr/2026-06-16-mcp-tools-to-direct-output.md`
- Flow：`docs/flows/agent-call-lifecycle.md`
- Spec：`docs/specs/2026-06-05-message-flow-and-persistence.md`
