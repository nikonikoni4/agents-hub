# 并发安全性审查报告

生成时间: 2026-06-14
审查范围: Core 模块 (agents_hub/core/)

## 执行摘要

本次审查识别出 **7 个高风险并发安全问题**，涉及 4 个核心模块：
- **AgentCallManager**: `_calls` 和 `_calls_by_receiver` 无锁保护，后台清理与主流程存在竞态
- **GroupChatManager**: `_group_chats` 在多线程环境下无锁保护
- **MessageRouter**: `_agents_queue` 注册/注销与消息投递存在竞态
- **GroupChatRuntime**: Runtime 层 read-modify-write 序列缺乏原子性保护

Repository 层有完善的文件锁保护，但 **Runtime 层的内存状态更新缺乏并发控制**，导致持久化数据可能不一致。

---

## 1. 共享状态清单

### 1.1 AgentCallManager (`agents_hub/core/communication/agent_call_manager.py`)

| 共享状态 | 类型 | 访问模式 | 并发来源 |
|---------|------|---------|---------|
| `_calls` | `dict[str, AgentCall]` | 读写 | 主流程创建/查询 + 后台清理删除 |
| `_calls_by_receiver` | `dict[str, list[str]]` | 读写 | 主流程索引 + 后台清理删除 |

**并发场景**:
- 主流程: `create_call()`, `get_call()`, `update_status()`, `list_all_calls()`, `get_runtime_calls_for_agent()`
- 后台任务: `_cleanup_loop()` 每 60 秒执行 `_cleanup_deletable_calls()` 删除条目

### 1.2 GroupChatManager (`agents_hub/core/orchestration/group_chat_manager.py`)

| 共享状态 | 类型 | 访问模式 | 并发来源 |
|---------|------|---------|---------|
| `_group_chats` | `dict[str, GroupChat]` | 读写 | FastMCP HTTP 多线程请求 |
| `_tokens` | `dict[str, tuple[str, str]]` | 读写 | FastMCP HTTP 多线程请求（**已加锁**） |

**并发场景**:
- `register()`, `unregister()`, `load_group_chat()`, `is_active_group()` 在不同 HTTP 线程并发调用
- `_tokens` 已用 `threading.RLock` 保护，但 `_group_chats` **完全无保护**

### 1.3 MessageRouter (`agents_hub/core/communication/message_router.py`)

| 共享状态 | 类型 | 访问模式 | 并发来源 |
|---------|------|---------|---------|
| `_agents_queue` | `dict[str, asyncio.Queue]` | 读写 | Agent 注册/注销 + 消息投递 + 清理 |

**并发场景**:
- `register()`, `unregister()` 在 Agent 生命周期管理时调用
- `send_message()` 在多个 Agent 协程中并发投递消息
- `clear()` 在群聊清理时遍历删除

### 1.4 GroupChatRuntime & GroupChatRuntimeState

| 共享状态 | 类型 | 访问模式 | 并发来源 |
|---------|------|---------|---------|
| `state.agent_member_infos` | `dict[str, AgentMemberInfo]` | 读写 | 多个 Agent 协程更新状态 |
| `state.group_chat_session` | `GroupChatSession` | 读写 | 多个 Agent 协程添加消息 |
| `state.compact_history` | `list[dict]` | 读写 | 压缩任务 + 查询 |
| `state.persistence_error` | `str | None` | 写 | 所有 `_persist()` 调用 |

**并发场景**:
- `add_message()`, `update_agent_status()`, `update_agent_context_usage()` 被多个 Agent 协程并发调用
- `append_compact_record_and_mark_compacted()` 在压缩任务中调用，包含**两次独立的 `_persist()` 调用**
- Repository 层有 `asyncio.Lock` 保护文件 I/O，但 **Runtime 层的 read-modify-write 无锁**

### 1.5 Repository 层锁机制（已完善）

| 锁 | 保护范围 | 位置 |
|---|---------|------|
| `_session_lock` | `messages.jsonl` 读写 | `GroupChatRepository:36` |
| `_agent_state_lock` | `agent_member.json` 读写 | `GroupChatRepository:37` |
| `_compact_lock` | `compact_history.jsonl` 读写 | `GroupChatRepository:38` |
| `_metadata_lock` | `group_metadata.json` 读写 | `GroupChatRepository:39` |

**评估**: Repository 层的锁**只保护文件 I/O**，不保护内存状态的 read-modify-write 序列。

---

## 2. 锁机制现状

### 2.1 已有的锁

