---
version: 1.1
created_at: 2026-06-05
updated_at: 2026-06-05
last_updated: 修正：所有消息都保存到群聊历史，GroupChat 提供统一包装方法
abstract: 定义 user、agent 之间的消息传递流程、MessageRouter 职责边界（纯投递层）、GroupChat.send_message_to_agent() 统一包装投递和保存、所有消息都保存到群聊历史的规则
id: spec-message-flow-and-persistence
title: 消息流转与持久化规格
status: draft
module: core/communication, core/orchestration, mcp
sourc_spec: null
related_plan: null
code_scope:
  - agents_hub/core/communication/message_router.py
  - agents_hub/mcp/server.py
  - agents_hub/core/orchestration/group_chat.py
contract_refs:
  - agents_hub/core/communication/message_router.py
  - agents_hub/core/context/group_chat_context.py
  - agents_hub/mcp/server.py
---

# 消息流转与持久化规格

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |
| 1.1 | 修正：所有消息都保存到群聊历史，GroupChat 提供统一包装方法 |

## Overview

本 spec 定义系统中所有消息的传递路径、MessageRouter 的职责边界、以及消息保存到群聊历史的统一机制。

**核心原则**：
1. **MessageRouter 是纯投递层**，只负责将消息投递到目标 Agent 的队列，不承担业务逻辑
2. **GroupChat 提供统一包装方法**，所有通过 MessageRouter 投递的消息都通过 `GroupChat.send_message_to_agent()` 完成投递和保存
3. **所有消息都保存到群聊历史**，确保完整的消息记录供前端展示和上下文管理

## Scope

### 范围内

- user → agent 消息流程
- agent → agent 消息流程（TASK / NOTIFICATION）
- 群聊公开发言流程（speak_in_group_chat）
- 消息保存到群聊历史的触发时机
- MessageRouter 的职责边界

### 范围外

- Agent 内部的执行逻辑（属于 agent 层）
- 群聊上下文的压缩和增量加载（属于 context 层）
- AgentCall 状态机（已在 core-communication spec 中定义）

## Core Behavior

### 消息传递路径

系统中存在三种主要消息流程：

#### 1. user → agent 消息（API 发送）

```
前端 → HTTP API (send_message_to_agent)
     → GroupChat.send_message_to_agent()
     → MessageRouter.send_message() (投递)
     → add_message() (保存发送方消息)
     → agent.message_queue
     → agent.run() 处理
     → complete_task 完成任务
     → 保存 agent 回复到群聊历史
```

**保存时机**：
1. 发送时保存 user 消息（`GroupChat.send_message_to_agent()` 调用 `add_message()`）
2. 完成时保存 agent 回复（`complete_task` 判断 `is_user_name()` 后保存）

#### 2. agent → agent 消息（MCP tool 调用）

```
agent_a 调用 call_agent
       → AgentCallManager.create_call()
       → GroupChat.send_message_to_agent()
       → MessageRouter.send_message() (投递)
       → add_message() (保存发送方消息)
       → agent_b.message_queue
       → agent_b.run() 处理
       → complete_task 完成任务
       → 发送 NOTIFICATION 给 agent_a
       → GroupChat.send_message_to_agent()
       → MessageRouter.send_message() (投递)
       → add_message() (保存 NOTIFICATION)
       → agent_a.message_queue
```

**保存时机**：每次调用 `GroupChat.send_message_to_agent()` 都会保存消息，包括：
1. agent_a 调用 agent_b 的 TASK 消息
2. agent_b 完成后发送给 agent_a 的 NOTIFICATION

#### 3. 群聊公开发言（speak_in_group_chat）

```
agent 调用 speak_in_group_chat
       → 直接调用 GroupChatContext.add_message()
       → 保存到群聊历史
       → 不经过 MessageRouter
```

**保存时机**：立即保存到群聊历史。

### MessageRouter 职责边界

**MessageRouter 只负责**：
- 验证消息格式（内容非空、发送方和接收方已注册）
- 投递消息到目标 Agent 的队列
- 处理投递失败（队列满、目标不存在）

**MessageRouter 不负责**：
- ❌ 决定哪些消息需要保存到群聊历史
- ❌ 调用 `GroupChatContext.add_message()`
- ❌ 区分消息类型（TASK / NOTIFICATION）
- ❌ 判断调用方是 user 还是 agent
- ❌ 依赖 `GroupChatContext` 或任何业务层组件

**原因**：
1. MessageRouter 属于 communication 层，不应依赖 context 层（违反分层原则）
2. 消息保存是业务逻辑，应由编排层（GroupChat）统一处理
3. MessageRouter 应该是可复用的通用组件，不耦合群聊历史的概念

