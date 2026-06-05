## GroupChatRuntimeState 状态改变与并发问题

- updated_at: 2026-06-05
- path: docs/history-bugs/2026-06-05-group-chat-runtime-state-concurrency.md

### Bug 简述

`GroupChatRuntimeState` 及其关联的 `GroupChatRuntime` 在多协程并发访问时缺乏内存状态保护，Repository 层虽有 `asyncio.Lock` 保护文件 I/O，但 Runtime 层的 read-modify-write 序列存在竞态条件，可能导致持久化数据不一致。

### 复用场景

- 任何涉及"读状态 → await → 修改 → 持久化"的异步操作都需要关注
- `AgentCallManager` 的后台清理循环与主流程并发访问 `_calls` 字典
- `GroupChatManager` 在 FastMCP HTTP 多线程环境下的 `_group_chats` 字典访问

### 代码位置

| 文件 | 行号 | 问题 |
|------|------|------|
| `agents_hub/core/context/group_chat_runtime.py` | 281-296 | `append_compact_record_and_mark_compacted` 双次 `_persist()` 非原子 |
| `agents_hub/core/context/group_chat_runtime.py` | 327-339 | `_persist()` 的 `persistence_error` 被并发协程覆盖 |
| `agents_hub/core/context/group_chat_context.py` | 88-186 | `compact_messages` 在 LLM 调用期间快照过时 (TOCTOU) |
| `agents_hub/core/communication/agent_call_manager.py` | 37-38 | `_calls` 和 `_calls_by_receiver` 无并发保护 |
| `agents_hub/core/orchestration/group_chat_manager.py` | 32 | `_group_chats` 无锁（对比 `_tokens` 有 `threading.RLock`） |
| `agents_hub/core/context/group_chat_session.py` | 39 | `# TODO 缺乏锁`（已知技术债） |

### 发生原因

1. **架构分层导致保护缺口**：Repository 层有 `asyncio.Lock` 保护文件读写，但 Runtime 层（负责"更新内存 + 调用持久化"）没有对应的锁，导致 read-modify-write 序列在 `await` 让出点被其他协程插入
2. **并发来源多**：`asyncio.gather()` 初始化新成员、每个 agent 的独立 `run()` Task、`AgentCallManager._cleanup_loop()` 后台任务、API 并发请求
3. **Python asyncio 单线程模型的误解**：虽然不会出现线程安全中的内存损坏，但 `await` 让出点的协程交错同样会产生逻辑竞态

### 各问题详细分析

#### 问题 1: `append_compact_record_and_mark_compacted` 双次 persist 非原子

```python
# group_chat_runtime.py:281-296
async def append_compact_record_and_mark_compacted(self, compact_record: dict) -> None:
    session = self.state.require_session()
    self.state.compact_history.append(compact_record)
    session.last_compacted_loc = len(session.messages)
    # 两次独立 persist，中间有 await 让出点
    await self._persist(lambda: self.repository.save_compact_history(...))   # 可能成功
    await self._persist(lambda: self.repository.save_group_chat_session(...))  # 可能失败
```

风险：第一次 persist 成功、第二次失败 → `compact_history.jsonl` 已追加记录，但 `messages.jsonl` 的 `last_compacted_loc` 未更新。重启后重复压缩。

#### 问题 2: `compact_messages` TOCTOU

```python
# group_chat_context.py:109
uncompacted_messages = self.group_chat_session.get_uncompact_messages()  # 读快照
# ... 长时间 LLM 调用 (await) ...
await self.runtime.append_compact_record_and_mark_compacted(...)  # 写
```

LLM 调用期间其他协程可能添加了新消息，`last_compacted_loc = len(session.messages)` 会把这些新消息标记为"已压缩"，导致它们被跳过压缩。

#### 问题 3: `AgentCallManager._calls` 无保护

`_cleanup_loop()` 在 `await asyncio.sleep()` 后删除 `_calls` 和 `_calls_by_receiver` 中的条目，而主流程的 `get_runtime_calls_for_agent()` 正在遍历这些字典。`del self._calls_by_receiver[send_to]` (line 476) 可能在迭代期间删除 key。

#### 问题 4: `GroupChatManager._group_chats` 无锁

代码注释声明"线程安全：token 索引操作使用 RLock 保护"，`_tokens` 有 `threading.RLock`，但 `_group_chats` 完全没有保护。在 FastMCP HTTP 多线程环境下，`register()` 和 `unregister()` 可能被不同线程并发调用。

### 最佳方案

**核心思路**：在 `GroupChatRuntime` 层添加 `asyncio.Lock`，保护所有 command 方法的 read-modify-write 序列。

```python
# group_chat_runtime.py
class GroupChatRuntime:
    def __init__(self, ...):
        ...
        self._state_lock = asyncio.Lock()  # 保护内存状态的 read-modify-write

    async def add_message(self, agent_result) -> None:
        async with self._state_lock:
            session = self.state.require_session()
            session.add_message(agent_result)
            await self._persist(lambda: self.repository.save_group_chat_session(session))

    async def append_compact_record_and_mark_compacted(self, compact_record: dict) -> None:
        async with self._state_lock:
            session = self.state.require_session()
            self.state.compact_history.append(compact_record)
            session.last_compacted_loc = len(session.messages)
            # 合并为单次 persist 或在同一锁内完成两次 persist
            await self._persist(lambda: self.repository.save_compact_history(self.state.compact_history))
            await self._persist(lambda: self.repository.save_group_chat_session(session))
```

**其他修复点**：

| 问题 | 方案 |
|------|------|
| `AgentCallManager._calls` | 添加 `asyncio.Lock`，在 `_cleanup_loop` 和 CRUD 操作间互斥 |
| `GroupChatManager._group_chats` | 与 `_tokens` 一致使用 `threading.RLock`，或确认仅在单线程 asyncio 中使用 |
| `compact_messages` TOCTOU | 在锁内读取快照并记录版本号，persist 时校验版本 |
| `GroupChatSession` 缺乏锁 | 由 Runtime 层的 `_state_lock` 间接保护，Session 自身可暂不加锁 |