| 模块 | 锁类型 | 保护对象 | 评价 |
|------|--------|---------|------|
| `GroupChatRepository` | `asyncio.Lock` (4 个) | 文件读写操作 | ✅ 完善 |
| `GroupChatManager` | `threading.RLock` | `_tokens` 字典 | ✅ 完善 |
| `GroupChatManager` | `threading.Lock` | 单例创建 | ✅ 完善 |

### 2.2 缺失的锁

| 模块 | 缺失保护 | 风险 |
|------|---------|------|
| `AgentCallManager` | `_calls`, `_calls_by_receiver` | ❌ 高风险 |
| `GroupChatManager` | `_group_chats` | ❌ 高风险 |
| `MessageRouter` | `_agents_queue` | ⚠️ 中风险 |
| `GroupChatRuntime` | Runtime 层 read-modify-write | ❌ 高风险 |

### 2.3 锁的层级缺口

```
┌─────────────────────────────────────┐
│  Runtime 层 (业务逻辑)               │
│  - read-modify-write 序列            │  ❌ 无锁保护
│  - 多个 await 让出点                 │
└─────────────────────────────────────┘
              ↓ _persist()
┌─────────────────────────────────────┐
│  Repository 层 (文件 I/O)            │
│  - asyncio.Lock 保护文件读写         │  ✅ 有锁保护
└─────────────────────────────────────┘
```

**问题**: Repository 锁只在 I/O 时生效，无法保护 Runtime 层的"读内存 → await → 修改内存 → 持久化"序列。

---

## 3. 竞态条件识别

### 3.1 AgentCallManager: 清理循环与主流程竞态

**代码位置**: `agents_hub/core/communication/agent_call_manager.py:320-388`

**竞态场景**:
```python
# 主流程遍历索引
def get_runtime_calls_for_agent(self, agent_name: str) -> list[AgentCall]:
    for call_id in self._calls_by_receiver.get(agent_name, []):  # 读取列表
        call = self._calls.get(call_id)  # 可能被清理循环删除
        ...

# 后台清理循环
async def _cleanup_loop(self):
    await asyncio.sleep(self._cleanup_interval)  # 让出点
    for call_id, call in list(self._calls.items()):  # 复制快照
        if call.can_be_deleted(...):
            del self._calls[call_id]  # 删除
            self._unindex_call(call)  # 删除索引
            # _unindex_call() 内部: call_ids.remove(call.call_id)  可能在遍历期间修改列表
```

**触发条件**:
1. Agent A 正在调用 `get_runtime_calls_for_agent()` 遍历 `_calls_by_receiver[agent_name]`
2. 同时清理循环执行 `_unindex_call()` 删除列表中的元素
3. Python 的 `list.remove()` 在迭代期间被调用 → 可能导致 `RuntimeError: list changed size during iteration`

**影响**: 虽然 `list()` 快照了 `_calls.items()`，但 `_calls_by_receiver` 的列表没有快照，遍历期间删除会引发异常。

### 3.2 GroupChatManager: 多线程 register/unregister 竞态

**代码位置**: `agents_hub/core/orchestration/group_chat_manager.py:60-75, 148-172`

**竞态场景**:
```python
# 线程 1: HTTP 请求 register
def register(self, group_chat_id: str, group_chat: GroupChat):
    self._group_chats[group_chat_id] = group_chat  # 写

# 线程 2: HTTP 请求 unregister
async def unregister(self, group_chat_id: str, timeout: float = 10.0):
    group_chat = self._group_chats.get(group_chat_id)  # 读
    if group_chat:
        await group_chat.cleanup(timeout=timeout)  # await 让出，期间 dict 可能被修改
        self._group_chats.pop(group_chat_id, None)  # 删除
```

**触发条件**:
- FastMCP HTTP 多线程环境下，不同线程并发调用 `register()` 和 `unregister()`
- Python dict 不是线程安全的，并发读写可能导致：
  1. `KeyError`（遍历期间删除）
  2. 数据丢失（并发写覆盖）
  3. 内存损坏（CPython 内部状态不一致）

**证据**: 代码注释 (line 29) 声明"线程安全：token 索引操作使用 RLock 保护"，但只有 `_tokens` 有锁，`_group_chats` **完全无保护**。

### 3.3 GroupChatRuntime: 双次 persist 非原子

**代码位置**: `agents_hub/core/context/group_chat_runtime.py:380-395`

