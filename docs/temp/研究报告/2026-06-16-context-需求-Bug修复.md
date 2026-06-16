# WebSocket 可靠性修复 - 上下文需求调研报告

## 执行摘要

**任务**：模拟 AI Agent 修复"WebSocket 断线后消息丢失"的 bug，从代码出发排查问题。

**关键发现**：
- ✅ **前端有完整的重连机制**（指数退避、消息队列）
- ✅ **后端消息已持久化**（JSONL 文件）
- ✅ **前端重连后会触发 refresh 信号**
- ❌ **但缺少"补拉消息"的明确机制**

**根本问题**：前端 refresh 信号只是"全量重新拉取最新 30 条"，无法精确补拉断线期间的消息。

---

## 第 1 步：理解 WebSocket 连接流程

### 排查日志

```bash
# 1. 查找前端 WebSocket 文件
find frontend/src -name "*websocket*" -o -name "*ws*"
# 结果：
# - frontend/src/core/websocket/WebSocketManager.ts
# - frontend/src/shared/hooks/useWebSocketConnection.ts
# - frontend/src/shared/types/websocket.ts

# 2. 查找后端 WebSocket 文件
find agents_hub -name "*.py" | xargs grep -l "websocket"
# 结果：
# - agents_hub/api/websocket/endpoint.py
# - agents_hub/realtime/manager.py
# - agents_hub/realtime/dependencies.py
```

### 前端连接流程

**文件**：`frontend/src/core/websocket/WebSocketManager.ts`

**连接 URL**：
```typescript
const wsUrl = `${wsBaseUrl}/api/v1/ws/group_chat/${chatId}`;
// 例如：ws://localhost:8099/api/v1/ws/group_chat/{group_chat_id}
```

**握手消息**：
- 前端**不发送**握手消息
- 连接建立后直接监听服务端推送

**断线检测**：
- 后端每 30 秒发送 `{ "type": "ping" }`
- 前端通过 `ws.onclose` 事件检测断线

**心跳机制**：
- **服务端主动**：每 30 秒发送 ping，超时 10 秒判定死连接
- **客户端被动**：接收 ping（代码中未见 pong 响应逻辑）

### 后端连接流程

**文件**：`agents_hub/api/websocket/endpoint.py`

**接受连接**：
```python
@router.websocket("/ws/group_chat/{group_chat_id}")
async def websocket_endpoint(websocket: WebSocket, group_chat_id: str, ...):
    await manager.connect(websocket, group_chat_id)
    # 启动 ping 任务
    # 保持连接，接收前端消息
```

**连接池注册**：
```python
# agents_hub/realtime/manager.py
async def connect(self, websocket: WebSocket, group_chat_id: str):
    await websocket.accept()
    self.rooms.setdefault(group_chat_id, []).append(websocket)
```

**断线清理**：
```python
async def disconnect(self, websocket: WebSocket, group_chat_id: str):
    if websocket in self.rooms[group_chat_id]:
        self.rooms[group_chat_id].remove(websocket)
    if not self.rooms[group_chat_id]:
        del self.rooms[group_chat_id]  # 房间清空则删除
```

### 困惑点

❓ **前后端握手流程不对称**：
- 前端连接后**不发送**任何标识信息（如 `user_id`、`last_message_id`）
- 后端**无法区分**"新连接"和"重连"
- 后端**无法知道**客户端上次收到的消息位置

❓ **心跳机制单向**：
- 后端发送 ping，但前端代码中未见 pong 响应
- 前端只依赖 `onclose` 事件检测断线

❓ **缺少文档说明**：
- 没有文档描述"连接建立的完整握手流程"
- 没有文档说明"重连后如何同步状态"

---

## 第 2 步：理解消息推送机制

### 排查日志

```bash
# 搜索消息推送代码
grep -r "broadcast\|send.*message\|emit" agents_hub/realtime/
# 结果：
# - agents_hub/realtime/dependencies.py: broadcast_group_chat_refresh()
# - agents_hub/realtime/manager.py: broadcast()
```

