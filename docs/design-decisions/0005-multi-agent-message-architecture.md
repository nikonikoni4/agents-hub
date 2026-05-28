---
version: 1.0
created_at: 2026-05-28
updated_at: 2026-05-28
last_updated: 2026-05-28
abstract: 多 Agent 消息传递架构设计，拒绝 MetaGPT 双向引用和 AutoGen 公共 Buffer 方案，选择 MessageBus + 私有队列的点对点路由方案
status: decided
---

# 多 Agent 消息传递架构设计

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0  | 创建文档初稿 |

## 问题界定

### 问题简述

在多 Agent 协作系统中，需要设计一个消息传递机制，使得：
1. Manager 能够向 SubAgent 分配任务
2. SubAgent 能够回复 Manager 或其他 Agent
3. User 能够直接与特定 Agent 交互
4. 所有消息都被记录到群聊历史中

当前存在两个主流方案（MetaGPT 和 AutoGen），需要决策是采用其中之一，还是设计新方案。

### 讨论范围

- Agent 之间的消息传递机制
- 消息路由方式（点对点 vs 广播）
- Agent 对其他 Agent 的访问权限控制
- 消息队列的使用方式（公共队列 vs 私有队列）
- 上下文获取方式（Agent 如何读取历史消息）

### 非讨论范围

- Manager 的决策逻辑（如何决定调用哪个 Agent）
- User 与系统的交互接口（UI 层）
- 消息内容的具体格式（LLM prompt 的组装方式）
- GroupChatContext 的实现细节（已在 `team.py` 中实现）

### 模糊信息的明确定义

- **耦合**：在本文中特指"Agent 能够直接访问其他 Agent 的方法和状态"，而非"Agent 持有共享资源的引用"
- **点对点**：消息精确路由到目标 Agent 的私有队列，目标 Agent 的队列中只包含发给它的消息
- **广播**：消息发送到公共 Buffer，所有 Agent 都能看到，需要 Agent 自己过滤

### 问题深度

这是一个涉及架构原则的深层问题：
- 如何在多 Agent 系统中实现职责边界
- 如何防止 Agent 越权访问
- 如何平衡解耦和效率
- 如何设计可扩展的消息传递机制

## 现状

### 已实现的部分

1. **GroupChatContext**（`tests/explore/多agent架构/team.py`）：
   - 管理群聊历史消息（`GroupChatSession`）
   - 管理压缩历史（`compact_history.jsonl`）
   - 提供 `get_agent_context(agent_name)` 方法，为每个 Agent 提供定制化上下文

2. **Agent 基础结构**：
   - 每个 Agent 有 `message_buffer: asyncio.Queue`（私有队列，已定义但未使用）
   - 每个 Agent 有 `execute()` 方法（LLM 调用接口）

### 当前问题

1. **消息传递机制缺失**：
   - Manager 无法向 SubAgent 发送任务
   - Agent 之间无法通信
   - 缺少消息路由逻辑

2. **参考方案的问题**：
   - **MetaGPT 方案**：Agent 通过 `env.roles[name]` 可以访问其他 Agent 的所有方法，存在越权风险
   - **AutoGen 方案**：所有 Agent 看到完整群聊历史，不符合"按需提供上下文"原则

## 可选方案

### 方案 A：MetaGPT 双向引用

**方案内容：**

```python
# Agent 持有 Environment 引用
Agent.rc.env → Environment

# Environment 持有所有 Agent 引用
Environment.roles[name] → Agent

# 消息发送
manager.rc.env.publish_message(msg)

# Environment 路由到目标 Agent
env.roles[target_name].message_buffer.push(msg)
```

**优势**

- 直接高效，无中间层
- MetaGPT 已验证可行
- 实现简单

**劣势**

- **越权风险**：Agent 能通过 `self.rc.env.roles[name]` 访问其他 Agent 的任何方法
- **程序上容易出错**：双向引用在重构时容易产生循环依赖
- **违反最小权限原则**：Agent 拥有超出其职责范围的权限
- **不符合设计原则 1**："避免越权访问"

### 方案 B：AutoGen 公共 Buffer + 主动过滤

**方案内容：**

```python
# 公共 Buffer
GroupChat.message_buffer = []

# Manager 发送
group_chat.message_buffer.append(msg)

# Agent 主动过滤
for msg in group_chat.message_buffer:
    if msg.send_to == self.name:
        # 处理消息
```

**优势**

- 实现简单，无需路由逻辑
- AutoGen 已验证可行
- 所有消息天然记录在 Buffer 中

**劣势**

