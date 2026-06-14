# Agent 生命周期审查报告

生成时间: 2026-06-14  
审查范围: `agents_hub/core/orchestration/group_chat.py`, `agents_hub/core/agent/base_agent.py`, `agents_hub/core/communication/message_router.py`

---

## 1. 创建与初始化

### 1.1 GroupChat 创建入口

**主入口**: `GroupChatManager.create_group_chat()` (group_chat_manager.py:374-428)

```
流程:
1. 创建 GroupChat 实例 (传入 team_members_name, group_type, project_path, group_chat_id)
2. 调用 group_chat.start() 启动
3. 注册到 GroupChatManager
```

### 1.2 Agent 初始化流程 (`_init_agents`)

**位置**: group_chat.py:172-221

**完整流程**:

```python
1. 获取 RoleManager 实例
2. 初始化 Manager:
   - 获取 manager_role (config.default_manager_name)
   - 创建 Manager(role, context, agent_call_manager, message_router, task_manager)
   
3. 初始化 Workers:
   - 遍历 team_members_name
   - 跳过 manager 名称
   - 为每个成员获取 role
   - 创建 Worker(role, context, agent_call_manager, message_router, task_manager)
   - 存入 self.workers 字典

4. ⭐ 注册到 MessageRouter:
   - self.message_router.register(manager.name, manager.message_queue)
   - 遍历 workers，注册每个 worker
   - 注册 "user" 伪 agent (asyncio.Queue())
   - 注册 "__HEARTBEAT__" 系统身份 (asyncio.Queue())
```

**关键点**:
- MessageRouter 注册发生在 Agent 创建之后
- 所有 Agent 共享同一个 GroupChatContext
- Manager 和 Worker 都持有相同的依赖组件引用

### 1.3 AgentMemberInfo 初始化

**位置**: runtime.get_or_create_agent_member_info()

初始化数据:
- token: 空 (后续由 _generate_and_register_tokens 填充)
- main_session: None
- btw_session: []
- status: "idle"
- context_usage: 0
- cwd: project_path (默认)

---

## 2. 启动流程

### 2.1 start() - 首次创建启动

**位置**: group_chat.py:86-126

```
完整链路:
1. 加载上下文数据 (group_chat_context.load())
2. 初始化并保存群聊元数据 (runtime.initialize_metadata())
3. 初始化并注册 agents (_init_agents())
   └─ 创建 Manager/Workers
   └─ 注册到 MessageRouter
4. 生成并注册 token (_generate_and_register_tokens())
   └─ 为每个 agent 生成 token
   └─ 注册到 GroupChatManager.register_token()
   └─ 更新 runtime (set_agent_token_and_default_cwd)
5. 初始化新成员 (_initialize_new_members())
   └─ 打招呼，执行首轮对话
6. 启动所有 agent 任务 (_start_agent_tasks())
   └─ 设置 _activated = True
```

### 2.2 load() - 加载已有群聊

**位置**: group_chat.py:128-149

```
流程 (不启动 agent):
1. 加载上下文数据 (group_chat_context.load())
2. 初始化并注册 agents (_init_agents())
   └─ 创建 Manager/Workers
   └─ 注册到 MessageRouter
3. 恢复并注册 token (_restore_and_register_tokens())
   └─ 从 runtime 读取已有 token
   └─ 注册到 GroupChatManager
   └─ 如果缺失，生成新 token
4. 初始化新成员 (_initialize_new_members())
```

**注意**: load() 不调用 _start_agent_tasks()，需要手动调用 activate()

### 2.3 activate() - 激活 agent.run() 任务

**位置**: group_chat.py:151-162

```
流程:
1. 检查 _activated 标志 (幂等性)
2. 调用 _start_agent_tasks()
3. 设置 _activated = True
```

### 2.4 _start_agent_tasks() - 内部任务启动

**位置**: group_chat.py:164-170

```
流程:
1. 校验 manager 已初始化
2. 创建 manager_task = asyncio.create_task(manager.run())
3. 为每个 worker 创建 task:
   worker_tasks[name] = asyncio.create_task(worker.run())
4. 启动 heartbeat 任务 (_heartbeat_task)
```