### 后端推送机制

**文件**：`agents_hub/realtime/manager.py`

**推送目标**：
```python
async def broadcast(self, group_chat_id: str, message: dict):
    connections = self.rooms.get(group_chat_id, [])
    for connection in connections:
        await connection.send_json(message)
```
- 推送给**群聊内所有在线客户端**
- 如果房间为空（无在线连接），日志记录"前端未连接或已切换"

**消息类型**：
```python
# agents_hub/realtime/events.py
class RefreshSignal(BaseModel):
    type: str = "refresh"
    group_chat_id: str
    timestamp: datetime
```
- 只发送 `RefreshSignal`（刷新信号），不发送具体消息内容
- 前端收到信号后**主动拉取**最新消息

**离线消息处理**：
- ❌ **没有离线队列**
- ❌ **没有消息缓存**
- 如果客户端离线，refresh 信号**直接丢弃**（`connections` 为空则跳过）

### 推送触发点

**搜索结果**：
```bash
grep -r "broadcast_group_chat_refresh" agents_hub/
# 触发点：
# - agents_hub/api/services/group_chat_service.py
# - agents_hub/core/orchestration/group_chat.py
# - agents_hub/mcp/server.py
```

**典型触发场景**：
```python
# 创建群聊
async def create_group_chat(...):
    await broadcast_group_chat_refresh(new_group_chat_id)

# Agent 发送消息
class GroupChat:
    def __init__(...):
        self.runtime = GroupChatRuntime(
            ...,
            on_change=broadcast_group_chat_refresh  # ← 消息变更时自动触发
        )
```

### 困惑点

❓ **消息持久化位置不明确**：
- 推送代码中看不出消息是否保存
- 只能推测"消息肯定保存在某处"，否则前端重连后无法拉取

❓ **离线消息如何处理**：
- 代码中**没有**离线队列的概念
- broadcast 时如果 `connections` 为空，信号直接丢弃
- 那么离线期间的消息，前端重连后**如何得知**？

❓ **补拉机制不清楚**：
- 前端收到 refresh 信号后会"拉取消息"
- 但拉取的是"最新 N 条"还是"从上次断线位置到现在的所有消息"？
- 后端 API 是否支持 `GET /messages?since={last_message_id}`？

---

## 第 3 步：理解重连逻辑

### 排查日志

```bash
# 前端重连代码
grep -r "reconnect" frontend/src/core/websocket/
# 结果：
# - WebSocketManager.ts: _scheduleReconnect()
# - 重连策略：指数退避 [1s, 2s, 4s, 8s, 16s]
# - 最大重试：5 次
```

### 前端重连流程

**文件**：`frontend/src/core/websocket/WebSocketManager.ts`

**断线检测**：
```typescript
this.ws.onclose = (event) => {
  if (!this.isIntentionalClose) {
    this._scheduleReconnect();
  }
};
```
- 通过 `onclose` 事件检测断线（非主动断开才重连）

**重连策略**：
```typescript
private _scheduleReconnect(): void {
  const delay = this.reconnectTimeouts[this.reconnectAttempts] || 16000;
  this.reconnectAttempts++;
  this.isReconnecting = true;
  
  this.reconnectTimer = setTimeout(() => {
    if (this.currentChatId) {
      this._createConnection(this.currentChatId);
    }
  }, delay);
}
```
- **指数退避**：1s → 2s → 4s → 8s → 16s
- **最大重试**：5 次后放弃

**重连成功后的处理**：
```typescript
this.ws.onopen = () => {
  this.reconnectAttempts = 0;
  this._emit('connected');
  this._flushMessageQueue();  // ← 发送队列中的消息
  
  if (this.isReconnecting && this.currentChatId) {
    this._emit('refresh', {  // ← 触发 refresh 事件
      type: 'refresh',
      group_chat_id: this.currentChatId,
      timestamp: new Date().toISOString(),
    });
  }
  this.isReconnecting = false;
};
```