- **不是真正的点对点**：所有 Agent 都能看到所有消息
- **依赖 Agent "自觉"**：Agent 可以偷看其他 Agent 的消息
- **上下文冗余**：每个 Agent 看到完整历史，包含大量无关信息
- **不符合设计原则 2**："按需提供上下文"
- **不符合设计原则 3**："点对点优于广播"

### 方案 C：MessageBus + 私有队列（本方案）

**方案内容：**

```python
# MessageBus 持有所有 Agent 的私有队列引用
class MessageBus:
    _agent_buffers: dict[str, asyncio.Queue]  # 私有变量
    
    def register(agent_name, buffer):
        """注册 Agent 的私有队列"""
    
    def publish_message(msg):
        """点对点路由"""
        target_buffer = self._agent_buffers.get(msg.send_to)
        if target_buffer:
            target_buffer.put_nowait(msg)

# Agent 持有 MessageBus 引用
class Agent:
    _bus: MessageBus
    message_buffer: asyncio.Queue
    context: GroupChatContext
    
    def send_message(content, send_to):
        msg = Message(content, send_to, sent_from=self.name)
        self._bus.publish_message(msg)
    
    async def run():
        while True:
            msg = await self.message_buffer.get()
            await self._process_message(msg)
```

**优势**

- **完全避免越权**：Agent 只能调用 `_bus.publish_message()`，无法访问 `_agent_buffers`（私有变量）
- **真正的点对点**：Agent 的队列中只有发给自己的消息，不需要过滤
- **按需提供上下文**：Agent 通过 `GroupChatContext.get_agent_context()` 获取定制化上下文
- **异步解耦**：发送者立即返回，接收者从队列阻塞等待
- **FIFO 保证**：`asyncio.Queue` 保证消息按顺序处理
- **符合所有设计原则**

**劣势**

- 需要实现 MessageBus 类（新增代码）
- Agent 需要持有 MessageBus 和 GroupChatContext 两个引用（但这是依赖注入，不是耦合）

## 最终决策

选择**方案 C：MessageBus + 私有队列**。

## 决策原因

### 原因 1：避免越权访问是核心安全需求

在多 Agent 系统中，Agent 之间应该是平等的协作关系，而非主从关系。如果 Agent A 能够直接调用 Agent B 的方法，会导致：
- 程序逻辑混乱（谁调用了谁？）
- 难以追踪消息流转
- 重构时容易引入 bug

**方案 A（MetaGPT）的问题：**
```python
# Agent A 可以这样做
agent_b = self.rc.env.roles["Agent B"]
agent_b.some_method()  # 直接调用 Agent B 的方法
```

这违反了"最小权限原则"，Agent A 不应该拥有这种权限。

**方案 C 的优势：**
```python
# Agent A 只能这样做
self._bus.publish_message(msg)  # 发送消息，不知道目标在哪
```

Agent A 无法访问 `_agent_buffers`（私有变量），完全避免越权。

---

### 原因 2：按需提供上下文是性能和清晰度的要求

在群聊场景中，不同 Agent 的职责不同，关注的信息也不同。例如：
- Agent A（需求分析师）关注用户需求和业务逻辑
- Agent B（架构师）关注技术选型和系统设计
- Agent C（开发者）关注具体实现细节

如果所有 Agent 都看到完整历史，会导致：
- **Token 浪费**：Agent A 不需要看到 Agent C 的代码实现细节
- **注意力分散**：大量无关信息干扰 Agent 的判断
- **上下文混乱**：Agent 可能误解其他 Agent 的任务

**方案 B（AutoGen）的问题：**
```python
# 所有 Agent 看到完整历史
for msg in group_chat.message_buffer:
    if msg.send_to == self.name:
        # 处理消息
    # 但 Agent 仍然能看到其他消息
```

**方案 C 的优势：**
- Agent 的私有队列只包含发给自己的消息
- Agent 通过 `GroupChatContext.get_agent_context(self.name)` 获取定制化上下文
- 上下文包括：压缩历史的 summary（全局）+ 针对自己的部分 + 最新消息（过滤后）

---

### 原因 3：点对点路由是消息传递的最佳实践

在分布式系统和消息队列系统中，点对点路由是标准做法：
- **RabbitMQ**：Direct Exchange 实现点对点路由
- **Kafka**：Topic + Partition 实现精确投递
- **Redis Pub/Sub**：Channel 实现订阅路由

广播模式（Pub/Sub）适用于"一对多"场景（如通知所有 Agent），但在"一对一"任务分配场景中，点对点更合适。

