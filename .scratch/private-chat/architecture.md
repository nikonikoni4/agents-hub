# 架构约束：群聊 Agent 单独聊天（Private Chat）

## 1. 模块职责边界

### 涉及模块

| 模块 | 职责 | 层级 |
|------|------|------|
| `core/context/group_chat_session.py` | 新增 `in_private_chat` 状态到 `AgentMemberInfo.status` | context |
| `core/orchestration/group_chat.py` | 消息拦截（`send_message_to_agent`）、状态检查（stop/reset/compress） | orchestration |
| `api/routes/group_chat.py` | 新增 `start-private-chat` / `stop-private-chat` 路由 | API |
| `api/services/group_chat_service.py` | 新增私聊业务逻辑、Manager 限制检查 | API |
| `api/schemas/group_chats.py` | 新增私聊相关 Schema | API |
| `frontend/src/core/api/groupChatApi.ts` | 新增 `startPrivateChat` / `stopPrivateChat` API 函数 | 前端 core |
| `frontend/src/features/chat/hooks/useMembers.ts` | 新增 `startPrivateChat` / `stopPrivateChat` 方法 | 前端 features |
| `frontend/src/layouts/RightSidebar/RightSidebar.tsx` | `MemberItem` 下拉菜单新增"邀请单聊"选项 | 前端 layouts |
| `frontend/src/features/single-chat/components/SingleChatPanel.tsx` | X 按钮改为"退出单聊" | 前端 features |
| `frontend/src/layouts/RightSidebar/RightSidebar.tsx` | 新增 `in_private_chat` 状态显示 | 前端 layouts |
| `frontend/src/features/private-chat/store/privateChatStore.ts` | **新建**：私聊状态管理（计时器、关联群聊） | 前端 features |

### 边界约束

- `core/context` 层只负责数据结构定义（`AgentMemberInfo` 新增状态值），不涉及业务逻辑
- `core/orchestration` 层负责消息拦截和状态检查，不直接与前端通信
- `api` 层负责 HTTP 协议处理和业务编排，委托给 core 层执行
- 前端 `privateChatStore` 管理私聊特有的状态（计时器、关联群聊 ID），与 `singleChatStore` 分离
- `SingleChatPanel` 复用现有组件，只修改按钮行为，不改变核心消息流

## 2. 数据流方向

### 主要数据流

```
用户点击"邀请单聊"
  → RightSidebar MemberItem 下拉菜单
    → groupChatApi.startPrivateChat(group_chat_id, agent_name)
      → API Route: POST /{group_chat_id}/members/{agent_name}/start-private-chat
        → GroupChatService.start_private_chat()
          → GroupChat 状态检查（必须 idle）
          → agent_member_info.status = "in_private_chat"
          → WebSocket RefreshSignal 广播
          → 返回 {agent_name, status, main_session_id}
    → privateChatStore 设置活跃私聊
    → singleChatStore.openDraftChat（type='continue_group_chat'）
    → SingleChatPanel 显示（X 按钮改为"退出单聊"）

用户发送消息（私聊中）
  → SingleChatPanel → singleChat SSE API → Agent Bridge → Agent 执行
  → privateChatStore.resetTimer() 重置 3 分钟计时器

用户在群聊中向私聊 Agent 发消息
  → GroupChat.send_message_to_agent()
    → 检查 agent_info.status == "in_private_chat"
    → 创建自动回复 NOTIFICATION 消息
    → 写入群聊历史
    → return（不投递到 Agent 队列）

3 分钟超时
  → privateChatStore 定时器触发
    → groupChatApi.stopPrivateChat(group_chat_id, agent_name)
      → API Route: POST /{group_chat_id}/members/{agent_name}/stop-private-chat
        → GroupChatService.stop_private_chat()
          → agent_member_info.status = "idle"
          → WebSocket RefreshSignal 广播
    → privateChatStore 清除状态
    → SingleChatPanel 关闭
    → toast 提示"单聊已自动退出"
```

### 关键数据节点

- **节点1**：`AgentMemberInfo.status = "in_private_chat"` — 状态隔离的核心，影响消息路由和操作限制
- **节点2**：`send_message_to_agent` 拦截 — 群聊消息被拦截，返回自动回复
- **节点3**：`privateChatStore` — 前端计时器管理，控制 3 分钟超时
- **节点4**：`main_session_id` 透传 — 私聊复用 Agent 的主会话，保持对话连续性

## 3. 依赖关系

### 依赖方向