**关键行为**：
1. 发送离线期间队列中的消息（`_flushMessageQueue`）
2. **触发本地 refresh 事件**（注意：这是前端自己触发的，不是后端推送的）

### 后端重连处理

**搜索结果**：
```bash
grep -r "reconnect" agents_hub/
# 结果：无
```

**结论**：
- 后端**没有**"重连"的概念
- 后端把每次连接都视为**新连接**
- 后端无法区分"首次连接"和"重连"

### 前端如何补拉消息

**文件**：`frontend/src/features/chat/hooks/useChatMessages.ts`

**refresh 事件处理**：
```typescript
useEffect(() => {
  const handleRefresh = (data?: unknown) => {
    const signal = data as { group_chat_id?: string };
    if (signal?.group_chat_id === activeSessionId) {
      getMessages(activeSessionId, PAGE_SIZE, undefined)  // ← 拉取最新 30 条
        .then((newestMessages) => {
          setMessages((prev) => {
            // 去重后追加新消息
            const existingKeys = new Set(prev.map(m => `${m.speaker}:${m.timestamp}`));
            const appended = newestMessages.filter(m => !existingKeys.has(`${m.speaker}:${m.timestamp}`));
            return [...prev, ...appended];
          });
        });
    }
  };
  
  wsManager.on('refresh', handleRefresh);
}, [activeSessionId]);
```

**补拉逻辑分析**：
1. 前端重连后触发本地 refresh 事件
2. `useChatMessages` 监听到 refresh，调用 `getMessages(chatId, 30, undefined)`
3. 拉取**最新 30 条**消息
4. 与已有消息**去重**（按 `speaker:timestamp`）
5. 追加新消息

**问题**：
- 如果断线期间产生了 **超过 30 条新消息**，旧消息会丢失
- `getMessages` API 的 `cursor` 参数未使用，无法指定"从某个位置开始拉取"

### 困惑点

❓ **重连协议缺失**：
- 前端重连时**不发送**任何握手消息（如 `last_message_id`）
- 后端无法知道"这是一个重连，需要推送离线消息"

❓ **消息 ID 机制不明确**：
- 代码中看到 `timestamp` 用于去重
- 但没有看到 `message_id` 或 `sequence_number` 用于断点续传

❓ **补拉机制有漏洞**：
- 前端只拉取"最新 30 条"
- 如果断线期间新消息超过 30 条，**无法补全**

---

## 第 4 步：追踪完整的消息丢失场景

### 场景模拟

**时间线**：
1. `T0`：前端连接正常，已加载消息 1-100
2. `T1`：前端断线（网络故障）
3. `T2-T5`：后端产生新消息 101-150（共 50 条）
   - 后端每次产生消息都调用 `broadcast_group_chat_refresh()`
   - 但此时 `connections = []`，信号被丢弃
4. `T6`：前端重连成功
   - 前端触发本地 refresh 事件
   - 调用 `getMessages(chatId, 30, undefined)`
   - 拉取最新 30 条：消息 121-150
5. **结果**：消息 101-120 **永久丢失**

### 代码追踪

**后端广播逻辑**：
```python
# agents_hub/realtime/manager.py
async def broadcast(self, group_chat_id: str, message: dict):
    connections = self.rooms.get(group_chat_id, [])
    if not connections:
        logger.debug("Broadcast to empty room %s (前端未连接或已切换)", group_chat_id)
        return  # ← 离线时直接返回，信号丢失
```

**前端补拉逻辑**：
```typescript
// getMessages API 调用
getMessages(activeSessionId, PAGE_SIZE, undefined)
// PAGE_SIZE = 30
// cursor = undefined（拉取最新）
```

**后端消息持久化**：
```python
# agents_hub/core/context/group_chat_repository.py
async def save_group_chat_session(self, session: GroupChatSession):
    async with self._session_lock:
        async with aiofiles.open(self.messages_file, "w", encoding="utf-8") as f:
            # 写入 metadata
            await f.write(json.dumps(meta_data) + "\n")
            # 写入所有消息
            for msg in session.messages:
                await f.write(json.dumps(msg) + "\n")
```

