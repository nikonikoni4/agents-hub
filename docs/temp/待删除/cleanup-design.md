# 资源清理机制设计

## 设计原则

1. **每个类单独实现清理方法**：遵循单一职责原则
2. **自底向上清理**：上层组件调用下层组件的清理方法
3. **幂等性**：清理方法可以多次调用，不会出错
4. **超时保护**：异步清理操作设置超时，避免永久阻塞
5. **异常安全**：清理过程中的异常不应阻止其他资源清理

## 清理层级

```
GroupChatManager
    └── GroupChat.cleanup()
            ├── Agent.stop() (Manager + Workers)
            ├── AgentCallManager.stop_cleanup()
            ├── MessageRouter.clear()
            └── GroupChatContext.close()
                    └── GroupChatRepository.close()
```

## 各组件清理方法设计

### 1. MessageRouter.clear()

**职责**：清空所有消息队列，注销所有 Agent

```python
class MessageRouter:
    def clear(self):
        """清空所有消息队列并注销所有 Agent"""
        # 清空所有队列中的消息
        for name, queue in self._agents_queue.items():
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        
        # 清空注册表
        self._agents_queue.clear()
```

**测试点**：
- 队列中的消息被清空
- 注册表被清空
- 多次调用不出错

---

### 2. Agent.stop()

**职责**：停止 Agent 的 run() 循环

```python
class Agent:
    async def stop(self, timeout: float = 5.0):
        """
        停止 Agent 的 run() 循环
        
        Args:
            timeout: 等待超时时间（秒）
        """
        # 设置停止标志
        self._run = False
        
        # 向队列发送一个哨兵消息，唤醒可能阻塞的 get()
        # 这样可以立即退出 run() 循环，而不是等待下一条消息
        try:
            sentinel = AgentMessage(
                call_id="__STOP__",
                send_from="__SYSTEM__",
                send_to=self.name,
                content="__STOP__",
                message_type=MessageType.NOTIFICATION,
            )
            self.message_queue.put_nowait(sentinel)
        except asyncio.QueueFull:
            pass  # 队列满了也没关系，_run=False 会让循环退出
```

**注意**：
- `stop()` 只设置停止标志，不等待任务完成
- 任务的等待由 `GroupChat.cleanup()` 负责
- 发送哨兵消息是为了唤醒可能阻塞在 `queue.get()` 的任务

**测试点**：
- `_run` 标志被设置为 False
- 哨兵消息被发送到队列
- 多次调用不出错

---

### 3. AgentCallManager.stop_cleanup()

**职责**：停止后台清理任务

**当前实现**：已存在，需要验证

```python
async def stop_cleanup(self):
    """停止后台清理任务"""
    if not self._running:
        return
    
    self._running = False
    if self._cleanup_task:
        self._cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._cleanup_task
        self._cleanup_task = None
    self.logger.info("后台清理任务已停止")
```

**改进建议**：添加超时保护

```python
async def stop_cleanup(self, timeout: float = 5.0):
    """停止后台清理任务"""
    if not self._running:
        return
    
    self._running = False
    if self._cleanup_task:
        self._cleanup_task.cancel()
        try:
            await asyncio.wait_for(self._cleanup_task, timeout=timeout)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        self._cleanup_task = None
    self.logger.info("后台清理任务已停止")
```

**测试点**：
- 清理任务被取消
- `_running` 标志被设置为 False
- 超时不会永久阻塞
- 多次调用不出错

---

### 4. GroupChatRepository.close()

**职责**：释放文件锁（如果有）

```python
class GroupChatRepository:
    def close(self):
        """释放所有文件锁"""
        # 如果使用了文件锁，在这里释放
        # 例如：
        # if self._lock:
        #     self._lock.release()
        #     self._lock = None
        pass  # 当前实现可能不需要，但预留接口
```

**测试点**：
- 文件锁被释放
- 多次调用不出错

---

### 5. GroupChatContext.close()

**职责**：关闭上下文，释放资源

```python
class GroupChatContext:
    def close(self):
        """关闭上下文，释放资源"""
        # 关闭 repository
        self.repository.close()
        
        # 清空引用
        self.group_chat_session = None
        self.agent_member_info.clear()
```

**测试点**：
- Repository 被关闭
- 引用被清空
- 多次调用不出错

---

### 6. GroupChat.cleanup()

**职责**：协调所有组件的清理，确保资源安全释放

```python
class GroupChat:
    async def cleanup(self, timeout: float = 10.0):
        """
        清理所有资源，确保安全退出
        
        Args:
            timeout: 等待任务完成的超时时间（秒）
        """
        # 1. 停止所有 Agent（设置停止标志）
        if self.manager:
            await self.manager.stop()
        for worker in self.workers.values():
            await worker.stop()
        
        # 2. 等待所有任务完成（设置超时）
        tasks = []
        if self.manager_task and not self.manager_task.done():
            tasks.append(self.manager_task)
        tasks.extend([t for t in self.worker_tasks if not t.done()])
        
        if tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # 超时则强制取消
                for task in tasks:
                    if not task.done():
                        task.cancel()
                # 等待取消完成
                await asyncio.gather(*tasks, return_exceptions=True)
        
        # 3. 停止 AgentCallManager 清理任务
        await self.agent_call_manager.stop_cleanup()
        
        # 4. 清空 MessageRouter
        self.message_router.clear()
        
        # 5. 关闭 GroupChatContext
        self.group_chat_context.close()
        
        # 6. 清空引用
        self.workers.clear()
        self.manager = None
        self.manager_task = None
        self.worker_tasks.clear()
```

