# broadcast_group_chat_refresh 全链路问题审查

- updated_at: 2026-06-15
- 触发规则：后端发送 refresh 信号但前端有时不刷新；前端短时间内大批量重复请求
- 审查范围：后端所有 `broadcast_group_chat_refresh` 调用点 + 前端所有监听 refresh 的 hooks
- 置信度评分：由 Haiku agent 独立评分（0-100）

---

## 问题总览

| # | 问题 | 置信度 | 类型 | 修复难度 | 状态 |
|---|------|--------|------|----------|------|
| 1 | 双重广播 `_handle_fallback_close()` | 85 | DRY 违反 | 低 | 待修复 |
| 2 | N+1 广播 `add_members_to_group_chat()` | 85 | DRY 违反 | 低 | 待修复 |
| 3 | 请求风暴（10 并发 / 6 冗余） | 78 | 性能 | 中 | 待修复 |
| 4 | broadcast 并发不安全 | 75 | 并发 bug | 低 | 待修复 |
| 5 | 无心跳/死连接 | 75 | 健壮性 | 低 | 待修复 |
| 6 | 重连窗口期 refresh 丢失 | 75 | 可靠性 | 低 | 待修复 |
| 7 | 断连期间 refresh 丢失 | 65 | 可靠性 | 低 | 待修复 |
| 8 | handleRefresh 无 cancelled 标志 | 60 | 竞态 | 低 | 待修复 |
| 9 | useMembers Promise.all 竞态 | 40 | 竞态 | 低 | 待修复 |

---

## 问题 1：双重广播 — `base_agent.py:600`（85 分）

**问题描述：** `_handle_fallback_close()` 中 `update_agent_session(result)` 内部已通过 `_save_agent_members()` → `_notify_change()` 触发一次广播，之后 line 600 又显式调用 `await self.runtime._notify_change()` 再广播一次。同一数据状态变更被广播了 2 次。

**证据链：**
1. `base_agent.py:578`/`583`：调用 `self.runtime.update_agent_session(result)`
2. `group_chat_runtime.py:423`：`update_agent_session` 内部调用 `await self._save_agent_members()`
3. `group_chat_runtime.py:435`：`_save_agent_members` 末尾调用 `await self._notify_change()` — 第一次广播
4. `base_agent.py:600`：显式调用 `await self.runtime._notify_change()` — 第二次广播

**违反 CLAUDE.md：** DRY 原则 — `update_agent_session` 已包含保存+通知的完整语义，调用方不应再手动补通知。

**修复方案：** 移除 `base_agent.py:600` 的 `await self.runtime._notify_change()` 调用。

---

## 问题 2：N+1 广播 — `group_chat_service.py:1260`（85 分）

**问题描述：** `add_members_to_group_chat()` 中，每个 `add_member()` 内部调用 `save_agent_members()` 触发一次 `_notify_change()`（即广播），循环结束后外部又显式调用 `broadcast_group_chat_refresh()` 一次。添加 N 个成员 = N+1 次广播。

**证据：**
- `group_chat.py:323`：`add_member` → `runtime.save_agent_members()` → `_notify_change()`（每次）
- `group_chat_service.py:1260`：显式 `await broadcast_group_chat_refresh(group_chat.group_chat_id)`（最后一次）

**评分说明：** 最后一次广播可能有意为之（注释提到"初始化时启动平台打招呼，需要显式推送"），需确认是否可安全移除。

**修复方案：** 评估最后一次显式广播是否可移除，或改为仅在循环结束后广播一次。

---

## 问题 3：请求风暴 — 单个 refresh 触发 10 个并发请求（78 分）

**问题描述：** 前端收到一个 refresh 信号时，8 个 hooks 全部无条件触发 API 请求。由于 `useMembers` 和 `usePinnedMessages` 各有 2 个实例（ChatArea + RightSidebar），总计 10 个并发 HTTP 请求，其中 6 个完全冗余。

**请求数量明细：**

| Hook | 实例数 | 每实例请求数 | 总计 | 冗余数 |
|------|--------|-------------|------|--------|
| useChatMessages | 1 | 1 (`getMessages`) | 1 | 0 |
| useMembers | 2 | 2 (`getMembers` + `listRoles`) | 4 | 4 |
| usePinnedMessages | 2 | 1 (`getPinnedMessages`) | 2 | 2 |
| useAgentCalls | 1 | 1 (`getAgentCalls`) | 1 | 0 |
| useTasks | 1 | 1 (`getActiveTasks`) | 1 | 0 |
| useGroupChatMembers | 1 | 1 (`getMembers`) | 1 | 0 |
| **合计** | | | **10** | **6** |

**缺失的防护机制（全部不存在）：**
- 防抖 (debounce)、节流 (throttle)
- 请求去重 (dedup) — 无 React Query/SWR
- 请求取消 (AbortController) — API 层不支持 signal 参数
- 事件合并 — WebSocketManager 收一条发一条

**评分说明（78，未达 80）：** 核心发现被完全确认，归类为性能问题而非正确性 bug。

**修复方案：** WebSocketManager 层添加 refresh 事件 debounce（300ms）；合并重复 hooks 实例为单实例共享。

---

## 问题 4：broadcast 并发不安全 — `manager.py`（75 分）

**问题描述：** `WebSocketManager.broadcast()` 遍历 `self.rooms[group_chat_id]` 列表时，`await connection.send_json(message)` 会让出控制权。此时如果另一个协程调用 `disconnect()`，会修改同一列表对象。