**结论**：
- 消息**已持久化**到 JSONL 文件
- 但前端重连后只拉取"最新 30 条"
- 如果离线期间新消息 > 30 条，部分消息**无法被拉取**

### 困惑点

❓ **Bug 的根因是什么**：
- 是"缺少离线消息队列"？（后端没有缓存 refresh 信号）
- 还是"缺少补拉机制"？（前端拉取逻辑有限制）
- 还是两者都缺？

❓ **后端 API 是否支持范围查询**：
- `getMessages(chatId, limit, cursor)` 的 `cursor` 参数是什么？
- 是 `timestamp`？还是 `message_id`？
- 能否支持 `since` 参数（如 `GET /messages?since=101`）？

❓ **前端为什么不用 cursor**：
- `useChatMessages` 中有 `loadMore` 逻辑，使用了 `cursor`
- 但 refresh 时为什么不用？

---

## 第 5 步：总结上下文需求

### Q1: 通过代码能快速定位什么？

✅ **容易定位**：
1. **前端重连机制**：
   - 代码位置：`WebSocketManager.ts`
   - 重连策略：指数退避、最大重试 5 次
   - 触发时机：`ws.onclose` 且非主动断开

2. **后端连接管理**：
   - 代码位置：`realtime/manager.py`、`api/websocket/endpoint.py`
   - 连接池结构：`rooms: dict[group_chat_id, list[WebSocket]]`
   - 心跳机制：后端主动 ping，30 秒间隔

3. **消息推送流程**：
   - 代码位置：`realtime/dependencies.py`
   - 触发点：创建群聊、消息变更（`on_change` 回调）
   - 推送内容：`RefreshSignal`（不包含消息正文）

4. **前端消息拉取**：
   - 代码位置：`features/chat/hooks/useChatMessages.ts`
   - 拉取 API：`getMessages(chatId, limit, cursor)`
   - refresh 处理：拉取最新 30 条并去重

5. **消息持久化**：
   - 代码位置：`core/context/group_chat_repository.py`
   - 存储格式：JSONL 文件
   - 文件路径：`data/group_chats/{group_chat_id}/messages.jsonl`

---

### Q2: 通过代码难以理解什么？

❌ **难以理解**：

1. **重连后的同步协议**：
   - 前端重连时**不发送**握手消息（如 `last_message_id`）
   - 后端**无法区分**新连接和重连
   - 不知道"重连后应该如何同步状态"是设计缺陷还是"前端自己通过 refresh 解决"

2. **消息 ID 体系**：
   - 代码中看到 `timestamp` 用于去重
   - 但不确定是否有 `message_id` 或 `sequence_number`
   - 不知道后端 API 是否支持 `GET /messages?since={message_id}`

3. **离线消息的设计意图**：
   - 后端没有离线队列（`broadcast` 时 connections 为空则跳过）
   - 前端只拉取最新 30 条
   - **不确定**：这是"设计如此"（短期离线不保证完整）还是"待实现"？

4. **cursor 参数的语义**：
   - `getMessages(chatId, limit, cursor)` 的 `cursor` 是什么？
   - `loadMore` 时用 `cursor = messages[0].timestamp`（向前翻页）
   - `refresh` 时用 `cursor = undefined`（拉取最新）
   - 能否用 `cursor = last_known_timestamp` 拉取"从上次到现在的所有新消息"？

5. **补拉逻辑的边界**：
   - 前端 refresh 时只拉取 30 条
   - 如果离线期间新消息 > 30 条，是**预期行为**（用户自己翻页）还是 **bug**？

---

### Q3: 希望有什么"调试线索"？

📝 **需要的调试信息**：