**测试点**：
- 所有 Agent 任务被停止
- AgentCallManager 清理任务被停止
- MessageRouter 被清空
- GroupChatContext 被关闭
- 引用被清空
- 超时不会永久阻塞
- 多次调用不出错

---

### 7. GroupChatManager.unregister()

**职责**：注销 GroupChat，先清理资源再删除引用

```python
class GroupChatManager:
    async def unregister(self, group_chat_id: str, timeout: float = 10.0):
        """
        注销一个 GroupChat，确保资源安全释放
        
        Args:
            group_chat_id: 群聊 ID
            timeout: 清理超时时间（秒）
        """
        group_chat = self._group_chats.get(group_chat_id)
        if group_chat:
            # 先清理资源
            await group_chat.cleanup(timeout=timeout)
            # 再删除引用
            self._group_chats.pop(group_chat_id, None)
```

**测试点**：
- GroupChat 被清理
- 引用被删除
- 超时不会永久阻塞
- 多次调用不出错

---

## 测试策略

### 1. 单元测试（每个组件单独测试）

```python
# test_message_router.py
async def test_message_router_clear():
    router = MessageRouter()
    queue = asyncio.Queue()
    router.register("agent1", queue)
    queue.put_nowait(AgentMessage(...))
    
    router.clear()
    
    assert len(router._agents_queue) == 0
    assert queue.empty()

# test_agent.py
async def test_agent_stop():
    agent = Agent(...)
    task = asyncio.create_task(agent.run())
    
    await agent.stop()
    await asyncio.sleep(0.1)  # 等待任务退出
    
    assert agent._run is False
    assert task.done()

# test_agent_call_manager.py
async def test_agent_call_manager_stop_cleanup():
    manager = AgentCallManager(...)
    manager.start_cleanup()
    
    await manager.stop_cleanup()
    
    assert manager._running is False
    assert manager._cleanup_task is None
```

### 2. 集成测试（测试整个清理流程）

```python
# test_group_chat_cleanup.py
async def test_group_chat_cleanup():
    group_chat = GroupChat(...)
    await group_chat.start()
    
    # 记录初始状态
    initial_tasks = len(asyncio.all_tasks())
    
    # 清理
    await group_chat.cleanup()
    
    # 验证
    assert group_chat.manager is None
    assert len(group_chat.workers) == 0
    assert len(group_chat.message_router._agents_queue) == 0
    
    # 等待一段时间，确保任务真的退出了
    await asyncio.sleep(0.5)
    final_tasks = len(asyncio.all_tasks())
    
    # 任务数应该回到初始状态（或更少）
    assert final_tasks <= initial_tasks
```

### 3. 内存泄漏测试

```python
# test_memory_leak.py
import tracemalloc
import gc

async def test_no_memory_leak():
    tracemalloc.start()
    
    # 创建并清理多个 GroupChat
    for i in range(100):
        group_chat = GroupChat(...)
        await group_chat.start()
        await group_chat.cleanup()
        
        # 强制 GC
        gc.collect()
    
    # 检查内存使用
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # 内存使用应该稳定（不会持续增长）
    print(f"Current: {current / 1024 / 1024:.2f} MB")
    print(f"Peak: {peak / 1024 / 1024:.2f} MB")
    
    # 可以设置一个合理的阈值
    assert current < 50 * 1024 * 1024  # 小于 50MB
```

### 4. 任务泄漏测试

```python
# test_task_leak.py
async def test_no_task_leak():
    initial_tasks = len(asyncio.all_tasks())
    
    # 创建并清理 GroupChat
    group_chat = GroupChat(...)
    await group_chat.start()
    await group_chat.cleanup()
    
    # 等待一段时间
    await asyncio.sleep(1)
    
    # 检查任务数
    final_tasks = len(asyncio.all_tasks())
    leaked_tasks = final_tasks - initial_tasks
    
    if leaked_tasks > 0:
        print(f"⚠️ 泄漏了 {leaked_tasks} 个任务:")
        for task in asyncio.all_tasks():
            print(f"  - {task.get_coro()}")
    
    assert leaked_tasks == 0
```

## 实现顺序

1. **Phase 1**：实现基础组件清理方法
   - MessageRouter.clear()
   - Agent.stop()
   - GroupChatRepository.close()
   - GroupChatContext.close()

2. **Phase 2**：改进 AgentCallManager
   - 为 stop_cleanup() 添加超时保护

3. **Phase 3**：实现 GroupChat.cleanup()
   - 协调所有组件清理

4. **Phase 4**：修改 GroupChatManager.unregister()
   - 改为异步方法
   - 先清理再删除

5. **Phase 5**：添加测试
   - 单元测试
   - 集成测试
   - 内存泄漏测试
   - 任务泄漏测试

## 注意事项

1. **幂等性**：所有清理方法都应该可以多次调用
2. **异常安全**：清理过程中的异常不应阻止其他资源清理
3. **超时保护**：避免清理操作永久阻塞
4. **日志记录**：记录清理过程，便于调试
5. **向后兼容**：考虑现有代码的兼容性
