# 多 Agent 消息架构设计方案

重要说明：该设计只是临时设计，不作为程序实现基础

## 设计日期
2026-05-28
claude session_id : 6ac09607-caa6-47f5-b5fd-00a02bd05996
"C:\Users\15535\.claude\projects\D--desktop------agents-hub\6ac09607-caa6-47f5-b5fd-00a02bd05996.jsonl"
## 设计目标

基于以下三个核心原则设计消息传递架构：

1. **避免越权访问**：Agent 不能直接访问其他 Agent 的方法和状态
2. **按需提供上下文**：每个 Agent 只获取与其职责相关的上下文信息
3. **点对点优于广播**：消息精确路由到目标 Agent，而非广播后过滤

---

## 核心组件

### 1. Message（消息）

**职责：**
- 承载消息内容和路由信息
- 关联任务 ID，用于异步任务追踪

**关键设计：**
```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Message:
    content: str                                    # 消息内容
    send_to: str                                    # 接收者（路由目标）
    sent_from: str                                  # 发送者
    task_id: str | None = None                      # 关联的任务 ID（用于异步任务追踪）
    timestamp: datetime = field(default_factory=datetime.now)  # 消息时间戳
```

**@ 符号的双重语义：**

1. **User 的 @**：有路由作用
   - `User: "@Agent A 请分析需求"`
   - 系统解析后：`send_to = "Agent A"`
   - 消息直接路由到 Agent A（绕过 Manager）

2. **Agent 的 @**：无路由作用，用于上下文澄清
   - `Manager: "@Agent A 请分析需求"`
   - `send_to = "Agent A"`（路由）
   - 内容中的 `@Agent A` 是给其他 Agent 看的
   - 避免后续 Agent 误解任务对象

**为什么需要 Agent 的 @：**
- 场景：Manager 说"请分析需求"（没有 @）
- 问题：后续 Agent B 被触发时，可能误以为任务是给自己的
- 解决：Manager 说"@Agent A 请分析需求"
- 效果：Agent B 看到上下文时，知道这是给 Agent A 的任务

---

### 2. TaskManager（任务管理器）

**职责：**
- 统一管理所有跨 Agent 的异步任务
- 提供任务状态追踪和查询能力
- 维护任务生命周期（创建 → 执行 → 完成/失败）

**关键设计：**
```python
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

class TaskStatus(Enum):
    PENDING = "pending"      # 已创建，等待执行
    RUNNING = "running"      # 正在执行
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"        # 执行失败

@dataclass
class Task:
    task_id: str = field(default_factory=lambda: str(uuid4()))
    send_from: str          # 任务发起者
    send_to: str            # 任务执行者
    content: str            # 任务内容
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: AgentResult | None = None  # 执行结果
    error: str | None = None           # 错误信息

class TaskManager:
    """统一管理所有跨 Agent 的异步任务"""
    
    def __init__(self):
        self._tasks: dict[str, Task] = {}  # task_id -> Task
    
    def create_task(self, send_from: str, send_to: str, content: str) -> str:
        """创建新任务，返回 task_id"""
        task = Task(send_from=send_from, send_to=send_to, content=content)
        self._tasks[task.task_id] = task
        return task.task_id
    
    def get_task(self, task_id: str) -> Task | None:
        """获取任务详情"""
        return self._tasks.get(task_id)
    
    def update_status(self, task_id: str, status: TaskStatus):
        """更新任务状态"""
        if task := self._tasks.get(task_id):
            task.status = status
            if status == TaskStatus.RUNNING:
                task.started_at = datetime.now()
            elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                task.completed_at = datetime.now()
    
    def set_result(self, task_id: str, result: AgentResult):
        """设置任务结果"""
        if task := self._tasks.get(task_id):
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
    
    def set_error(self, task_id: str, error: str):
        """设置任务错误"""
        if task := self._tasks.get(task_id):
            task.error = error
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
```

**设计要点：**
- 所有任务都在 `TaskManager` 中注册，避免任务分散在各个 Agent 的队列中
- 每个任务都有唯一的 `task_id`，用于追踪和查询
- 支持查询任务状态、执行时长、结果等信息
- `_tasks` 字典就是异步任务的 "pending 池"

---

### 3. MessageRouter（消息总线）

