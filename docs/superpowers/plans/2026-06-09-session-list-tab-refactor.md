# Session 列表 Tab 分区重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将群聊和单聊列表完全分离，通过 Tab 导航切换，消除混合显示带来的 bug

**Architecture:** sessionStore 和 singleChatStore 完全独立，各自管理自己的状态。SessionList 组件内 Tab 状态控制显示哪个列表。SingleChatPanel 是自包含组件，通过 displayLocation 状态控制渲染位置（sidebar 或 main）。

**Tech Stack:** React 18, Zustand, TypeScript, CSS Modules

---

## 文件结构

### 新建文件

| 文件 | 职责 |
|------|------|
| `features/session/store/sessionStore.ts` | 群聊状态管理 |
| `features/session/hooks/useGroupChatList.ts` | 群聊数据获取 |
| `features/session/hooks/useSessionActions.ts` | 群聊选择、标记已读 |
| `features/session/hooks/useCreateGroupChat.ts` | 创建群聊 |
| `features/session/hooks/useDeleteGroupChat.ts` | 删除群聊 |
| `features/session/hooks/index.ts` | hooks barrel export |
| `features/session/components/SessionList.tsx` | session 列表（含 Tab） |
| `features/session/components/SessionItem.tsx` | session 项 |
| `features/session/components/ProjectGroup.tsx` | 项目分组 |
| `features/session/components/SessionList.css` | SessionList 样式 |
| `features/session/components/SessionItem.css` | SessionItem 样式 |
| `features/session/components/ProjectGroup.css` | ProjectGroup 样式 |
| `features/session/components/CreateGroupChatDialog.tsx` | 创建对话弹窗 |
| `features/session/components/CreateGroupChatDialog.module.css` | 弹窗样式 |
| `features/session/components/TeamListDialog.tsx` | 团队列表弹窗 |
| `features/session/components/TeamListDialog.module.css` | 团队弹窗样式 |
| `features/session/components/index.ts` | components barrel export |
| `features/session/index.ts` | feature barrel export |
| `features/single-chat/store/singleChatStore.ts` | 单聊状态管理 |
| `features/single-chat/hooks/useSingleChatList.ts` | 单聊数据获取 |
| `features/single-chat/hooks/useSingleChatMessages.ts` | 单聊消息管理 |
| `features/single-chat/hooks/useSingleChatMembers.ts` | 单聊成员 |
| `features/single-chat/hooks/useNavigationHandler.ts` | 导航处理 |
| `features/single-chat/hooks/useCreateSingleChat.ts` | 创建单聊 |
| `features/single-chat/hooks/index.ts` | hooks barrel export |
| `features/single-chat/components/SingleChatPanel.tsx` | 单聊面板 |
| `features/single-chat/components/SingleChatPanel.module.css` | 面板样式 |
| `features/single-chat/components/ToolCallCard.tsx` | 工具调用卡片 |
| `features/single-chat/components/ToolCallCard.module.css` | 卡片样式 |
| `features/single-chat/components/index.ts` | components barrel export |
| `features/single-chat/index.ts` | feature barrel export |

### 修改文件

| 文件 | 变更 |
|------|------|
| `layouts/MainLayout/MainLayout.tsx` | 根据 displayLocation 切换渲染 ChatArea 或 SingleChatPanel |
| `layouts/RightSidebar/RightSidebar.tsx` | 移除 activeSessionType 判断，简化 displayLocation 逻辑 |
| `layouts/ChatArea/ChatArea.tsx` | 移除所有单聊相关代码 |
| `layouts/LeftSidebar/LeftSidebar.tsx` | 移除 onSelectSingleChat 回调，订阅 store 变化自动切换视图 |

---

## Task 1: 创建 sessionStore

**Files:**
- Create: `frontend/src/features/session/store/sessionStore.ts`

- [ ] **Step 1: 创建 sessionStore**

```typescript
// features/session/store/sessionStore.ts
import { create } from 'zustand';
import { ProjectGroup, SessionItem } from '@/shared/adapters/sessionAdapter';

interface SessionState {
  projectGroups: ProjectGroup[];
  activeSessionId: string | null;
  lastSelectedAt: number;

  setProjectGroups: (groups: ProjectGroup[]) => void;
  selectGroupChat: (id: string) => void;
  updateSession: (id: string, updates: Partial<SessionItem>) => void;
  clearActive: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  projectGroups: [],
  activeSessionId: null,
  lastSelectedAt: 0,

  setProjectGroups: (groups) => set({ projectGroups: groups }),

  selectGroupChat: (id) =>
    set({ activeSessionId: id, lastSelectedAt: Date.now() }),

  updateSession: (id, updates) =>
    set((state) => ({
      projectGroups: state.projectGroups.map((group) => ({
        ...group,
        sessions: group.sessions.map((s) =>
          s.id === id ? { ...s, ...updates } : s
        ),
      })),
    })),

  clearActive: () => set({ activeSessionId: null }),
}));
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit --pretty`
Expected: 无报错（其他文件引用 sessionStore 的 import 会报错，这是预期的，后续任务修复）

