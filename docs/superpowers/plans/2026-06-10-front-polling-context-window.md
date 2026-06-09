# 前端轮询刷新 + 上下文窗口显示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让前端成员列表显示 context_window，并为成员列表、Task、Agent Call 增加 15 秒轮询刷新。

**Architecture:** 后端在已有的 `get_member_dicts()` 返回值中加上 `context_window` 字段，前端三个 hook 各自增加 `setInterval` 轮询作为 WebSocket 的补充。

**Tech Stack:** Python (FastAPI/Pydantic), TypeScript (React)

---

## File Structure

| 操作 | 文件 | 职责 |
|------|------|------|
| Modify | `agents_hub/core/context/group_chat_runtime.py:99-118` | `get_member_dicts()` 增加 `context_window` 字段 |
| Modify | `agents_hub/api/schemas/group_chats.py:36-44` | `GroupChatMember` schema 增加 `context_window` |
| Modify | `frontend/src/shared/types/api-schemas.ts:243-255` | `GroupChatMemberApiItem` 增加 `context_window` |
| Modify | `frontend/src/layouts/RightSidebar/RightSidebar.tsx:86-127` | `MemberItem` 显示 context_window |
| Modify | `frontend/src/layouts/RightSidebar/RightSidebar.module.css` | context_window 样式 |
| Modify | `frontend/src/features/chat/hooks/useMembers.ts` | 增加轮询 |
| Modify | `frontend/src/features/chat/hooks/useTasks.ts` | 增加轮询 |
| Modify | `frontend/src/features/chat/hooks/useAgentCalls.ts` | 增加轮询 |

---

### Task 1: 后端暴露 context_window

**Files:**
- Modify: `agents_hub/core/context/group_chat_runtime.py:99-118`
- Modify: `agents_hub/api/schemas/group_chats.py:36-44`

- [ ] **Step 1: 修改 `get_member_dicts()` 增加 context_window**

在 `group_chat_runtime.py` 的 `get_member_dicts()` 方法中，字典增加 `"context_window"` 键：

```python
def get_member_dicts(self) -> list[dict]:
    members = []
    for agent_name, agent_member_info in self.state.agent_member_infos.items():
        members.append(
            {
                "name": agent_name,
                "main_session": agent_member_info.main_session,
                "btw_session": agent_member_info.btw_session,
                "cwd": agent_member_info.cwd,
                "use_docker": agent_member_info.use_docker,
                "status": agent_member_info.status,
                "context_window": agent_member_info.context_window,
            }
        )
    return members
```

- [ ] **Step 2: 修改 `GroupChatMember` schema 增加 context_window**

在 `group_chats.py` 的 `GroupChatMember` 类中增加字段：

```python
class GroupChatMember(BaseModel):
    """群聊成员（运行时信息）"""

    name: str
    main_session: str | None
    btw_session: list[str]
    cwd: str | None
    use_docker: bool = False
    status: str = "idle"
    context_window: int | None = None
```

- [ ] **Step 3: 验证后端改动**

启动后端，调用 `GET /group-chats/{id}/members`，确认返回 JSON 中包含 `context_window` 字段。

- [ ] **Step 4: Commit**

```bash
git add agents_hub/core/context/group_chat_runtime.py agents_hub/api/schemas/group_chats.py
git commit -m "feat: expose context_window in member list API"
```

---

### Task 2: 前端类型定义 + context_window 显示

**Files:**
- Modify: `frontend/src/shared/types/api-schemas.ts:243-255`
- Modify: `frontend/src/layouts/RightSidebar/RightSidebar.tsx:86-127`
- Modify: `frontend/src/layouts/RightSidebar/RightSidebar.module.css`

- [ ] **Step 1: 修改 `GroupChatMemberApiItem` 类型**

在 `api-schemas.ts` 的 `GroupChatMemberApiItem` 接口中增加字段：

```typescript
export interface GroupChatMemberApiItem {
  name: string;
  main_session: string | null;
  btw_session: string[];
  cwd: string | null;
  use_docker: boolean;
  status: 'idle' | 'busy';
  context_window: number | null;
}
```

