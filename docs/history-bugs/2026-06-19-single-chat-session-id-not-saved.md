---
version: 1.0
created_at: 2026-06-19
bug_id: single-chat-session-id-not-saved
severity: high
status: fixed
platforms: all
affected_versions: <= 2026-06-19
fixed_in: 2026-06-19
---

# 单聊历史记录加载失败 - session_id 未保存

## 问题描述

用户创建单聊并发送消息后，切换到其他聊天再切回来时，无法加载历史记录。后端返回空数组 `{"messages":[]}`。

**关键现象**：
- 用户在 AI 回复到一半时切换聊天
- 切回来后历史记录消失
- `local_data/single_chats/index.json` 中 `session_id` 和 `session_path` 为 `null`

## 触发场景

1. 创建单聊（特别是 fork 模式）
2. 发送消息，AI 开始流式回复
3. **在回复未完成时切换到其他聊天**（关键）
4. 切回单聊 → 历史记录为空

## 根因分析

### 问题 1：Codex 解析器不生成 INIT 事件

**位置**：`agents_hub/agent_bridge/parsers/codex.py`

Codex CLI 的 `thread.started` 事件包含 `thread_id`（即 `session_id`），但解析器只缓存到内存，不生成 `StreamEvent`：

```python
# 问题代码
if event_type == "thread.started":
    self._thread_id = event.get("thread_id", "")
    return None  # ❌ 不生成事件
```

虽然后续的 `TEXT_DELTA` 和 `TURN_COMPLETE` 事件也包含 `session_id`（从缓存的 `self._thread_id` 获取），但这依赖于后续事件能够触发更新逻辑。

**对比**：Claude 解析器在 `system.init` 事件中生成 `AgentEventType.INIT` 事件，确保第一时间提供 `session_id`。

### 问题 2：session_id 保存延迟到流结束（严重 Bug）

**位置**：`agents_hub/api/services/single_chat_service.py:320-343`

```python
async for event in agent_platform_client.execute_stream(...):
    yield self._serialize_event(event)
    
    # 在内存中更新 session_id
    if event.session_id and not index.session_id:
        index.session_id = event.session_id
        session_updated = True

# 流结束后才保存到磁盘
if session_updated:
    index.session_path = self._resolve_session_path(...)
    
self._save_index()  # ❌ 只有流完全耗尽才会执行
```

**时间线**：
1. 用户发送消息，流式输出开始
2. 第一个事件到达，`index.session_id` 在内存中更新 ✅
3. 用户切换聊天，前端取消 SSE 订阅
4. 后端生成器中断，`_save_index()` 永远不会执行 ❌
5. 内存中的更新丢失，磁盘上的 index 仍然是 `null`
6. 切回来时重新从磁盘加载 → `session_id` 为 `null` → 无法加载历史

**根本原因**：生成器函数只有在完全耗尽后才会执行后续代码。流中断 = 生成器中断 = 保存操作永远不执行。

### 为什么群聊没有这个问题？

群聊使用不同的架构：
- Agent 的 `main_session` 在 Agent 注册时就分配并保存到 `agent_member.json`
- 群聊使用非流式 `execute()` 方法，该方法会完整消费流并提取 `session_id`
- 不依赖流式输出完成来保存 session 状态

## 修复方案

### 修复 1：Codex 解析器生成 INIT 事件

**文件**：`agents_hub/agent_bridge/parsers/codex.py`

```python
# 修复后
if event_type == "thread.started":
    self._thread_id = event.get("thread_id", "")
    return StreamEvent(
        type=AgentEventType.INIT,
        content={},
        session_id=self._thread_id,  # ✅ 第一个事件就包含 session_id
        timestamp=datetime.now().isoformat(),
        agent_name="",
        platform=AgentPlatform.CODEX,
        role_type=RoleType.TEAM_MEMBER,
    )
```

**收益**：
- 与 Claude/OpenCode 解析器保持一致
- 第一个事件就提供 `session_id`，更早触发保存逻辑
- 提升健壮性，作为兜底机制