---

## Task 2: 创建 singleChatStore

**Files:**
- Create: `frontend/src/features/single-chat/store/singleChatStore.ts`

- [ ] **Step 1: 创建 singleChatStore**

```typescript
// features/single-chat/store/singleChatStore.ts
import { create } from 'zustand';
import type { SingleChatApiResponse } from '@/shared/types';

interface SingleChatState {
  singleChats: SingleChatApiResponse[];
  activeSingleChatId: string | null;
  displayLocation: 'sidebar' | 'main';

  setSingleChats: (chats: SingleChatApiResponse[]) => void;
  openSingleChat: (id: string) => void;
  closeSingleChat: () => void;
  addSingleChat: (chat: SingleChatApiResponse) => void;
  toggleLocation: () => void;
  clearActive: () => void;
}

export const useSingleChatStore = create<SingleChatState>((set) => ({
  singleChats: [],
  activeSingleChatId: null,
  displayLocation: 'sidebar',

  setSingleChats: (chats) => set({ singleChats: chats }),

  openSingleChat: (id) =>
    set({ activeSingleChatId: id, displayLocation: 'sidebar' }),

  closeSingleChat: () => set({ activeSingleChatId: null }),

  addSingleChat: (chat) =>
    set((state) => ({ singleChats: [...state.singleChats, chat] })),

  toggleLocation: () =>
    set((state) => ({
      displayLocation: state.displayLocation === 'sidebar' ? 'main' : 'sidebar',
    })),

  clearActive: () => set({ activeSingleChatId: null }),
}));
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit --pretty`
Expected: 无新增报错

---

## Task 3: 创建 useGroupChatList hook

**Files:**
- Create: `frontend/src/features/session/hooks/useGroupChatList.ts`

- [ ] **Step 1: 创建 useGroupChatList**

```typescript
// features/session/hooks/useGroupChatList.ts
import { useEffect, useCallback } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { wsManager } from '@/core/websocket/WebSocketManager';
import { storage } from '@/core/storage';
import { listGroupChatInfos, getMembers } from '@/core/api';
import { groupSessionsByProject } from '@/shared/adapters/sessionAdapter';
import { buildRoleAvatarMap } from '@/shared/adapters/roleAvatarAdapter';
import type { RefreshSignal } from '@/shared/types';

export function useGroupChatList() {
  const { projectGroups, setProjectGroups } = useSessionStore();
  const activeSessionId = useSessionStore((s) => s.activeSessionId);

  const refreshGroupChats = useCallback(async () => {
    try {
      const [chats, lastViewRecords] = await Promise.all([
        listGroupChatInfos(),
        storage.getLastViewRecords(),
      ]);

      // 只传群聊数据，不传单聊
      const groups = groupSessionsByProject(chats, lastViewRecords, []);

      // 加载成员头像
      const groupChatSessionIds = groups.flatMap((g) =>
        g.sessions.map((s) => s.id)
      );

      const roleAvatarMap = await buildRoleAvatarMap();

      if (groupChatSessionIds.length > 0) {
        const memberResults = await Promise.all(
          groupChatSessionIds.map((id) => getMembers(id).catch(() => []))
        );

        let idx = 0;
        for (const group of groups) {
          for (const session of group.sessions) {
            const members = memberResults[idx++] ?? [];
            session.memberAvatars = members
              .slice(0, 4)
              .map((m) => roleAvatarMap.get(m.name) ?? null);
            session.memberCount = members.length;
          }
        }
      }

      setProjectGroups(groups);
    } catch (error) {
      console.error('Failed to fetch group chats:', error);
    }
  }, [setProjectGroups]);

  useEffect(() => {
    refreshGroupChats();
  }, [refreshGroupChats]);

  useEffect(() => {
    const handleRefresh = (data?: unknown) => {
      const signal = data as RefreshSignal;
      if (!signal?.group_chat_id || signal.group_chat_id === activeSessionId) {
        refreshGroupChats();
      }
    };
    wsManager.on('refresh', handleRefresh);
    return () => { wsManager.off('refresh', handleRefresh); };
  }, [refreshGroupChats, activeSessionId]);

  return { projectGroups, refreshGroupChats };
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit --pretty`
Expected: 无新增报错

---

## Task 4: 创建 useSingleChatList hook 和 groupSingleChatsByProject 共享函数

**Files:**
- Create: `frontend/src/features/single-chat/hooks/useSingleChatList.ts`
- Modify: `frontend/src/shared/adapters/sessionAdapter.ts`

