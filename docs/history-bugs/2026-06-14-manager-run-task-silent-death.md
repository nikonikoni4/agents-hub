# Manager run() 任务静默死亡导致消息队列堆积

**updated_at**: 2026-06-14

**状态**: 🔍 诊断日志已添加，待复现确认根因

**关联**: [GroupChat.activate() 幂等性缺陷导致消息投递失败](./2026-06-13-group-chat-activate-missing-agent-registration.md) 的延续

## 问题描述

停止并重启 manager 后，用户发送的消息成功入队（queue_size 递增：3→4→5→6），但 manager 的 `run()` 任务不再消费消息。AgentCall 状态永远停在 PENDING。

**核心症状**：
- 13:50:40 manager 通过 `start_member` 重启，创建新 `asyncio.create_task(agent.run())`
- 13:50:40~13:51:13 manager 成功处理了 2 条 NOTIFICATION 消息
- 13:51:13 之后 manager 再无任何处理日志
- 13:51:46 用户发消息，queue_size=3，无人消费
- 13:56:26 queue_size=4，13:56:56 queue_size=5，持续增长
- 三条未处理消息（997d241f, dd99a34a, 0021b19d）AgentCall 状态均为 `pending`
- 日志中**没有** `执行异常`（_process_message 内部的 ERROR 日志）
- 日志中**没有** `Task exception was never retrieved`（因 self.manager_task 持有引用）

## 与前一个 Bug 的关系

前一个 Bug（2026-06-13）的核心问题是 `activate()` 幂等性缺陷 — 对象重建后 MessageRouter 注册丢失。本次修复了该问题后，暴露了更深层的问题：

**前一个 Bug**：消息投递失败（AgentNotFoundError）→ 消息根本没进队列
**本次 Bug**：消息成功入队，但消费者（run() 任务）静默死亡 → 消息堆积在队列中

两个 Bug 的共同根因：**`run()` 任务缺乏异常监控和恢复机制**。

## 根本原因（未完全确认）

### 已确认的事实

1. **`_process_message` 不是崩溃点**
   - `_process_message` 内部有 `self.logger.error("执行异常: ...", exc_info=True)`
   - 日志中没有此记录 → 崩溃不在 `_process_message`

2. **`run()` 任务停止消费但无异常日志**
   - 13:51:13 成功处理最后一条消息
   - 13:51:46 新消息入队但无人消费
   - 没有 `Task exception was never retrieved`（因 `self.manager_task` 持有 task 引用，GC 不触发警告）

3. **`_activated` 标志未被 `stop_member` 重置**
   - `stop_member` 不设置 `_activated = False`
   - 但 `start_member` 直接创建新 task，不经过 `activate()`，所以不是直接原因

4. **其他 agent 正常工作**
   - UI设计和界面布局 在 13:54:32 正常处理消息（queue_size=1）
   - 问题仅限于 manager 的 `run()` 任务

### 可能的崩溃点（无 error log）

`_run_loop` 结构：
```python
try:
    result = await self._process_message(msg, prompt)   # ← 有 error log，已排除
    await self._update_context_usage(result)             # ← 无 error log
finally:
    await self._sync_status("idle")                      # ← 无 error log
await self._fallback_close_task(msg, result)             # ← 无 error log，在 try/finally 之外
```

| 崩溃点 | 有 error log | 可能性 | 说明 |
|--------|-------------|--------|------|
| `_process_message` | **有** | 已排除 | 日志中没有 "执行异常" |
| `_update_context_usage` | 无 | 低 | 读取 usage 数据，不太可能抛异常 |
| `_sync_status("idle")` | 无 | 中 | 在 finally 中，按编码规则不做 catch |
| `_fallback_close_task` | 无 | **高** | 在 try/finally 之外，对 NOTIFICATION 直接 return |

### 排除的假设