**职责：**
- 管理所有 Agent 的私有队列引用
- 负责点对点消息路由
- 记录所有消息到 GroupChatSession

**关键设计：**
```python
class MessageRouter:
    def __init__(self, context: GroupChatContext):
        self._agent_buffers: dict[str, asyncio.Queue] = {}  # 实例变量：Agent 名称 → 私有队列
        self._context = context                              # 实例变量：群聊上下文引用
    
    def register(self, agent_name: str, buffer: asyncio.Queue):
        """注册 Agent 的私有队列"""
        self._agent_buffers[agent_name] = buffer
    
    def publish_message(self, msg: Message):
        """点对点路由 + 记录历史"""
        # 1. 记录到 GroupChatSession
        self._context.group_chat_session.add_message(
            sender=msg.sent_from,
            content=msg.content,
            send_to=msg.send_to
        )
        # 2. 路由到目标 Agent 的私有队列
        target_buffer = self._agent_buffers.get(msg.send_to)
        if target_buffer:
            target_buffer.put_nowait(msg)
```

**为什么不用中心化暂存队列：**
- 私有队列已经提供异步解耦
- 中心化队列只是多一层中转，无实际价值
- 直接路由更简单高效

---

### 4. Agent（智能体）

**职责：**
- 持有私有消息队列（`asyncio.Queue`）
- 持有 MessageRouter 引用（用于发送消息）
- 持有 GroupChatContext 引用（用于读取上下文）
- 从队列接收消息并处理
- 更新任务状态到 TaskManager

**关键设计：**
```python
class Agent:
    def __init__(self, name: str, message_router: MessageRouter, context: GroupChatContext):
        self.name = name                        # 实例变量：每个 Agent 独立
        self.message_buffer = asyncio.Queue()   # 实例变量：每个 Agent 独立的私有队列
        self.context = context                  # 实例变量：持有 GroupChatContext 引用
        self._bus = message_router              # 实例变量：持有 MessageRouter 引用（共享同一实例）
        
        # 注册自己的队列到 MessageRouter
        self._bus.register(self.name, self.message_buffer)
    
    def send_message(self, content: str, send_to: str):
        """发送消息：Agent 不知道目标在哪，只知道名字"""
        msg = Message(content, send_to, sent_from=self.name)
        self._bus.publish_message(msg)
    
    async def run(self):
        """主循环：从队列取消息并处理"""
        while True:
            msg = await self.message_buffer.get()  # 阻塞等待
            await self._process_message(msg)
    
    async def _process_message(self, msg: Message):
        """处理消息，并更新任务状态"""
        task_id = msg.task_id
        
        try:
            # 1. 标记任务为 RUNNING
            if task_id:
                self.context.task_manager.update_status(task_id, TaskStatus.RUNNING)
            
            # 2. 从 GroupChatContext 获取上下文
            agent_context = self.context.get_agent_context(self.name)
            
            # 3. 组装 prompt 并执行 LLM 调用
            prompt = f"{agent_context}\n\n新消息：{msg.content}"
            result = await self.execute(prompt)
            
            # 4. 写入群聊历史
            self.context.group_chat_session.add_message(result)
            self.context.save_group_chat_session()
            
            # 5. 更新 session_id
            self.context.update_agent_session_id(result)
            self.context.save_agent_session_id()
            
            # 6. 标记任务为 COMPLETED
            if task_id:
                self.context.task_manager.set_result(task_id, result)
            
            # 7. 发送回复消息（可选，根据消息类型决定）
            # self.send_message(result.text, msg.sent_from)
            
        except Exception as e:
            # 8. 标记任务为 FAILED
            if task_id:
                self.context.task_manager.set_error(task_id, str(e))
            raise
```

**为什么 Agent 持有 GroupChatContext：**
- 这不是"耦合"，这是"依赖注入"
- Agent 需要读取上下文来执行任务
- Agent 只读取，不修改其他 Agent 的状态
- 类比：Agent 依赖 RoleConfig 一样合理

**群聊消息写入时机：**
- 在 `_process_message()` 中，LLM 返回后立即写入
- 确保每次 Agent 的回复都被记录到群聊历史
- 写入时机：LLM 返回后、发送下一条消息前

---

### 5. GroupChatContext（群聊上下文）