- [ ] **Step 1: 在 sessionAdapter.ts 中添加 groupSingleChatsByProject 函数**

在 `sessionAdapter.ts` 末尾添加：

```typescript
/**
 * 将单聊列表按 cwd 分组为 ProjectGroup 格式
 */
export function groupSingleChatsByProject(
  singleChats: SingleChatApiResponse[]
): ProjectGroup[] {
  const grouped: Record<string, ProjectGroup> = {};
  for (const sc of singleChats) {
    const projectName = extractProjectName(sc.cwd);
    if (!grouped[projectName]) {
      grouped[projectName] = {
        projectPath: sc.cwd,
        projectName,
        sessions: [],
      };
    }
    grouped[projectName].sessions.push({
      id: sc.single_chat_id,
      title: sc.single_chat_name,
      preview: `${sc.agent_name} · ${sc.platform}`,
      lastUpdateAt: new Date(sc.last_active_at),
      lastViewAt: null,
      isUnread: false,
      memberCount: 1,
      projectPath: sc.cwd,
      memberAvatars: [],
      type: 'single_chat',
      agentName: sc.agent_name,
      platform: sc.platform,
    });
  }
  return Object.values(grouped).map((group) => ({
    ...group,
    sessions: group.sessions.sort(
      (a, b) => b.lastUpdateAt.getTime() - a.lastUpdateAt.getTime()
    ),
  }));
}
```

- [ ] **Step 2: 创建 useSingleChatList**

```typescript
// features/single-chat/hooks/useSingleChatList.ts
import { useEffect, useCallback } from 'react';
import { useSingleChatStore } from '../store/singleChatStore';
import { wsManager } from '@/core/websocket/WebSocketManager';
import { listSingleChats } from '@/core/api/singleChatApi';
import type { RefreshSignal } from '@/shared/types';

export function useSingleChatList() {
  const { singleChats, setSingleChats } = useSingleChatStore();

  const refreshSingleChats = useCallback(async () => {
    try {
      const chats = await listSingleChats();
      setSingleChats(chats);
    } catch (error) {
      console.error('Failed to fetch single chats:', error);
    }
  }, [setSingleChats]);

  useEffect(() => {
    refreshSingleChats();
  }, [refreshSingleChats]);

  useEffect(() => {
    const handleRefresh = (data?: unknown) => {
      const signal = data as RefreshSignal;
      if (!signal?.group_chat_id) {
        refreshSingleChats();
      }
    };
    wsManager.on('refresh', handleRefresh);
    return () => { wsManager.off('refresh', handleRefresh); };
  }, [refreshSingleChats]);

  return { singleChats, refreshSingleChats };
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit --pretty`
Expected: 无新增报错

---

## Task 5: 创建 SessionItem 组件

**Files:**
- Create: `frontend/src/features/session/components/SessionItem.tsx`
- Create: `frontend/src/features/session/components/SessionItem.css`

- [ ] **Step 1: 创建 SessionItem.css**

```css
.session-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 14px 16px;
  cursor: pointer;
  border-radius: 10px;
  transition: all 0.15s;
  margin-bottom: 8px;
  position: relative;
}

.session-content {
  flex: 1;
  min-width: 0;
}

.session-item:hover {
  background: var(--bg-hover, #f0f0f0);
}

.session-item.active {
  background: var(--bg-selected, rgb(232, 232, 232));
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.session-item.unread {
  font-weight: 600;
}

.session-title {
  font-size: 14px;
  color: var(--text-primary, #333);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-preview {
  font-size: 12px;
  color: var(--text-secondary, #666);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-tertiary, #999);
}

.session-time {
  flex: 1;
}

.unread-badge {
  color: var(--accent-color);
  font-size: 16px;
  line-height: 1;
}

.session-actions {
  position: relative;
  opacity: 0;
  transition: opacity 0.15s;
}

.session-item:hover .session-actions {
  opacity: 1;
}

.menu-button {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 18px;
  color: var(--text-secondary, #666);
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.15s;
  line-height: 1;
}

.menu-button:hover {
  background: var(--bg-hover, #f0f0f0);
  color: var(--text-primary, #333);
}

.context-menu {
  position: absolute;
  top: 100%;
  right: 0;
  background: white;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  min-width: 120px;
  margin-top: 4px;
}

.menu-item {
  display: block;
  width: 100%;
  padding: 10px 16px;
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-primary, #333);
  transition: background 0.15s;
}

.menu-item:hover:not(:disabled) {
  background: var(--bg-hover, #f0f0f0);
}

.menu-item.danger {
  color: #ef4444;
}

.menu-item.danger:hover:not(:disabled) {
  background: #fef2f2;
}

.menu-item:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.session-type-badge {
  display: inline-block;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  background: color-mix(in srgb, var(--accent-color, #4a9eff) 15%, transparent);
  color: var(--accent-color, #4a9eff);
  margin-right: 6px;
  font-weight: 500;
  vertical-align: middle;
}
```

