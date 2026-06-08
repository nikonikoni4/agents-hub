# Message PIN 后右侧栏不自动刷新

## 问题描述

**症状**：在群聊中置顶/取消置顶消息后，右侧栏的 Pinned 列表不会自动更新，必须手动切换 session 或刷新页面才能看到最新的 pin 数据。

**发现时间**：2026-06-08

**影响范围**：前端 `RightSidebar` 组件的 Pinned 部分

---

## 根本原因

后端 `pin_message` 方法返回 `None`，前端需要额外调用 GET 请求才能获取最新数据。虽然前端 `pin()` 方法中有 `await refresh()` 调用，但由于响应不包含创建的数据，无法直接更新 state。

### 数据流分析（修复前）

```
前端 pin(messageId)
    ↓
POST /pinned-messages { message_id: 123 }
    ↓
后端创建 pin，返回 { ok: true }（不包含创建的数据）
    ↓
前端调用 refresh() → GET /pinned-messages（额外请求）
    ↓
后端返回最新列表
    ↓
前端更新 pinnedMessages state
    ↓
右侧栏更新 ✅（但需要两次请求，且有延迟）
```

---

## 修复方案

**选定方案**：方案 A（POST 后立即返回创建的数据）

**原理**：修改后端 `pin_message` 返回 `PinnedMessageInfo`，前端直接使用返回的数据更新 state。

### 数据流分析（修复后）

```
前端 pin(messageId)
    ↓
POST /pinned-messages { message_id: 123 }
    ↓
后端创建 pin，返回 PinnedMessageInfo
    ↓
前端将返回的数据添加到 pinnedMessages state
    ↓
右侧栏立即更新 ✅（单次请求，即时反馈）
```

---

## 实施细节

### 后端修改

**文件**：`agents_hub/api/services/group_chat_service.py`

**修改**：`pin_message` 方法返回 `PinnedMessageInfo` 而不是 `None`。

```python
async def pin_message(self, group_chat_id: str, message_id: int) -> PinnedMessageInfo:
    # ... 创建 pin 数据 ...
    return PinnedMessageInfo(**pin_data)
```

### 后端路由修改

**文件**：`agents_hub/api/routes/group_chat.py`

**修改**：POST 路由响应类型改为 `PinnedMessageInfo`。

```python
@router.post(
    "/{group_chat_id}/pinned-messages",
    response_model=PinnedMessageInfo,  # 从 PinOperationResponse 改为 PinnedMessageInfo
)
async def pin_message(...):
    return await service.pin_message(group_chat_id, body.message_id)
```

### 前端 API 修改

**文件**：`frontend/src/core/api/groupChatApi.ts`

**修改**：`pinMessage` 函数返回 `PinnedMessageInfo`。

```typescript
export async function pinMessage(
  chatId: string,
  data: PinMessageRequest
): Promise<PinnedMessageInfo> {
  return apiClient.post<PinnedMessageInfo>(`/group-chats/${chatId}/pinned-messages`, data);
}
```

### 前端 Hook 修改

**文件**：`frontend/src/features/chat/hooks/usePinnedMessages.ts`

**修改**：`pin` 方法直接使用返回的数据更新 state。

```typescript
const pin = useCallback(
  async (messageId: number) => {
    if (!chatId) return;
    try {
      const newPin = await pinMessage(chatId, { message_id: messageId });
      // 直接将返回的数据添加到 state，无需再次请求
      setPinnedMessages((prev) => [...prev, newPin]);
    } catch (err) {
      console.error('Failed to pin message:', err);
      throw err;
    }
  },
  [chatId]
);
```

---

## 前端依赖链路

```
RightSidebar.tsx
    ↓
usePinnedMessages(activeSessionId)
    ↓
pin(messageId) → pinMessage() API
    ↓
返回 PinnedMessageInfo
    ↓
setPinnedMessages((prev) => [...prev, newPin])
    ↓
RightSidebar Pinned 列表立即更新
```

---

## 验证方法

1. 启动后端服务
2. 在群聊中置顶一条消息
3. 观察右侧栏 Pinned 部分是否**立即**显示该消息（无需手动刷新）
4. 取消置顶该消息
5. 观察右侧栏 Pinned 部分是否**立即**移除该消息

---

## 经验教训

1. **POST 请求应该返回创建的资源**：符合 RESTful 最佳实践，减少额外请求
2. **前端直接使用返回数据更新 state**：比再次请求更高效，用户体验更好
3. **避免不必要的 WebSocket 广播**：对于单客户端操作，直接使用 API 响应即可

---

## 相关文件

### 后端
- `agents_hub/api/schemas/group_chats.py` - Schema 定义（PinnedMessageInfo）
- `agents_hub/api/services/group_chat_service.py` - Service 层实现
- `agents_hub/api/routes/group_chat.py` - 路由层

### 前端
- `frontend/src/shared/types/api-schemas.ts` - TypeScript 类型
- `frontend/src/core/api/groupChatApi.ts` - API 函数
- `frontend/src/features/chat/hooks/usePinnedMessages.ts` - Hook 实现
- `frontend/src/layouts/RightSidebar/RightSidebar.tsx` - 右侧栏组件

### 文档
- `docs/temp/frontend-refresh-audit-2026-06-07.md` - 刷新审计报告
