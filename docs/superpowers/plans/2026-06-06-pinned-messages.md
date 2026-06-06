# Pinned Messages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现消息置顶功能：hover 消息气泡底部 pin 按钮置顶消息，右侧栏展示已置顶消息列表并支持取消置顶。

**Architecture:** 后端在 GroupChatService 层通过 pins.json 文件持久化 pin 数据（SSOT），不改动核心层。前端新增 usePinnedMessages hook 管理状态，ChatArea 增加 hover pin 按钮，RightSidebar 增加 Pinned 模块。

**Tech Stack:** Python/FastAPI/Pydantic（后端），React/TypeScript/Zustand（前端），文件持久化（pins.json）

**Design Spec:** `docs/superpowers/specs/2026-06-06-pinned-messages-design.md`

---

## File Structure

### Backend (create/modify)

| File | Action | Responsibility |
|------|--------|---------------|
| `agents_hub/api/schemas/group_chats.py` | Modify | 新增 PinMessageRequest, PinnedMessageInfo, PinOperationResponse, PinErrorResponse |
| `agents_hub/api/services/group_chat_service.py` | Modify | 新增 get_pinned_messages, pin_message, unpin_message 方法 + pins.json 读写 |
| `agents_hub/api/routes/group_chat.py` | Modify | 新增 3 个 pinned-messages 端点 |

### Frontend (create/modify)

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/shared/types/api-schemas.ts` | Modify | 新增 PinnedMessageInfo, PinMessageRequest, PinOperationResponse 类型 |
| `frontend/src/core/api/groupChatApi.ts` | Modify | 新增 getPinnedMessages, pinMessage, unpinMessage 函数 + mock 数据 |
| `frontend/src/features/chat/hooks/usePinnedMessages.ts` | Create | Pin 状态管理 hook |
| `frontend/src/layouts/ChatArea/ChatArea.tsx` | Modify | MessageBubble 增加 hover pin 按钮 |
| `frontend/src/layouts/ChatArea/ChatArea.module.css` | Modify | pin 按钮和操作栏样式 |
| `frontend/src/layouts/RightSidebar/RightSidebar.tsx` | Modify | 新增 Pinned 模块 |
| `frontend/src/layouts/RightSidebar/RightSidebar.module.css` | Modify | pinned 消息列表样式 |

---

### Task 1: Backend Schemas

**Files:**
- Modify: `agents_hub/api/schemas/group_chats.py:66`

- [ ] **Step 1: 新增 Pin 相关 Schema**

在 `group_chats.py` 末尾追加：

```python
# --- Pin Messages Schemas ---

class PinMessageRequest(BaseModel):
    """POST /pinned-messages 请求体"""
    speaker: str = Field(..., min_length=1, description="消息发送者名称")
    timestamp: str = Field(..., description="消息时间戳（ISO 8601）")


class PinnedMessageInfo(BaseModel):
    """GET /pinned-messages 响应列表项"""
    speaker: str = Field(..., description="消息发送者名称")
    content: str = Field(..., description="消息完整内容（快照）")
    timestamp: str = Field(..., description="消息原始时间戳")
    platform: str = Field(..., description="消息来源平台")
    pinned_at: str = Field(..., description="置顶操作时间")


class PinOperationResponse(BaseModel):
    """POST/DELETE /pinned-messages 成功响应"""
    ok: bool = Field(default=True, description="操作是否成功")


class PinErrorResponse(BaseModel):
    """错误响应的统一格式"""
    error_code: str = Field(..., description="错误码")
    message: str = Field(..., description="人类可读的错误描述")
```

- [ ] **Step 2: 验证语法**

Run: `cd D:\desktop\软件开发\agents-hub && python -c "from agents_hub.api.schemas.group_chats import PinMessageRequest, PinnedMessageInfo, PinOperationResponse; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add agents_hub/api/schemas/group_chats.py
git commit -m "feat: add pin message schemas"
```

---

### Task 2: Backend Service - pins.json 持久化

**Files:**
- Modify: `agents_hub/api/services/group_chat_service.py:565`

- [ ] **Step 1: 新增 pin 相关 import 和常量**

在 `group_chat_service.py` 顶部 import 区域添加：

```python
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone
```

在 `GroupChatService` 类内部添加类属性：

```python
class GroupChatService:
    # ... 现有 __init__ ...
    _pins_locks: dict[str, asyncio.Lock] = {}  # 按 group_chat_id 隔离的锁