- [ ] **Step 2: 创建 SessionItem.tsx**

```typescript
// features/session/components/SessionItem.tsx
import { useState } from 'react';
import { SessionItem as SessionItemType } from '@/shared/adapters/sessionAdapter';
import { useSessionStore } from '../store/sessionStore';
import { useSessionActions } from '../hooks/useSessionActions';
import { useDeleteGroupChat } from '../hooks/useDeleteGroupChat';
import { useSingleChatStore } from '@/features/single-chat/store/singleChatStore';
import { formatRelativeTime } from '@/shared/adapters/sessionAdapter';
import './SessionItem.css';

interface SessionItemProps {
  session: SessionItemType;
  isActive?: boolean;
}

export function SessionItem({ session, isActive = false }: SessionItemProps) {
  const { handleSelectSession } = useSessionActions();
  const { deleteChat, deleting } = useDeleteGroupChat();
  const clearActive = useSingleChatStore((s) => s.clearActive);
  const openSingleChat = useSingleChatStore((s) => s.openSingleChat);
  const clearGroupActive = useSessionStore((s) => s.clearActive);
  const [showMenu, setShowMenu] = useState(false);

  const isSingleChat = session.type === 'single_chat';

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`确定要删除群聊「${session.title}」吗？`)) return;
    try {
      await deleteChat(session.id, false);
    } catch {
      alert('删除失败，请重试');
    } finally {
      setShowMenu(false);
    }
  };

  const handleItemClick = () => {
    if (showMenu) return;
    if (isSingleChat) {
      openSingleChat(session.id);
      clearGroupActive();
    } else {
      handleSelectSession(session.id);
      clearActive();
    }
  };

  return (
    <div
      className={`session-item ${session.isUnread ? 'unread' : ''} ${isActive ? 'active' : ''}`}
      onClick={handleItemClick}
    >
      <div className="session-content">
        <div className="session-title">
          <span className="session-type-badge">
            {isSingleChat ? '单聊' : '群聊'}
          </span>
          {session.title}
        </div>
        <div className="session-preview">{session.preview}</div>
        <div className="session-meta">
          <span className="session-time">
            {session.lastViewAt
              ? formatRelativeTime(session.lastViewAt)
              : formatRelativeTime(session.lastUpdateAt)}
          </span>
          {session.isUnread && <span className="unread-badge">●</span>}
        </div>
      </div>
      {!isSingleChat && (
        <div className="session-actions">
          <button
            className="menu-button"
            onClick={(e) => { e.stopPropagation(); setShowMenu(!showMenu); }}
            title="更多操作"
          >
            ⋮
          </button>
          {showMenu && (
            <div className="context-menu">
              <button
                className="menu-item danger"
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? '删除中...' : '删除群聊'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit --pretty`
Expected: 无新增报错

---

## Task 6: 创建 ProjectGroup 和 SessionList 组件

**Files:**
- Create: `frontend/src/features/session/components/ProjectGroup.tsx`
- Create: `frontend/src/features/session/components/ProjectGroup.css`
- Create: `frontend/src/features/session/components/SessionList.tsx`
- Create: `frontend/src/features/session/components/SessionList.css`

- [ ] **Step 1: 创建 ProjectGroup.css**

```css
.project-group {
  margin-bottom: 16px;
}

.project-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary, #333);
  background: var(--bg-secondary, #f5f5f5);
  border-radius: 4px;
  transition: background 0.2s;
}

.project-header:hover {
  background: var(--bg-hover, #e8e8e8);
}

.project-icon {
  font-size: 10px;
  color: var(--text-secondary, #666);
}

.project-name {
  flex: 1;
}

.session-count {
  font-size: 12px;
  font-weight: normal;
  color: var(--text-secondary, #666);
  background: var(--bg-tertiary, #e0e0e0);
  padding: 2px 6px;
  border-radius: 10px;
}

.sessions {
  padding-left: 16px;
  margin-top: 4px;
}
```

- [ ] **Step 2: 创建 ProjectGroup.tsx**