### GroupChat 统一包装方法

GroupChat 提供 `send_message_to_agent()` 方法，包装消息投递和保存：

```python
async def send_message_to_agent(self, message: AgentMessage):
    """
    发送消息到目标 Agent 并保存到群聊历史
    
    1. 通过 MessageRouter 投递消息
    2. 保存发送方消息到群聊历史
    """
    await self.message_router.send_message(message)  # 投递
    await self.group_chat_context.add_message(...)    # 保存
```

**使用场景**：
- MCP tool `call_agent`：agent 调用 agent
- MCP tool `complete_task`：发送 NOTIFICATION 给原调用方
- API `send_message_to_agent`：user 发送消息给 agent

### 群聊历史保存规则

| 消息来源 | 消息类型 | 是否保存到群聊历史 | 保存位置 |
|---------|---------|----------------|---------|
| user → agent TASK | 发送消息 | ✅ 保存 | `GroupChat.send_message_to_agent()` |
| user → agent TASK 完成 | 回复内容 | ✅ 保存 | `complete_task` 中判断 `is_user_name()` |
| agent → agent TASK | 发送消息 | ✅ 保存 | `GroupChat.send_message_to_agent()` |
| agent → agent NOTIFICATION | 完成通知 | ✅ 保存 | `GroupChat.send_message_to_agent()` |
| speak_in_group_chat | 公开发言 | ✅ 保存 | `speak_in_group_chat` 直接调用 `add_message()` |
| Agent 初始化打招呼 | 初始化消息 | ✅ 保存 | `GroupChat._initialize_new_members()` |

**判断原则**：
- 所有通过 MessageRouter 投递的消息都保存（通过 `GroupChat.send_message_to_agent()` 统一处理）
- 公开发言直接保存（不经过 MessageRouter）
- 确保完整的消息记录供前端展示和上下文管理

## Technical Contract

### MessageRouter 接口

```python
class MessageRouter:
    def __init__(self):
        """不依赖任何业务组件，不注入 group_chat_context"""
        self._agents_queue: dict[str, asyncio.Queue] = {}
    
    def register(self, name: str, queue: asyncio.Queue):
        """注册 Agent 的消息队列"""
    
    def unregister(self, name: str):
        """注销 Agent 的消息队列"""
    
    async def send_message(self, message: AgentMessage):
        """
        发送消息到目标 Agent 的队列（纯投递，不保存）
        
        职责：
        1. 验证消息格式
        2. 投递到目标队列
        3. 抛出投递失败异常
        
        不做：
        - 不调用 add_message()
        - 不依赖 GroupChatContext
        - 不区分消息类型
        """
    
    def clear(self):
        """清空所有消息队列并注销所有 Agent"""
```

### GroupChat 接口

```python
class GroupChat:
    async def send_message_to_agent(self, message: AgentMessage):
        """
        发送消息到目标 Agent 并保存到群聊历史
        
        包装 MessageRouter.send_message() 和消息保存逻辑，
        确保所有通过控制面投递的消息都被记录。
        
        流程：
        1. 通过 MessageRouter 投递消息
        2. 获取发送方的 platform 信息
        3. 构造 AgentResult 并保存到群聊历史
        
        使用方：
        - MCP tool call_agent
        - MCP tool complete_task (发送 NOTIFICATION)
        - API send_message_to_agent
        """
```

### MCP 工具接口

```python
# mcp/server.py
async def call_agent(
    agent_token: str,
    send_to: str,
    content: str,
    need_response: bool = True,
    timeout_seconds: float | None = None,
) -> dict:
    """
    调用另一个 agent
    
    使用 GroupChat.send_message_to_agent() 投递并保存消息
    """
    message = AgentMessage(...)
    await group_chat.send_message_to_agent(message)

async def complete_task(
    agent_token: str,
    call_id: str,
    content: str,
    success: bool = True,
) -> dict:
    """
    完成 AgentCall 并根据调用方类型决定如何处理
    
    保存规则：
    - 调用方是 user → 保存 agent 回复到群聊历史
    - 调用方是 agent → 发送 NOTIFICATION (通过 GroupChat.send_message_to_agent() 保存)
    """
    if config.is_user_name(call.send_from):
        # user 调用：保存 agent 回复到群聊历史
        await group_chat.group_chat_context.add_message(...)
    else:
        # agent 调用：发送 NOTIFICATION (会自动保存)
        await _send_agent_call_completion_notification(...)

async def _send_agent_call_completion_notification(
    group_chat: GroupChat,
    send_from: str,
    send_to: str,
    content: str,
) -> None:
    """
    创建并投递 AgentCall 完成通知
    
    使用 GroupChat.send_message_to_agent() 确保消息被保存
    """
    message = AgentMessage(...)
    await group_chat.send_message_to_agent(message)
    """
    完成 AgentCall 并根据调用方类型决定是否保存到群聊历史
    
    保存规则：
    - 调用方是 user → 保存 agent 回复到群聊历史
    - 调用方是 agent → 发送 NOTIFICATION（不保存）
    """
    if config.is_user_name(call.send_from):
        # user 调用：保存到群聊历史
        await group_chat.group_chat_context.add_message(...)
    else:
        # agent 调用：发送私有通知
        await _send_agent_call_completion_notification(...)

async def speak_in_group_chat(
    agent_token: str,
    content: str,
    send_to: str | None = None,
) -> dict:
    """
    在群聊中公开发言（不经过 MessageRouter）
    
    立即保存到群聊历史
    """
    await group_chat.group_chat_context.add_message(...)
```

