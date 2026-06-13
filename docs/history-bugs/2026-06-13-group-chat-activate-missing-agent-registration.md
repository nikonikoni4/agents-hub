# GroupChat.activate() 幂等性缺陷导致消息投递失败

**updated_at**: 2026-06-13

## 问题描述

Manager 通过 MCP `call_agent` 派活给前端执行者后，消息一直未送达。AgentCall 状态停留在 PENDING，前端执行者完全未收到任务。

**核心症状**：
- Call ID `936bf532` 创建成功（21:31:21）
- MCP 工具返回 `{"call_id":"936bf532"}`，未报错
- 前端执行者最后活动时间 21:28:30，之后停止工作
- 日志中没有任何 ERROR/EXCEPTION，只有 call 创建日志

## 根本原因

### 触发条件

GroupChat 对象被重新创建（如服务重启、热重载、GC 回收后重新加载）后，首次调用 `send_message_to_agent()` 时：

1. **新 GroupChat 实例的 MessageRouter 是全新对象**（agents 未注册）
2. `send_message_to_agent()` 调用 `activate()` 懒加载启动 agents
3. `activate()` 只检查 `_activated` 标志（实例变量）
4. 如果 `_activated=False`，只启动 agent 任务，**不重新注册 agents 到 MessageRouter**
5. 消息投递时，MessageRouter 中找不到接收者，抛出 `AgentNotFoundError`

### 代码位置

**agents_hub/core/orchestration/group_chat.py:151-162**
```python
async def activate(self):
    """激活群聊：启动所有 agent 的 run() 任务"""
    if self._activated:  # ⚠️ 只检查实例变量
        return
    logger.info("激活群聊: id=%s", self.group_chat_id)
    self._start_agent_tasks()  # ⚠️ 只启动任务，不注册
    self._activated = True
```

**agents_hub/core/orchestration/group_chat.py:208-221**
```python
async def _init_agents(self):
    """初始化 manager 和 workers，注册到 message_router"""
    ...
    # 注册所有 agent 到 message_router
    self.message_router.register(self.manager.name, self.manager.message_queue)
    for worker in self.workers.values():
        self.message_router.register(worker.name, worker.message_queue)
    # ⚠️ 注册在 _init_agents() 中，但 activate() 不调用它
```

**agents_hub/core/communication/message_router.py:114-122**
```python
if message.send_to not in self._agents_queue:
    logger.debug(  # ⚠️ DEBUG 级别，日志中不可见
        "消息校验失败: call_id=%s, 原因=接收者 '%s' 未注册, 已注册agents=%s",
        message.call_id,
        message.send_to,
        list(self._agents_queue.keys()),
    )
    raise AgentNotFoundError(message.send_to)
```

### 时间线证据

```
20:50:08 - agents 注册完成 (MessageRouter_id=2670173702864)
20:55:39 - 激活群聊
21:19:28 - agents 重新注册 (MessageRouter_id=3010499645120) ← GroupChat 重建
21:21:24 - agents 再次注册 (MessageRouter_id=2429898331472) ← 又一次重建
21:22:23 - 激活群聊（第二次）
21:31:21 - 创建 call 936bf532，没有注册日志！ ← bug 发生
          MCP 返回成功但消息未送达
```

**MessageRouter ID 变化**证明 GroupChat 被多次重建，但第三次重建后没有重新注册。

### 为什么异常没有体现在日志中

1. `AgentNotFoundError` 日志级别是 **DEBUG**（message_router.py:116）
2. 异常在 `message_router.send_message()` 抛出后应传播到 MCP 层
3. 但 MCP `call_agent` 返回成功 `{"call_id":"936bf532"}`，说明异常被某处吞掉（待进一步排查）

## 修复方案

### 方案 1：在 activate() 中强制重新注册（推荐）

**目标**：确保每次激活时 agents 都已注册到 MessageRouter

```python
async def activate(self):
    """激活群聊：启动所有 agent 的 run() 任务"""
    if self._activated:
        return
    logger.info("激活群聊: id=%s", self.group_chat_id)
    
    # ⭐ 确保 agents 已注册到 MessageRouter
    self._register_agents_to_router()
    
    self._start_agent_tasks()
    self._activated = True

def _register_agents_to_router(self):
    """注册所有 agents 到 MessageRouter（幂等）"""
    if self.manager is None:
        raise StateError("Manager 未初始化，请先调用 _init_agents()")
    
    # 幂等注册（register 可重复调用）
    self.message_router.register(self.manager.name, self.manager.message_queue)
    for worker in self.workers.values():
        self.message_router.register(worker.name, worker.message_queue)
    self.message_router.register(config.default_user_name, asyncio.Queue())
    self.message_router.register("__HEARTBEAT__", asyncio.Queue())
    
    logger.info(
        "agents 注册完成: group=%s, 已注册agents=%s, MessageRouter_id=%s",
        self.group_chat_id,
        list(self.message_router._agents_queue.keys()),
        id(self.message_router),
    )
```

**优点**：
- 根本解决问题，无论 GroupChat 重建多少次都能正确注册
- 保持 activate() 的懒加载语义
- 注册操作幂等，重复调用无副作用

### 方案 2：AgentNotFoundError 改为 ERROR 级别（临时方案）

**目标**：让问题可见，方便排查

```python
# agents_hub/core/communication/message_router.py:114
if message.send_to not in self._agents_queue:
    logger.error(  # 改为 ERROR
        "消息校验失败: call_id=%s, 原因=接收者 '%s' 未注册, 已注册agents=%s, MessageRouter_id=%s",
        message.call_id,
        message.send_to,
        list(self._agents_queue.keys()),
        id(self),
    )
    raise AgentNotFoundError(message.send_to)
```

**优点**：
- 快速实施，立即可见
- 帮助定位其他潜在的未注册问题

**缺点**：
- 不解决根本问题，只是让问题可见

### 方案 3：检查为什么 MCP 异常被吞掉（补充排查）

需要确认 `group_chat.send_message_to_agent()` 抛出的 `AgentNotFoundError` 为什么没有传播到 MCP 层。

检查点：
1. `mcp/server.py:236` 的 `await group_chat.send_message_to_agent(message)` 周围是否有隐式 try-catch
2. `group_chat.py:458` 的 `await self.message_router.send_message(message)` 是否被意外捕获
3. MCP 层的异常处理顺序（line 242-257）是否正确

## 复现步骤

1. 创建群聊并激活（agents 注册到 MessageRouter）
2. 触发 GroupChat 对象重建（如热重载、服务重启）
3. **不调用 `_init_agents()`，直接发送消息**
4. `activate()` 被调用，但只启动任务不注册
5. 消息投递失败，AgentNotFoundError（DEBUG 级别不可见）

## 相关 Bug

- [MCP 创建群聊后发送消息报"接收者未注册"](./2026-06-08-mcp-created-group-chat-message-router-agent-not-registered.md) - 相同症状，当时未找到根因
- [API 路由创建独立 GroupChatManager 实例导致双 Manager 状态分裂](./2026-06-06-api-route-created-separate-group-chat-manager.md) - 也涉及 MessageRouter 注册问题

## 教训

1. **幂等性设计需考虑对象生命周期**：`_activated` 是实例变量，对象重建后会重置，需要确保重建后的激活过程完整
2. **关键错误必须用 ERROR 级别**：AgentNotFoundError 是致命错误，不应该是 DEBUG 级别
3. **分层初始化容易漏步骤**：`_init_agents()` 负责注册，`activate()` 负责启动，两者分离容易导致遗漏
4. **异常传播路径必须清晰**：MCP 返回成功但实际失败，说明异常被意外吞掉，需要排查
