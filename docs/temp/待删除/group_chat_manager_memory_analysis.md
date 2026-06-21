# GroupChatManager 内存管理分析

## 问题描述

`GroupChatManager.unregister()` 方法直接使用 `pop(group_chat_id)` 删除 GroupChat 实例，是否能保证其下所有实例状态管理都能安全退出？

## 当前实现

```python
def unregister(self, group_chat_id: str):
    """注销一个 GroupChat"""
    self._group_chats.pop(group_chat_id, None)
```

## 潜在问题分析

### 1. **异步任务未停止** ⚠️ 严重问题

`GroupChat` 在启动时创建了多个异步任务：

```python
# group_chat.py:79-80
self.manager_task = asyncio.create_task(self.manager.run())
self.worker_tasks = [asyncio.create_task(w.run()) for w in self.workers.values()]
```

**问题**：
- 直接 `pop` 删除引用后，这些异步任务仍在后台运行
- 任务持有 `Agent` 对象的引用，导致内存无法释放
- 任务中的 `while self._run` 循环会持续消耗 CPU
- 任务可能尝试访问已删除的资源，导致异常

**影响**：
- **内存泄漏**：Agent 对象、消息队列无法被 GC 回收
- **资源浪费**：后台任务持续运行，消耗 CPU
- **潜在崩溃**：任务访问已删除的资源时可能抛出异常

### 2. **AgentCallManager 后台清理任务未停止** ⚠️ 严重问题

`AgentCallManager` 启动了后台清理任务：

```python
# agent_call_manager.py:366
self._cleanup_task = asyncio.create_task(self._cleanup_loop())
```

**问题**：
- 清理任务会持续运行，定期扫描 `_calls` 字典
- 任务持有 `AgentCallManager` 的引用，阻止 GC

**影响**：
- **内存泄漏**：`AgentCallManager` 及其管理的所有 `AgentCall` 对象无法释放
- **资源浪费**：后台任务持续运行

### 3. **MessageRouter 中的消息队列未清空** ⚠️ 中等问题

`MessageRouter` 管理所有 Agent 的消息队列：

```python
# message_router.py:21
self._agents_queue: dict[str, asyncio.Queue] = {}
```

**问题**：
- 队列中可能还有未处理的消息
- 队列对象持有消息引用，阻止 GC

**影响**：
- **内存泄漏**：未处理的消息和队列对象无法释放
- **数据丢失**：队列中的消息被丢弃

### 4. **文件锁未释放** ⚠️ 中等问题

`GroupChatRepository` 使用文件锁保护并发访问：

```python
# group_chat_repository.py (推测)
# 可能使用 fcntl.flock 或 filelock 库
```

**问题**：
- 如果有正在进行的文件操作，锁可能未释放
- 其他进程/线程可能无法访问这些文件

**影响**：
- **资源泄漏**：文件锁未释放
- **死锁风险**：其他操作可能被阻塞

### 5. **Agent 平台 CLI 子进程未清理** ⚠️ 低风险

`agent_platform_client` 可能持有子进程引用：

```python
# agent_bridge/executors/claude.py (推测)
# subprocess.Popen() 创建的子进程
```

**问题**：
- 如果有正在执行的 Agent 调用，子进程可能仍在运行
- 子进程可能持有文件描述符、网络连接等资源

**影响**：
- **资源泄漏**：子进程、文件描述符未释放
- **僵尸进程**：子进程可能变成僵尸进程

## 正确的清理流程

### 推荐方案：添加 `cleanup()` 方法

```python
class GroupChat:
    async def cleanup(self):
        """清理所有资源，确保安全退出"""
        # 1. 停止所有 Agent 任务
        if self.manager:
            self.manager.set_run(False)
        for worker in self.workers.values():
            worker.set_run(False)
        
        # 2. 等待任务完成（设置超时）
        tasks = []
        if self.manager_task:
            tasks.append(self.manager_task)
        tasks.extend(self.worker_tasks)
        
        if tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                # 超时则强制取消
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
        
        # 3. 停止 AgentCallManager 清理任务
        await self.agent_call_manager.stop_cleanup()
        
        # 4. 清空消息队列
        for queue in [self.manager.message_queue] + [w.message_queue for w in self.workers.values()]:
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        
        # 5. 注销所有 Agent
        self.message_router.unregister(self.manager.name)
        for worker in self.workers.values():
            self.message_router.unregister(worker.name)
        
        # 6. 释放文件锁（如果有）
        # await self.group_chat_context.repository.release_locks()
        
        # 7. 清空引用
        self.workers.clear()
        self.manager = None
        self.manager_task = None
        self.worker_tasks.clear()
```

### 修改 `GroupChatManager.unregister()`

```python
class GroupChatManager:
    async def unregister(self, group_chat_id: str):
        """注销一个 GroupChat，确保资源安全释放"""
        group_chat = self._group_chats.get(group_chat_id)
        if group_chat:
            # 先清理资源
            await group_chat.cleanup()
            # 再删除引用
            self._group_chats.pop(group_chat_id, None)
```

## 测试建议

### 1. 内存泄漏测试

```python
import tracemalloc
import gc

tracemalloc.start()

# 创建并注销多个 GroupChat
for i in range(100):
    group_chat = GroupChat(...)
    await group_chat.start()
    group_chat_manager.register(f"test_{i}", group_chat)
    await group_chat_manager.unregister(f"test_{i}")
    
    # 强制 GC
    gc.collect()

# 检查内存使用
current, peak = tracemalloc.get_traced_memory()
print(f"Current memory: {current / 1024 / 1024:.2f} MB")
print(f"Peak memory: {peak / 1024 / 1024:.2f} MB")
```

### 2. 任务泄漏测试

```python
import asyncio

# 记录初始任务数
initial_tasks = len(asyncio.all_tasks())

# 创建并注销 GroupChat
group_chat = GroupChat(...)
await group_chat.start()
group_chat_manager.register("test", group_chat)
await group_chat_manager.unregister("test")

# 等待一段时间
await asyncio.sleep(1)

# 检查任务数
final_tasks = len(asyncio.all_tasks())
leaked_tasks = final_tasks - initial_tasks

if leaked_tasks > 0:
    print(f"⚠️ 泄漏了 {leaked_tasks} 个任务")
    for task in asyncio.all_tasks():
        print(f"  - {task.get_coro()}")
```

### 3. 文件锁测试

```python
import os
import fcntl

# 创建并注销 GroupChat
group_chat = GroupChat(...)
await group_chat.start()
group_chat_manager.register("test", group_chat)
await group_chat_manager.unregister("test")

# 尝试访问文件
file_path = "local_data/teams/.../test/test.jsonl"
try:
    with open(file_path, "r") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        print("✓ 文件锁已释放")
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
except BlockingIOError:
    print("⚠️ 文件锁未释放")
```

## 总结

**当前实现存在严重的内存泄漏和资源泄漏问题**：

1. ❌ 异步任务未停止（严重）
2. ❌ 后台清理任务未停止（严重）
3. ❌ 消息队列未清空（中等）
4. ❌ 文件锁可能未释放（中等）
5. ❌ 子进程可能未清理（低风险）

**建议**：
1. 立即添加 `GroupChat.cleanup()` 方法
2. 修改 `GroupChatManager.unregister()` 为异步方法
3. 添加内存泄漏和任务泄漏测试
4. 考虑使用上下文管理器（`async with`）模式

**优先级**：
- P0：修复异步任务泄漏（影响最大）
- P1：修复 AgentCallManager 清理任务泄漏
- P2：清空消息队列
- P3：释放文件锁
- P4：清理子进程