**竞态场景**:
```python
async def append_compact_record_and_mark_compacted(self, compact_record: dict) -> None:
    session = self.state.require_session()
    self.state.compact_history.append(compact_record)  # 修改内存
    session.last_compacted_loc = len(session.messages)  # 修改内存
    
    # 两次独立 persist，中间有 await 让出点
    await self._persist(lambda: self.repository.save_compact_history(...))  # 可能成功
    await self._persist(lambda: self.repository.save_group_chat_session(...))  # 可能失败
```

**风险**:
1. 第一次 persist 成功，`compact_history.jsonl` 已追加记录
2. 第二次 persist 失败（磁盘满、IO 错误），`messages.jsonl` 的 `last_compacted_loc` 未更新
3. 重启后重新读取，`last_compacted_loc` 指向旧位置 → **重复压缩相同消息**

**历史 Bug**: 已在 `docs/history-bugs/2026-06-05-group-chat-runtime-state-concurrency.md` 记录。

### 3.4 GroupChatRuntime: 多 Agent 并发更新状态

**代码位置**: `agents_hub/core/context/group_chat_runtime.py:453-470`

**竞态场景**:
```python
# Agent A 协程
async def update_agent_status(self, agent_name: str, status: str) -> AgentMemberInfo:
    agent_member_info = self.get_or_create_agent_member_info(agent_name)  # 读内存
    agent_member_info.status = status  # 修改内存
    await self._persist(lambda: self.repository.save_agent_member(...))  # await 让出点

# Agent B 协程同时执行
async def update_agent_context_usage(self, agent_name: str, context_usage: int):
    agent_member_info = self.get_or_create_agent_member_info(agent_name)  # 读内存
    agent_member_info.context_usage = context_usage  # 修改内存
    await self._persist(lambda: self.repository.save_agent_member(...))  # await 让出点
```

**触发条件**:
1. Agent A 调用 `update_agent_status()` 修改 `status`，await 让出
2. Agent B 调用 `update_agent_context_usage()` 修改 `context_usage`，先完成持久化
3. Agent A 恢复执行，持久化**覆盖** Agent B 的修改 → `context_usage` 丢失

**影响**: 
- `save_agent_member()` 保存整个 `agent_member_infos` 字典，后持久化的会覆盖先持久化的
- 虽然两个 Agent 修改不同字段，但持久化是全量覆盖 → **丢失并发修改**

### 3.5 MessageRouter: 注册/注销与消息投递竞态

**代码位置**: `agents_hub/core/communication/message_router.py:26-44, 46-91`

**竞态场景**:
```python
# 协程 1: Agent 注销
def unregister(self, name: str):
    self._agents_queue.pop(name, None)  # 删除队列

# 协程 2: 同时投递消息
async def send_message(self, message: AgentMessage):
    self._validate_message(message)  # 检查 send_to 是否在 _agents_queue
    self._agents_queue[message.send_to].put_nowait(message)  # 可能 KeyError
```

**触发条件**:
1. `_validate_message()` 检查通过，确认 `send_to` 在 `_agents_queue`
2. `unregister()` 删除了该 Agent 的队列
3. `put_nowait()` 访问不存在的 key → `KeyError`

**风险等级**: ⚠️ 中风险（已有异常处理捕获 `Exception`，但会转换为 `MessageDeliveryError` 误导诊断）

### 3.6 compact_messages TOCTOU (Time-of-Check to Time-of-Use)

**代码位置**: `agents_hub/core/context/group_chat_context.py:88-186`

**竞态场景**:
```python
async def compact_messages(self, agent_info: dict[str, str]):
    # 读取未压缩消息快照
    uncompacted_messages = self.group_chat_session.get_uncompact_messages()  # 读
    
    # 长时间 LLM 调用（可能 10-30 秒）
    result = await agent_platform_client.bare_claude_call(compact_prompt)  # await 让出
    
    # 其他协程可能在此期间调用 add_message() 添加新消息
    
    # 标记压缩位置
    session.last_compacted_loc = len(session.messages)  # 写，可能把新消息标记为"已压缩"
    await self._persist(...)
```

**触发条件**:
1. 压缩任务读取快照（10 条消息）
2. LLM 调用期间，其他 Agent 添加了 2 条新消息
3. 压缩完成，`last_compacted_loc = 12`，但压缩内容只包含前 10 条
4. 新增的 2 条消息被**跳过压缩**，永久丢失

**历史 Bug**: 已在 `docs/history-bugs/2026-06-05-group-chat-runtime-state-concurrency.md:52-60` 记录。

---