**职责：**
- 管理群聊历史消息（`GroupChatSession`）
- 管理压缩历史（`compact_history.jsonl`）
- 管理任务状态（`TaskManager`）
- 为每个 Agent 提供定制化上下文

**关键设计：**
```python
class GroupChatContext:
    group_chat_session: GroupChatSession    # 原始消息历史
    compact_history_file: str               # 压缩历史文件路径
    task_manager: TaskManager               # 任务管理器
    
    def get_agent_context(agent_name) -> str:
        """获取该 Agent 的上下文（已实现）"""
        # 1. 压缩历史的 summary（全局）
        # 2. 压缩历史中针对该 Agent 的部分
        # 3. 最新未压缩消息（过滤后）
```

**上下文过滤规则（已在 team.py 实现）：**
- Agent 只看到与自己相关的消息
- 避免被无关信息干扰
- 减少 token 消耗

---

## 异步任务管理架构

### 设计目标

解决以下问题：
1. **任务分散问题**：任务不再分散在各个 Agent 的队列中，而是统一在 TaskManager 中管理
2. **状态追踪问题**：通过 task_id 可以查询任务的执行状态、进度、结果
3. **异步执行问题**：`call_agent` 立即返回 task_id，不阻塞调用者

### 完整调用链路

```
A 调用 call_agent(B, "分析需求")
    ↓
1. TaskManager.create_task() → 返回 task_id
    ↓
2. MessageRouter.publish_message(msg with task_id)
    ↓
3. 投递到 B.message_buffer
    ↓
4. 立即返回 "任务已派遣，task_id: xxx"
    ↓
（A 可以继续做其他事情，不阻塞）
    ↓
5. B.run() 从队列取出消息
    ↓
6. B._process_message()
   - 标记任务为 RUNNING
   - 执行 LLM 调用
   - 写入群聊历史
   - 标记任务为 COMPLETED
    ↓
7. A 调用 query_task_status(task_id) 查询结果
```

### 工具接口设计

#### 1. call_agent（派遣任务）

```python
def call_agent(
    send_from: str, 
    send_to: str, 
    content: str, 
    group_chat: GroupChat
) -> str:
    """
    派遣任务给目标 Agent（异步执行）
    
    Args:
        send_from: 发送者名称
        send_to: 接收者名称
        content: 任务内容
        group_chat: 群聊实例
    
    Returns:
        "任务已派遣，task_id: xxx"
    """
    # 1. 创建任务记录
    task_id = group_chat.task_manager.create_task(send_from, send_to, content)
    
    # 2. 发送消息到目标 Agent
    message = AgentsMessage(
        content=content,
        send_from=send_from,
        send_to=send_to,
        task_id=task_id
    )
    group_chat.message_router._agents_queue[send_to].put_nowait(message)
    
    return f"任务已派遣，task_id: {task_id}"
```

**设计要点：**
- 立即返回 task_id，不等待执行完成
- 真正的异步，调用者不阻塞
- 任务状态由 TaskManager 统一管理

#### 2. query_task_status（查询任务状态）

```python
def query_task_status(task_id: str, group_chat: GroupChat) -> str:
    """
    查询任务执行状态
    
    Args:
        task_id: 任务 ID
        group_chat: 群聊实例
    
    Returns:
        任务状态的 JSON 字符串
    """
    task = group_chat.task_manager.get_task(task_id)
    
    if not task:
        return f"任务不存在: {task_id}"
    
    # 构建返回信息
    info = {
        "task_id": task.task_id,
        "status": task.status.value,
        "send_from": task.send_from,
        "send_to": task.send_to,
        "content": task.content[:50] + "...",
        "created_at": task.created_at.isoformat(),
    }
    
    if task.status == TaskStatus.COMPLETED and task.result:
        info["result"] = task.result.text[:200] + "..."
        info["duration"] = (task.completed_at - task.created_at).total_seconds()
    
    if task.status == TaskStatus.FAILED and task.error:
        info["error"] = task.error
    
    return json.dumps(info, ensure_ascii=False, indent=2)
```

**设计要点：**
- 返回任务的完整状态信息
- 包括执行时长、结果摘要、错误信息
- 支持 LLM 解析 JSON 格式

### 使用示例