### GroupChatContext 接口

```python
class GroupChatContext:
    async def add_message(self, result: AgentResult):
        """
        保存消息到群聊历史
        
        调用方：
        1. complete_task（user 调用的 TASK 完成）
        2. speak_in_group_chat（公开发言）
        3. GroupChat._initialize_new_members()（初始化消息）
        
        不调用方：
        - MessageRouter（投递层不保存）
        - _send_agent_call_completion_notification（私有通知）
        """
```

## Interaction / UX Notes

N/A（后端消息流转机制，无前端交互）

## Acceptance Notes

### 验收点

1. **MessageRouter 职责纯粹**
   - ✅ MessageRouter 不依赖 GroupChatContext
   - ✅ send_message() 只做投递，不调用 add_message()
   - ✅ MessageRouter 可以独立测试（不需要 mock GroupChatContext）

2. **GroupChat 统一包装**
   - ✅ GroupChat.send_message_to_agent() 包装投递和保存
   - ✅ 所有 MCP 工具使用 GroupChat.send_message_to_agent()
   - ✅ 构造完整的 AgentResult 对象（包含 platform 信息）

3. **群聊历史保存完整**
   - ✅ user → agent 发送消息保存到群聊历史
   - ✅ user → agent TASK 完成后，agent 回复保存到群聊历史
   - ✅ agent → agent TASK 消息保存到群聊历史
   - ✅ agent → agent NOTIFICATION 保存到群聊历史
   - ✅ speak_in_group_chat 的消息保存到群聊历史
   - ✅ Agent 初始化打招呼消息保存到群聊历史

4. **消息流转完整**
   - ✅ user 发送消息 → 保存 → agent 处理 → 回复保存 → 前端可见
   - ✅ agent 调用 agent → TASK 保存 → 处理完成 → NOTIFICATION 保存 → 前端可见
   - ✅ agent 公开发言 → 立即保存 → 前端可见

### 测试场景

```python
# 场景 1：user 调用 agent
user_message → send_message_to_agent API
            → GroupChat.send_message_to_agent()
            → MessageRouter.send_message() (投递)
            → add_message() (保存 user 消息)
            → agent 处理
            → complete_task
            → add_message() (保存 agent 回复)
            → 前端调用 getMessages 可以看到 user 消息和 agent 回复

# 场景 2：agent 调用 agent
agent_a.call_agent(agent_b, task)
       → GroupChat.send_message_to_agent()
       → MessageRouter.send_message(TASK) (投递)
       → add_message() (保存 TASK 消息)
       → agent_b 处理
       → complete_task
       → _send_agent_call_completion_notification
       → GroupChat.send_message_to_agent()
       → MessageRouter.send_message(NOTIFICATION) (投递)
       → add_message() (保存 NOTIFICATION)
       → agent_a 收到通知
       → 前端调用 getMessages 可以看到 TASK 和 NOTIFICATION

# 场景 3：agent 公开发言
agent.speak_in_group_chat("大家好")
     → 直接调用 add_message()
     → 不经过 MessageRouter
     → 保存到群聊历史
     → 前端可见
```

## Out of Spec

以下内容不在本 spec 范围内：

1. **消息渲染格式**（属于 foundation 层的 render_for_chat / render_for_llm）
2. **AgentCall 状态机**（已在 core-communication spec 中定义）
3. **群聊上下文压缩**（属于 context 层的 compact_messages）
4. **Agent 执行逻辑**（属于 agent 层的 run() / execute()）
5. **前端消息拉取**（属于 API 层的 getMessages）
6. **WebSocket 刷新通知**（属于 websocket 层的 broadcast_group_chat_refresh）
