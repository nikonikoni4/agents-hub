# Pinned Messages 详细设计

> 外部接口确认 > 内部实现。本文档穷举所有接口边界和细节，内部实现方式由实现者决定。

---

## 1. 总览

在群聊中支持消息置顶功能。用户通过 hover 消息气泡底部的 pin 按钮将消息置顶，已置顶消息展示在右侧栏 Pinned 模块中，支持取消置顶。

**消息标识**：使用 `(speaker, timestamp)` 复合键，不新增消息 ID 字段。

---

## 2. 后端 API 契约

### 2.1 获取已置顶消息列表

```
GET /api/v1/group-chats/{group_chat_id}/pinned-messages
```

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| group_chat_id | str | 群聊 ID |

**请求体**：无

**成功响应 200**：

```json
[
  {
    "speaker": "pm",
    "content": "我们决定采用方案 A",
    "timestamp": "2026-06-06T10:30:00Z",
    "platform": "cli",
    "pinned_at": "2026-06-06T10:35:00Z"
  },
  {
    "speaker": "architect",
    "content": "数据库表结构已确认...",
    "timestamp": "2026-06-06T10:32:00Z",
    "platform": "cli",
    "pinned_at": "2026-06-06T10:36:00Z"
  }
]
```

**响应字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| speaker | str | 消息发送者名称 |
| content | str | 消息完整内容（不截断） |
| timestamp | str | 消息原始时间戳 |
| platform | str | 消息来源平台 |
| pinned_at | str | 置顶操作的时间 |

**排序规则**：按 `pinned_at` 升序（最早 pin 的排最前）。

**错误响应**：

| 状态码 | 场景 | 响应体 |
|--------|------|--------|
| 404 | group_chat_id 不存在 | `{ "error_code": "NOT_FOUND", "message": "Group chat not found" }` |
| 500 | 服务器内部错误 | `{ "error_code": "INTERNAL_ERROR", "message": "..." }` |

---

### 2.2 置顶一条消息

```
POST /api/v1/group-chats/{group_chat_id}/pinned-messages
```

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| group_chat_id | str | 群聊 ID |

**请求体**：

```json
{
  "speaker": "pm",
  "timestamp": "2026-06-06T10:30:00Z"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| speaker | str | 是 | 消息发送者名称 |
| timestamp | str | 是 | 消息时间戳（ISO 8601） |

**成功响应 200**：

```json
{
  "ok": true
}
```

**幂等性**：重复 pin 同一条消息返回 200（不报错），行为等同于成功。

**副作用**：后端在 pin 时保存消息内容快照（speaker + content + timestamp + platform + pinned_at），供 GET 接口直接返回。这样即使原消息后续被清理，pin 记录仍可独立展示。

**错误响应**：

| 状态码 | 场景 | 响应体 |
|--------|------|--------|
| 400 | 请求体字段缺失或格式错误 | `{ "error_code": "VALIDATION_ERROR", "message": "..." }` |
| 404 | group_chat_id 不存在 | `{ "error_code": "NOT_FOUND", "message": "Group chat not found" }` |
| 422 | 指定的消息在群聊历史中不存在 | `{ "error_code": "MESSAGE_NOT_FOUND", "message": "..." }` |
| 500 | 服务器内部错误 | `{ "error_code": "INTERNAL_ERROR", "message": "..." }` |

---

### 2.3 取消置顶一条消息

```
DELETE /api/v1/group-chats/{group_chat_id}/pinned-messages?speaker={speaker}&timestamp={timestamp}
```

> 使用 query params 而非 request body，因为部分 HTTP 客户端对 DELETE 搭配 body 支持不佳。

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| group_chat_id | str | 群聊 ID |

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| speaker | str | 是 | 消息发送者名称 |
| timestamp | str | 是 | 消息时间戳（ISO 8601，需 URL encode） |

**成功响应 200**：

```json
{
  "ok": true
}
```

**幂等性**：对未 pin 的消息执行 unpin 返回 200（不报错）。

**错误响应**：

| 状态码 | 场景 | 响应体 |
|--------|------|--------|
| 400 | 请求体字段缺失或格式错误 | `{ "error_code": "VALIDATION_ERROR", "message": "..." }` |
| 404 | group_chat_id 不存在 | `{ "error_code": "NOT_FOUND", "message": "Group chat not found" }` |
| 500 | 服务器内部错误 | `{ "error_code": "INTERNAL_ERROR", "message": "..." }` |

> 注意：DELETE 取消 pin 时**不要求消息存在于群聊历史中**（消息可能已被清理，但 pin 记录还在）。只要 pin 记录存在就删除，不存在就幂等返回 ok。

---

### 2.4 Schema 定义

#### 后端 Pydantic 模型

```python
# --- 请求 Schema ---