```python
# 场景：Manager 派遣任务给 Agent A

# 1. Manager 调用 call_agent
result = call_agent("Manager", "Agent A", "请分析需求", group_chat)
# 返回: "任务已派遣，task_id: 123e4567-e89b-12d3-a456-426614174000"

# 2. 提取 task_id
task_id = "123e4567-e89b-12d3-a456-426614174000"

# 3. Manager 继续做其他事情（不阻塞）
# ...

# 4. 稍后查询任务状态
status = query_task_status(task_id, group_chat)
# 返回:
# {
#   "task_id": "123e4567-e89b-12d3-a456-426614174000",
#   "status": "running",
#   "send_from": "Manager",
#   "send_to": "Agent A",
#   "content": "请分析需求",
#   "created_at": "2026-05-29T10:30:00"
# }

# 5. 任务完成后再次查询
status = query_task_status(task_id, group_chat)
# 返回:
# {
#   "task_id": "123e4567-e89b-12d3-a456-426614174000",
#   "status": "completed",
#   "send_from": "Manager",
#   "send_to": "Agent A",
#   "content": "请分析需求",
#   "created_at": "2026-05-29T10:30:00",
#   "result": "需求分析完成：用户需要一个登录功能...",
#   "duration": 40.0
# }
```

### 任务完成后的通知机制

**问题：B 完成任务后，是否自动通知 A？**

**方案：引入消息类型，避免无限循环**

```python
class MessageType(Enum):
    TASK = "task"           # 任务派遣，需要执行并回复
    NOTIFICATION = "notification"  # 通知消息，不需要回复
    QUERY = "query"         # 查询请求，需要回复

@dataclass
class AgentsMessage:
    content: str
    send_from: str
    send_to: str
    task_id: str | None = None
    message_type: MessageType = MessageType.TASK  # 默认是任务
    session_type: SessionType = SessionType.MAIN
    timestamp: datetime = field(default_factory=datetime.now)
```

**使用场景：**

1. **A 派遣任务给 B**：
   ```python
   call_agent(A, B, "请分析需求", message_type=MessageType.TASK)
   # B 执行完成后，发送 NOTIFICATION 给 A
   send_message(B, A, "任务完成：需求分析结果...", message_type=MessageType.NOTIFICATION)
   ```

2. **A 收到 NOTIFICATION**：
   ```python
   async def _process_message(self, msg: AgentsMessage):
       result = await self.execute(msg.content)
       
       # 只有 TASK 类型才需要回复
       if msg.message_type == MessageType.TASK:
           self.send_message(msg.send_from, result.text, MessageType.NOTIFICATION)
   ```

**这样就避免了循环：**
- A → B (TASK)
- B 执行 → A (NOTIFICATION)
- A 收到 NOTIFICATION，不回复 ✅

**注意：**
- 当前设计中，B 完成任务后**不会自动通知 A**
- A 需要主动调用 `query_task_status` 查询结果
- 如果需要自动通知，可以在 `_process_message` 中添加逻辑：
  ```python
  # 任务完成后，发送 NOTIFICATION 给发起者
  if task_id and msg.message_type == MessageType.TASK:
      self.send_message(
          msg.send_from, 
          f"任务 {task_id} 已完成：{result.text[:100]}...",
          MessageType.NOTIFICATION
      )
  ```

---

## 消息流转完整链路

### 基本流程（带任务管理）

```
发送者调用 call_agent(send_to, content)
    ↓
1. TaskManager.create_task() → 返回 task_id
    ↓
2. MessageRouter.publish_message(msg with task_id)
    ↓
3. 记录到 GroupChatSession
4. 路由到目标 Agent 的 message_buffer
    ↓
5. 立即返回 "任务已派遣，task_id: xxx"（不阻塞）
    ↓
目标 Agent.message_buffer.get()
    ↓
目标 Agent._process_message(msg)
    ↓
1. 标记任务为 RUNNING
2. 从 GroupChatContext 获取上下文
3. 组装 prompt
4. 执行 LLM 调用
5. 写入群聊历史
6. 更新 session_id
7. 标记任务为 COMPLETED
8. （可选）发送 NOTIFICATION 给发起者
```

### 关键点

1. **异步解耦**：
   - 发送者调用 `call_agent()` 立即返回 task_id
   - 接收者从队列阻塞等待（`await queue.get()`）
   - 发送者不等待接收者处理，可以继续做其他事情

