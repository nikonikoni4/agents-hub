---
version: 1.0
created_at: 2026-06-22
updated_at: 2026-06-22
last_updated: 2026-06-22
abstract: call_agent 的 need_response 参数让 AI 在 TASK/NOTIFICATION 间选择，但 AI 频繁误设导致后续 check_agent_call 失败。最终移除该参数，固定所有 call_agent 为 TASK 类型，通过缩小动作空间消除犯错可能。
status: decided
---

# call_agent 移除 need_response 参数

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建文档初稿 |

## 问题界定

### 问题简述

Manager 通过 MCP 工具 `call_agent` 派活给团队成员时，`need_response` 参数决定创建 TASK（需回复）还是 NOTIFICATION（通知）类型的 AgentCall。AI 频繁错误地设置 `need_response=False`（创建 NOTIFICATION），但后续又通过 `check_agent_call` 查询状态等待回复。NOTIFICATION 类型完成后不会触发通知机制，且保留时间短会被清理，导致 Manager 查不到结果。

### 讨论范围

- `call_agent` MCP 工具的参数设计
- AgentCall 的消息类型（TASK vs NOTIFICATION）对生命周期的影响
- AI 动作空间大小与系统稳定性的关系

### 非讨论范围

- 系统内部由代码控制的 NOTIFICATION（如 `_fallback_close_task` 中的通知机制）不受影响
- `check_agent_call` 工具本身的保留（仍需要，用于查询 TASK 状态）

### 问题深度

这是接口设计层面的决策：暴露给 AI 的参数是否应该存在。涉及"AI 动作空间"与"系统稳定性"的权衡。

## 现状

`call_agent` 签名：

```python
async def call_agent(
    agent_token: str,
    send_to: str,
    content: str,
    need_response: bool = True,  # 问题根源
    timeout_seconds: int | None = None,
) -> dict
```

**问题链**：
1. AI 设 `need_response=False` → 创建 NOTIFICATION 类型 AgentCall
2. Agent 处理完 NOTIFICATION 后，`_fallback_close_task` 跳过（`msg.message_type != TASK`）
3. 调用方不会收到完成通知
4. Manager 用 `check_agent_call` 查询时，NOTIFICATION 可能已被清理

**已有缓解措施**（不充分）：
- `NOTIFICATION_RETENTION_SECONDS` 从 300s 延长到 1500s（25 分钟）
- 依赖心跳检查清理，响应慢

## 可选方案

### 方案 A：延长 NOTIFICATION_RETENTION_SECONDS

保留 `need_response` 参数，通过延长 NOTIFICATION 的保留时间让 `check_agent_call` 能查到结果。

**优势**

- 不改变接口，向后兼容
- 实现简单，只改配置值

**劣势**

- 治标不治本：AI 仍然会误设参数，只是清理时间变长
- 依赖心跳检查周期（20 分钟），响应延迟大
- NOTIFICATION 完成后不触发通知机制，Manager 仍需主动轮询
- 增加内存占用（更多 NOTIFICATION 记录驻留更久）

### 方案 B：移除 need_response，固定 TASK 类型

移除 `need_response` 参数，所有 `call_agent` 调用固定创建 TASK 类型 AgentCall。

**优势**

- 从根源消除 AI 犯错的可能（参数不存在就不可能设错）
- TASK 类型完成后自动触发 `_fallback_close_task` 通知调用方
- 简化接口，减少 LLM 的参数决策负担
- 清理策略更合理（TASK 保留 1 小时 vs NOTIFICATION 保留 5-25 分钟）

**劣势**

- Manager 发送不需要回复的消息时，也会创建 TASK，接收方处理完会通知调用方
- 接口变更，需要同步更新测试和文档

## 演进历史

| 版本 | 方案 | 解决的问题 | 引入的新问题 |
| ---- | ---- | ---------- | ------------ |
| v1 | 延长 NOTIFICATION_RETENTION_SECONDS 到 1500s | NOTIFICATION 被过早清理 | AI 仍会误设参数，心跳响应慢，只是延迟了问题 |
| v2 | 移除 need_response 参数，固定 TASK | AI 无法再误设参数 | 不需要回复的消息也会触发通知（影响极小） |

## 最终决策

选择 **方案 B：移除 need_response，固定 TASK 类型**。

## 决策原因

1. **缩小动作空间优于延长保留时间**：问题根因是 AI 在 TASK/NOTIFICATION 间做出了错误选择。延长保留时间只是让错误的后果延迟显现，而移除选择权直接消除犯错可能。

2. **TASK 的生命周期语义更完整**：TASK 类型完成后自动触发 `_fallback_close_task` 通知调用方，Manager 无需主动轮询。NOTIFICATION 完成后不触发通知，调用方只能靠 `check_agent_call` 查询。

3. **实际场景中"不需要回复"的情况极少**：Manager 派活给团队成员的典型场景都是需要知道结果的。即使偶尔有纯通知需求，接收方多发一个通知的代价远小于 Manager 查不到结果的代价。

4. **接口简化降低 LLM 负担**：少一个参数意味着少一次决策，LLM 工具调用的稳定性与参数数量负相关。

## 后续影响

- `call_agent` 接口简化，不再有 `need_response` 参数
- 所有 `call_agent` 调用固定创建 TASK 类型 AgentCall
- 系统内部的 NOTIFICATION 机制（`_fallback_close_task` 中的通知、`_send_agent_call_completion_notification`）不受影响，由代码控制
- `agent_context.py` 中的 `need_response` 字段仍根据 `msg.message_type` 动态推导，`call_agent` 消息将始终显示 `need_response="true"`
- 测试文件已同步更新：移除 `need_response` 调用，替换 notification 类型测试为 always-task 测试
