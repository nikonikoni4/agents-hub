# Message PIN 后右侧栏不自动刷新

## 问题描述

**症状**：在群聊中置顶/取消置顶消息后，右侧栏的 Pinned 列表不会自动更新，必须手动切换 session 或刷新页面才能看到最新的 pin 数据。

**发现时间**：2026-06-08

**影响范围**：前端 `RightSidebar` 组件的 Pinned 部分

---

## 根本原因

后端 `GroupChatService` 的 `pin_message` 和 `unpin_message` 方法中**没有调用 `broadcast_group_chat_refresh` 发送 WebSocket refresh 信号**。

### 对比分析

| 方法 | 是否发送 refresh 信号 | 结果 |
|------|----------------------|------|
| `add_group_chat_members` | ✅ 是（第 817 行） | 前端自动刷新 |
| `pin_message` | ❌ 否（已修复） | 前端不刷新 |
| `unpin_message` | ❌ 否（已修复） | 前端不刷新 |

### 数据流分析

```
后端 pin_message()
    ↓
写入 pins.json
    ↓ (缺少 broadcast_group_chat_refresh)
前端 usePinnedMessages 监听 WebSocket refresh 信号
    ↓ (收不到信号)
RightSidebar Pinned 列表不更新 ❌
```

修复后：

```
后端 pin_message()
    ↓
写入 pins.json
    ↓
broadcast_group_chat_refresh(group_chat_id) ✅
    ↓
前端 usePinnedMessages 收到 refresh 信号
    ↓
调用 refresh() → getPinnedMessages() API
    ↓
RightSidebar Pinned 列表自动更新 ✅
```

---

## 修复方案

**文件**：`agents_hub/api/services/group_chat_service.py`

**修改**：在 `pin_message` 和 `unpin_message` 方法中，成功写入 pins 后添加 `await broadcast_group_chat_refresh(group_chat_id)` 调用。

```python
# pin_message 方法中（第 762 行之后）
await self._write_pins(pins_path, pins)
# 必须发送 refresh 信号，否则前端 usePinnedMessages 不会自动刷新
await broadcast_group_chat_refresh(group_chat_id)

# unpin_message 方法中（第 781 行之后）
await self._write_pins(pins_path, new_pins)
# 必须发送 refresh 信号，否则前端 usePinnedMessages 不会自动刷新
await broadcast_group_chat_refresh(group_chat_id)
```

---

## 前端依赖链路

```
RightSidebar.tsx
    ↓
usePinnedMessages(activeSessionId)
    ↓
监听 wsManager.on('refresh', handleRefresh)
    ↓
收到 refresh 信号后调用 refresh()
    ↓
getPinnedMessages(chatId) API
    ↓
更新 pinnedMessages state
    ↓
RightSidebar Pinned 列表重新渲染
```

---

## 验证方法

1. 启动后端服务
2. 在群聊中置顶一条消息
3. 观察右侧栏 Pinned 部分是否立即显示该消息
4. 取消置顶该消息
5. 观察右侧栏 Pinned 部分是否立即移除该消息

---

## 经验教训

1. **任何修改数据的 mutation 操作都必须发送 refresh 信号**，否则前端依赖 WebSocket 信号的 hooks 不会自动刷新
2. **参考已有的成功实现**：`add_group_chat_members` 方法已经正确发送了 refresh 信号，应该作为模板
3. **前端 hooks 的依赖关系**：`usePinnedMessages` 依赖 WebSocket refresh 信号，后端必须配合发送

---

## 相关文件

- 后端：`agents_hub/api/services/group_chat_service.py`
- 前端 hooks：`frontend/src/features/chat/hooks/usePinnedMessages.ts`
- 前端组件：`frontend/src/layouts/RightSidebar/RightSidebar.tsx`
- 刷新审计报告：`docs/temp/frontend-refresh-audit-2026-06-07.md`