1. ❌ **_process_message 崩溃**：有 error log，日志中没有
2. ❌ **_fallback_close_task 处理 NOTIFICATION 时崩溃**：NOTIFICATION 不满足前置条件（`call.message_type == MessageType.TASK`），直接 return
3. ❌ **heartbeat 干扰**：heartbeat 每 20 分钟一次，且只发消息不消费

## 诊断方案

### 已添加的诊断日志（base_agent.py）

```python
async def run(self):
    self.logger.info("Agent run() 启动: %s, 队列剩余=%d", self.name, self.message_queue.qsize())
    try:
        await self._run_loop()
    except asyncio.CancelledError:
        self.logger.info("Agent run() 被取消: %s", self.name)
        raise
    except Exception as e:
        self.logger.error(
            "Agent run() 异常退出: agent=%s, error=%s, queue_remaining=%d",
            self.name, str(e), self.message_queue.qsize(), exc_info=True,
        )
        raise
    finally:
        self.logger.warning(
            "Agent run() 已终止: agent=%s, _run=%s, queue_remaining=%d",
            self.name, self._run, self.message_queue.qsize(),
        )
```

### 已添加的诊断日志（group_chat.py）

1. **`_on_agent_task_done` 回调**：所有 `create_task` 都添加了 `add_done_callback`，检测 task 异常退出
2. **`_heartbeat_loop` 健康检查**：每次心跳检查 `manager_task.done()`，如果已退出记录 ERROR
3. **`_start_agent_tasks` / `start_member` / `reset_member` / `add_member`**：所有 create_task 均添加回调

### 日志级别规范（符合 CLAUDE.md）

| 场景 | 级别 | 理由 |
|------|------|------|
| run() 启动 | INFO | 生命周期事件 |
| run() 被取消 | INFO | 生命周期事件 |
| run() 异常退出 | ERROR | 异常抛出前，含完整 traceback |
| run() 已终止 | WARNING | finally 中，可疑状态 |
| 收到停止信号 | DEBUG | 内部状态检查 |
| 已处于 stopped 状态 | DEBUG | 幂等性检查 |
| 开始处理消息 | DEBUG | 循环内，已有 _process_message 内 INFO |
| task 异常退出回调 | ERROR | 检测到问题 |
| task 被取消回调 | DEBUG | 正常清理 |
| Manager run() 任务已退出 | ERROR | heartbeat 检测到问题 |

## 复现步骤

1. 创建群聊，启动所有 agent
2. 通过前端 stop_member 停止 manager
3. 通过前端 start_member 重启 manager
4. 发送消息给 manager
5. 观察 queue_size 是否递增但无消费日志

## 待确认

1. 下次复现时，`run()` 的顶层 try/except 会捕获完整 traceback，确认具体崩溃点
2. 如果 `_run_loop` 的 finally 中 `_sync_status("idle")` 抛异常，需要决定是否在 finally 中 catch
3. 是否需要在 `run()` 中添加自动重启机制

## 相关 Bug

- [GroupChat.activate() 幂等性缺陷导致消息投递失败](./2026-06-13-group-chat-activate-missing-agent-registration.md) — 前一个 Bug，消息投递失败
- [MCP 创建群聊后发送消息报"接收者未注册"](./2026-06-08-mcp-created-group-chat-message-router-agent-not-registered.md) — 相似症状
- [Manager Agent sleep 轮询循环 Bug](./2026-06-14-agent-sleep-polling-loop-and-async-receipt.md) — manager 行为异常

## 教训

1. **asyncio.create_task 的异常会被静默吞掉**：如果没人 await task，异常不会打印到日志（GC 时的警告也可能因引用存在而不触发）
2. **try/finally 不等于 try/except**：finally 只保证清理代码执行，不捕获异常
3. **run() 作为长生命周期协程必须有顶层异常处理**：否则任何未捕获异常都会导致 task 静默死亡
4. **缺少 task 健康监控**：没有 done_callback、没有 heartbeat 检查，task 死了没人知道