- [ ] **Step 2: 在 `MemberItem` 中显示 context_window**

在 `RightSidebar.tsx` 的 `MemberItem` 组件中，在 `memberRole` div 后面增加 context_window 显示：

```tsx
<div className={styles.memberRole}>
  {member.role?.type === 'leader' ? '负责人' : '成员'}
  <span className={styles.memberPlatform}>{member.role?.platform ?? 'unknown'}</span>
</div>
{member.context_window != null && member.context_window > 0 && (
  <div className={styles.memberContext}>
    {member.context_window}K
  </div>
)}
```

- [ ] **Step 3: 添加 context_window 样式**

在 `RightSidebar.module.css` 的 `.memberPlatform` 样式后添加：

```css
.memberContext {
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 3px;
  background: var(--bg-bubble);
  color: var(--text-secondary);
  margin-top: 2px;
  display: inline-block;
}
```

- [ ] **Step 4: 验证前端显示**

启动前端，进入群聊，确认成员列表中显示 context_window（如 "200K"）。值为 0 或 null 时不显示。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/shared/types/api-schemas.ts frontend/src/layouts/RightSidebar/RightSidebar.tsx frontend/src/layouts/RightSidebar/RightSidebar.module.css
git commit -m "feat: display context_window in member list"
```

---

### Task 3: 前端轮询机制

**Files:**
- Modify: `frontend/src/features/chat/hooks/useMembers.ts`
- Modify: `frontend/src/features/chat/hooks/useTasks.ts`
- Modify: `frontend/src/features/chat/hooks/useAgentCalls.ts`

- [ ] **Step 1: 给 `useMembers` 增加轮询**

在 `useMembers.ts` 中，在 WebSocket listener 的 `useEffect` 后面增加一个新的 `useEffect`：

```typescript
// 轮询刷新（补充 WebSocket）
useEffect(() => {
  if (!activeSessionId) return;

  const timeout = setTimeout(() => {
    fetchMembers();
  }, 15000);

  const interval = setInterval(() => {
    fetchMembers();
  }, 15000);

  return () => {
    clearTimeout(timeout);
    clearInterval(interval);
  };
}, [activeSessionId, fetchMembers]);
```

- [ ] **Step 2: 给 `useTasks` 增加轮询**

在 `useTasks.ts` 中，在 WebSocket listener 的 `useEffect` 后面增加：

```typescript
// 轮询刷新（补充 WebSocket）
useEffect(() => {
  if (!chatId) return;

  const timeout = setTimeout(() => {
    refresh();
  }, 15000);

  const interval = setInterval(() => {
    refresh();
  }, 15000);

  return () => {
    clearTimeout(timeout);
    clearInterval(interval);
  };
}, [chatId, refresh]);
```

- [ ] **Step 3: 给 `useAgentCalls` 增加轮询**

在 `useAgentCalls.ts` 中，在 WebSocket listener 的 `useEffect` 后面增加：

```typescript
// 轮询刷新（补充 WebSocket）
useEffect(() => {
  if (!chatId) return;

  const timeout = setTimeout(() => {
    refresh();
  }, 15000);

  const interval = setInterval(() => {
    refresh();
  }, 15000);

  return () => {
    clearTimeout(timeout);
    clearInterval(interval);
  };
}, [chatId, refresh]);
```

- [ ] **Step 4: 验证轮询行为**

启动前端，进入群聊，打开浏览器 DevTools Network 面板，确认：
1. 首次进入后 15 秒发出第一次轮询请求
2. 之后每 15 秒发出一次
3. 切换群聊后重新开始计时
4. WebSocket refresh 信号仍然正常工作

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/chat/hooks/useMembers.ts frontend/src/features/chat/hooks/useTasks.ts frontend/src/features/chat/hooks/useAgentCalls.ts
git commit -m "feat: add 15s polling to members, tasks, and agent calls hooks"
```