```

- [ ] **Step 2: 新增 `_get_pins_path` 私有方法**

```python
def _get_pins_path(self, group_chat_id: str) -> Path:
    """获取 pins.json 文件路径（与群聊其他数据文件同级）"""
    group_chat = self.group_chat_manager.load_group_chat(group_chat_id)
    # 群聊基础目录 = runtime 的 repository base_dir
    base_dir = group_chat.runtime.repository.base_dir
    return base_dir / "pins.json"
```

- [ ] **Step 3: 新增 `_get_pins_lock` 私有方法**

```python
def _get_pins_lock(self, group_chat_id: str) -> asyncio.Lock:
    """获取按 group_chat_id 隔离的 asyncio.Lock"""
    if group_chat_id not in self._pins_locks:
        self._pins_locks[group_chat_id] = asyncio.Lock()
    return self._pins_locks[group_chat_id]
```

- [ ] **Step 4: 新增 `_read_pins` 私有方法**

```python
async def _read_pins(self, pins_path: Path) -> list[dict]:
    """从 pins.json 读取 pin 列表，文件不存在返回空列表"""
    if not pins_path.exists():
        return []
    async with aiofiles.open(pins_path, "r", encoding="utf-8") as f:
        content = await f.read()
        return json.loads(content) if content.strip() else []
```

- [ ] **Step 5: 新增 `_write_pins` 私有方法**

```python
async def _write_pins(self, pins_path: Path, pins: list[dict]) -> None:
    """将 pin 列表写入 pins.json"""
    pins_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(pins_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(pins, ensure_ascii=False, indent=2))
```

- [ ] **Step 6: 新增 `get_pinned_messages` 方法**

```python
async def get_pinned_messages(self, group_chat_id: str) -> list[dict]:
    """获取已置顶消息列表，按 pinned_at 升序"""
    self.group_chat_manager.load_group_chat(group_chat_id)  # 验证群聊存在
    pins_path = self._get_pins_path(group_chat_id)
    lock = self._get_pins_lock(group_chat_id)
    async with lock:
        pins = await self._read_pins(pins_path)
    return sorted(pins, key=lambda p: p.get("pinned_at", ""))
```

- [ ] **Step 7: 新增 `pin_message` 方法**

```python
async def pin_message(self, group_chat_id: str, speaker: str, timestamp: str) -> None:
    """置顶一条消息。幂等：已 pin 则跳过。422：消息不存在。"""
    group_chat = self.group_chat_manager.load_group_chat(group_chat_id)
    # 从消息历史中查找目标消息
    messages = group_chat.runtime.get_message_dicts()
    target = None
    for msg in messages:
        if msg.get("agent_name") == speaker and msg.get("timestamp") == timestamp:
            target = msg
            break
    if target is None:
        raise MessageNotFoundError(f"Message not found: speaker={speaker}, timestamp={timestamp}")
    # 读取现有 pins
    pins_path = self._get_pins_path(group_chat_id)
    lock = self._get_pins_lock(group_chat_id)
    async with lock:
        pins = await self._read_pins(pins_path)
        # 幂等检查：已存在则跳过
        for p in pins:
            if p["speaker"] == speaker and p["timestamp"] == timestamp:
                return
        # 保存快照
        pins.append({
            "speaker": target.get("agent_name", speaker),
            "content": target.get("content", ""),
            "timestamp": target.get("timestamp", timestamp),
            "platform": target.get("platform", ""),
            "pinned_at": datetime.now(timezone.utc).isoformat(),
        })
        await self._write_pins(pins_path, pins)