```
前端 privateChatStore
  → groupChatApi（API 调用）
    → GroupChatService（业务编排）
      → GroupChat（核心逻辑）
        → AgentMemberInfo（状态管理）
```

### 本任务的依赖

- **依赖模块**：
  - `core/context/group_chat_session.py` — `AgentMemberInfo` 数据结构
  - `core/orchestration/group_chat.py` — `send_message_to_agent`、`stop_member`、`reset_member`、`compress_agent_context`
  - `api/routes/group_chat.py` — 路由定义
  - `api/services/group_chat_service.py` — Service 层
  - `frontend/src/features/single-chat/` — SingleChatPanel、singleChatStore
  - `frontend/src/features/chat/` — useMembers
- `frontend/src/layouts/RightSidebar/` — MemberItem 下拉菜单

- **被依赖模块**：
  - 前端 RightSidebar（读取成员状态）
  - WebSocket 通知机制（RefreshSignal 广播）

## 4. 接口契约

### 新增 API 端点

**进入私聊**：

```
POST /api/v1/group-chats/{group_chat_id}/members/{agent_name}/start-private-chat

Response 200:
{
  "agent_name": str,
  "status": "in_private_chat",
  "main_session_id": str | null
}

Error 404: 群聊或 Agent 不存在
Error 403: Agent 是 Manager（禁止私聊）
Error 409: Agent 非 idle 状态（StateError）
```

**退出私聊**：

```
POST /api/v1/group-chats/{group_chat_id}/members/{agent_name}/stop-private-chat

Response 200:
{
  "agent_name": str,
  "status": "idle"
}

Error 404: 群聊或 Agent 不存在
Error 409: Agent 非 in_private_chat 状态（StateError）
```

### 修改的接口

**`send_message_to_agent`（消息拦截）**：

```python
# 在现有 stopped 检查之后，消息投递之前
if agent_info.status == "in_private_chat":
    auto_reply = AgentMessage(
        send_from=agent_name,
        send_to=message.send_from,
        content=f"当前{agent_name}正在与user进行单独聊天，无法处理当前的消息：{message.content[:20]}，请稍后再发送该任务",
        type=MessageType.NOTIFICATION
    )
    await self.group_chat_context.add_message(auto_reply)
    return
```

**`stop_member` / `reset_member`（操作限制）**：

```python
if agent_info.status == "in_private_chat":
    raise StateError(
        f"Agent {agent_name} 正在单聊中，无法停止/重置",
        details={"agent_name": agent_name, "current_status": "in_private_chat"}
    )
```

**`compress_agent_context`（压缩限制）**：

```python
if agent_info.status == "in_private_chat":
    raise StateError(
        f"Agent {agent_name} 正在单聊中，无法压缩上下文",
        details={"agent_name": agent_name, "current_status": "in_private_chat"}
    )
```

**`compress_all_agents`（全量压缩跳过）**：

```python
for agent in agents:
    if agent.status == "in_private_chat":
        results.append({"agent_name": agent.name, "status": "skipped", "reason": "in_private_chat"})
        continue
```

### 数据结构变更

**`AgentMemberInfo.status` 新增值**：

```python
# 现有值：idle, busy, stopped, error, in_loop
# 新增值：in_private_chat
status: str = "idle"  # idle/busy/stopped/error/in_loop/in_private_chat
```

### 前端新增 Store

**`privateChatStore`**：

```typescript
interface PrivateChatState {
  // 状态
  activeGroupChatId: string | null;  // 关联的群聊 ID
  activeAgentName: string | null;    // 私聊中的 Agent 名称
  lastActivityTime: number | null;   // 最后活动时间戳
  timerId: ReturnType<typeof setTimeout> | null;  // 计时器 ID

  // 方法
  startPrivateChat: (groupChatId: string, agentName: string) => void;
  stopPrivateChat: () => void;
  resetTimer: () => void;
  clearTimer: () => void;
}
```

## 5. 实现位置

### 代码位置

