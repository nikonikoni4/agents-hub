# 前端轮询刷新 + 上下文窗口显示

## 背景

前端右侧栏成员列表、Task、Agent Call 的状态更新完全依赖 WebSocket `refresh` 信号，当 WebSocket 信号丢失或延迟时，UI 不会自动更新，需要手动刷新页面。

## 目标

1. 后端 `/group-chats/{id}/members` API 返回 `context_window` 字段
2. 前端成员列表显示上下文窗口大小（格式 `"100K"`、`"200K"`）
3. 前端成员列表、Task、Agent Call 增加 15 秒轮询刷新

## 设计

### 1. 后端：暴露 context_window

**改动文件**：

- `agents_hub/core/context/group_chat_runtime.py` → `get_member_dicts()` 增加 `context_window` 字段
- `agents_hub/api/schemas/group_chats.py` → `GroupChatMember` schema 增加 `context_window: int | None = None`

**数据流**：
```
AgentMemberInfo.context_window (int, 单位 K)
  → GroupChatRuntime.get_member_dicts()
    → GroupChatMember schema
      → API 响应 JSON
```

### 2. 前端：context_window 显示

**改动文件**：`frontend/src/layouts/RightSidebar/RightSidebar.tsx`

在 `MemberItem` 组件中显示上下文窗口。后端返回 int（单位 K），前端格式化为 `"100K"` 字符串。值为 `null` 时不显示。

### 3. 前端：轮询机制

**方案**：轮询作为 WebSocket 的补充（双重保障）

**改动文件**：
- `frontend/src/features/chat/hooks/useMembers.ts`
- `frontend/src/features/chat/hooks/useTasks.ts`
- `frontend/src/features/chat/hooks/useAgentCalls.ts`

**策略**：
- 每个 hook 内部增加 `useEffect`，启动 `setInterval` 每 15 秒调用已有的 fetch 函数
- 首次进入群聊后延迟 15 秒再发第一次轮询请求
- 切换群聊时清除旧 interval，重新开始计时
- WebSocket `refresh` 保持不变，两种机制共存
- 只轮询当前活跃群聊（通过 `chatId` 过滤）

**伪代码**：
```typescript
useEffect(() => {
  if (!chatId) return;
  const timeout = setTimeout(() => {
    fetchData();
  }, 15000);
  const interval = setInterval(() => {
    fetchData();
  }, 15000);
  return () => {
    clearTimeout(timeout);
    clearInterval(interval);
  };
}, [chatId]);
```

## 不做的事

- 不移除 WebSocket 依赖，轮询是补充不是替代
- 不做轮询管理器/共享 timer，三个 hook 各自独立计时
- 不做差异化间隔，统一 15 秒