```

- [ ] **Step 8: 新增 `unpin_message` 方法**

```python
async def unpin_message(self, group_chat_id: str, speaker: str, timestamp: str) -> None:
    """取消置顶。幂等：未 pin 则跳过。不要求消息存在于历史中。"""
    self.group_chat_manager.load_group_chat(group_chat_id)  # 验证群聊存在
    pins_path = self._get_pins_path(group_chat_id)
    lock = self._get_pins_lock(group_chat_id)
    async with lock:
        pins = await self._read_pins(pins_path)
        new_pins = [p for p in pins if not (p["speaker"] == speaker and p["timestamp"] == timestamp)]
        if len(new_pins) != len(pins):
            await self._write_pins(pins_path, new_pins)
```

- [ ] **Step 9: 验证 import 正确**

Run: `cd D:\desktop\软件开发\agents-hub && python -c "from agents_hub.api.services.group_chat_service import GroupChatService; print('OK')"`
Expected: `OK`

- [ ] **Step 10: Commit**

```bash
git add agents_hub/api/services/group_chat_service.py
git commit -m "feat: add pin/unpin/get_pinned_messages to GroupChatService"
```

---

### Task 3: Backend Routes

**Files:**
- Modify: `agents_hub/api/routes/group_chat.py:110`

- [ ] **Step 1: 新增 pin 相关 import**

在 `group_chat.py` 顶部 import 区域添加：

```python
from agents_hub.api.schemas.group_chats import (
    # ... 现有 import ...
    PinMessageRequest,
    PinnedMessageInfo,
    PinOperationResponse,
)
```

- [ ] **Step 2: 新增 GET pinned-messages 端点**

在现有端点之后添加：

```python
@router.get(
    "/{group_chat_id}/pinned-messages",
    response_model=list[PinnedMessageInfo],
)
async def get_pinned_messages(
    group_chat_id: str,
    service: GroupChatService = Depends(get_group_chat_service),
):
    return await service.get_pinned_messages(group_chat_id)
```

- [ ] **Step 3: 新增 POST pinned-messages 端点**

```python
@router.post(
    "/{group_chat_id}/pinned-messages",
    response_model=PinOperationResponse,
)
async def pin_message(
    group_chat_id: str,
    body: PinMessageRequest,
    service: GroupChatService = Depends(get_group_chat_service),
):
    await service.pin_message(group_chat_id, body.speaker, body.timestamp)
    return PinOperationResponse()
```

- [ ] **Step 4: 新增 DELETE pinned-messages 端点**

```python
@router.delete(
    "/{group_chat_id}/pinned-messages",
    response_model=PinOperationResponse,
)
async def unpin_message(
    group_chat_id: str,
    speaker: str = Query(..., min_length=1),
    timestamp: str = Query(...),
    service: GroupChatService = Depends(get_group_chat_service),
):
    await service.unpin_message(group_chat_id, speaker, timestamp)
    return PinOperationResponse()
```

- [ ] **Step 5: 确认 Query import 已存在**

确认 `from fastapi import APIRouter, Depends, Query` 中包含 `Query`。若没有则添加。

- [ ] **Step 6: 验证路由注册**

Run: `cd D:\desktop\软件开发\agents-hub && python -c "from agents_hub.api.routes.group_chat import router; print([r.path for r in router.routes])"`
Expected: 输出中包含 `/{group_chat_id}/pinned-messages`

- [ ] **Step 7: Commit**

```bash
git add agents_hub/api/routes/group_chat.py
git commit -m "feat: add pinned-messages API endpoints"
```

---

### Task 4: Frontend Types

**Files:**
- Modify: `frontend/src/shared/types/api-schemas.ts:295`

- [ ] **Step 1: 新增 Pin 相关类型**

在 `api-schemas.ts` 末尾追加：

```typescript
// --- Pinned Messages ---

/** GET /pinned-messages 响应列表项 */
export interface PinnedMessageInfo {
  speaker: string
  content: string
  timestamp: string
  platform: string
  pinned_at: string
}

/** POST /pinned-messages 请求体 */
export interface PinMessageRequest {
  speaker: string
  timestamp: string
}

/** POST/DELETE /pinned-messages 成功响应 */
export interface PinOperationResponse {
  ok: boolean
}
```

- [ ] **Step 2: 确认类型从 index.ts 导出**

检查 `frontend/src/shared/types/index.ts` 是否 re-export `api-schemas.ts` 中的所有类型。如果是 `export * from './api-schemas'` 则无需改动。否则手动添加导出。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/shared/types/api-schemas.ts
git commit -m "feat: add pinned message TypeScript types"
```