2. **任务追踪**：
   - 所有任务都在 `TaskManager` 中注册
   - 通过 `task_id` 可以查询任务状态、进度、结果
   - 支持 PENDING → RUNNING → COMPLETED/FAILED 状态流转

3. **FIFO 保证**：
   - `asyncio.Queue` 保证消息按顺序处理
   - Manager 连续发送 3 个任务，Agent 按顺序执行

4. **消息记录**：
   - 所有消息都记录到 `GroupChatSession`
   - 包括 User 消息、Manager 任务、Agent 结果
   - 便于调试和信息公开

5. **群聊消息写入时机**：
   - 在 `Agent._process_message()` 中，LLM 返回后立即写入
   - 确保每次 Agent 的回复都被记录到群聊历史
   - 写入时机：LLM 返回后、发送下一条消息前

---

## 三种使用场景

### 场景 1：Workflow（顺序执行）

**特点：**
- 执行顺序确定（User 明确告知）
- Manager 维护 workflow 状态机
- 按顺序调度 Agent

**流程：**
```
User: "请按照 A→B→C 顺序开发登录功能"
    ↓
Manager 解析：workflow = ["Agent A", "Agent B", "Agent C"]
    ↓
Manager → Agent A: "@Agent A 请分析需求"
    ↓
Agent A 完成 → Manager: "@Manager 任务完成"
    ↓
Manager → Agent B: "@Agent B 请开始设计"
    ↓
Agent B 完成 → Manager: "@Manager 任务完成"
    ↓
Manager → Agent C: "@Agent C 请开始编码"
    ↓
...
```

**Manager 实现要点：**
- 维护 `workflow` 列表和 `current_step` 索引
- 收到 Agent 回复后，`current_step += 1`
- 继续发送给下一个 Agent

---

### 场景 2：Manager-SubAgent（动态协调）

**特点：**
- 执行顺序不确定
- Manager 通过 LLM 动态决策下一步
- 灵活应对复杂任务

**流程：**
```
User: "帮我开发登录功能"
    ↓
Manager LLM 决策：需要先分析需求 → 调用 Agent A
    ↓
Manager → Agent A: "@Agent A 请分析需求"
    ↓
Agent A 完成 → Manager: "@Manager 需求分析完成"
    ↓
Manager LLM 决策：需要设计架构 → 调用 Agent B
    ↓
Manager → Agent B: "@Agent B 请设计架构"
    ↓
...
```

**Manager 实现要点：**
- 每次收到消息后，调用 LLM 决策
- LLM 输出：调用哪个 Agent + 给他什么任务
- 动态调整执行流程

**注意：**
- Manager 的决策逻辑超出消息设计范围
- 需要防止死循环（最大轮数限制）

---

### 场景 3：User 直接 @Agent

**特点：**
- User 绕过 Manager，直接与 Agent 对话
- Manager 通过 GroupChatSession 仍能看到对话

**流程：**
```
User: "@Agent A 请分析这个需求"
    ↓
系统解析 @Agent A
    ↓
匹配成功 → 直接路由到 Agent A
匹配失败 → 降级到 Manager
    ↓
Agent A 处理 → 回复 User
    ↓
消息记录到 GroupChatSession
    ↓
Manager 下次被触发时，能看到这段对话
```

**实现要点：**
- 外部系统（UI 层）解析 User 输入的 `@`
- 提取目标 Agent 名称
- 调用 `message_bus.publish_message()` 直接路由
- 所有消息都记录到 `GroupChatSession`，Manager 不会丢失上下文

---

## 关键设计决策

### 决策 1：为什么不用 MetaGPT 的双向引用？

**MetaGPT 方式：**
```python
Agent.rc.env → Environment
Environment.roles[name] → Agent
```

**问题：**
- Agent 能通过 `self.rc.env.roles[name]` 访问其他 Agent
- Agent 理论上能调用其他 Agent 的任何方法
- 程序上容易出错，存在越权风险

**我们的方式：**
```python
Agent._bus → MessageRouter
MessageRouter._agent_buffers[name] → Queue（私有变量）
```

**优点：**
- Agent 只能调用 `_bus.publish_message()`
- Agent 无法访问 `_agent_buffers`（私有变量）
- 完全避免越权

---

### 决策 2：为什么不用 AutoGen 的公共 Buffer？