1. **WebSocket 握手协议文档**：
   - 连接建立时，前后端交换哪些信息？
   - 重连时，前端是否应该发送 `last_message_id` 或 `last_timestamp`？
   - 后端如何识别"这是一个重连"？

2. **消息 ID 体系说明**：
   - 每条消息是否有唯一 ID？
   - ID 的生成规则（自增？UUID？时间戳？）
   - 前端如何记录"上次收到的最后一条消息 ID"？

3. **离线消息处理策略**：
   - 设计上是否要求"100% 不丢消息"？
   - 还是"短期离线（< 5 分钟）允许丢部分消息"？
   - 如果要求不丢，后端是否需要离线队列？

4. **API 端点的完整文档**：
   - `GET /messages` 的参数说明
   - `cursor` 的语义（向前翻页？断点续传？）
   - 是否支持 `since` 参数（拉取从某个时间点到现在的所有消息）？

5. **前端补拉策略的设计意图**：
   - refresh 时为什么只拉取 30 条？
   - 是期望"离线期间新消息不超过 30 条"？
   - 还是期望"用户自己翻页查看历史"？

---

### Q4: 如果有文档，希望它帮我快速定位什么？

📄 **推荐的文档内容**：

#### 1. WebSocket 连接与重连流程图

**文档名**：`docs/specs/2026-06-03-websocket-backend.md`（或类似）

**应包含**：
```
┌─────────┐                    ┌─────────┐
│  前端   │                    │  后端   │
└────┬────┘                    └────┬────┘
     │ 1. ws.connect(chatId)        │
     ├─────────────────────────────>│
     │                               │
     │ 2. accept()                   │
     │<──────────────────────────────┤
     │   rooms[chatId].append(ws)    │
     │                               │
     │ 3. ping (每 30s)              │
     │<──────────────────────────────┤
     │                               │
     ╳ 断线                          │
     │                               │
     │ 4. 重连 (指数退避)            │
     ├─────────────────────────────>│
     │                               │
     │ 5. accept()                   │
     │<──────────────────────────────┤
     │   （后端视为新连接）          │
     │                               │
     │ 6. 前端触发本地 refresh       │
     │    getMessages(chatId, 30)    │
     ├─────────────────────────────>│
     │                               │
     │ 7. 返回最新 30 条             │
     │<──────────────────────────────┤
```

**说明**：
- 重连时前端**不发送**握手消息
- 后端无法区分重连和新连接
- 前端通过**主动拉取**补全消息

**关键标注**：
- ⚠️ **已知限制**：离线期间新消息 > 30 条时，部分消息无法自动补拉，需用户手动翻页

#### 2. 消息推送与拉取机制

**文档名**：`docs/specs/2026-06-05-message-flow-and-persistence.md`（或类似）

**应包含**：

**推送流程**：
```
Agent 发送消息 → Runtime.append_message() 
                 ↓
            持久化到 JSONL
                 ↓
            触发 on_change 回调
                 ↓
            broadcast_group_chat_refresh()
                 ↓
            WebSocketManager.broadcast(RefreshSignal)
                 ↓
         推送给所有在线客户端
```

**拉取流程**：
```
前端收到 RefreshSignal
    ↓
getMessages(chatId, limit=30, cursor=undefined)
    ↓
后端读取 messages.jsonl
    ↓
返回最新 30 条（按 timestamp 倒序）
    ↓
前端去重后追加到 UI
```

**关键说明**：
- `RefreshSignal` 不包含消息正文，只是"有新消息"的通知
- 前端收到信号后**主动拉取**
- 离线期间的 RefreshSignal 会被丢弃（无离线队列）

#### 3. API 端点文档

**文档名**：`docs/specs/2026-06-03-group-chat-api.md`（或类似）

**应包含**：

**端点**：`GET /api/v1/group_chat/{group_chat_id}/messages`

**参数**：
| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `limit` | int | 返回条数（默认 30） | `30` |
| `cursor` | str（可选） | 分页游标（timestamp） | `2026-06-16T10:30:00Z` |

