---
created_at: 2026-06-22
updated_at: 2026-06-22
trigger: 编写后端异步代码、修改状态管理、操作 MessageRouter 时
---

# 后端并发与状态管理规则

> 上级规则：[backend-style.md](backend-style.md)

## 并发安全优先级

**黄金法则**：隔离 > 锁 > 共享

**禁止**：
- ❌ 多个 asyncio 协程共享同一个有状态对象（Parser、Runtime、Manager）
- ❌ 在并发环境下使用共享可变状态而不加保护

**决策表**：

| 场景 | 策略 | 示例 |
|------|------|------|
| 对象有可变状态 | 每次创建新实例 | Parser |
| 必须共享状态 | 加锁保护 | GroupChat.state |
| 只读数据 | 共享即可 | 配置对象 |

**示例**：
```python
# ❌ 多个协程共享有状态对象
self._parsers = {
    AgentPlatform.CODEX: CodexParser(),  # 内部有 _thread_id 可变状态
}

# ✅ 无状态对象每次创建新实例
def _create_parser(self, platform):
    if platform == AgentPlatform.CODEX:
        return CodexParser()  # 每次创建独立实例

# ✅ 有状态操作加锁
async def add_message(self, agent_result):
    async with self._state_lock:
        session = self.state.require_session()
        session.add_message(agent_result)
        await self._persist(...)
```

## 状态变更必须立即持久化

**禁止**：
- ❌ 修改内存状态后依赖"稍后自动持久化"
- ❌ 依赖"首次执行时自动创建"而非立即写入磁盘
- ❌ 序列化/反序列化时遗漏字段

**示例**：
```python
# ❌ 只更新内存，不持久化
group_chat.team_members_name.append(role_name)

# ✅ 状态变更后立即持久化
agent_member_info = self.runtime.get_or_create_agent_member_info(role_name)
await self.runtime.repository.save_agent_member(
    self.runtime.state.agent_member_infos  # 保存完整字典
)
```

**规则**：
- 所有涉及状态变更的操作，必须在同一事务中完成持久化
- 序列化/反序列化必须包含所有字段
- 添加新字段时必须同步更新序列化和反序列化两处

## 注册/注销必须对称

**禁止**：
- ❌ stop 时注销了组件，但 start/reset 时忘记重新注册
- ❌ 注册和注销逻辑分散在多处，没有统一方法

**示例**：
```python
# ❌ stop_member 中注销了
self.message_router.unregister(agent_name)

# start_member 中忘记重新注册
agent._run = True
asyncio.create_task(agent.run())
# 缺少：self.message_router.register(agent_name, agent.message_queue)

# ✅ 注册和注销必须成对出现
def _register_agents_to_router(self):
    """注册所有 agents 到 MessageRouter（幂等）"""
    self.message_router.register(self.manager.name, self.manager.message_queue)
    for worker in self.workers.values():
        self.message_router.register(worker.name, worker.message_queue)

def start_member(self, agent_name):
    agent._run = True
    self._register_agents_to_router()  # 确保注册
    asyncio.create_task(agent.run())
```

**规则**：
- 任何 `unregister` 调用，必须在对应的 start/reset 路径中有 `register`
- 建议将注册逻辑提取为独立方法（如 `_register_agents_to_router`），在所有需要的地方调用

## asyncio.create_task 必须添加异常监控

**禁止**：
- ❌ 创建长生命周期任务后没有监控
- ❌ `run()` 作为长生命周期协程没有顶层 try/except

**示例**：
```python
# ❌ 创建任务后没有监控
self.manager_task = asyncio.create_task(agent.run())
# agent.run() 内部异常退出，但没有 done_callback
# 消息堆积在队列中，无人消费

# ✅ 添加 done_callback 监控任务异常
def _on_agent_task_done(self, task: asyncio.Task):
    if task.cancelled():
        return
    if task.exception():
        logger.error("Agent task 异常退出: %s", task.exception())

task = asyncio.create_task(agent.run())
task.add_done_callback(self._on_agent_task_done)
```

**规则**：
- 所有 `asyncio.create_task()` 创建的长生命周期任务，必须添加 `add_done_callback` 监控异常退出
- `run()` 作为长生命周期协程必须有顶层 try/except