## 4. 高风险场景

### 4.1 FastMCP HTTP 多线程环境

**场景**: GroupChatManager 在 FastMCP HTTP 服务中暴露 MCP 工具，每个 HTTP 请求在独立线程中执行。

**风险**:
- 多个客户端同时调用 `call_agent` MCP 工具
- 并发的 `load_group_chat()` 可能同时读写 `_group_chats` 字典
- Python dict 在 CPython 中不是线程安全的，GIL 不保护复合操作

**潜在后果**:
1. `KeyError` / `RuntimeError` 导致 MCP 工具调用失败
2. 数据结构损坏，需要重启进程
3. GroupChat 对象被意外覆盖或丢失

**证据**: 
- `_tokens` 使用 `threading.RLock` 保护（line 48）
- `_group_chats` 完全无保护（line 46）
- 注释 (line 29) 自相矛盾："线程安全"仅针对 `_tokens`

### 4.2 多 Agent 并发初始化

**场景**: `GroupChat.start()` 使用 `asyncio.gather()` 并发初始化所有新成员。

**代码位置**: `agents_hub/core/orchestration/group_chat.py` (推测，未在提供的代码段中)

**风险**:
- 多个 Agent 并发调用 `runtime.set_agent_token_and_default_cwd()`
- 每个调用都会触发 `save_agent_member()` 全量持久化
- 后完成的持久化会覆盖先完成的，可能丢失某些 Agent 的 token

**触发条件**: 群聊有 5+ 个新成员时，并发初始化导致 token 丢失。

### 4.3 AgentCall 清理期间的查询

**场景**: 前端查询 Agent 调用列表时，后台清理循环正在删除过期调用。

**风险**:
```python
# API 查询
calls = agent_call_manager.list_all_calls()  # 返回 list(self._calls.values())

# 清理循环同时执行
del self._calls[call_id]  # 字典大小变化
```

**影响**: 
- 虽然 `list()` 会复制引用，但如果清理循环在迭代 `_calls.items()` 期间删除，仍可能触发 `RuntimeError`
- `get_runtime_calls_for_agent()` 遍历 `_calls_by_receiver` 时，`_unindex_call()` 修改列表 → 高危

### 4.4 压缩任务与消息添加并发

**场景**: 压缩任务正在调用 LLM，同时多个 Agent 在添加新消息。

**数据流**:
```
压缩任务:  读快照(10条) → LLM调用(20秒) → 标记 last_compacted_loc=12
Agent A:                    添加消息(11) ↓
Agent B:                    添加消息(12) ↓
```

**结果**: 消息 11 和 12 被跳过压缩，但标记为"已压缩"，永久丢失。

**严重性**: ⚠️ 数据丢失，但不会导致崩溃。

---

## 5. 发现的问题

### 问题 1: AgentCallManager 缺乏并发保护

**位置**: `agents_hub/core/communication/agent_call_manager.py:38-39`

**问题描述**:
- `_calls` 和 `_calls_by_receiver` 无 `asyncio.Lock` 保护
- 后台清理循环 `_cleanup_loop()` 与主流程并发访问

**复现条件**:
1. 启动后台清理任务（60秒间隔）
2. 高频调用 `get_runtime_calls_for_agent()`
3. 清理循环执行 `_unindex_call()` 时，主流程正在遍历 `_calls_by_receiver[agent_name]`

**影响范围**: 所有使用 AgentCallManager 的群聊，高负载时易触发。

**建议修复**:
```python
class AgentCallManager:
    def __init__(...):
        self._calls: dict[str, AgentCall] = {}
        self._calls_by_receiver: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()  # 新增锁
    
    async def create_call(...) -> AgentCall:
        async with self._lock:
            call = AgentCall(...)
            self._calls[call.call_id] = call
            self._index_call(call)
            self._persist_call(call)
        return call
    
    def get_runtime_calls_for_agent(self, agent_name: str) -> list[AgentCall]:
        # 复制列表快照，避免迭代期间被修改
        with self._lock:  # 同步锁获取快照
            call_ids = list(self._calls_by_receiver.get(agent_name, []))
        calls = []
        for call_id in call_ids:
            if call := self._calls.get(call_id):
                if self._should_include_in_runtime(call):
                    calls.append(call)
        return calls
```

**严重程度**: 🔴 高危

### 问题 2: GroupChatManager._group_chats 无线程锁

**位置**: `agents_hub/core/orchestration/group_chat_manager.py:46`