**AutoGen 方式：**
```python
GroupChat.message_buffer = []  # 公共 buffer
Agent 主动过滤：for msg in buffer if msg.send_to == self.name
```

**问题：**
- 所有 Agent 都能看到所有消息
- 依赖 Agent "自觉"不偷看其他消息
- 不符合"按需提供上下文"原则

**我们的方式：**
```python
每个 Agent 有私有队列
MessageRouter 精确路由到目标队列
```

**优点：**
- Agent 的队列里只有发给自己的消息
- 不需要过滤，不会看到无关消息
- 真正的点对点路由

---

### 决策 3：为什么不用中心化暂存队列？

**中心化队列方式：**
```python
MessageRouter._central_queue = asyncio.Queue()
后台任务：从 central_queue 取消息 → 路由到私有队列
```

**问题：**
- 多了一层中转，增加延迟
- 需要后台任务维护
- 增加复杂度，无实际价值

**我们的方式：**
```python
MessageRouter.publish_message() 直接路由到私有队列
```

**优点：**
- 简单直接，无额外延迟
- 私有队列已经提供异步解耦
- 不需要后台任务

---

## 与现有代码的集成

### 已实现的部分（team.py）

1. **GroupChatContext**：
   - `get_agent_context(agent_name)`：获取定制化上下文
   - `compact_messages(agent_info)`：压缩历史消息
   - `load_compact_history()`：加载压缩历史

2. **GroupChatSession**：
   - `add_message(agent_result)`：记录消息
   - `get_uncompact_messages()`：获取未压缩消息

3. **Agent 基础结构**：
   - `Agent.message_buffer`：私有队列（已定义）
   - `Agent.execute()`：LLM 调用接口

4. **MessageRouter 基础**：
   - 已实现 `register()` 和 `send_message()`
   - 需要扩展以支持任务管理

### 需要新增的部分

1. **TaskManager 类**：
   - 实现 `Task` 和 `TaskStatus` 数据结构
   - 实现 `create_task()`、`get_task()`、`update_status()`、`set_result()`、`set_error()`
   - 集成到 `GroupChatContext` 中

2. **Message 数据类扩展**：
   - 添加 `task_id` 字段
   - 添加 `message_type` 字段（可选，用于避免循环回复）

3. **Agent 消息处理逻辑扩展**：
   - 修改 `_process_message()`，添加任务状态更新逻辑
   - 添加群聊消息写入逻辑
   - 添加 session_id 更新逻辑

4. **call_agent 工具扩展**：
   - 修改为先创建任务，再发送消息
   - 返回 task_id 而不是简单的成功消息

5. **query_task_status 工具**：
   - 新增工具，用于查询任务状态
   - 返回 JSON 格式的任务详情

6. **GroupChat 类扩展**：
   - 添加 `task_manager` 成员变量
   - 在初始化时创建 `TaskManager` 实例

---

## 实现优先级

### P0（核心功能）

1. 实现 `TaskManager` 类和相关数据结构
2. 实现 `Task` 和 `TaskStatus` 枚举
3. 修改 `AgentsMessage`：添加 `task_id` 字段
4. 修改 `Agent._process_message()`：
   - 添加任务状态更新逻辑
   - 添加群聊消息写入逻辑
   - 添加 session_id 更新逻辑
5. 修改 `call_agent()`：集成任务创建和 task_id 返回
6. 实现 `query_task_status()` 工具
7. 修改 `GroupChat.__init__()`：添加 `TaskManager` 初始化
2. 实现 `Message` 数据类
3. 修改 `Agent` 类：
   - 添加 `send_message()` 方法
   - 添加 `run()` 主循环
   - 添加 `_process_message()` 方法
4. 修改 `GroupChatSession.add_message()`：支持通用消息格式

### P1（场景支持）

1. 实现 `MessageType` 枚举（TASK / NOTIFICATION / QUERY）
2. 修改 `Agent._process_message()`：根据 `message_type` 决定是否回复
3. 实现 `Manager` 类的 workflow 调度逻辑
4. 实现 User `@Agent` 的解析和路由
5. 实现任务完成后的自动通知机制（可选）

### P2（优化）

1. 添加消息路由日志
2. 添加错误处理（目标 Agent 不存在）
3. 添加任务超时机制
4. 添加任务取消功能
5. 实现任务持久化（保存到文件）