### 2.5 Agent.run() 循环

**位置**: base_agent.py:585-662

```
核心循环:
while self._run:
    1. 从 message_queue 获取消息 (await queue.get())
    2. 检查停止信号 (call_id == "__STOP__")
    3. 检查 agent 状态 (跳过 stopped 状态)
    4. 渲染 prompt (render_for_llm)
    5. 更新状态为 "busy" 或 "chatting"
    6. 处理消息 (_process_message)
    7. 更新 context_usage
    8. 恢复状态为 "idle"
    9. 兜底闭环 (_fallback_close_task)
```

---

## 3. 运行时操作

### 3.1 start_member() - 重启已停止的 agent

**位置**: group_chat.py:665-724

```
流程:
1. 查找 agent (manager 或 worker)
2. 校验状态为 "stopped"
3. 重置 agent._run = True
4. 创建新 asyncio.Task:
   - manager: self.manager_task = asyncio.create_task(agent.run())
   - worker: self.worker_tasks[name] = asyncio.create_task(agent.run())
5. 更新状态为 "idle"
```

**问题**: ❌ **未重新注册到 MessageRouter**

### 3.2 stop_member() - 停止运行中的 agent

**位置**: group_chat.py:572-636

```
流程:
1. 查找 agent
2. 更新状态为 "stopped"
3. ⭐ 终止 CLI 进程 (_stop_agent_process)
4. 调用 agent.stop() 发送停止信号
5. 取消 asyncio.Task:
   - manager: 取消 manager_task
   - worker: 从 worker_tasks 删除并取消
6. 清空消息队列并闭环未完成的 AgentCall (_cleanup_agent_queue)
```

**问题**: ❌ **未从 MessageRouter 注销**

### 3.3 reset_member() - 重置 agent (清空上下文)

**位置**: group_chat.py:726-800

```
流程:
1. 查找 agent
2. 如果正在运行，先调用 stop_member()
3. 清空 main_session 和 btw_sessions
4. 清空消息队列
5. 重置 context_usage = 0
6. 重新初始化 (_initialize_single_member, 打招呼)
7. 自动启动 (设置 _run=True, 创建 task)
8. 更新状态为 "idle"
```

**问题**: ❌ **未重新注册到 MessageRouter** (依赖 stop_member 后残留的注册)

### 3.4 add_member() - 增量添加成员

**位置**: group_chat.py:223-282

```
流程:
1. 验证角色存在
2. 幂等检查 (已存在则跳过)
3. 创建新 Worker
4. ⭐ 注册到 MessageRouter (register)
5. 添加到 workers 字典
6. 立即持久化到 agent_member.json
7. 生成并注册 token
8. 如果群聊已激活，启动新任务
9. 更新 team_members_name
10. 初始化新成员 (打招呼)
```

**正确**: ✅ 正确注册到 MessageRouter

### 3.5 compress_context() - 压缩上下文

**位置**: base_agent.py:305-423

```
流程:
1. 忙碌校验
2. 发送压缩 prompt 给当前 session
3. 提取摘要
4. 写入留痕文件 (docs/hand-off/)
5. 清空 main_session
6. 用摘要新建 session (失败时回滚)
7. 更新留痕文件中的 new_session_id
8. 重置 context_usage = 0
9. 写入系统消息
```

**注意**: 不影响 MessageRouter 注册

---

## 4. 销毁流程

### 4.1 cleanup() - 清理所有资源

**位置**: group_chat.py:817-891

```
流程:
1. 停止所有 Agent (调用 agent.stop())
2. 停止 heartbeat 任务
3. 等待所有任务完成 (超时则强制取消)
4. 停止 AgentCallManager 清理任务
5. ⭐ 清空 MessageRouter (message_router.clear())
6. 关闭 GroupChatContext
7. 注销所有 token (group_chat_manager.unregister_tokens)
8. 清空引用 (workers, manager, tasks)
```

### 4.2 Agent.stop() - 停止 run() 循环

**位置**: base_agent.py:88-114

```
流程:
1. 设置 _run = False
2. 发送哨兵消息 (call_id="__STOP__") 唤醒阻塞的 queue.get()
```