**问题描述**:
- `_group_chats` 字典在多线程 FastMCP 环境下无锁保护
- `_tokens` 有 `threading.RLock` (line 48)，但 `_group_chats` 完全无保护
- 注释 (line 29) 声明"线程安全"，但不一致

**复现条件**:
1. FastMCP HTTP 多线程环境
2. 并发调用 `register()`, `unregister()`, `load_group_chat()`
3. Python dict 并发写入/删除导致 `RuntimeError` 或数据损坏

**影响范围**: 所有通过 MCP 工具访问的 GroupChat 操作。

**建议修复**:
```python
class GroupChatManager:
    def __init__(self):
        if GroupChatManager._initialized:
            return
        self._group_chats: dict[str, GroupChat] = {}
        self._tokens: dict[str, tuple[str, str]] = {}
        self._token_lock = threading.RLock()
        self._group_chat_lock = threading.RLock()  # 新增锁，与 _token_lock 一致
        GroupChatManager._initialized = True
    
    def register(self, group_chat_id: str, group_chat: GroupChat):
        with self._group_chat_lock:
            self._group_chats[group_chat_id] = group_chat
    
    async def load_group_chat(self, group_chat_id: str) -> GroupChat:
        with self._group_chat_lock:
            group_chat = self._group_chats.get(group_chat_id)
        if group_chat:
            return group_chat
        # 从磁盘加载（锁外执行，避免阻塞）
        group_chat = await self.load_group_chat_from_disk(group_chat_id)
        with self._group_chat_lock:
            # 二次检查（防止重复加载）
            if existing := self._group_chats.get(group_chat_id):
                return existing
            self._group_chats[group_chat_id] = group_chat
        return group_chat
```

**严重程度**: 🔴 高危

### 问题 3: GroupChatRuntime 缺乏 read-modify-write 原子性

**位置**: `agents_hub/core/context/group_chat_runtime.py:453-470`

**问题描述**:
- Runtime 层的 command 方法（`update_agent_status`, `update_agent_context_usage` 等）无锁保护
- Repository 层的 `asyncio.Lock` 只保护文件 I/O，不保护内存状态更新
- 多个协程并发调用时，后持久化的会覆盖先持久化的修改

**复现条件**:
1. Agent A 调用 `update_agent_status()`
2. Agent B 同时调用 `update_agent_context_usage()`
3. 两者都修改 `agent_member_infos`，但全量持久化导致覆盖

**影响范围**: 所有修改 `agent_member_infos` 的操作，高频更新时易触发。

**建议修复**:
```python
class GroupChatRuntime:
    def __init__(...):
        ...
        self._state_lock = asyncio.Lock()  # 保护 State 的 read-modify-write
    
    async def update_agent_status(self, agent_name: str, status: str):
        async with self._state_lock:
            agent_member_info = self.get_or_create_agent_member_info(agent_name)
            agent_member_info.status = status
            await self._persist(lambda: self.repository.save_agent_member(...))
    
    async def update_agent_context_usage(self, agent_name: str, context_usage: int):
        async with self._state_lock:
            agent_member_info = self.get_or_create_agent_member_info(agent_name)
            agent_member_info.context_usage = context_usage
            await self._persist(lambda: self.repository.save_agent_member(...))
```

**严重程度**: 🔴 高危

### 问题 4: append_compact_record_and_mark_compacted 双次 persist 非原子

**位置**: `agents_hub/core/context/group_chat_runtime.py:380-395`

**问题描述**:
- 两次独立的 `_persist()` 调用，中间有 `await` 让出点
- 第一次成功、第二次失败 → 数据不一致

**复现条件**:
1. 压缩任务调用 `append_compact_record_and_mark_compacted()`
2. 第一次 `save_compact_history()` 成功
3. 第二次 `save_group_chat_session()` 失败（磁盘满、IO 错误）
4. `compact_history.jsonl` 已追加，但 `messages.jsonl` 的 `last_compacted_loc` 未更新

**影响范围**: 压缩功能，低频但后果严重（重复压缩）。

**建议修复**:
```python
async def append_compact_record_and_mark_compacted(self, compact_record: dict):
    async with self._state_lock:
        session = self.state.require_session()
        self.state.compact_history.append(compact_record)
        old_loc = session.last_compacted_loc
        session.last_compacted_loc = len(session.messages)
        
        try:
            # 在同一事务中保存两个文件
            await self._persist(lambda: self.repository.save_compact_history(...))
            await self._persist(lambda: self.repository.save_group_chat_session(...))
        except Exception:
            # 回滚内存状态
            self.state.compact_history.pop()
            session.last_compacted_loc = old_loc
            raise
```

