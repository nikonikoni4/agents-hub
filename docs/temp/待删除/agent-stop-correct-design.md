# Agent.stop() 正确实现方案

## 问题

原设计中，发送哨兵消息后会进入 `run()` 循环的消息处理逻辑，这不是我们想要的。

## 解决方案

### 方案 1：在 run() 中检查哨兵消息（推荐）

#### 1. 修改 Agent.run()

```python
async def run(self):
    """持续监听私有队列，处理收到的消息"""
    while self._run:
        # 1. 从队列中取回消息
        msg: AgentMessage = await self.message_queue.get()
        
        # 2. 检查是否是停止信号
        if msg.call_id == "__STOP__":
            break
        
        # 3. 渲染 LLM prompt（不写回 msg.content）
        prompt = render_for_llm(msg)
        result = await self._process_message(msg, prompt)
        
        # 4. 出口 A：写回群聊（@发起者 result.text）
        self.group_chat_context.add_message(
            render_for_chat(self.name, msg.send_from, result.text)
        )
        
        # 5. 出口 B：如果是 TASK 且发起者不是 user，投递回复
        if msg.message_type == MessageType.TASK and msg.send_from != "user":
            send_message_content = f"提示 : 消息回复见上文聊天记录中speaker为[{self.name}] @[{msg.send_from}]的最新一条"
            response_call = self.agent_call_manager.create_call(
                send_from=self.name,
                send_to=msg.send_from,
                content=send_message_content,
                message_type=MessageType.NOTIFICATION,
            )
            self.send_message_to_agent(response_call.call_id, msg.send_from, send_message_content)
```

#### 2. 实现 Agent.stop()

```python
async def stop(self):
    """
    停止 Agent 的 run() 循环
    
    通过设置 _run 标志和发送哨兵消息来停止循环。
    哨兵消息用于唤醒可能阻塞在 queue.get() 的任务。
    """
    # 设置停止标志
    self._run = False
    
    # 发送哨兵消息，唤醒可能阻塞的 get()
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
        # 队列满了也没关系，_run=False 会让循环在处理完当前消息后退出
        pass
```

**优点**：
- 立即唤醒阻塞的 `get()`，快速退出
- 不会处理哨兵消息
- 逻辑清晰，易于理解

**缺点**：
- 需要修改 `run()` 方法

---

### 方案 2：使用 asyncio.Event（更优雅）

如果不想修改 `run()` 的消息处理逻辑，可以使用 `asyncio.Event`：

#### 1. 修改 Agent.__init__()

```python
def __init__(self, ...):
    # ... 现有代码 ...
    self._stop_event = asyncio.Event()
```

#### 2. 修改 Agent.run()

```python
async def run(self):
    """持续监听私有队列，处理收到的消息"""
    while self._run:
        # 同时等待消息和停止信号
        get_task = asyncio.create_task(self.message_queue.get())
        stop_task = asyncio.create_task(self._stop_event.wait())
        
        done, pending = await asyncio.wait(
            [get_task, stop_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # 取消未完成的任务
        for task in pending:
            task.cancel()
        
        # 如果是停止信号，退出循环
        if stop_task in done:
            break
        
        # 否则处理消息
        msg: AgentMessage = get_task.result()
        
        # 正常处理消息...
        prompt = render_for_llm(msg)
        result = await self._process_message(msg, prompt)
        # ...
```

#### 3. 实现 Agent.stop()

```python
async def stop(self):
    """停止 Agent 的 run() 循环"""
    self._run = False
    self._stop_event.set()
```

**优点**：
- 不需要哨兵消息
- 更优雅的异步模式
- 立即响应停止信号

**缺点**：
- 需要修改 `run()` 方法，逻辑更复杂
- 增加了一个 `_stop_event` 属性

---

### 方案 3：只设置标志，依赖超时（最简单但不优雅）

#### 实现 Agent.stop()

```python
def stop(self):
    """停止 Agent 的 run() 循环"""
    self._run = False
    # 不发送任何消息，等待下一条消息到来时自然退出
```

#### 在 GroupChat.cleanup() 中处理

```python
async def cleanup(self, timeout: float = 10.0):
    # 1. 停止所有 Agent
    if self.manager:
        self.manager.stop()
    for worker in self.workers.values():
        worker.stop()
    
    # 2. 等待任务完成（设置超时）
    tasks = []
    if self.manager_task and not self.manager_task.done():
        tasks.append(self.manager_task)
    tasks.extend([t for t in self.worker_tasks if not t.done()])
    
    if tasks:
        try:
            # 等待任务自然退出
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            # 超时则强制取消
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
```

**优点**：
- 不需要修改 `run()` 方法
- 实现最简单

**缺点**：
- 如果队列一直没有新消息，需要等待超时才能退出
- 不够优雅

---

## 推荐方案

我推荐**方案 1**（哨兵消息 + run() 检查），原因：

1. **立即响应**：不需要等待超时
2. **实现简单**：只需在 `run()` 开头加一个 `if` 判断
3. **易于理解**：逻辑清晰，容易维护
4. **向后兼容**：不改变现有的消息处理逻辑

## 实现步骤

1. 在 `Agent.run()` 开头添加哨兵消息检查
2. 实现 `Agent.stop()` 方法
3. 添加单元测试验证停止逻辑

## 测试用例

```python
async def test_agent_stop():
    """测试 Agent 能够正确停止"""
    agent = Agent(...)
    
    # 启动 Agent
    task = asyncio.create_task(agent.run())
    
    # 等待一小段时间，确保任务已经启动
    await asyncio.sleep(0.1)
    
    # 停止 Agent
    await agent.stop()
    
    # 等待任务完成（应该很快）
    try:
        await asyncio.wait_for(task, timeout=1.0)
    except asyncio.TimeoutError:
        pytest.fail("Agent 未能在 1 秒内停止")
    
    # 验证任务已完成
    assert task.done()
    assert agent._run is False
```
