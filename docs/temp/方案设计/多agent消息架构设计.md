# 多 Agent 消息架构设计方案

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

### 1. MessageBus（消息总线）

**职责：**
- 管理所有 Agent 的私有队列引用
- 负责点对点消息路由
- 记录所有消息到 GroupChatSession

**关键设计：**
```python
class MessageBus:
    _agent_buffers: dict[str, asyncio.Queue]  # Agent 名称 → 私有队列
    _context: GroupChatContext                 # 群聊上下文引用
    
    def register(agent_name, buffer):
        """注册 Agent 的私有队列"""
    
    def publish_message(msg):
        """点对点路由 + 记录历史"""
        # 1. 记录到 GroupChatSession
        # 2. 路由到目标 Agent 的私有队列
```

**为什么不用中心化暂存队列：**
- 私有队列已经提供异步解耦
- 中心化队列只是多一层中转，无实际价值
- 直接路由更简单高效

---

### 2. Agent（智能体）

**职责：**
- 持有私有消息队列（`asyncio.Queue`）
- 持有 MessageBus 引用（用于发送消息）
- 持有 GroupChatContext 引用（用于读取上下文）
- 从队列接收消息并处理

**关键设计：**
```python
class Agent:
    name: str
    message_buffer: asyncio.Queue           # 私有队列
    context: GroupChatContext               # 上下文引用
    _bus: MessageBus                        # 消息总线引用
    
    def send_message(content, send_to):
        """发送消息：Agent 不知道目标在哪，只知道名字"""
        msg = Message(content, send_to, sent_from=self.name)
        self._bus.publish_message(msg)
    
    async def run():
        """主循环：从队列取消息并处理"""
        while True:
            msg = await self.message_buffer.get()  # 阻塞等待
            await self._process_message(msg)
    
    async def _process_message(msg):
        # 1. 从 GroupChatContext 获取上下文
        # 2. 组装 prompt
        # 3. 执行 LLM 调用
        # 4. 发送回复消息
```

**为什么 Agent 持有 GroupChatContext：**
- 这不是"耦合"，这是"依赖注入"
- Agent 需要读取上下文来执行任务
- Agent 只读取，不修改其他 Agent 的状态
- 类比：Agent 依赖 RoleConfig 一样合理

---

### 3. Message（消息）

**职责：**
- 承载消息内容和路由信息

**关键设计：**
```python
@dataclass
class Message:
    content: str        # 消息内容
    send_to: str        # 接收者（路由目标）
    sent_from: str      # 发送者
    timestamp: datetime
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

### 4. GroupChatContext（群聊上下文）

**职责：**
- 管理群聊历史消息（`GroupChatSession`）
- 管理压缩历史（`compact_history.jsonl`）
- 为每个 Agent 提供定制化上下文

**关键设计：**
```python
class GroupChatContext:
    group_chat_session: GroupChatSession    # 原始消息历史
    compact_history_file: str               # 压缩历史文件路径
    
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

## 消息流转完整链路

### 基本流程

```
发送者.send_message(content, send_to)
    ↓
MessageBus.publish_message(msg)
    ↓
1. 记录到 GroupChatSession
2. 路由到目标 Agent 的 message_buffer
    ↓
目标 Agent.message_buffer.get()
    ↓
目标 Agent._process_message(msg)
    ↓
1. 从 GroupChatContext 获取上下文
2. 组装 prompt
3. 执行 LLM 调用
4. 发送回复消息（回到第一步）
```

### 关键点

1. **异步解耦**：
   - 发送者调用 `send_message()` 立即返回
   - 接收者从队列阻塞等待（`await queue.get()`）
   - 发送者不等待接收者处理

2. **FIFO 保证**：
   - `asyncio.Queue` 保证消息按顺序处理
   - Manager 连续发送 3 个任务，Agent 按顺序执行

3. **消息记录**：
   - 所有消息都记录到 `GroupChatSession`
   - 包括 User 消息、Manager 任务、Agent 结果
   - 便于调试和信息公开

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
Agent._bus → MessageBus
MessageBus._agent_buffers[name] → Queue（私有变量）
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
MessageBus 精确路由到目标队列
```

**优点：**
- Agent 的队列里只有发给自己的消息
- 不需要过滤，不会看到无关消息
- 真正的点对点路由

---

### 决策 3：为什么不用中心化暂存队列？

**中心化队列方式：**
```python
MessageBus._central_queue = asyncio.Queue()
后台任务：从 central_queue 取消息 → 路由到私有队列
```

**问题：**
- 多了一层中转，增加延迟
- 需要后台任务维护
- 增加复杂度，无实际价值

**我们的方式：**
```python
MessageBus.publish_message() 直接路由到私有队列
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

### 需要新增的部分

1. **MessageBus 类**：
   - 实现 `register()` 和 `publish_message()`
   - 注入 `GroupChatContext` 引用

2. **Message 数据类**：
   - 定义消息格式

3. **Agent 消息处理逻辑**：
   - 实现 `send_message()`
   - 实现 `run()` 主循环
   - 实现 `_process_message()`

4. **GroupChatSession 扩展**：
   - 支持记录非 `AgentResult` 的消息（User、Manager 的消息）
   - 建议：`add_message()` 改为接受通用参数（sender, content, send_to）

---

## 实现优先级

### P0（核心功能）

1. 实现 `MessageBus` 类
2. 实现 `Message` 数据类
3. 修改 `Agent` 类：
   - 添加 `send_message()` 方法
   - 添加 `run()` 主循环
   - 添加 `_process_message()` 方法
4. 修改 `GroupChatSession.add_message()`：支持通用消息格式

### P1（场景支持）

1. 实现 `Manager` 类的 workflow 调度逻辑
2. 实现 User `@Agent` 的解析和路由
3. 实现 Agent 回复逻辑（根据 `sent_from` 决定回复对象）

### P2（优化）

1. 添加消息路由日志
2. 添加错误处理（目标 Agent 不存在）
3. 添加消息重试机制（可选）

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
   - MessageBus 不负责持久化，只负责路由

4. **并发安全**：
   - `asyncio.Queue` 天然支持并发
   - 多个 Agent 可以并发发送消息
   - MessageBus 的 `publish_message()` 是同步方法，但 `put_nowait()` 是线程安全的

---

## 总结

本方案通过以下设计实现了三个核心原则：

1. **避免越权**：Agent 只持有 MessageBus 引用，无法访问其他 Agent
2. **按需上下文**：通过 `GroupChatContext.get_agent_context()` 提供定制化上下文
3. **点对点路由**：MessageBus 精确路由到目标 Agent 的私有队列

核心优势：
- 简单直接，无过度设计
- 异步解耦，支持并发
- 消息有序，FIFO 保证
- 完整记录，便于调试

下一步：按照实现优先级逐步开发。