---

### Task 5: Frontend API Functions

**Files:**
- Modify: `frontend/src/core/api/groupChatApi.ts:423`

- [ ] **Step 1: 新增 import 类型**

在 `groupChatApi.ts` 顶部 import 中添加：

```typescript
import type {
  // ... 现有类型 ...
  PinnedMessageInfo,
  PinMessageRequest,
  PinOperationResponse,
} from '@/shared/types'
```

- [ ] **Step 2: 新增 mock 数据**

在 mock 数据区域追加：

```typescript
const MOCK_PINNED_MESSAGES: PinnedMessageInfo[] = []

const MOCK_PIN_OPERATION: PinOperationResponse = { ok: true }
```

- [ ] **Step 3: 新增 getPinnedMessages 函数**

```typescript
export async function getPinnedMessages(
  chatId: string
): Promise<PinnedMessageInfo[]> {
  return mockableRequest(
    () =>
      apiClient.get<PinnedMessageInfo[]>(
        `/group-chats/${chatId}/pinned-messages`
      ),
    MOCK_PINNED_MESSAGES
  )
}
```

- [ ] **Step 4: 新增 pinMessage 函数**

```typescript
export async function pinMessage(
  chatId: string,
  data: PinMessageRequest
): Promise<PinOperationResponse> {
  return mockableRequest(
    () =>
      apiClient.post<PinOperationResponse>(
        `/group-chats/${chatId}/pinned-messages`,
        data
      ),
    MOCK_PIN_OPERATION
  )
}
```

- [ ] **Step 5: 新增 unpinMessage 函数**

```typescript
export async function unpinMessage(
  chatId: string,
  data: PinMessageRequest
): Promise<PinOperationResponse> {
  return mockableRequest(
    () =>
      apiClient.delete<PinOperationResponse>(
        `/group-chats/${chatId}/pinned-messages`,
        { params: data }
      ),
    MOCK_PIN_OPERATION
  )
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/core/api/groupChatApi.ts
git commit -m "feat: add pinned message API functions"
```

---

### Task 6: Frontend Hook - usePinnedMessages

**Files:**
- Create: `frontend/src/features/chat/hooks/usePinnedMessages.ts`

- [ ] **Step 1: 创建 usePinnedMessages hook**

```typescript
import { useState, useEffect, useCallback, useMemo } from 'react'
import { getPinnedMessages, pinMessage, unpinMessage } from '@/core/api/groupChatApi'
import type { PinnedMessageInfo } from '@/shared/types'
import { useWebSocket } from '@/features/chat/hooks/useWebSocket'

export function usePinnedMessages(chatId: string | null) {
  const [pinnedMessages, setPinnedMessages] = useState<PinnedMessageInfo[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const refresh = useCallback(async () => {
    if (!chatId) return
    setIsLoading(true)
    try {
      const data = await getPinnedMessages(chatId)
      setPinnedMessages(data)
    } finally {
      setIsLoading(false)
    }
  }, [chatId])

  // chatId 变化时拉取
  useEffect(() => {
    refresh()
  }, [refresh])

  // WebSocket RefreshSignal 触发刷新
  useWebSocket(chatId, () => {
    refresh()
  })

  const pin = useCallback(async (speaker: string, timestamp: string) => {
    if (!chatId) return
    await pinMessage(chatId, { speaker, timestamp })
    await refresh()
  }, [chatId, refresh])

  const unpin = useCallback(async (speaker: string, timestamp: string) => {
    if (!chatId) return
    await unpinMessage(chatId, { speaker, timestamp })
    await refresh()
  }, [chatId, refresh])

  const pinnedSet = useMemo(() => {
    return new Set(pinnedMessages.map(p => `${p.speaker}:${p.timestamp}`))
  }, [pinnedMessages])

  const isPinned = useCallback((speaker: string, timestamp: string) => {
    return pinnedSet.has(`${speaker}:${timestamp}`)
  }, [pinnedSet])

  return { pinnedMessages, isLoading, pin, unpin, isPinned, refresh }
}
```

