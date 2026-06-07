---
updated_at: 2026-06-04
trigger: 修改 agents_hub/core/ 或依赖 core 行为的代码时
---

# Core CLAUDE.md

## 相关 Spec

| Spec | 路径 |
|------|------|
| core-overview | `docs/specs/2026-05-31-core-overview.md` |
| core-foundation | `docs/specs/2026-05-31-core-foundation.md` |
| core-communication | `docs/specs/2026-05-31-core-communication.md` |
| core-context | `docs/specs/2026-05-31-core-context.md` |
| core-agent-orchestration | `docs/specs/2026-05-31-core-agent-orchestration.md` |

## 编码规则

### Runtime 是 GroupChat 上下文状态入口

**适用范围**：群聊上下文状态（消息历史、成员会话、压缩记录、元数据）

**禁止**：
- ❌ 在 `GroupChatManager`、API service 或 MCP tool 中直接打开 `agent_member.json`、`group_metadata.json`、消息 jsonl 来获取已加载群聊状态
- ❌ 从 `group_chat.group_chat_context.repository` 读取业务状态

**示例**：
```python
# ✅ 正确
group_chat = await group_chat_manager.load_group_chat(group_chat_id)
info = group_chat.runtime.get_info_dict(is_active=group_chat_manager.is_active_group(group_chat_id))
members = group_chat.runtime.get_member_dicts()

# ❌ 错误
with open(agent_member_file, encoding="utf-8") as f:
    members = json.load(f)
```

### 通信状态访问规则

**适用范围**：AgentCallManager 和 TaskManager 管理的通信层状态

**架构说明**：
- `GroupChatRuntime` 管理**群聊上下文状态**（context/ 层）
- `AgentCallManager` 和 `TaskManager` 管理**通信控制面状态**（communication/ 层）
- 两者是**平级组件**，都由 `GroupChat` 组装

**访问方式**：
```python
# ✅ 正确：通过 GroupChat 访问平级组件
group_chat = await group_chat_manager.load_group_chat(group_chat_id)

# 获取 Agent 调用记录
all_calls = group_chat.agent_call_manager.list_all_calls()

# 获取任务列表
task_list = group_chat.task_manager.get_active_task_list(group_chat_id)

# ❌ 错误：直接访问私有属性
all_calls = group_chat.agent_call_manager._calls.values()

# ❌ 错误：试图通过 Runtime 访问（Runtime 不管理通信状态）
all_calls = group_chat.runtime.get_agent_calls()  # Runtime 没有这个方法
```

**为什么不集成到 Runtime**：
- Runtime 职责：管理群聊上下文（消息、成员、元数据）
- Manager 职责：管理通信控制面（调用追踪、任务协作）
- 保持分层清晰：`context/` 和 `communication/` 平级，互不依赖

### user 身份只能通过 config 判断

**禁止**：
- ❌ 使用 `name == "user"` 或 `name == config.default_user_name` 判断前端用户
- ❌ 把带 `(user)` 标记的前端用户当作可调用 Agent

**示例**：
```python
# ✅ 正确
if config.is_user_name(call.send_from):
    ...

# ❌ 错误
if call.send_from == "user":
    ...
```

### Agent 间消息必须经过控制面

**禁止**：
- ❌ 直接向另一个 Agent 的 `message_queue` put 消息
- ❌ 绕过 `AgentCallManager` 投递需要追踪的任务
- ❌ 直接调用 `message_router.send_message()`（必须通过 `GroupChat.send_message_to_agent()` 统一包装）

**示例**：
```python
# ✅ 正确
call = group_chat.agent_call_manager.create_call(...)
await group_chat.send_message_to_agent(message)

# ❌ 错误：绕过 GroupChat 包装层
call = group_chat.agent_call_manager.create_call(...)
await group_chat.message_router.send_message(message)

# ❌ 错误：直接操作队列
target_agent.message_queue.put_nowait(message)
```

### Core 分层依赖

**禁止**：
- ❌ `foundation/`、`communication/`、`context/` 依赖 `agent/` 或 `orchestration/`
- ❌ `communication/` 读取 context/repository

## 决策规则

| 场景 | 决策 |
|------|------|
| 查询已加载群聊上下文信息 | 用 `group_chat.runtime.get_*` |
| 查询 Agent 调用记录 | 用 `group_chat.agent_call_manager.list_all_calls()` |
| 查询任务列表 | 用 `group_chat.task_manager.get_active_task_list()` |
| 修改群聊状态并持久化 | 给 `GroupChatRuntime` 增加 command 方法 |
| Agent 调用另一个 Agent | 创建 `AgentCall` 后通过 `GroupChat.send_message_to_agent()` 投递并保存 |
| 判断调用方是否是前端用户 | 用 `config.is_user_name(name)` |
| user 调用的 TASK 完成 | 写入群聊历史并触发 refresh |
| Agent 调用的 TASK 完成 | 投递 `NOTIFICATION` 唤醒原调用方 |