### 4.3 MessageRouter.clear() - 清空路由表

**位置**: message_router.py:124-142

```
流程:
1. 清空所有队列中的消息
2. 清空 _agents_queue 字典
```

**注意**: 这是唯一批量注销 MessageRouter 的地方

### 4.4 GroupChatManager.unregister() - 注销群聊

**位置**: group_chat_manager.py:146-170

```
流程:
1. 获取 group_chat
2. 调用 group_chat.cleanup(timeout)
3. 从 _group_chats 字典删除
4. 清理该 GroupChat 的所有 token (unregister_tokens)
```

---

## 5. MessageRouter 注册问题专项

### 5.1 所有注册调用点

| 调用位置 | 场景 | 操作 |
|---------|------|------|
| `_init_agents()` L209-214 | 创建/加载群聊 | ✅ 注册 manager + workers + user + heartbeat |
| `add_member()` L254 | 增量添加成员 | ✅ 注册新 worker |
| `cleanup()` L876 | 清理群聊 | ✅ 批量清空 (clear()) |

### 5.2 所有注销调用点

| 调用位置 | 场景 | 操作 |
|---------|------|------|
| `cleanup()` L876 | 清理群聊 | ✅ 批量清空 (clear()) |
| ❌ **缺失** | stop_member | ❌ 未注销 |
| ❌ **缺失** | start_member | ❌ 未重新注册 |
| ❌ **缺失** | reset_member | ❌ 未处理注册 |

### 5.3 MessageRouter.unregister() 方法

**位置**: message_router.py:37-44

```python
def unregister(self, name: str):
    """注销 Agent 的消息队列"""
    self._agents_queue.pop(name, None)
```

**状态**: ✅ 方法存在，但 ❌ **从未被单独调用**

---

## 6. 发现的问题

### ❌ P0 - MessageRouter 注册不完整

**问题描述**:
1. `stop_member()` 停止 agent 后，未从 MessageRouter 注销
2. `start_member()` 重启 agent 后，未重新注册到 MessageRouter (依赖残留注册)
3. `reset_member()` 内部调用 `stop_member()`，同样未重新注册

**代码位置**:
- group_chat.py:572-636 (stop_member)
- group_chat.py:665-724 (start_member)
- group_chat.py:726-800 (reset_member)

**影响范围**:
- stop 后 agent 仍在 MessageRouter 中，可能收到消息 (但 run() 已停止，消息堆积在队列)
- start 后如果 MessageRouter 中的注册被清理，agent 无法收到消息
- reset 后状态不一致

**建议修复**:
```python
# stop_member() 添加:
async def stop_member(self, agent_name: str) -> dict:
    # ... 现有逻辑 ...
    
    # 6. 从 MessageRouter 注销
    self.message_router.unregister(agent_name)
    
    logger.info("Agent %s 已停止并注销", agent_name)
    return {...}

# start_member() 添加:
async def start_member(self, agent_name: str) -> dict:
    # ... 现有逻辑 ...
    
    # 3.5 重新注册到 MessageRouter
    agent = self._find_agent(agent_name)
    self.message_router.register(agent_name, agent.message_queue)
    
    # 4. 创建新任务
    # ...
```

**严重程度**: 🔴 高 - 可能导致消息丢失或状态不一致

---

### ❌ P1 - stop_member 后消息队列残留

**问题描述**:
`stop_member()` 在取消 asyncio.Task 后调用 `_cleanup_agent_queue()`，但此时 agent 仍在 MessageRouter 中注册，新消息仍可能投递到队列。

**代码位置**: group_chat.py:626-628

```python
# 5. 强制取消 agent 的 asyncio.Task
# ... cancel task ...

# 6. 清空消息队列并闭环未完成的 AgentCall
processed_calls = await self._cleanup_agent_queue(agent_name)
```

**影响范围**:
- 清空队列后，新消息仍可能投递 (因为 MessageRouter 未注销)
- 时序竞争：cleanup 和新消息投递并发