注意：`useWebSocket` 的具体签名需要根据现有实现调整。如果现有 hook 不支持回调模式，则改为在 `useChatMessages` 相同的地方触发 refresh（即依赖组件层传入 refresh 信号）。

- [ ] **Step 2: 确认 useWebSocket 签名**

检查 `frontend/src/features/chat/hooks/useWebSocket.ts` 或类似文件，确认其 API。若不存在回调式 hook，则简化为：

```typescript
// 不使用 useWebSocket，改为暴露 refresh 供外部调用
// ChatArea 在收到 WebSocket 信号时调用 refresh
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/chat/hooks/usePinnedMessages.ts
git commit -m "feat: add usePinnedMessages hook"
```

---

### Task 7: ChatArea - Hover Pin 按钮

**Files:**
- Modify: `frontend/src/layouts/ChatArea/ChatArea.tsx:313`
- Modify: `frontend/src/layouts/ChatArea/ChatArea.module.css`

- [ ] **Step 1: ChatArea.tsx - import usePinnedMessages**

在 `ChatArea.tsx` 顶部添加 import：

```typescript
import { usePinnedMessages } from '@/features/chat/hooks/usePinnedMessages'
```

- [ ] **Step 2: ChatArea.tsx - 在组件内调用 hook**

在 `ChatArea` 组件内部，`useChatMessages()` 之后添加：

```typescript
const { pin, unpin, isPinned } = usePinnedMessages(activeSessionId)
```

- [ ] **Step 3: ChatArea.tsx - 修改 MessageBubble 签名**

将 `MessageBubble` 的 props 从：

```typescript
function MessageBubble({ msg, avatar }: { msg: MessageApiItem; avatar?: string | null })
```

改为：

```typescript
function MessageBubble({
  msg,
  avatar,
  pinned,
  onPin,
  onUnpin,
}: {
  msg: MessageApiItem
  avatar?: string | null
  pinned: boolean
  onPin: () => void
  onUnpin: () => void
})
```

- [ ] **Step 4: ChatArea.tsx - MessageBubble 内部增加操作栏 JSX**

在 `MessageBubble` 的 return 中，气泡 div 之后追加：

```tsx
<div className={`${styles.messageActions} ${msg.speaker === 'user' ? styles.actionsRight : ''}`}>
  <button
    className={`${styles.pinButton} ${pinned ? styles.pinButtonActive : ''}`}
    onClick={pinned ? onUnpin : onPin}
    title={pinned ? '取消置顶' : '置顶消息'}
  >
    📌
  </button>
</div>
```

- [ ] **Step 5: ChatArea.tsx - 调用处传入 pin props**

在 `allMessages.map` 处修改：

```tsx
<MessageBubble
  key={i}
  msg={msg}
  avatar={roleAvatarMap[msg.speaker]}
  pinned={isPinned(msg.speaker, msg.timestamp)}
  onPin={() => pin(msg.speaker, msg.timestamp)}
  onUnpin={() => unpin(msg.speaker, msg.timestamp)}
/>
```

- [ ] **Step 6: ChatArea.module.css - 新增 pin 按钮样式**

```css
.messageActions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.15s ease;
  margin-top: 2px;
}

.actionsRight {
  justify-content: flex-end;
}

/* hover 气泡时显示操作栏 */
.messageBubble:hover + .messageActions,
.messageActions:hover {
  opacity: 1;
}

.pinButton {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 4px;
  border-radius: 4px;
  opacity: 0.5;
  transition: opacity 0.15s ease;
}

.pinButton:hover {
  opacity: 1;
  background: var(--bg-hover);
}

.pinButtonActive {
  opacity: 1;
}
```

注意：CSS 变量名（如 `--bg-hover`）需要与项目现有主题变量对齐。

- [ ] **Step 7: 验证 hover 效果**

Run: `cd D:\desktop\软件开发\agents-hub\frontend && npm run dev`
在浏览器中打开群聊，hover 消息气泡，确认 pin 按钮出现且点击可切换状态。

- [ ] **Step 8: Commit**