class PinMessageRequest(BaseModel):
    """POST /pinned-messages 请求体"""
    speaker: str = Field(..., min_length=1, description="消息发送者名称")
    timestamp: str = Field(..., description="消息时间戳（ISO 8601）")

# --- 响应 Schema ---

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

# --- 错误响应 Schema ---

class PinErrorResponse(BaseModel):
    """所有错误响应的统一格式"""
    error_code: str = Field(..., description="错误码：VALIDATION_ERROR | NOT_FOUND | MESSAGE_NOT_FOUND | INTERNAL_ERROR")
    message: str = Field(..., description="人类可读的错误描述")
```

**字段约束**：

| Schema | 字段 | 类型 | 约束 | 说明 |
|--------|------|------|------|------|
| PinMessageRequest | speaker | str | min_length=1 | 非空字符串 |
| PinMessageRequest | timestamp | str | ISO 8601 格式 | 如 `2026-06-06T10:30:00Z` |
| PinnedMessageInfo | speaker | str | — | 从消息快照读取 |
| PinnedMessageInfo | content | str | — | pin 时保存的完整内容 |
| PinnedMessageInfo | timestamp | str | — | 消息原始时间戳 |
| PinnedMessageInfo | platform | str | — | 消息来源平台 |
| PinnedMessageInfo | pinned_at | str | — | 后端生成的置顶时间 |
| PinOperationResponse | ok | bool | default=True | 固定返回 true |
| PinErrorResponse | error_code | str | 枚举值 | 见上表 |
| PinErrorResponse | message | str | — | 错误详情 |

---

### 2.5 端点汇总

| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| GET | `.../pinned-messages` | 无 | `PinnedMessageInfo[]` | 按 pinned_at 升序 |
| POST | `.../pinned-messages` | `PinMessageRequest` | `PinOperationResponse` | 幂等 |
| DELETE | `.../pinned-messages?speaker=&timestamp=` | query params | `PinOperationResponse` | 幂等 |

---

### 2.6 持久化方案

**SSOT（Single Source of Truth）**：`pins.json` 文件是 pin 数据的唯一数据来源。所有读写操作都直接作用于该文件，**不在 Service 内存中缓存 pin 状态**。

- 每次 GET 请求：从 `pins.json` 读取 → 返回
- 每次 POST/DELETE 请求：从 `pins.json` 读取 → 修改 → 写回 `pins.json`

**存储位置**：

```
local_data/teams/<sanitized_project_path>/<group_chat_id>/pins.json
```

与群聊其他数据文件（`<id>.jsonl`、`group_metadata.json` 等）同级目录。

**存储格式**：

```json
[
  {
    "speaker": "pm",
    "content": "我们决定采用方案 A",
    "timestamp": "2026-06-06T10:30:00Z",
    "platform": "cli",
    "pinned_at": "2026-06-06T10:35:00Z"
  }
]
```

**文件不存在时**：视为空数组 `[]`（首次 pin 时创建文件）。

**并发控制**：使用 `asyncio.Lock` 保护读写。Pin 操作频率极低（用户偶尔点击一次），锁竞争几乎为零，但必须加锁防止并发写入导致数据丢失（两个请求同时读 → 各自修改 → 各自写回，后写覆盖先写）。

**与核心层的关系**：Pin 功能完全封装在 `GroupChatService` 层，不经过 `GroupChatRuntime`/`GroupChatContext`/`GroupChatRepository`。核心层零改动。

**群聊删除**：`shutil.rmtree` 删除整个群聊目录，`pins.json` 自然被清理，无需额外处理。

---

## 3. 前端 API 层

### 3.1 类型定义

在 `frontend/src/shared/types/api-schemas.ts` 中新增：

```typescript
/** GET /pinned-messages 响应列表项 */
export interface PinnedMessageInfo {
  /** 消息发送者名称 */
  speaker: string
  /** 消息完整内容（快照） */
  content: string
  /** 消息原始时间戳 */
  timestamp: string
  /** 消息来源平台 */
  platform: string
  /** 置顶操作时间 */
  pinned_at: string
}

/** POST /pinned-messages 请求体 */
export interface PinMessageRequest {
  /** 消息发送者名称 */
  speaker: string
  /** 消息时间戳（ISO 8601） */
  timestamp: string
}

/** POST/DELETE /pinned-messages 成功响应 */
export interface PinOperationResponse {
  /** 操作是否成功 */
  ok: boolean
}
```

### 3.2 函数签名

在 `frontend/src/shared/types/api-requests.ts` 中新增请求类型导出，在 `frontend/src/core/api/groupChatApi.ts` 中新增：

```typescript
/** 获取已置顶消息列表 */
function getPinnedMessages(chatId: string): Promise<PinnedMessageInfo[]>

/** 置顶一条消息 */
function pinMessage(chatId: string, data: PinMessageRequest): Promise<PinOperationResponse>

