# load_group_chat_from_disk 自动激活群聊导致前端加载时启动 agent 任务

## 问题描述

前端加载 session 列表时，没有点击任何群聊，没有发送任何信息，但群聊都被自动激活了，启动了 agent 任务和 heartbeat。

**日志表现**：
```
2026-06-08 23:31:09,245 [agents_hub.core.orchestration.group_chat] INFO group_chat.py:143 - 群聊加载完成: id=4ba63427-30ff-4378-bc53-6a630bf42b68
2026-06-08 23:31:09,246 [agents_hub.core.orchestration.group_chat] INFO group_chat.py:154 - 激活群聊: id=4ba63427-30ff-4378-bc53-6a630bf42b68
2026-06-08 23:31:09,247 [heartbeat.4ba63427-30ff-4378-bc53-6a630bf42b68] INFO group_chat.py:589 - Heartbeat 启动: interval=1200s
```

## 触发条件

1. 前端 `useSessionList.ts` 在加载 session 列表时，对所有群聊调用 `getMembers` API
2. 后端 `get_group_chat_members` 调用 `group_chat_manager.load_group_chat()`
3. `load_group_chat` 调用 `load_group_chat_from_disk()`
4. `load_group_chat_from_disk` 在加载完成后自动调用 `group_chat.activate()`
5. `activate()` 启动所有 agent 的 `run()` 任务和 heartbeat

## 根本原因

`group_chat_manager.py` 的 `load_group_chat_from_disk` 方法在从磁盘加载 GroupChat 时，会自动调用 `activate()` 方法，启动 agent 任务。

```python
# 问题代码（group_chat_manager.py 第 350-366 行）
# 5. 加载GroupChat状态
await group_chat.load()

# 6. 激活GroupChat（启动 agent 任务，标记为活跃）  ← 问题在这里
await group_chat.activate()

# 7. 注册到 GroupChatManager
self.register(group_chat_id, group_chat)
```

**设计意图**：
- `GroupChat.load()` - 从磁盘加载已有群聊，**只读**，不启动 agent
- `GroupChat.activate()` - 激活群聊，启动 agent.run() 任务
- `load_group_chat_from_disk` 应该只调用 `load()`，不应该调用 `activate()`

**违反原则**：从磁盘加载应该是只读操作，不应该有副作用（启动 agent 任务）。激活应该只在用户主动发送消息时发生。

## 前端触发路径

```typescript
// useSessionList.ts 第 40 行
...allSessionIds.map((id) => getMembers(id).catch(() => [])),
```

前端在加载 session 列表时，为了获取成员信息（显示头像等），对所有群聊都调用了 `getMembers` API，这触发了群聊的激活。

## 修复方案

修改 `group_chat_manager.py` 的 `load_group_chat_from_disk` 方法，移除自动调用 `activate()` 的逻辑：

```python
# 修复后
# 5. 加载GroupChat状态
await group_chat.load()

# 6. 注册到 GroupChatManager（不激活，激活应在用户发送消息时触发）
self.register(group_chat_id, group_chat)
```

**激活时机**：只有在用户发送消息时（通过 `send_message` 方法），才调用 `activate_group_chat` 激活群聊。

## 相关文件

- `agents_hub/core/orchestration/group_chat_manager.py` - load_group_chat_from_disk 方法
- `agents_hub/core/orchestration/group_chat.py` - load() 和 activate() 方法
- `frontend/src/features/session/hooks/useSessionList.ts` - 前端触发点
- `frontend/src/features/chat/hooks/useMembers.ts` - getMembers 调用
- `agents_hub/api/services/group_chat_service.py` - send_message 中的 activate 调用

## 教训

1. **AI 执行偏离意图**：用户已经明确说明"一开始不是激活，而是加载"，但 AI 执行时仍然在加载时调用了激活
2. **只读操作不应有副作用**：从磁盘加载应该是只读操作，不应该启动 agent 任务
3. **懒加载设计**：激活应该延迟到真正需要时（发送消息时）才执行
