---
version: 1.2
created_at: 2026-06-05
updated_at: 2026-06-16
last_updated: 修正：complete_task 参数补充、Heartbeat 消息流、Agent 停止清理流程、工具注册状态标注等
abstract: 定义 user、agent 之间的消息传递流程、MessageRouter 职责边界（纯投递层）、GroupChat.send_message_to_agent() 统一包装投递和保存、所有业务消息都保存到群聊历史的规则
id: spec-message-flow-and-persistence
title: 消息流转与持久化规格
status: draft
module: core/communication, core/orchestration, mcp
source_spec: null
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
| 1.2 | 修正：complete_task 参数补充、Heartbeat 消息流、Agent 停止清理流程、工具注册状态标注、send_message_to_agent 行为契约补充 |

## Overview

本 spec 定义系统中所有消息的传递路径、MessageRouter 的职责边界、以及消息保存到群聊历史的统一机制。

**核心原则**：
1. **MessageRouter 是纯投递层**，只负责将消息投递到目标 Agent 的队列，不承担业务逻辑
2. **GroupChat 提供统一包装方法**，所有通过 MessageRouter 投递的消息都通过 `GroupChat.send_message_to_agent()` 完成投递和保存
3. **所有业务消息都保存到群聊历史**，确保完整的消息记录供前端展示和上下文管理（Heartbeat 等系统消息不保存）

## Scope

### 范围内

- user → agent 消息流程
- agent → agent 消息流程（TASK / NOTIFICATION）
- 群聊公开发言流程（report_progress）
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

#### 3. 群聊公开发言（report_progress）

```
agent 调用 report_progress
       → 直接调用 GroupChatRuntime.add_message()
       → 保存到群聊历史
       → 不经过 MessageRouter
```

**保存时机**：立即保存到群聊历史。

#### 4. Heartbeat 系统消息（定时唤醒）

```
_heartbeat_loop 定时触发
       → 构造 Heartbeat 消息（虚拟身份 __HEARTBEAT__）
       → MessageRouter.send_message() (直接投递)
       → manager.message_queue
       → 不经过 GroupChat.send_message_to_agent()
       → 不保存到群聊历史
```

**关键区别**：Heartbeat 消息直接调用 `MessageRouter.send_message()` 投递，不经过 `GroupChat.send_message_to_agent()`，因此不会保存到群聊历史。Heartbeat 使用虚拟身份 `__HEARTBEAT__` 作为发送方，仅用于定时唤醒 Manager 检查任务进度。

### Agent 停止时的清理流程

当 Agent 被停止时，`_cleanup_agent_queue` 执行以下清理：

1. 获取该 Agent 的所有 PENDING/RUNNING 状态的 AgentCall
2. 对每个未完成的 Call：标记为 FAILED，内容为"用户主动停止该 Agent 运行，调用失败"
3. 根据调用方类型处理通知：
   - 调用方是 Agent → 通过 `send_message_to_agent()` 发送 NOTIFICATION 通知调用方
   - 调用方是 user → 直接保存失败消息到群聊历史（`add_message()`）
4. 清空 Agent 的消息队列

### MessageRouter 职责边界

**MessageRouter 只负责**：
- 验证消息格式（内容非空、发送方和接收方已注册）
- 投递消息到目标 Agent 的队列
- 处理投递失败（队列满、目标不存在）

**MessageRouter 不负责**：
- ❌ 决定哪些消息需要保存到群聊历史
- ❌ 调用 `GroupChatRuntime.add_message()`
- ❌ 区分消息类型（TASK / NOTIFICATION）
- ❌ 判断调用方是 user 还是 agent
- ❌ 依赖 `GroupChatRuntime` 或任何业务层组件

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
| report_progress | 公开发言 | ✅ 保存 | `report_progress` 直接调用 `add_message()` |
| Agent 初始化打招呼 | 初始化消息 | ✅ 保存 | `GroupChat._initialize_new_members()` / `_initialize_single_member()` |
| Heartbeat 系统消息 | 系统通知 | ❌ 不保存 | 直接通过 `MessageRouter.send_message()` 投递，不经过 `GroupChat.send_message_to_agent()` |
| Agent 停止清理通知 | 失败通知 | ✅ 保存 | `_cleanup_agent_queue` 通过 `send_message_to_agent()` 或 `add_message()` 保存 |