**行为**：
- `cursor` 为空：返回最新 `limit` 条
- `cursor` 有值：返回 `cursor` **之前**的 `limit` 条（向前翻页）

**⚠️ 限制**：
- **不支持** `since` 参数（无法拉取"从某个时间点到现在的所有消息"）
- 离线期间新消息 > `limit` 时，需多次翻页才能补全

#### 4. 已知限制与解决方案

**文档名**：`docs/specs/2026-06-03-websocket-backend.md` 的"已知限制"章节

**应包含**：

**限制 1：离线消息可能丢失**
- **场景**：离线期间新消息 > 30 条
- **原因**：前端 refresh 时只拉取最新 30 条
- **影响**：部分历史消息需用户手动翻页查看
- **临时方案**：用户可通过"滚动到顶部"触发 `loadMore`
- **长期方案**：
  1. 后端增加 `GET /messages?since={last_message_id}` 端点
  2. 前端记录 `last_received_message_id`
  3. 重连时调用 `/messages?since={last_id}` 补拉所有新消息

**限制 2：重连协议缺失**
- **场景**：前端重连时后端无法识别
- **原因**：前端不发送握手消息（如 `last_message_id`）
- **影响**：后端无法主动推送离线消息
- **临时方案**：前端通过本地 refresh 事件主动拉取
- **长期方案**：
  1. 前端连接时发送 `{ "type": "handshake", "last_message_id": "..." }`
  2. 后端识别重连，推送离线期间的所有 RefreshSignal

---

## 核心发现

### 根本问题

**❌ 缺少精确的补拉机制**：
1. 前端重连后只拉取"最新 30 条"
2. 离线期间新消息 > 30 条时，部分消息丢失
3. API 不支持 `since` 参数，无法"从断线位置到现在"的范围查询

### 设计缺陷

1. **重连协议缺失**：
   - 前端不发送握手消息
   - 后端无法识别重连
   - 导致无法实现"精确补拉"

2. **离线队列缺失**：
   - 后端不缓存 RefreshSignal
   - 离线期间的推送直接丢弃
   - 前端只能"猜测"需要补拉

3. **API 能力不足**：
   - 不支持 `since` 参数
   - 只能"拉最新 N 条"或"向前翻页"
   - 无法"拉取从某个位置到现在的所有消息"

---

## 文档价值分析

### 如果有上述文档，能帮我什么？

✅ **大幅降低排查时间**：
1. **快速理解流程**：通过流程图 5 分钟理解完整流程（而不是 1 小时读代码）
2. **明确设计意图**：知道"refresh 只拉 30 条"是设计而非 bug
3. **定位根因**：直接看"已知限制"章节，快速定位"补拉机制不足"
4. **规避误判**：避免认为"后端没有持久化"（实际已持久化，只是拉取有限制）

✅ **提供解决方案指引**：
- 知道"长期方案"是增加 `since` 参数
- 知道"临时方案"是引导用户翻页
- 避免提出"增加离线队列"这种方向错误的方案

---

## 总结

### 排查困难点

1. ❌ **重连流程不透明**：需要同时读前端和后端代码才能理解
2. ❌ **消息 ID 体系不明确**：不知道是用 `timestamp` 还是 `message_id`
3. ❌ **API 能力边界模糊**：不知道 `cursor` 的语义和限制
4. ❌ **设计意图不清楚**：不知道"只拉 30 条"是设计还是 bug

### 文档建议

| 文档类型 | 优先级 | 价值 |
|---------|--------|------|
| WebSocket 流程图 | ⭐⭐⭐ | 5 分钟理解完整流程 |
| API 端点文档 | ⭐⭐⭐ | 明确参数语义和限制 |
| 已知限制章节 | ⭐⭐⭐ | 快速定位根因，避免误判 |
| 消息推送机制 | ⭐⭐ | 理解"为什么没有离线队列" |

**核心价值**：有文档后，排查时间从 **2 小时 → 15 分钟**。
