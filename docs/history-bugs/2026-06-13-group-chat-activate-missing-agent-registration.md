# GroupChat.activate() 幂等性缺陷导致消息投递失败

**updated_at**: 2026-06-13

**状态**: ✅ 已修复（预防性修复），但根因未完全确认，待重构时进一步排查

## 问题描述

Manager 派活给前端执行者后，消息未送达。AgentCall 状态停留在 PENDING，前端执行者完全未收到任务。

**核心症状**：
- Call ID `936bf532` 创建成功（21:31:21）
- **消息投递完全没有日志**（既没有成功也没有失败）
- `send_message()` 的 DEBUG 日志缺失，说明消息根本没有进入投递流程
- 1小时9分钟后（22:40:42）该 call 被标记为 failed
- 日志中没有任何 ERROR/EXCEPTION

## 根本原因（未完全确认）

## 根本原因（未完全确认）

### 已确认的事实

1. **消息投递被完全跳过**
   - 21:31:21 创建 call 936bf532
   - **没有 `send_message()` 的任何日志**（无论成功或失败）
   - ⚠️ 注意：`send_message()` 使用 DEBUG 级别日志，当前日志级别为 INFO，因此看不到
   - **真实问题**：关键流程使用 DEBUG 日志，导致排查困难
   - 22:40:42 call 被标记为 failed（1小时9分钟后）

2. **应用频繁重启**
   - 20:47、20:49、21:04、21:07、21:11、21:19、21:21 多次重启
   - 原因：开发调试 + 端口 8765 冲突
   - 每次重启后 GroupChat 对象从磁盘重新加载

3. **MessageRouter 注册记录**
   - 21:21:24 agents 注册完成（MessageRouter_id=2429898331472）
   - 21:22:23 激活群聊，agents 正常工作
   - 21:31:21 创建 call 时**没有重新注册**

### 可能的原因（待确认）

#### 假设1：MessageRouter 被意外清空（可能性较高）
- 某个操作调用了 `message_router.clear()` 或批量 `unregister()`
- 但日志中没有找到 cleanup 或 unregister 的记录
- 需要重构时排查所有可能清空 MessageRouter 的路径

#### 假设2：消息投递代码路径被跳过（可能性中等）
- `send_message_to_agent()` 内部某个条件判断导致提前返回
- 异常被静默吞掉（虽然已增强日志，但可能仍有遗漏）

#### 假设3：GroupChat 实例不一致（可能性较低）
- 创建 call 和投递消息使用了不同的 GroupChat 实例
- 但日志显示 GroupChatManager_id 一致，且用户确认是从前端 @ 触发

### 排除的原因

1. ❌ **对象重建后未注册**：重启后 `load()` 会调用 `_init_agents()` 完成注册
2. ❌ **MCP 多进程问题**：用户确认是从前端 @ 触发，不走 MCP
3. ❌ **activate() 未调用**：21:22 已激活，agents 正常工作了一段时间

## 修复方案

### 实施的修复（预防性）

虽然根因未完全确认，但实施了以下修复以增强系统健壮性：

#### 1. 提取注册逻辑为独立方法（agents_hub/core/orchestration/group_chat.py）

新增 `_register_agents_to_router()` 方法（幂等）：
   
```python
def _register_agents_to_router(self):
    """注册所有 agents 到 MessageRouter（幂等）
    
    此方法可以安全地重复调用，MessageRouter.register() 是幂等的。
    """
    if self.manager is None:
        raise StateError("Manager 未初始化，请先调用 _init_agents()")
    
    # 注册 Manager
    self.message_router.register(self.manager.name, self.manager.message_queue)
    
    # 注册所有 Workers
    for worker in self.workers.values():
        self.message_router.register(worker.name, worker.message_queue)
    
    # 注册 user 伪 agent
    self.message_router.register(config.default_user_name, asyncio.Queue())
    
    # 注册 heartbeat 系统身份
    self.message_router.register("__HEARTBEAT__", asyncio.Queue())
    
    logger.info(
        "agents 注册完成: group=%s, 已注册agents=%s, MessageRouter_id=%s",
        self.group_chat_id,
        list(self.message_router._agents_queue.keys()),
        id(self.message_router),
    )
```

