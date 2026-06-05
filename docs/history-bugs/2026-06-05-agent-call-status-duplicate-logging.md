# Bug: AgentCall 状态重复更新导致日志泛滥和 MCP 连接重建

**日期**：2026-06-05  
**状态**：已修复  
**影响范围**：`AgentCallManager`, 日志系统, MCP 连接管理

## 问题描述

系统日志中出现大量重复的状态变更记录：

```
2026-06-05 21:14:32 [agent_call_manager] INFO - 调用 f26c168b 状态变更: running -> running
2026-06-05 21:14:42 [agent_call_manager] INFO - 调用 f26c168b 状态变更: running -> running
2026-06-05 21:14:56 [agent_call_manager] INFO - 调用 f26c168b 状态变更: running -> running
...（持续重复）
```

同时每次状态更新都触发：
- 新的 MCP transport session 创建
- 持久化文件写入
- ListToolsRequest/ListPromptsRequest/ListResourcesRequest 请求

## 根本原因

### 问题 1: update_status 缺少状态检查（已修复）

`AgentCallManager.update_status()` 方法在状态相同时仍然执行：
- 记录 INFO 日志
- 调用 `_persist_call()` 写入持久化文件
- 触发下游逻辑

**触发路径**：
```python
# base_agent.py:191
async def _process_message(self, msg: AgentMessage, prompt: str):
    # 每次处理消息都调用 update_status(RUNNING)
    self.agent_call_manager.update_status(msg.call_id, CallStatus.RUNNING)
    
    # 如果 call 已经是 RUNNING 状态，这会导致：
    # 1. 记录 "running -> running"
    # 2. 持久化文件追加相同记录
    # 3. 下游系统误以为状态发生了变化
```

### 问题 2: finish_agent_call 提醒循环（需进一步调查）

从聊天记录可以看出，Agent 在完成任务后仍不断收到系统提醒：

```
系统提醒：你刚刚处理的是一个需要回复的 TASK 调用，但该调用尚未闭环。
请调用 finish_agent_call，传入 call_id=f26c168b
```

这表明 `call.has_agent_response` 没有被正确设置为 `True`。

**可能的原因**：
- `finish_agent_call` MCP tool 没有正确调用 `agent_call_manager.mark_agent_response()`
- 持久化/加载过程中 `has_agent_response` 字段丢失
- 并发竞争条件导致状态不一致

## 修复方案

### 已实施的修复

**文件**：`agents_hub/core/communication/agent_call_manager.py`

在 `update_status` 方法中增加状态检查：

```python
def update_status(self, call_id: str, status: CallStatus):
    if call := self._calls.get(call_id):
        old_status = call.status

        # 如果状态没有变化，跳过更新
        if old_status == status:
            self.logger.debug(f"调用 {call_id} 状态未变化，跳过更新: {status.value}")
            return

        # ... 原有逻辑
```

**测试覆盖**：`tests/utils/core/communication/test_agent_call_manager.py::test_update_same_status_skips_update`

### 待调查问题

需要进一步调查 `finish_agent_call` 提醒循环的根本原因：

1. 检查 `finish_agent_call` MCP tool 实现
2. 验证 `mark_agent_response()` 是否正确调用
3. 检查持久化逻辑是否正确保存 `has_agent_response` 字段
4. 添加更多日志来追踪状态变更

## 影响

### 修复前
- 日志文件快速增长
- 持久化文件包含大量冗余记录
- 每次重复更新都触发 MCP 连接重建，浪费资源
- 难以从日志中识别真实的状态变更

### 修复后
- 相同状态的更新被跳过，只记录 DEBUG 级别日志
- 减少不必要的持久化写入
- 避免触发下游的状态变更处理逻辑
- 日志更清晰，便于调试

## 相关文件

- `agents_hub/core/communication/agent_call_manager.py`
- `agents_hub/core/agent/base_agent.py`
- `tests/utils/core/communication/test_agent_call_manager.py`
- `agents_hub/mcp/server.py` (finish_agent_call tool)

## 经验教训

1. **状态机更新应该检查状态变化**：任何状态更新方法都应该先检查新旧状态是否相同，避免无意义的更新
2. **日志级别要恰当**：重复的、高频的日志应该使用 DEBUG 而不是 INFO
3. **持久化要谨慎**：频繁的持久化操作会影响性能，应该只在状态真正变化时执行
4. **测试要覆盖边界情况**：包括"相同状态的重复更新"这样的边界情况