**影响分析**：
- 前端：只处理 `text_delta` 和 `tool_use`，忽略 INIT → 无影响
- 群聊：非流式 `execute()` 只提取特定类型，INIT 被忽略 → 无影响

### 修复 2：立即保存 session_id（核心修复）

**文件**：`agents_hub/api/services/single_chat_service.py`

```python
async for event in agent_platform_client.execute_stream(...):
    yield self._serialize_event(event)
    
    # 首次获取 session_id 时立即保存
    if event.session_id and not index.session_id:
        logger.info("单聊首次获取 session_id: %s", event.session_id)
        index.session_id = event.session_id
        
        # 立即解析并设置 session_path
        index.session_path = self._resolve_session_path(
            index.session_id, index.platform, role_config.work_root
        )
        
        # 立即保存到磁盘，防止流中断导致丢失
        self._save_index()  # ✅ 立即持久化
        logger.info("单聊 session_id 已立即保存: %s", single_chat_id)

# 流结束后只更新活跃时间
index.last_active_at = datetime.now().isoformat()
self._save_index()
```

**关键改进**：
- 一旦获取到 `session_id` 就立即保存到磁盘
- 即使流中断，已保存的 `session_id` 和 `session_path` 不会丢失
- 用户可以随时切换聊天而不丢失数据

## 测试验证

**测试场景 1**：流中断后 session_id 持久化
1. 创建新单聊并发送消息
2. 在 AI 回复到一半时切换到其他聊天
3. 检查 `local_data/single_chats/index.json`
4. 验证：`session_id` 和 `session_path` 已保存 ✅

**测试场景 2**：切回单聊后历史加载
1. 从测试场景 1 继续
2. 切回单聊
3. 验证：能够看到之前的消息历史 ✅

**测试场景 3**：后端日志验证
```
INFO: 单聊首次获取 session_id: single_chat_id=xxx, session_id=019edd9d-3632-70f0-98b9-39cf549a2edb
INFO: 单聊 session_path 已更新: single_chat_id=xxx, session_path=.../sessions/.../rollout-xxx.jsonl
INFO: 单聊 session_id 已立即保存: single_chat_id=xxx
```

## 关键教训

### 1. 生成器函数的后续代码执行时机

生成器函数中 `yield` 之后的代码**只有在生成器完全耗尽后才会执行**。如果消费者中途取消，后续代码永远不会运行。

**错误模式**：
```python
async def stream_data():
    async for item in source:
        yield item
    # ❌ 如果消费者取消，这里永远不会执行
    save_to_disk()
```

**正确模式**：
```python
async def stream_data():
    async for item in source:
        if should_save(item):
            save_to_disk()  # ✅ 在循环内立即保存
        yield item
```

### 2. 关键状态必须立即持久化

对于影响用户体验的关键状态（如 `session_id`），不能延迟到操作完成后才保存。应该在获取到数据的第一时间就持久化。

### 3. 跨平台 Parser 一致性

不同平台的解析器应该保持一致的事件生成策略。如果 Claude 生成 INIT 事件，Codex 也应该生成，避免出现平台差异导致的 bug。

### 4. 流式接口的中断鲁棒性

设计流式接口时，必须考虑消费者可能随时中断的场景。关键操作不能依赖流的完整执行。

## 相关文件

- `agents_hub/agent_bridge/parsers/codex.py` - Codex 解析器
- `agents_hub/api/services/single_chat_service.py` - 单聊服务
- `docs/specs/2026-06-08-single-chat.md` - 单聊通道规格
- `docs/specs/2026-06-19-chat-history.md` - 聊天历史规格

## 相关 Bug

- [2026-06-15-parser-concurrency-race-condition.md](2026-06-15-parser-concurrency-race-condition.md) - Parser 并发竞态问题
- [2026-06-08-load-group-chat-auto-activate.md](2026-06-08-load-group-chat-auto-activate.md) - 加载与副作用分离原则