---

## 注意事项

1. **User 消息的处理**：
   - User 不是 Agent，没有 `message_buffer`
   - User 消息的发送和接收由外部业务层处理
   - 本方案暂不涉及 User 与系统的交互接口

2. **Manager 的决策逻辑**：
   - 超出消息设计范围
   - 需要单独设计 Manager 的 prompt 和决策流程

3. **消息持久化**：
   - 当前通过 `GroupChatSession` 持久化到 JSONL 文件
   - MessageRouter 不负责持久化，只负责路由

4. **并发安全**：
   - `asyncio.Queue` 天然支持并发
   - 多个 Agent 可以并发发送消息
   - MessageRouter 的 `publish_message()` 是同步方法，但 `put_nowait()` 是线程安全的

5. **任务管理的持久化**：
   - 当前 `TaskManager._tasks` 是内存字典
   - 如果需要持久化，可以扩展为定期保存到文件
   - 或者在任务状态变更时触发保存

6. **异步设计的权衡**：
   - **优点**：真正的异步，调用者不阻塞，支持并发任务
   - **缺点**：LLM 需要主动查询结果，增加复杂度
   - **建议**：初期实现异步 + 查询工具，后期可以添加自动通知机制

7. **循环回复的避免**：
   - 通过 `MessageType` 区分 TASK 和 NOTIFICATION
   - TASK 需要执行并回复，NOTIFICATION 只记录不回复
   - 确保消息链路有明确的终止条件

---

## 设计决策总结

### 决策 1：群聊消息何时写入？

**决策**：在 `Agent._process_message()` 中，LLM 返回后立即写入

**理由**：
- 确保每次 Agent 的回复都被记录
- 写入时机明确：LLM 返回后、发送下一条消息前
- 便于调试和追踪对话历史

### 决策 2：call_agent 是否立即返回结果？

**决策**：采用异步设计，立即返回 task_id，不等待执行完成

**理由**：
- 真正的异步，调用者不阻塞
- 支持并发任务（A 可以同时派遣多个任务给不同的 Agent）
- 符合现实场景（派遣任务后继续做其他事）
- 通过 `query_task_status` 工具查询结果

**权衡**：
- 增加了 LLM 的使用复杂度（需要主动查询）
- 但提供了更大的灵活性和并发能力

### 决策 3：B 完成任务后是否自动通知 A？

**决策**：默认不自动通知，A 需要主动查询；可选支持自动通知

**理由**：
- 避免无限循环（A → B → A → B ...）
- 通过 `MessageType` 区分 TASK 和 NOTIFICATION
- 给予 LLM 更多控制权（决定何时查询结果）

**可选扩展**：
- 在 `_process_message` 中添加自动通知逻辑
- 发送 NOTIFICATION 类型消息给任务发起者
- A 收到 NOTIFICATION 后不会自动回复

### 决策 4：任务如何统一管理？

**决策**：引入 `TaskManager`，所有任务在其中注册

**理由**：
- 避免任务分散在各个 Agent 的队列中
- 提供统一的任务状态追踪和查询能力
- `_tasks` 字典就是异步任务的 "pending 池"
- 支持查询任务状态、执行时长、结果等信息

---

## 总结

2. **Manager 的决策逻辑**：
   - 超出消息设计范围
   - 需要单独设计 Manager 的 prompt 和决策流程

3. **消息持久化**：
   - 当前通过 `GroupChatSession` 持久化到 JSONL 文件
   - MessageRouter 不负责持久化，只负责路由

4. **并发安全**：
   - `asyncio.Queue` 天然支持并发
   - 多个 Agent 可以并发发送消息
   - MessageRouter 的 `publish_message()` 是同步方法，但 `put_nowait()` 是线程安全的

---

## 总结

本方案通过以下设计实现了三个核心原则：

1. **避免越权**：Agent 只持有 MessageRouter 引用，无法访问其他 Agent
2. **按需上下文**：通过 `GroupChatContext.get_agent_context()` 提供定制化上下文
3. **点对点路由**：MessageRouter 精确路由到目标 Agent 的私有队列

核心优势：
- 简单直接，无过度设计
- 异步解耦，支持并发
- 消息有序，FIFO 保证
- 完整记录，便于调试

下一步：按照实现优先级逐步开发。