**方案 B（AutoGen）的问题：**
- 广播所有消息，依赖 Agent 自己过滤
- 不适合"Manager → Agent A"这种明确的一对一场景

**方案 C 的优势：**
- MessageBus 根据 `msg.send_to` 精确路由
- 目标 Agent 的队列中只有发给自己的消息
- 符合消息队列的最佳实践

---

### 原因 4：依赖注入不是耦合

用户在讨论中提到"担心 Agent 持有 GroupChatContext 会导致耦合"。这是对"耦合"概念的误解。

**耦合的定义：**
- Agent A 能够修改 Agent B 的状态
- Agent A 的实现依赖 Agent B 的实现细节

**依赖注入的定义：**
- Agent 依赖一个接口或抽象类
- Agent 通过构造函数接收依赖
- Agent 只调用依赖的公开方法

**方案 C 中的依赖关系：**
```python
class Agent:
    def __init__(self, name, message_bus, context):
        self._bus = message_bus          # 依赖注入
        self.context = context            # 依赖注入
```

这和 Agent 依赖 `RoleConfig` 一样合理：
```python
class Agent:
    def __init__(self, role: Role):
        self.role_config = role.get_role_config()  # 依赖注入
```

Agent 只读取 `GroupChatContext`，不修改其他 Agent 的状态，这不是耦合。

---

### 原因 5：方案 C 的"劣势"实际上不是问题

**劣势 1："需要实现 MessageBus 类"**
- 实现成本低（约 20 行代码）
- 职责清晰，易于测试
- 符合单一职责原则（SRP）

**劣势 2："Agent 需要持有两个引用"**
- 这是依赖注入的标准做法
- 两个依赖的职责不同：
  - `MessageBus`：发送消息
  - `GroupChatContext`：读取上下文
- 符合接口隔离原则（ISP）

---

### 原因 6：方案 C 支持所有使用场景

在讨论中确认了三种使用场景：

**场景 1：Workflow（顺序执行）**
- Manager 维护 workflow 状态机
- 按顺序发送消息给 Agent A → Agent B → Agent C
- ✅ 方案 C 支持

**场景 2：Manager-SubAgent（动态协调）**
- Manager 通过 LLM 动态决策下一步
- 发送消息给任意 Agent
- ✅ 方案 C 支持

**场景 3：User 直接 @Agent**
- User 绕过 Manager，直接与 Agent 对话
- 消息仍然记录到 GroupChatSession
- ✅ 方案 C 支持（通过 MessageBus 路由 + GroupChatSession 记录）

方案 A 和方案 B 也能支持这些场景，但方案 C 在安全性和清晰度上更优。

## 后续影响

### 对代码结构的影响

1. **需要新增 MessageBus 类**：
   - 位置：`agents_hub/messaging/message_bus.py`
   - 职责：管理 Agent 队列引用，实现点对点路由

2. **需要新增 Message 数据类**：
   - 位置：`agents_hub/messaging/models.py`
   - 字段：`content`, `send_to`, `sent_from`, `timestamp`

3. **需要修改 Agent 类**：
   - 添加 `send_message()` 方法
   - 添加 `run()` 主循环
   - 添加 `_process_message()` 方法

4. **需要扩展 GroupChatSession**：
   - 当前 `add_message()` 只接受 `AgentResult`
   - 需要支持通用消息格式（User 消息、Manager 任务消息）

### 对测试的影响

1. **MessageBus 单元测试**：
   - 测试注册机制
   - 测试路由逻辑
   - 测试错误处理（目标 Agent 不存在）

2. **Agent 消息处理测试**：
   - 测试消息发送
   - 测试消息接收
   - 测试上下文获取

### 对文档的影响

1. **需要更新架构文档**：
   - 说明 MessageBus 的职责
   - 说明消息流转链路

2. **需要编写使用指南**：
   - 如何创建 Agent
   - 如何发送消息
   - 如何处理消息

### 需要后续验证的事项

1. **性能验证**：
   - 在 10+ Agent 并发场景下，MessageBus 的性能是否满足要求
   - 私有队列的内存占用是否可接受

2. **错误处理验证**：
   - 目标 Agent 不存在时的处理
   - Agent 处理消息失败时的重试机制

3. **扩展性验证**：
   - 是否需要支持消息优先级
   - 是否需要支持消息持久化（当前通过 GroupChatSession 实现）

## 与其他决策的关联

- 本决策与 `0003-agent-bridge-architecture-choice.md` 一致：都选择了职责清晰、扩展性强的架构
- 本决策体现了用户的一贯偏好：**安全性和清晰度优于实现简单性**（参见 `user-design-summary.md`）