```typescript
// features/session/components/ProjectGroup.tsx
import { useState } from 'react';
import { ProjectGroup as ProjectGroupType } from '@/shared/adapters/sessionAdapter';
import { SessionItem } from './SessionItem';
import { useSessionStore } from '../store/sessionStore';
import { useSingleChatStore } from '@/features/single-chat/store/singleChatStore';
import './ProjectGroup.css';

interface ProjectGroupProps {
  group: ProjectGroupType;
  type: 'group_chat' | 'single_chat';
}

export function ProjectGroup({ group, type }: ProjectGroupProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const activeSingleChatId = useSingleChatStore((s) => s.activeSingleChatId);

  const activeId = type === 'group_chat' ? activeSessionId : activeSingleChatId;

  return (
    <div className="project-group">
      <div className="project-header" onClick={() => setIsExpanded(!isExpanded)}>
        <span className="project-icon">{isExpanded ? '▼' : '▶'}</span>
        <span className="project-name">{group.projectName}</span>
        <span className="session-count">{group.sessions.length}</span>
      </div>
      {isExpanded && (
        <div className="sessions">
          {group.sessions.map((session) => (
            <SessionItem
              key={session.id}
              session={session}
              isActive={session.id === activeId}
            />
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: 创建 SessionList.css**

```css
.session-list {
  overflow-y: auto;
  height: 100%;
  padding: 8px 0;
}

.session-list-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--text-secondary, #666);
  font-size: 14px;
}

.session-tabs {
  display: flex;
  gap: 0;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
}

.session-tab {
  flex: 1;
  padding: 8px 16px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary, #666);
  border-bottom: 2px solid transparent;
  transition: all 0.15s;
}