| 功能 | 文件路径 | 说明 |
|------|---------|------|
| 状态定义 | `agents_hub/core/context/group_chat_session.py:22` | `AgentMemberInfo.status` 新增 `in_private_chat` |
| 消息拦截 | `agents_hub/core/orchestration/group_chat.py:1059` | `send_message_to_agent` 方法中新增拦截逻辑 |
| 状态检查 | `agents_hub/core/orchestration/group_chat.py` | `stop_member`(L732)、`reset_member`(L925)、`compress_agent_context` |
| API 路由 | `agents_hub/api/routes/group_chat.py` | 新增 2 个路由端点 |
| Service 层 | `agents_hub/api/services/group_chat_service.py` | 新增 `start_private_chat`、`stop_private_chat` 方法 |
| Schema | `agents_hub/api/schemas/group_chats.py` | 新增 `PrivateChatResponse` Schema |
| 前端 API | `frontend/src/core/api/groupChatApi.ts` | 新增 `startPrivateChat`、`stopPrivateChat` 函数 |
| 前端 Store | `frontend/src/features/private-chat/store/privateChatStore.ts` | **新建** |
| 邀请单聊入口 | `frontend/src/layouts/RightSidebar/RightSidebar.tsx` | `MemberItem` 下拉菜单新增"邀请单聊"选项 |
| 单聊面板 | `frontend/src/features/single-chat/components/SingleChatPanel.tsx` | X 按钮改为"退出单聊" |
| 成员 Hook | `frontend/src/features/chat/hooks/useMembers.ts` | 新增 `startPrivateChat`、`stopPrivateChat` |
| 状态显示 | `frontend/src/layouts/RightSidebar/RightSidebar.tsx` | 新增 `in_private_chat` 状态标签 |

### 目录结构变更

```
frontend/src/features/private-chat/    # 新增 feature 模块
├── store/
│   └── privateChatStore.ts            # 私聊状态管理
└── index.ts                           # 模块导出
```

## 6. 关键设计决策

### 决策1：复用 SingleChatPanel 而非新建组件

**选择**：复用现有 `SingleChatPanel`，只修改 X 按钮行为

**原因**：
- SingleChatPanel 已经支持 SSE 流式消息、消息历史、fork/continue 模式
- 私聊的消息流与普通单聊完全一致，区别仅在于入口和退出逻辑
- 避免代码重复，符合 DRY 原则

**约束**：
- SingleChatPanel 的 `closeSingleChat` 需要判断是否为私聊模式
- 私聊模式下 X 按钮调用 `stop-private-chat` API，而非普通的 `closeSingleChat`

### 决策2：前端管理计时器，后端只做状态变更

**选择**：3 分钟超时计时器在前端 `privateChatStore` 中管理

**原因**：
- 计时器需要在用户发送消息和收到 Agent 回复时重置，这些事件前端最清楚
- 后端只负责状态变更（`in_private_chat` → `idle`），不维护定时器
- 简化后端逻辑，避免后端定时任务的复杂性

**约束**：
- 前端计时器触发时调用 `stop-private-chat` API
- 后端 API 是幂等的（重复调用返回 409）
- WebSocket RefreshSignal 确保状态同步

### 决策3：私聊 session 不保存到 index.json

**选择**：私聊不创建 `SingleChatIndex`，直接使用 Agent 的 `main_session`

**原因**：
- 私聊是临时通道，3 分钟超时自动退出，不适合持久化
- 使用 `main_session` 保持与群聊的对话连续性
- 避免 `index.json` 被临时 session 污染

**约束**：
- 前端 `singleChatStore` 的 `openDraftChat` 用于显示面板，但不创建持久化索引
- 私聊结束后，session 状态由底层平台管理

### 决策4：Manager 禁止私聊

**选择**：前后端双重限制 Manager 私聊

**原因**：
- Manager 在群聊中负责 Heartbeat 和 Loop 结束通知
- 私聊 Manager 会导致这些通知无法处理
- 增加消息处理逻辑复杂度

**约束**：
- 后端：`start-private-chat` API 检查 `agent_name == config.default_manager_name`，返回 403
- 前端：`RightSidebar` 的 `MemberItem` 下拉菜单中 Manager 成员不显示"邀请单聊"选项

## 7. 相关文档链接

### Spec（技术规格）
- [core-agent-orchestration](../../docs/specs/2026-05-31-core-agent-orchestration.md) — Agent 状态管理和 GroupChat 编排机制
- [group-chat-api](../../docs/specs/2026-06-03-group-chat-api.md) — 群聊 API 端点和 Schema 定义
- [single-chat](../../docs/specs/2026-06-08-single-chat.md) — 单聊通道模块，私聊复用其消息流
- [core-foundation](../../docs/specs/2026-05-31-core-foundation.md) — AgentMemberInfo 数据结构基础定义

### Flow（数据流）
- [agent-status-lifecycle](../../docs/flows/agent-status-lifecycle.md) — Agent 状态生命周期，需新增 `in_private_chat` 状态流转

### PRD
- [Private Chat PRD](./PRD.md) — 产品需求文档