**判断原则**：
- 所有通过 `GroupChat.send_message_to_agent()` 投递的业务消息都保存
- 公开发言直接保存（不经过 MessageRouter）
- Heartbeat 等系统消息直接通过 `MessageRouter.send_message()` 投递，不保存到群聊历史
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
        - 不依赖 GroupChatRuntime
        - 不区分消息类型
        """
    
    def clear(self):
        """清空所有消息队列并注销所有 Agent"""
```

### GroupChat 接口

`send_message_to_agent` 的完整行为契约：

1. **懒加载激活检查**：调用 `activate()` 确保群聊已激活，未激活时自动触发初始化
2. **目标 Agent 状态检查**：检查目标 Agent 的 `agent_member_info.status`，若为 `stopped` 则抛出 StateError，阻止消息投递
3. **消息投递**：调用 `MessageRouter.send_message()` 将消息投递到目标队列
4. **获取发送方 platform**：查找发送方 Agent 实例，获取其 `role_config.platform`；未找到时默认 `AgentPlatform.CLAUDE`
5. **格式化消息内容**：检查内容是否已有 `@目标Agent` 前缀，没有则调用 `render_for_chat()` 格式化
6. **处理附件**：将消息中的 `files` 字段传递到 AgentResult
7. **保存到群聊历史**：构造 AgentResult 并调用 `runtime.add_message()` 保存

**使用方**：
- MCP tool `call_agent`：agent 调用 agent
- MCP tool `complete_task`：发送 NOTIFICATION 给原调用方
- `_send_agent_call_completion_notification`：创建并投递完成通知
- `_cleanup_agent_queue`：Agent 停止时发送清理通知
- API `send_message_to_agent`：user 发送消息给 agent

### MCP 工具接口

#### call_agent

**参数说明**：agent_token（身份令牌）、send_to（目标 Agent 名称）、content（消息内容）、need_response（是否需要响应，默认 True）、timeout_seconds（超时时间，整数秒，默认 300）

**处理流程**：
1. 验证身份令牌，解析 agent_name 和 group_chat_id
2. 获取 GroupChat 实例
3. 创建 AgentCall（need_response 为 True 时类型为 TASK，为 False 时为 NOTIFICATION）
4. 通过 `GroupChat.send_message_to_agent()` 投递并保存消息
5. 返回 call_id

#### complete_task

**基本参数**：agent_token（身份令牌）、call_id（要结束的 AgentCall ID）、content（成果汇报）、success（True 表示完成，False 表示阻塞或失败）

**附加参数**：
- modified_files：修改的文件列表（相对路径），用于文件快照和变更追踪
- git_diff_range：Git diff 范围（格式：commit..commit），配合 modified_files 使用
- web_preview_url：网页预览 URL，当完成 HTML 文件时传入，支持相对路径和绝对 URL
- web_preview_title：网页预览标题

**处理流程**：
1. 验证 token、群聊、AgentCall 存在性和权限（只有接收者可以结束调用）
2. 验证 AgentCall 类型为 TASK（NOTIFICATION 不需要回复）
3. 验证未重复处理（`has_agent_response` 为 False）
4. 脱敏 content 中的 token 信息
5. 处理文件快照（modified_files 和 git_diff_range 存在时）
6. 闭环 AgentCall（`mark_agent_response`）
7. 根据调用方类型处理通知：
   - 调用方是 user → 保存 agent 回复到群聊历史（含文件快照和 web_preview 信息）
   - 调用方是 Agent → 通过 `send_message_to_agent()` 发送 NOTIFICATION 并保存

#### _send_agent_call_completion_notification

创建一条 NOTIFICATION 类型的 AgentCall，然后通过 `GroupChat.send_message_to_agent()` 投递并保存到群聊历史，唤醒原调用方。

#### report_progress

在群聊中公开发言，不经过 MessageRouter，直接调用 `GroupChatRuntime.add_message()` 保存到群聊历史。

**工具注册状态**（2026-06-16）：

当前 `mcp/server.py` 中以下工具已被注释掉，未注册到 FastMCP：
- `report_progress`
- `complete_task`
- `request_permission`

这意味着这些工具目前无法通过 MCP 协议调用，但函数定义仍然存在。

### GroupChatRuntime 接口

```python
class GroupChatRuntime:
    async def add_message(self, result: AgentResult):
        """
        保存消息到群聊历史
        
        调用方：
        1. complete_task（user 调用的 TASK 完成）
        2. report_progress（公开发言）
        3. GroupChat._initialize_new_members()（初始化消息）
        4. GroupChat._initialize_single_member()（单个新成员打招呼）
        5. GroupChat._cleanup_agent_queue()（user 调用方的失败消息）
        6. GroupChat.send_message_to_agent()（通过包装层保存所有业务消息）
        
        不调用方：
        - MessageRouter（投递层不保存）
        """
```

## Interaction / UX Notes

N/A（后端消息流转机制，无前端交互）

## Acceptance Notes

### 验收点

1. **MessageRouter 职责纯粹**
   - ✅ MessageRouter 不依赖 GroupChatRuntime
   - ✅ send_message() 只做投递，不调用 add_message()
   - ✅ MessageRouter 可以独立测试（不需要 mock GroupChatRuntime）

2. **GroupChat 统一包装**
   - ✅ GroupChat.send_message_to_agent() 包装投递和保存
   - ✅ 所有 MCP 工具使用 GroupChat.send_message_to_agent()
   - ✅ 构造完整的 AgentResult 对象（包含 platform 信息）

3. **群聊历史保存完整**
   - ✅ user → agent 发送消息保存到群聊历史
   - ✅ user → agent TASK 完成后，agent 回复保存到群聊历史
   - ✅ agent → agent TASK 消息保存到群聊历史
   - ✅ agent → agent NOTIFICATION 保存到群聊历史
   - ✅ report_progress 的消息保存到群聊历史
   - ✅ Agent 初始化打招呼消息保存到群聊历史
   - ✅ Agent 停止清理的通知/失败消息保存到群聊历史
   - ✅ Heartbeat 系统消息不保存到群聊历史

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
agent.report_progress("大家好")
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