.session-tab:hover {
  color: var(--text-primary, #333);
}

.session-tab.active {
  color: var(--accent-color, #4a9eff);
  border-bottom-color: var(--accent-color, #4a9eff);
}
```

- [ ] **Step 4: 创建 SessionList.tsx**

```typescript
// features/session/components/SessionList.tsx
import { useState, useMemo } from 'react';
import { useGroupChatList } from '../hooks/useGroupChatList';
import { useSingleChatStore } from '@/features/single-chat/store/singleChatStore';
import { groupSingleChatsByProject } from '@/shared/adapters/sessionAdapter';
import { ProjectGroup } from './ProjectGroup';
import './SessionList.css';

type SessionTab = 'group' | 'single';

export function SessionList() {
  const [activeTab, setActiveTab] = useState<SessionTab>('group');
  const { projectGroups: groupChatGroups } = useGroupChatList();
  const singleChats = useSingleChatStore((s) => s.singleChats);

  const singleChatGroups = useMemo(
    () => groupSingleChatsByProject(singleChats),
    [singleChats]
  );

  const groups = activeTab === 'group' ? groupChatGroups : singleChatGroups;

  return (
    <div className="session-list">
      <div className="session-tabs">
        <button
          className={`session-tab ${activeTab === 'group' ? 'active' : ''}`}
          onClick={() => setActiveTab('group')}
        >
          群聊
        </button>
        <button
          className={`session-tab ${activeTab === 'single' ? 'active' : ''}`}
          onClick={() => setActiveTab('single')}
        >
          单聊
        </button>
      </div>
      {groups.length === 0 ? (
        <div className="session-list-empty">
          <p>{activeTab === 'group' ? '暂无群聊' : '暂无单聊'}</p>
        </div>
      ) : (
        groups.map((group) => (
          <ProjectGroup
            key={group.projectPath}
            group={group}
            type={activeTab === 'group' ? 'group_chat' : 'single_chat'}
          />
        ))
      )}
    </div>
  );
}
```

- [ ] **Step 5: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit --pretty`
Expected: 无新增报错

---

## Task 7: 创建 session hooks

**Files:**
- Create: `frontend/src/features/session/hooks/useSessionActions.ts`
- Create: `frontend/src/features/session/hooks/useDeleteGroupChat.ts`
- Create: `frontend/src/features/session/hooks/useCreateGroupChat.ts`
- Create: `frontend/src/features/session/hooks/index.ts`

- [ ] **Step 1: 创建 useSessionActions.ts**

```typescript
// features/session/hooks/useSessionActions.ts
import { useSessionStore } from '../store/sessionStore';
import { storage } from '@/core/storage';

export function useSessionActions() {
  const { selectGroupChat, updateSession } = useSessionStore();

  const handleSelectSession = async (sessionId: string) => {
    try {
      selectGroupChat(sessionId);
      const now = new Date().toISOString();
      await storage.setLastView(sessionId, now);
      updateSession(sessionId, { isUnread: false });
    } catch (error) {
      console.error('Failed to select session:', error);
    }
  };

  return { handleSelectSession };
}
```

- [ ] **Step 2: 创建 useDeleteGroupChat.ts**

```typescript
// features/session/hooks/useDeleteGroupChat.ts
import { useCallback, useState } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { deleteGroupChat } from '@/core/api/groupChatApi';
import { useGroupChatList } from './useGroupChatList';

export function useDeleteGroupChat() {
  const { projectGroups, setProjectGroups } = useSessionStore();
  const { refreshGroupChats } = useGroupChatList();
  const [deleting, setDeleting] = useState(false);

  const deleteChat = useCallback(
    async (chatId: string, keepData: boolean = false): Promise<void> => {
      setDeleting(true);
      const updatedGroups = projectGroups
        .map((group) => ({
          ...group,
          sessions: group.sessions.filter((s) => s.id !== chatId),
        }))
        .filter((group) => group.sessions.length > 0);
      setProjectGroups(updatedGroups);

      try {
        await deleteGroupChat(chatId, keepData);
      } catch (error) {
        await refreshGroupChats();
        throw error;
      } finally {
        setDeleting(false);
      }
    },
    [projectGroups, setProjectGroups, refreshGroupChats]
  );

  return { deleteChat, deleting };
}
```

- [ ] **Step 3: 创建 useCreateGroupChat.ts**

```typescript
// features/session/hooks/useCreateGroupChat.ts
import { useState, useEffect, useCallback } from 'react';
import { listRoles } from '@/core/api/roleApi';
import { createGroupChat } from '@/core/api/groupChatApi';
import { aggregateAllTeams } from '@/shared/adapters/teamAdapter';
import type { RoleApiResponse } from '@/shared/types/api-schemas';
import type { CreateGroupChatRequest } from '@/shared/types/api-requests';
import { useGroupChatList } from './useGroupChatList';

export interface TeamOption {
  name: string;
  members: string[];
}

export function useCreateGroupChat() {
  const [roles, setRoles] = useState<RoleApiResponse[]>([]);
  const [teams, setTeams] = useState<TeamOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const { refreshGroupChats } = useGroupChatList();

  useEffect(() => {
    let cancelled = false;
    Promise.all([listRoles(), aggregateAllTeams()]).then(([roleData, teamData]) => {
      if (!cancelled) {
        setRoles(roleData);
        setTeams(teamData.map((t) => ({ name: t.name, members: t.members })));
        setLoading(false);
      }
    });
    return () => { cancelled = true; };
  }, []);

  const createChat = useCallback(
    async (data: CreateGroupChatRequest): Promise<string | null> => {
      setSubmitting(true);
      try {
        const result = await createGroupChat(data);
        await refreshGroupChats();
        return result.group_chat_id;
      } catch (err) {
        console.error('Failed to create group chat:', err);
        return null;
      } finally {
        setSubmitting(false);
      }
    },
    [refreshGroupChats]
  );

  const leaders = roles.filter((r) => r.type === 'leader');
  const workers = roles.filter((r) => r.type === 'team_member');

  return { roles, leaders, workers, teams, loading, submitting, createChat };
}
```

- [ ] **Step 4: 创建 hooks/index.ts**

```typescript
// features/session/hooks/index.ts
export { useGroupChatList } from './useGroupChatList';
export { useSessionActions } from './useSessionActions';
export { useCreateGroupChat } from './useCreateGroupChat';
export { useDeleteGroupChat } from './useDeleteGroupChat';
```

- [ ] **Step 5: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit --pretty`
Expected: 无新增报错

---

## Task 8: 创建 CreateGroupChatDialog 和 barrel exports

**Files:**
- Create: `frontend/src/features/session/components/CreateGroupChatDialog.tsx`
- Create: `frontend/src/features/session/components/CreateGroupChatDialog.module.css`
- Create: `frontend/src/features/session/components/index.ts`
- Create: `frontend/src/features/session/index.ts`

- [ ] **Step 1: 复制 CreateGroupChatDialog 从 git 历史**

Run: `cd "D:\desktop\软件开发\agents-hub\.claude\worktrees\test_branch" && git show HEAD:"frontend/src/features/session copy/components/CreateGroupChatDialog.tsx" > "frontend/src/features/session/components/CreateGroupChatDialog.tsx"`

Run: `cd "D:\desktop\软件开发\agents-hub\.claude\worktrees\test_branch" && git show HEAD:"frontend/src/features/session copy/components/CreateGroupChatDialog.module.css" > "frontend/src/features/session/components/CreateGroupChatDialog.module.css"`

- [ ] **Step 2: 修改 CreateGroupChatDialog 中的 import**

将 `useSessionList` 引用改为 `useGroupChatList`，将 `selectSession` 改为 `selectGroupChat`。

- [ ] **Step 3: 创建 components/index.ts**

```typescript
export { SessionList } from './SessionList';
export { ProjectGroup } from './ProjectGroup';
export { SessionItem } from './SessionItem';
export { CreateGroupChatDialog } from './CreateGroupChatDialog';
```

- [ ] **Step 4: 创建 index.ts**

```typescript
export { SessionList, CreateGroupChatDialog } from './components';
export { useGroupChatList, useSessionActions } from './hooks';
export { useSessionStore } from './store/sessionStore';
```

- [ ] **Step 5: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit --pretty`
Expected: 无新增报错

---

## Task 9: 创建 single-chat hooks

**Files:**
- Create: `frontend/src/features/single-chat/hooks/useSingleChatMessages.ts`
- Create: `frontend/src/features/single-chat/hooks/useSingleChatMembers.ts`
- Create: `frontend/src/features/single-chat/hooks/useNavigationHandler.ts`
- Create: `frontend/src/features/single-chat/hooks/useCreateSingleChat.ts`
- Create: `frontend/src/features/single-chat/hooks/index.ts`

- [ ] **Step 1: 从 git 历史复制 hooks**

Run: `cd "D:\desktop\软件开发\agents-hub\.claude\worktrees\test_branch" && git show HEAD:"frontend/src/features/single-chat copy/hooks/useSingleChatMessages.ts" > "frontend/src/features/single-chat/hooks/useSingleChatMessages.ts"`

Run: `cd "D:\desktop\软件开发\agents-hub\.claude\worktrees\test_branch" && git show HEAD:"frontend/src/features/single-chat copy/hooks/useSingleChatMembers.ts" > "frontend/src/features/single-chat/hooks/useSingleChatMembers.ts"`

Run: `cd "D:\desktop\软件开发\agents-hub\.claude\worktrees\test_branch" && git show HEAD:"frontend/src/features/single-chat copy/hooks/useNavigationHandler.ts" > "frontend/src/features/single-chat/hooks/useNavigationHandler.ts"`

Run: `cd "D:\desktop\软件开发\agents-hub\.claude\worktrees\test_branch" && git show HEAD:"frontend/src/features/single-chat copy/hooks/useCreateSingleChat.ts" > "frontend/src/features/single-chat/hooks/useCreateSingleChat.ts"`

- [ ] **Step 2: 修改 useNavigationHandler 中的 import**

将 `selectSession` 改为 `selectGroupChat`。

- [ ] **Step 3: 创建 hooks/index.ts**

```typescript
export { useSingleChatList } from './useSingleChatList';
export { useSingleChatMessages } from './useSingleChatMessages';
export { useSingleChatMembers } from './useSingleChatMembers';
export { useNavigationHandler } from './useNavigationHandler';
export { useCreateSingleChat } from './useCreateSingleChat';
```

- [ ] **Step 4: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit --pretty`
Expected: 无新增报错

---

## Task 10: 创建 SingleChatPanel 和 barrel exports

**Files:**
- Create: `frontend/src/features/single-chat/components/SingleChatPanel.tsx`
- Create: `frontend/src/features/single-chat/components/SingleChatPanel.module.css`
- Create: `frontend/src/features/single-chat/components/ToolCallCard.tsx`
- Create: `frontend/src/features/single-chat/components/ToolCallCard.module.css`
- Create: `frontend/src/features/single-chat/components/index.ts`
- Create: `frontend/src/features/single-chat/index.ts`

- [ ] **Step 1: 从 git 历史复制组件**

Run: `cd "D:\desktop\软件开发\agents-hub\.claude\worktrees\test_branch" && git show HEAD:"frontend/src/features/single-chat copy/components/SingleChatPanel.tsx" > "frontend/src/features/single-chat/components/SingleChatPanel.tsx"`

Run: `cd "D:\desktop\软件开发\agents-hub\.claude\worktrees\test_branch" && git show HEAD:"frontend/src/features/single-chat copy/components/SingleChatPanel.module.css" > "frontend/src/features/single-chat/components/SingleChatPanel.module.css"`

Run: `cd "D:\desktop\软件开发\agents-hub\.claude\worktrees\test_branch" && git show HEAD:"frontend/src/features/single-chat copy/components/ToolCallCard.tsx" > "frontend/src/features/single-chat/components/ToolCallCard.tsx"`

Run: `cd "D:\desktop\软件开发\agents-hub\.claude\worktrees\test_branch" && git show HEAD:"frontend/src/features/single-chat copy/components/ToolCallCard.module.css" > "frontend/src/features/single-chat/components/ToolCallCard.module.css"`

- [ ] **Step 2: 修改 SingleChatPanel 中的 import**

将 `selectSession` 改为 `selectGroupChat`。

- [ ] **Step 3: 创建 barrel exports**

```typescript
// features/single-chat/components/index.ts
export { SingleChatPanel } from './SingleChatPanel';
export { ToolCallCard } from './ToolCallCard';
```

```typescript
// features/single-chat/index.ts
export { useSingleChatStore } from './store/singleChatStore';
export { useCreateSingleChat } from './hooks/useCreateSingleChat';
export { useSingleChatMessages } from './hooks/useSingleChatMessages';
export { useSingleChatMembers } from './hooks/useSingleChatMembers';
export { SingleChatPanel } from './components/SingleChatPanel';
```

- [ ] **Step 4: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit --pretty`
Expected: 无新增报错

---

## Task 11: 修改 MainLayout

**Files:**
- Modify: `frontend/src/layouts/MainLayout/MainLayout.tsx`

- [ ] **Step 1: 修改 MainLayout**

在 MainLayout 中：
1. 订阅 `singleChatStore.activeSingleChatId` 和 `singleChatStore.displayLocation`
2. 当 `displayLocation === 'main' && activeSingleChatId` 时，渲染 SingleChatPanel 替代 ChatArea
3. 订阅 `singleChatStore.activeSingleChatId` 变化，自动切换 viewMode 为 'chat'

```typescript
// 在 MainLayout 中添加：
import { useSingleChatStore } from '@/features/single-chat/store/singleChatStore';
import { SingleChatPanel } from '@/features/single-chat/components/SingleChatPanel';

// 在组件内部：
const activeSingleChatId = useSingleChatStore((s) => s.activeSingleChatId);
const displayLocation = useSingleChatStore((s) => s.displayLocation);
const singleChatLocation = useSingleChatStore((s) => s.displayLocation);

// 当单聊激活时，自动切换到 chat 视图
useEffect(() => {
  if (activeSingleChatId) {
    setViewMode('chat');
  }
}, [activeSingleChatId]);

// 在渲染区域：
{viewMode === 'chat' && (
  <>
    {displayLocation === 'main' && activeSingleChatId ? (
      <SingleChatPanel />
    ) : (
      <ChatArea
        onToggleRightSidebar={handleToggleRightSidebar}
        onContentChange={setRightSidebarContent}
      />
    )}
  </>
)}
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit --pretty`
Expected: 无新增报错

---

## Task 12: 修改 RightSidebar

**Files:**
- Modify: `frontend/src/layouts/RightSidebar/RightSidebar.tsx`

- [ ] **Step 1: 简化 RightSidebar**

移除 `activeSessionType` 相关逻辑，简化为：
- 当 `activeSingleChatId` 存在且 `displayLocation === 'sidebar'` 时，显示 SingleChatPanel
- 否则显示群聊侧边栏内容（成员列表、置顶消息等）

```typescript
// 移除：
const activeSessionType = useSessionStore((s) => s.activeSessionType);
const groupChatId = activeSessionType === 'group_chat' ? activeSessionId : null;

// 改为：
// 群聊功能：当有 activeSessionId 且没有 activeSingleChatId 时启用
const groupChatId = activeSessionId && !activeSingleChatId ? activeSessionId : null;
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit --pretty`
Expected: 无新增报错

---

## Task 13: 修改 ChatArea

**Files:**
- Modify: `frontend/src/layouts/ChatArea/ChatArea.tsx`

- [ ] **Step 1: 移除单聊相关代码**

从 ChatArea 中移除：
1. `useSingleChatStore` 引用
2. `showingSingleChat` 判断
3. 单聊 UI 分支（移动到主界面的按钮、单聊消息列表）
4. `activeSessionType` 相关判断
5. 单聊相关的 early return

保留：
1. 群聊消息显示
2. 群聊发送逻辑
3. 置顶消息、文件预览等群聊功能

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit --pretty`
Expected: 无新增报错

---

## Task 14: 修改 LeftSidebar

**Files:**
- Modify: `frontend/src/layouts/LeftSidebar/LeftSidebar.tsx`

- [ ] **Step 1: 简化 LeftSidebar**

移除 `onSelectSingleChat` 回调，改为订阅 store 变化自动切换视图：

```typescript
// 移除：
const openSingleChat = useSingleChatStore((s) => s.openSingleChat);
const handleSelectSingleChat = useCallback(
  (id: string) => {
    openSingleChat(id);
    onViewModeChange?.('chat');
  },
  [openSingleChat, onViewModeChange]
);

// 添加：
const activeSessionId = useSessionStore((s) => s.activeSessionId);
const activeSingleChatId = useSingleChatStore((s) => s.activeSingleChatId);
const lastSelectedAt = useSessionStore((s) => s.lastSelectedAt);

// 当 session 被选中时，自动切换到 chat 视图
useEffect(() => {
  if (activeSessionId || activeSingleChatId) {
    onViewModeChange?.('chat');
  }
}, [activeSessionId, activeSingleChatId, lastSelectedAt, onViewModeChange]);

// SessionList 不再需要 onSelectSingleChat prop
<SessionList />
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit --pretty`
Expected: 无新增报错

---

## Task 15: 最终验证

- [ ] **Step 1: TypeScript 编译检查**

Run: `cd frontend && npx tsc --noEmit --pretty`
Expected: 无报错

- [ ] **Step 2: ESLint 检查**

Run: `cd frontend && npx eslint src/ --ext .ts,.tsx`
Expected: 无新增 warning 或 error

- [ ] **Step 3: 提交所有变更**

Run: `cd "D:\desktop\软件开发\agents-hub\.claude\worktrees\test_branch" && git add frontend/src/features/ frontend/src/layouts/ && git commit -m "feat: session 列表 Tab 分区重构，群聊/单聊完全解耦"`