**实际风险（评分 agent 修正）：**
- CPython 中 `remove()` 不抛 ValueError，但会导致**跳过元素**或**提前终止循环**
- 更严重：如果 `disconnect` 删除了最后一个连接并执行 `del self.rooms[group_chat_id]`，broadcast 结束后访问字典会抛 **KeyError**

**证据：**
- `manager.py:48`：拿到的是列表引用，不是副本
- `manager.py:56`：`await connection.send_json(message)` 是 await 点
- 整个类无 `asyncio.Lock` 或其他同步机制

**修复方案：** 遍历副本 `for connection in list(connections):`

---

## 问题 5：无心跳/死连接 — `endpoint.py`（75 分）

**问题描述：** WebSocket 端点接受连接后进入 `while True` 循环等待前端消息，但后端既不发送 ping 也不检测超时。客户端网络静默断开时，死连接会留在 `rooms` 中直到下次 `broadcast` 发送失败才被动清理。

**证据：**
- `endpoint.py:43-46`：注释说"接收前端消息（如心跳）"，但实际无心跳实现
- `group_chat.py:1046` 的 `_heartbeat_loop` 是 Agent 编排层心跳，与 WebSocket 连接健康无关

**修复方案：** 后端定期发送 WebSocket ping 或检测连接超时。

---

## 问题 6：重连窗口期 refresh 丢失 — `WebSocketManager.ts`（75 分）

**问题描述：** 前端 WebSocket 重连使用指数退避 `[1000, 2000, 4000, 8000, 16000]` ms（最长 31 秒累计），此期间后端发的所有 refresh 信号丢失。重连成功后 `onopen` 回调只重置 `reconnectAttempts` 和 `_flushMessageQueue()`（仅发送方向），**不主动拉取接收方向的最新数据**。

**证据：**
- `WebSocketManager.ts:234-254`：`_scheduleReconnect` 使用 `setTimeout`
- `WebSocketManager.ts:187-195`：`onopen` 回调无数据拉取逻辑
- `_emit('connected')` 被触发但**零个组件监听该事件**

**与问题 7 的关系：** 本质是同一问题的不同视角 — 问题 7 关注根因（断连），问题 6 关注具体时长（重连窗口）。

**修复方案：** `onopen` 回调中主动 `_emit('refresh', { group_chat_id: this._currentChatId })`。

---

## 问题 7：断连期间 refresh 信号丢失 — 全链路（65 分）

**问题描述：** WebSocket 断开期间后端发的 refresh 信号丢失。后端 `broadcast()` 发送失败时静默移除连接、丢弃消息，前端所有 8 个 refresh hooks 都是被动监听，重连后不补发。

**证据：**
- `manager.py:46-77`：broadcast 中 send_json 失败的连接被移除，消息丢弃，无重试
- `WebSocketManager.ts:234-254`：重连使用 setTimeout 延迟，期间无消息缓冲
- 8 个 hooks 全部只监听 `refresh` 事件，无组件监听 `connected` 事件

**评分说明（65）：** 问题确认存在，但窗口有限、手动刷新可用、非消息丢失（消息持久化在后端），单人场景不易触发。

**修复方案：** 同问题 6，重连后主动拉取。

---

## 问题 8：useChatMessages handleRefresh 无 cancelled 标志（60 分）

**问题描述：** `useChatMessages.ts` 初始加载（line 72）有 `let cancelled = false` 守卫，但 `handleRefresh`（line 99-116）完全没有。session 切换后旧请求返回可能将消息追加到新 session 的 state。

**证据：**
- line 72：初始加载有 `let cancelled = false`
- line 99-116：`handleRefresh` 中无 cancelled 检查
- `setMessages` 使用函数式更新 `setMessages((prev) => ...)`，基于当前 state 追加

**评分说明（60）：** `useEffect` cleanup 会在 `activeSessionId` 变化时移除旧监听器，覆盖大部分场景。实际触发需要精确时序窗口。

**修复方案：** 在 `handleRefresh` 中添加 `cancelled` 标志，与初始加载保持一致。

---

## 问题 9：useMembers Promise.all 竞态条件（40 分）

**问题描述：** `useMembers` 的 `fetchMembers` 使用 `Promise.all([getMembers, listRoles])` 但无取消机制。

**评分 agent 修正：** 原报告声称"第一次的 `listRoles` 可能先于第二次的 `getMembers` 返回导致数据混合"——**不可能发生**。`Promise.all` 内部两个 promise 始终一起解析。

**真实竞态（评分 agent 指出）：** 如果 `activeSessionId` 快速切换，第一次 `fetchMembers(session-A)` 的响应可能在第二次之后到达，导致 session-B 显示 session-A 的数据。这是经典的 stale closure / stale response 问题。

**评分说明（40）：** 缺少取消机制是真实的，但原报告触发场景在技术上不可能发生。

**修复方案：** 在 `useEffect` cleanup 中添加 `cancelled` 标志。

---

## 后端时序审查结论

**后端不会在数据还未完全保存时就发送 refresh 信号。** 所有 11 个调用点都遵循 "先 await 持久化，后 await 广播" 的正确顺序。没有 `create_task` 包裹，没有竞态条件。锁保护到位（`_state_lock`）。

额外发现：
- `agent_call_manager.py:341` 使用同步 `open()/f.write()` 写文件，在 async 上下文中阻塞事件循环（不影响正确性，影响并发性能）