#### 2. 修改 activate() 确保注册

在 `activate()` 方法中添加注册调用：
   
```python
async def activate(self):
    """激活群聊：启动所有 agent 的 run() 任务"""
    if self._activated:
        return
    logger.info("激活群聊: id=%s", self.group_chat_id)
    
    # ⭐ 确保 agents 已注册到 MessageRouter（防止注册丢失）
    self._register_agents_to_router()
    
    self._start_agent_tasks()
    self._activated = True
```

**效果**：无论什么原因导致 MessageRouter 被清空，首次 `send_message_to_agent()` 时都会重新注册。

#### 3. 增强 _init_agents() 的幂等性

添加幂等性检查：
   
```python
async def _init_agents(self):
    """初始化 manager 和 workers，注册到 message_router"""
    
    # 幂等性检查：如果已初始化，直接返回
    if self.manager is not None:
        logger.debug("agents 已初始化，跳过: id=%s", self.group_chat_id)
        return
    
    logger.debug("初始化 agents: id=%s, members=%s", self.group_chat_id, self.team_members_name)
    # ... 后续逻辑保持不变
```

#### 4. 补充 stop_member() 的注销逻辑

agent 停止后从 MessageRouter 注销：
   
```python
# 从 MessageRouter 注销
self.message_router.unregister(agent_name)
logger.debug("Agent %s 已从 MessageRouter 注销", agent_name)
```

## 复现步骤

1. 创建群聊并激活（agents 注册到 MessageRouter）
2. 触发 GroupChat 对象重建（如热重载、服务重启）
3. **不调用 `_init_agents()`，直接发送消息**
4. `activate()` 被调用，但只启动任务不注册
5. 消息投递失败，AgentNotFoundError（DEBUG 级别不可见）

## 相关 Bug

- [MCP 创建群聊后发送消息报"接收者未注册"](./2026-06-08-mcp-created-group-chat-message-router-agent-not-registered.md) - 相同症状，当时未找到根因
- [API 路由创建独立 GroupChatManager 实例导致双 Manager 状态分裂](./2026-06-06-api-route-created-separate-group-chat-manager.md) - 也涉及 MessageRouter 注册问题
- [Manager run() 任务静默死亡导致消息队列堆积](./2026-06-14-manager-run-task-silent-death.md) - **延续**：修复 activate 幂等性后暴露的更深层问题，run() 任务缺乏异常监控

## 教训

1. **日志机制不完善是根本问题**：关键流程（`send_message()`）使用 DEBUG 级别，生产环境无法排查问题
2. **关键错误必须用 ERROR 级别**：AgentNotFoundError 是致命错误，不应该是 DEBUG 级别
3. **预防性修复的价值**：即使根因未找到，增强系统容错能力也是有意义的
4. **分层初始化容易漏步骤**：`_init_agents()` 负责注册，`activate()` 负责启动，两者分离容易导致遗漏

## 后续行动

### 重构时必须完成的排查

1. **完善日志机制（最高优先级）**
   - 在 `send_message_to_agent()` 入口添加 INFO 日志（记录 call_id、from、to）
   - 记录 MessageRouter 状态变化（注册/注销/清空）
   - 统一关键流程的日志级别规范

2. **排查消息投递被跳过的原因**
   - 完善日志后复现问题
   - 检查 `send_message_to_agent()` 的所有代码路径
   - 确认是否有条件判断导致提前返回

3. **排查 MessageRouter 被清空的原因**
   - 搜索所有 `message_router.clear()` 调用
   - 检查是否有批量 `unregister()` 
   - 确认 `cleanup()` 的调用时机和条件

### 改进建议

**日志级别规范**：
- **INFO**：关键流程入口/出口（消息投递、agent 启动/停止、GroupChat 生命周期）
- **ERROR**：所有异常抛出前、关键操作失败
- **DEBUG**：内部状态变化、详细参数

**本次修复的局限性**：
- ✅ 增强了系统容错能力（activate 时强制注册）
- ✅ 提升了错误可见性（ERROR 日志）
- ❌ 未找到真正的根因（因为日志不足）
- ⚠️ 重构时需要先完善日志，再复现并彻底解决问题