**建议修复**:
调整顺序，先注销 MessageRouter，再清理队列:
```python
# 5. 从 MessageRouter 注销 (阻止新消息投递)
self.message_router.unregister(agent_name)

# 6. 强制取消 agent 的 asyncio.Task
# ...

# 7. 清空消息队列并闭环未完成的 AgentCall
processed_calls = await self._cleanup_agent_queue(agent_name)
```

**严重程度**: 🟡 中 - 竞态条件，低概率但可能导致消息处理异常

---

### ❌ P2 - reset_member 未显式处理 MessageRouter

**问题描述**:
`reset_member()` 依赖 `stop_member()` 的注销，但 `stop_member()` 当前未注销 MessageRouter，导致 reset 后状态不一致。

**代码位置**: group_chat.py:758-760

```python
# 2. 如果正在运行，先停止
if agent_member_info and agent_member_info.status != "stopped":
    await self.stop_member(agent_name)
```

**影响范围**:
- reset 后 agent 可能无法收到消息 (如果 stop 时注销了)
- 或者收到旧队列中的消息 (如果 stop 时未注销)

**建议修复**:
在 reset_member 中显式处理注册:
```python
# 2. 如果正在运行，先停止 (会注销 MessageRouter)
if agent_member_info and agent_member_info.status != "stopped":
    await self.stop_member(agent_name)

# 3. 清空 main_session 和 btw_sessions
# ...

# 7. 重新注册到 MessageRouter
agent = self._find_agent(agent_name)
self.message_router.register(agent_name, agent.message_queue)

# 8. 自动启动
# ...
```

**严重程度**: 🟡 中 - 依赖 P0 修复

---

### ⚠️ P3 - activate() 幂等性未验证任务状态

**问题描述**:
`activate()` 只检查 `_activated` 标志，未验证 asyncio.Task 是否真的在运行。

**代码位置**: group_chat.py:151-162

```python
async def activate(self):
    if self._activated:
        return  # 直接返回，不检查 task 状态
    logger.info("激活群聊: id=%s", self.group_chat_id)
    self._start_agent_tasks()
    self._activated = True
```

**影响范围**:
- 如果 task 因异常退出，但 `_activated=True`，activate() 不会重启 task
- 低概率场景：agent.run() 抛出未捕获异常

**建议修复**:
```python
async def activate(self):
    if self._activated:
        # 校验 task 是否真的在运行
        if self.manager_task and not self.manager_task.done():
            return  # 确实在运行，幂等返回
        # 否则重新启动
        logger.warning("群聊已标记为激活，但 task 已退出，重新启动")
    logger.info("激活群聊: id=%s", self.group_chat_id)
    self._start_agent_tasks()
    self._activated = True
```

**严重程度**: 🟢 低 - 异常场景，但会导致 agent 失联

---

### ⚠️ P4 - cleanup() 超时后未验证取消结果

**问题描述**:
`cleanup()` 超时后强制取消所有 task，但未验证取消是否成功。

**代码位置**: group_chat.py:864-870

```python
except asyncio.TimeoutError:
    # 超时则强制取消
    for task in tasks:
        if not task.done():
            task.cancel()
    # 等待取消完成
    await asyncio.gather(*tasks, return_exceptions=True)
```

**影响范围**:
- 如果 task 无法被取消 (极端场景，如阻塞 C 扩展)，资源无法释放
- `return_exceptions=True` 吞掉了所有异常，无法观测

**建议修复**:
```python
except asyncio.TimeoutError:
    logger.warning("清理超时，强制取消所有任务")
    for task in tasks:
        if not task.done():
            task.cancel()
    # 等待取消完成，记录失败的任务
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for task, result in zip(tasks, results):
        if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
            logger.error("任务取消失败: %s, error=%s", task.get_name(), result)
```

**严重程度**: 🟢 低 - 极端场景

---

### ✅ 正确实现 - add_member()

**亮点**:
1. ✅ 正确注册到 MessageRouter (L254)
2. ✅ 立即持久化 AgentMemberInfo (L260-261)
3. ✅ 生成并注册 token (L265-268)
4. ✅ 群聊已激活时启动任务 (L271-274)
5. ✅ 初始化新成员 (L280)

**代码位置**: group_chat.py:223-282

---

## 7. 幂等性与并发安全性评估