```bash
git add frontend/src/layouts/ChatArea/ChatArea.tsx frontend/src/layouts/ChatArea/ChatArea.module.css
git commit -m "feat: add hover pin button to message bubbles"
```

---

### Task 8: RightSidebar - Pinned 模块

**Files:**
- Modify: `frontend/src/layouts/RightSidebar/RightSidebar.tsx:122`
- Modify: `frontend/src/layouts/RightSidebar/RightSidebar.module.css:136`

- [ ] **Step 1: RightSidebar.tsx - import usePinnedMessages 和 useSessionStore**

```typescript
import { usePinnedMessages } from '@/features/chat/hooks/usePinnedMessages'
import { useSessionStore } from '@/features/session/store/sessionStore'
```

- [ ] **Step 2: RightSidebar.tsx - 调用 hook**

在组件内部添加：

```typescript
const activeSessionId = useSessionStore(s => s.activeSessionId)
const { pinnedMessages, unpin } = usePinnedMessages(activeSessionId)
```

- [ ] **Step 3: RightSidebar.tsx - 新增 Pinned 模块 JSX**

在现有三个 `rightModule` 之后追加：

```tsx
<div className={styles.rightModule}>
  <div className={styles.moduleTitle}>
    <span>📌</span>
    <span>Pinned</span>
  </div>
  {pinnedMessages.length === 0 ? (
    <div className={styles.emptyText}>暂无置顶消息</div>
  ) : (
    <div className={styles.pinnedList}>
      {pinnedMessages.map((p) => (
        <div key={`${p.speaker}:${p.timestamp}`} className={styles.pinnedItem}>
          <div className={styles.pinnedContent}>
            <span className={styles.pinnedSpeaker}>{p.speaker}</span>
            <span className={styles.pinnedText}>{p.content}</span>
          </div>
          <button
            className={styles.pinnedRemove}
            onClick={() => unpin(p.speaker, p.timestamp)}
            title="取消置顶"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )}
</div>
```

- [ ] **Step 4: RightSidebar.module.css - 新增 pinned 模块样式**

```css
.pinnedList {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pinnedItem {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  transition: background 0.15s ease;
}

.pinnedItem:hover {
  background: var(--bg-hover);
}

.pinnedContent {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.pinnedSpeaker {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.pinnedText {
  font-size: 12px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pinnedRemove {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-secondary);
  padding: 2px 4px;
  border-radius: 4px;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.pinnedItem:hover .pinnedRemove {
  opacity: 1;
}

.pinnedRemove:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}
```

- [ ] **Step 5: 验证右侧栏效果**

Run: `cd D:\desktop\软件开发\agents-hub\frontend && npm run dev`
打开右侧栏，pin 一条消息后确认出现在 Pinned 模块中，点击 × 可取消。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/layouts/RightSidebar/RightSidebar.tsx frontend/src/layouts/RightSidebar/RightSidebar.module.css
git commit -m "feat: add pinned messages module to right sidebar"
```

---

### Task 9: 端到端验证

- [ ] **Step 1: 启动后端**

Run: `cd D:\desktop\软件开发\agents-hub && python -m agents_hub`
确认服务启动无报错。

- [ ] **Step 2: 启动前端**

Run: `cd D:\desktop\软件开发\agents-hub\frontend && npm run dev`
确认前端启动无报错。

- [ ] **Step 3: 手动测试完整流程**

1. 打开一个群聊
2. hover 任意消息气泡 → 确认底部出现 pin 按钮
3. 点击 pin 按钮 → 确认按钮高亮
4. 打开右侧栏 → 确认 Pinned 模块出现该消息
5. hover 已 pin 消息 → 确认 pin 按钮高亮
6. 点击高亮 pin 按钮 → 确认取消 pin
7. 右侧栏确认该消息消失
8. 再次 pin 一条消息 → 在右侧栏点击 × → 确认取消

- [ ] **Step 4: 验证 pins.json 持久化**

找到 `local_data/teams/<project>/<chat_id>/pins.json`，确认文件存在且内容正确。

- [ ] **Step 5: 最终 Commit**

```bash
git add -A
git commit -m "feat: complete pinned messages feature"
```