**严重程度**: 🟡 中危（低频但后果严重）

### 问题 5: compact_messages TOCTOU 竞态

**位置**: `agents_hub/core/context/group_chat_context.py:88-186`

**问题描述**:
- 读取快照 → LLM 调用（10-30秒） → 标记压缩位置
- LLM 调用期间，新消息被添加但未被压缩
- `last_compacted_loc = len(session.messages)` 把新消息标记为"已压缩"

**复现条件**:
1. 压缩任务读取 10 条消息快照
2. LLM 调用期间，Agent 添加 2 条新消息
3. 压缩完成，标记 `last_compacted_loc = 12`
4. 新消息 11、12 永久丢失

**影响范围**: 高活跃度群聊，压缩期间有新消息时触发。

**建议修复**:
```python
async def compact_messages(self, agent_info: dict[str, str]):
    async with self.runtime._state_lock:
        session = self.runtime.state.require_session()
        snapshot_loc = len(session.messages)  # 记录快照版本
        uncompacted_messages = session.get_uncompact_messages()
    
    # LLM 调用（锁外执行）
    result = await agent_platform_client.bare_claude_call(...)
    compact_data = json.loads(result.text)
    compact_record = {...}
    
    async with self.runtime._state_lock:
        # 校验版本：如果有新消息，放弃本次压缩
        if len(session.messages) != snapshot_loc:
            logger.warning("压缩期间有新消息，放弃本次压缩")
            return
        
        self.runtime.state.compact_history.append(compact_record)
        session.last_compacted_loc = snapshot_loc
        await self.runtime._persist(...)
```

**严重程度**: 🟡 中危（数据丢失，但可恢复）

### 问题 6: MessageRouter 注册/注销与消息投递竞态

**位置**: `agents_hub/core/communication/message_router.py:26-91`

**问题描述**:
- `_validate_message()` 检查 → `unregister()` 删除队列 → `put_nowait()` 访问不存在的 key

**复现条件**:
1. Agent 正在注销（调用 `unregister()`）
2. 同时有消息投递给该 Agent
3. 检查通过但执行时队列已删除 → `KeyError`

**影响范围**: Agent 生命周期管理，中等频率。

**建议修复**:
```python
class MessageRouter:
    def __init__(self):
        self._agents_queue: dict[str, asyncio.Queue] = {}
        self._lock = asyncio.Lock()  # 新增锁
    
    async def register(self, name: str, queue: asyncio.Queue):
        async with self._lock:
            self._agents_queue[name] = queue
    
    async def unregister(self, name: str):
        async with self._lock:
            self._agents_queue.pop(name, None)
    
    async def send_message(self, message: AgentMessage):
        async with self._lock:
            self._validate_message(message)
            self._agents_queue[message.send_to].put_nowait(message)
```

**严重程度**: 🟡 中危

### 问题 7: 多 Agent 并发初始化覆盖 token

**位置**: `agents_hub/core/orchestration/group_chat.py` (推测使用 `asyncio.gather()`)

**问题描述**:
- `asyncio.gather()` 并发初始化多个新成员
- 每个调用 `set_agent_token_and_default_cwd()` 都触发 `save_agent_member()` 全量持久化
- 后完成的持久化覆盖先完成的 → token 丢失

**复现条件**:
1. 创建群聊，有 5 个新成员
2. `asyncio.gather()` 并发初始化
3. 持久化时序： A → B → C → D → E
4. E 的持久化可能只包含 E 的 token，A-D 的 token 丢失

**影响范围**: 新群聊创建，成员数 >= 3 时易触发。

**建议修复**:
```python
# 方案 1: 串行初始化（简单但慢）
for agent_name in new_members:
    await self._initialize_agent(agent_name)

# 方案 2: 批量初始化（推荐）
async def _initialize_new_members(self):
    async with self.runtime._state_lock:
        for agent_name in new_members:
            agent_member_info = self.runtime.get_or_create_agent_member_info(agent_name)
            agent_member_info.token = generate_token()
            agent_member_info.cwd = self.runtime.project_path
        # 一次性持久化所有
        await self.runtime._persist(lambda: self.runtime.repository.save_agent_member(...))
```

**严重程度**: 🟡 中危

---

## 6. 修复优先级

### P0 - 立即修复（高危 + 高频）