### 7.1 幂等性评估

| 操作 | 幂等性 | 说明 |
|------|-------|------|
| `start()` | ❌ 否 | 重复调用会重复注册 MessageRouter，导致覆盖 |
| `load()` | ❌ 否 | 同 start()，重复调用会覆盖注册 |
| `activate()` | ✅ 是 | 检查 `_activated` 标志 |
| `stop_member()` | ⚠️ 部分 | 状态检查不完整，task 可能已取消 |
| `start_member()` | ⚠️ 部分 | 状态检查存在，但未检查 task 是否已存在 |
| `reset_member()` | ⚠️ 部分 | 依赖 stop_member 的幂等性 |
| `add_member()` | ✅ 是 | 幂等检查 (L240-242) |
| `cleanup()` | ✅ 是 | 可多次调用，操作均为幂等 |

### 7.2 并发安全性评估

| 操作 | 并发安全 | 风险点 |
|------|---------|--------|
| `send_message_to_agent()` | ✅ 是 | MessageRouter 投递是线程安全的 (asyncio.Queue) |
| `stop_member()` | ⚠️ 风险 | cleanup_queue 和新消息投递有竞态 |
| `start_member()` | ⚠️ 风险 | 未加锁，并发 start 可能创建多个 task |
| `reset_member()` | ⚠️ 风险 | stop + 清空 + start 有竞态窗口 |
| `add_member()` | ⚠️ 风险 | 未加锁，并发添加可能重复创建 |
| `cleanup()` | ✅ 是 | 统一协调所有清理，单入口 |

**建议**:
- 为 stop/start/reset/add_member 添加 agent 级别的锁
- 或在 GroupChat 级别添加操作锁 (防止并发修改 workers 字典)

---

## 8. 总结与修复优先级

### 8.1 核心问题

1. **MessageRouter 生命周期管理不完整** (P0)
   - stop_member 未注销
   - start_member 未重新注册
   - reset_member 未显式处理

2. **操作顺序问题** (P1)
   - stop_member 应先注销 MessageRouter，再清理队列

3. **幂等性与并发安全性不足** (P2-P3)
   - 缺少操作锁
   - 状态校验不完整

### 8.2 修复建议优先级

**必须修复 (阻塞)**:
- [ ] P0: stop_member() 添加 MessageRouter 注销
- [ ] P0: start_member() 添加 MessageRouter 重新注册
- [ ] P0: reset_member() 显式处理 MessageRouter 注册

**应该修复 (重要)**:
- [ ] P1: 调整 stop_member() 操作顺序 (先注销再清理)
- [ ] P2: 为 start/stop/reset/add_member 添加并发锁

**可以修复 (优化)**:
- [ ] P3: activate() 增强幂等性校验
- [ ] P4: cleanup() 增强错误日志

### 8.3 风险评估

**当前系统风险**:
- 🔴 高风险：stop/start/reset 后 agent 可能无法收到消息
- 🟡 中风险：并发操作可能导致状态不一致
- 🟢 低风险：极端场景下资源泄漏

**修复后收益**:
- 完整的 Agent 生命周期管理
- 消息路由一致性保证
- 更好的并发安全性

---

## 附录: 关键数据结构

### Agent 状态机

```
[创建] → idle
  ↓
[收到消息] → busy/chatting
  ↓
[处理完成] → idle
  ↓
[stop] → stopped
  ↓
[start] → idle
```

### MessageRouter 注册表

```python
_agents_queue: dict[str, asyncio.Queue] = {
    "manager": <Queue>,
    "worker1": <Queue>,
    "worker2": <Queue>,
    "user": <Queue>,  # 伪 agent
    "__HEARTBEAT__": <Queue>,  # 系统身份
}
```

### GroupChat 任务管理

```python
manager_task: asyncio.Task | None
worker_tasks: dict[str, asyncio.Task] = {
    "worker1": <Task>,
    "worker2": <Task>,
}
_heartbeat_task: asyncio.Task | None
```

---

**审查完成**. 报告生成于 D:\desktop\软件开发\agents-hub\.claude\worktrees\task-33-front-improve\docs\generated\agent-lifecycle-review.md