/** 取消置顶（data 作为 query params 传递） */
function unpinMessage(chatId: string, data: PinMessageRequest): Promise<PinOperationResponse>
```

遵循现有 `mockableRequest` 模式，提供 mock 数据用于开发。

---

## 4. 前端 Hook 层

### 4.1 usePinnedMessages

位置：`frontend/src/features/chat/hooks/usePinnedMessages.ts`

**职责**：管理当前群聊的 pinned 消息状态，提供 pin/unpin 操作。

**对外接口**：

```typescript
function usePinnedMessages(chatId: string | null): {
  pinnedMessages: PinnedMessageInfo[]
  isLoading: boolean
  pin: (speaker: string, timestamp: string) => Promise<void>
  unpin: (speaker: string, timestamp: string) => Promise<void>
  isPinned: (speaker: string, timestamp: string) => boolean
  refresh: () => Promise<void>
}
```

| 返回值 | 说明 |
|--------|------|
| pinnedMessages | 当前已置顶的消息列表 |
| isLoading | 是否正在加载 |
| pin | 置顶操作，调用后自动刷新列表 |
| unpin | 取消置顶，调用后自动刷新列表 |
| isPinned | 判断某条消息是否已置顶（O(1) 查找） |
| refresh | 手动刷新 pin 列表 |

**内部行为**：
- chatId 变化时重新拉取
- pin/unpin 操作完成后自动 refresh
- 通过 WebSocket RefreshSignal 触发 refresh（与其他数据同步）
- isPinned 内部用 `Set<`${speaker}:${timestamp}`>` 实现 O(1) 查找

---

## 5. 前端组件层

### 5.1 ChatArea 改动

**改动点**：`MessageBubble` 组件增加 hover 操作栏。

**交互规则**：

| 状态 | hover 时显示 | 按钮样式 | 点击行为 |
|------|-------------|----------|----------|
| 未 pin | pin 按钮 | 默认（灰色） | 执行 pin |
| 已 pin | pin 按钮 | 高亮（蓝色/实心） | 执行 unpin |

**布局规则**：
- 操作栏在消息气泡**下方**
- agent 消息：操作栏左对齐
- user 消息：操作栏右对齐
- 操作栏仅在 hover 时可见（`opacity: 0 → 1` 过渡）

**数据来源**：
- `usePinnedMessages` hook 提供 `isPinned` 和 `pin`/`unpin` 方法
- `isPinned(speaker, timestamp)` 决定按钮高亮状态

### 5.2 RightSidebar 改动

**新增模块**：Pinned 模块，遵循现有 `.rightModule` 卡片模式。

**模块结构**：

```
┌─────────────────────────┐
│ Pinned                  │  ← 标题
├─────────────────────────┤
│ 📌 pm: 我们决定采用方...  │  ×  ← pin 条目 + 取消按钮
│ 📌 architect: 数据库表... │  ×
│                         │
│ （空状态）                │
│ 暂无置顶消息              │
└─────────────────────────┘
```

**列表项内容**：
- 左侧：speaker 名称 + 内容截断（单行，超出省略）
- 右侧：取消 pin 按钮（× 图标）

**数据来源**：`usePinnedMessages` hook 的 `pinnedMessages` 和 `unpin`。

---

## 6. WebSocket 同步

Pin 操作完成后，后端广播 RefreshSignal：

```json
{
  "type": "refresh",
  "group_chat_id": "xxx",
  "timestamp": "2026-06-06T10:35:00Z"
}
```

前端收到 RefreshSignal 后，`usePinnedMessages` 自动 re-fetch pin 列表。

这是现有架构的通用模式，pin 功能复用即可，不需要新增事件类型。

---

## 7. 边界情况与规则

| 场景 | 行为 |
|------|------|
| 重复 pin 同一条消息 | 幂等，返回 200，不报错 |
| unpin 未 pin 的消息 | 幂等，返回 200，不报错 |
| 消息被 pin 后，原消息从历史中清除 | pin 记录保留，右侧栏仍显示。pin 时后端同时保存消息内容快照（content 字段），GET 返回的 content 取快照值 |
| 群聊被删除 | 级联删除所有 pin 记录 |
| 切换群聊 | pin 列表随 chatId 变化自动刷新 |
| 无 pin 消息 | 右侧栏显示"暂无置顶消息" |
| 同一秒同一人发两条消息 | timestamp 精度足够区分（ISO 8601 含毫秒），实际不会冲突 |

---

## 8. 不在范围内

- 点击 pin 消息跳转到原消息位置（后续迭代）
- 消息 ID 机制
- Pin 消息排序（固定按 pinned_at 升序）
- 批量 pin/unpin
- Pin 消息数量上限（当前不限制）
- Pin 消息的搜索/过滤