| 问题 | 模块 | 原因 | 预计工作量 |
|------|------|------|----------|
| **问题 1** | AgentCallManager | 后台清理与主流程竞态，易触发 RuntimeError | 2 小时 |
| **问题 2** | GroupChatManager | FastMCP 多线程环境下 dict 竞态，可能崩溃 | 1 小时 |
| **问题 3** | GroupChatRuntime | 多 Agent 并发更新状态，持久化覆盖 | 3 小时 |

**总计**: 约 6 小时，建议在本周内完成。

### P1 - 近期修复（中危 + 中频）

| 问题 | 模块 | 原因 | 预计工作量 |
|------|------|------|----------|
| **问题 4** | GroupChatRuntime | 双次 persist 非原子，压缩数据不一致 | 2 小时 |
| **问题 5** | GroupChatContext | 压缩期间新消息丢失（TOCTOU） | 2 小时 |
| **问题 6** | MessageRouter | 注册/注销与消息投递竞态 | 1 小时 |

**总计**: 约 5 小时，建议在下周完成。

### P2 - 择机修复（低危 + 低频）

| 问题 | 模块 | 原因 | 预计工作量 |
|------|------|------|----------|
| **问题 7** | GroupChat | 并发初始化覆盖 token（低频） | 1.5 小时 |

**总计**: 约 1.5 小时，可在下次重构时一并处理。

---

## 7. 测试建议

### 7.1 单元测试（针对性测试）

```python
# 测试 1: AgentCallManager 并发清理
async def test_agent_call_manager_concurrent_cleanup():
    manager = AgentCallManager(...)
    manager.start_cleanup()
    
    # 创建 100 个调用
    for i in range(100):
        manager.create_call(...)
    
    # 并发查询 + 清理
    async def query_loop():
        for _ in range(1000):
            manager.get_runtime_calls_for_agent("agent_1")
            await asyncio.sleep(0.001)
    
    await asyncio.gather(
        query_loop(),
        query_loop(),
        asyncio.sleep(65),  # 触发清理
    )
    
    await manager.stop_cleanup()

# 测试 2: GroupChatManager 多线程竞态
def test_group_chat_manager_thread_safety():
    import threading
    manager = GroupChatManager()
    
    def register_loop():
        for i in range(100):
            group_chat = GroupChat(...)
            manager.register(f"group_{i}", group_chat)
    
    def unregister_loop():
        for i in range(100):
            manager.unregister(f"group_{i}")
    
    threads = [
        threading.Thread(target=register_loop),
        threading.Thread(target=unregister_loop),
        threading.Thread(target=register_loop),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

# 测试 3: GroupChatRuntime 并发更新
async def test_runtime_concurrent_updates():
    runtime = GroupChatRuntime(...)
    await runtime.load()
    
    async def update_status():
        for i in range(100):
            await runtime.update_agent_status("agent_1", f"status_{i}")
    
    async def update_context():
        for i in range(100):
            await runtime.update_agent_context_usage("agent_1", i)
    
    await asyncio.gather(update_status(), update_context())
    
    # 验证：status 和 context_usage 都应保留最后的值
    info = runtime.get_or_create_agent_member_info("agent_1")
    assert info.status == "status_99"
    assert info.context_usage == 99
```

### 7.2 压力测试（高负载场景）

```python
# 压测 1: 模拟高频消息投递
async def stress_test_message_routing():
    router = MessageRouter()
    # 注册 10 个 Agent
    for i in range(10):
        router.register(f"agent_{i}", asyncio.Queue())
    
    # 1000 个协程并发发送消息
    async def send_messages():
        for _ in range(100):
            message = AgentMessage(
                call_id=str(uuid4()),
                send_from="agent_0",
                send_to=f"agent_{random.randint(1, 9)}",
                content="test",
                message_type=MessageType.TASK,
            )
            await router.send_message(message)
    
    tasks = [send_messages() for _ in range(1000)]
    await asyncio.gather(*tasks)

# 压测 2: 模拟压缩期间的消息添加
async def stress_test_compaction():
    runtime = GroupChatRuntime(...)
    await runtime.load()
    
    # 添加 1000 条初始消息
    for i in range(1000):
        await runtime.add_message(create_test_message(f"msg_{i}"))
    
    # 并发：压缩任务 + 持续添加消息
    async def compact_loop():
        for _ in range(10):
            await context.compact_messages(agent_info)
            await asyncio.sleep(1)
    
    async def add_message_loop():
        for i in range(500):
            await runtime.add_message(create_test_message(f"new_{i}"))
            await asyncio.sleep(0.1)
    
    await asyncio.gather(compact_loop(), add_message_loop())
    
    # 验证：所有消息都应被压缩或保留
    assert no_messages_skipped(runtime)
```

### 7.3 集成测试（真实场景）

```bash
# 测试场景 1: 多客户端并发调用 MCP 工具
for i in {1..10}; do
  (
    echo "Client $i: call_agent"
    # 模拟 MCP 客户端调用
    curl -X POST http://localhost:8000/mcp/call_agent \
      -d '{"group_chat_id": "test", "agent_name": "agent_1", "message": "hello"}'
  ) &
done
wait

# 测试场景 2: 群聊高频消息
# 1. 创建 5 人群聊
# 2. 每秒发送 10 条消息，持续 5 分钟
# 3. 同时触发压缩任务
# 4. 验证：无异常，无消息丢失
```

### 7.4 监控指标

建议在生产环境添加以下监控：

| 指标 | 监控目的 | 告警阈值 |
|------|---------|---------|
| `agent_call_manager.list_all_calls()` 异常率 | 检测清理竞态 | > 1% |
| `GroupChatManager.load_group_chat()` 异常率 | 检测多线程竞态 | > 0.1% |
| `GroupChatRuntime._persist()` 失败率 | 检测持久化错误 | > 5% |
| `compact_messages()` 平均耗时 | 检测 TOCTOU 窗口期 | > 30 秒 |
| `MessageRouter.send_message()` `KeyError` 数量 | 检测注册/注销竞态 | > 10/小时 |

---

## 8. 附录：Python asyncio 并发模型

### 8.1 asyncio 不是线程安全的

**常见误解**: "Python 有 GIL，asyncio 是单线程的，所以不需要锁。"

**真相**:
1. **GIL 不保护复合操作**: `dict.get()` → 判断 → `dict[key] = value` 在两个 `await` 之间可能被其他协程插入
2. **FastMCP 使用多线程**: 每个 HTTP 请求在独立线程中执行，`GroupChatManager` 必须线程安全
3. **asyncio.Lock 保护协程调度**: 防止 `await` 让出点的交错

### 8.2 常见竞态模式

| 模式 | 示例 | 风险 |
|------|------|------|
| **Check-Then-Act** | `if key in dict: dict[key] += 1` | 检查后、操作前被插入 |
| **Read-Modify-Write** | `value = dict[key]; value.count += 1; save(value)` | 读后、写前被覆盖 |
| **TOCTOU** | `snapshot = get(); await llm(); save(snapshot)` | LLM 调用期间数据变化 |
| **Iterator Modification** | `for key in dict: del dict[key]` | 迭代期间删除 → RuntimeError |

### 8.3 修复原则

1. **最小锁范围**: 只锁住必要的 read-modify-write 序列，I/O 操作在锁外执行
2. **避免嵌套锁**: 防止死锁
3. **快照 + 版本校验**: 长时间操作（如 LLM 调用）使用乐观锁
4. **复制容器**: 迭代前复制 `list(dict.keys())`

---

## 9. 总结

### 9.1 核心发现

- **Repository 层锁完善，但 Runtime 层缺乏保护** → 内存状态更新非原子
- **AgentCallManager 和 GroupChatManager 无锁** → 高频并发易崩溃
- **历史 Bug 记录准确** → `docs/history-bugs/2026-06-05-group-chat-runtime-state-concurrency.md` 已识别主要问题

### 9.2 修复路径

```
Phase 1 (本周): P0 问题 - 防止崩溃
├─ AgentCallManager 加锁
├─ GroupChatManager._group_chats 加锁
└─ GroupChatRuntime 加 _state_lock

Phase 2 (下周): P1 问题 - 保证数据一致性
├─ append_compact_record_and_mark_compacted 事务化
├─ compact_messages 版本校验
└─ MessageRouter 加锁

Phase 3 (后续): P2 问题 + 测试覆盖
├─ 并发初始化批量化
├─ 单元测试覆盖
└─ 压力测试 + 监控
```

### 9.3 预期收益

- **可靠性提升**: 消除 7 个已知竞态条件，降低生产崩溃风险
- **数据一致性**: 防止持久化覆盖、消息丢失
- **可维护性**: 明确的锁策略，降低未来并发 Bug 风险

---

**审查人**: Claude Code (Autonomous Agent)  
**审查日期**: 2026-06-14  
**参考文档**: `docs/history-bugs/2026-06-05-group-chat-runtime-state-concurrency.md`

