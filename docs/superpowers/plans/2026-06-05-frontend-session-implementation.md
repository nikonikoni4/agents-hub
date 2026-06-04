# Session 切换功能实施计划

## Context

用户需要实现前端的 session 切换功能，包括：
- **两层结构**：项目文件夹 + session 列表（如图所示）
- **未读标记**：基于 `last_view_at` 计算
- **实时更新**：WebSocket 消息自动更新 session 预览
- **前端聚合**：从后端扁平数据（`GroupChatInfo[]`）聚合为项目分组

**当前状态**：
- ✅ 已完成设计规格（`docs/superpowers/specs/2026-06-05-session-switching-design.md`）
- ✅ 前端基础设施已完善（83% 完成度）：
  - ✅ Core 层：API 客户端、WebSocket 管理器已实现
  - ✅ Shared 层：类型系统、Adapters 框架已完善
  - ✅ Features 层：roles、skills 功能已实现
  - ⚠️ ChatArea：占位符实现（需连接真实聊天逻辑）
  - ❌ Session 功能：尚未实现（本次任务）

**实施策略**：
基于现有架构，按照 shared → features 的顺序实现 session 功能，复用已有的 API 客户端、WebSocket 管理器、Adapters 框架。

---

## 实施步骤

### Phase 1：实现 Shared 层（数据适配和类型定义）

**目标**：创建 session 数据适配器，将后端扁平数据聚合为前端所需的项目分组结构

#### 1.1 定义 API 类型（shared/types/api-schemas.ts）

**新增类型**：
```typescript
// 后端 GroupChatInfo 响应
export interface GroupChatInfoApiResponse {
  group_chat_id: string;
  project_path: string;
  title: string;
  last_message_preview: string | null;
  last_update_at: string; // ISO 8601
  member_count: number;
  unread_count?: number; // 可选（后端可能未提供）
}

// 本地存储的 last_view 记录
export interface LastViewRecord {
  group_chat_id: string;
  last_view_at: string; // ISO 8601
}
```

#### 1.2 实现 sessionAdapter（shared/adapters/sessionAdapter.ts）

**功能**：
```typescript
import { GroupChatInfoApiResponse, LastViewRecord } from '../types/api-schemas';

// 前端聚合后的数据结构
export interface SessionItem {
  id: string;
  title: string;
  preview: string;
  lastUpdateAt: Date;
  isUnread: boolean;
  memberCount: number;
  projectPath: string;
}

export interface ProjectGroup {
  projectPath: string;
  projectName: string;
  sessions: SessionItem[];
}

// 核心聚合函数
export function groupSessionsByProject(
  chats: GroupChatInfoApiResponse[],
  lastViewRecords: Record<string, string> // { group_chat_id: last_view_at }
): ProjectGroup[] {
  // 1. 按 project_path 分组
  // 2. 计算 isUnread（last_update_at > last_view_at）
  // 3. 提取 projectName（从 project_path）
  // 4. 排序：未读在前，按 lastUpdateAt 降序
}

// 辅助函数
export function extractProjectName(projectPath: string): string {
  // 从 "D:\projects\agents-hub" 提取 "agents-hub"
}

export function isUnread(lastUpdateAt: string, lastViewAt?: string): boolean {
  // 比较时间戳
}

export function formatRelativeTime(date: Date): string {
  // "1小时前"、"昨天"、"3天前"
}
```

**测试文件**（shared/adapters/sessionAdapter.test.ts）：
- 测试聚合逻辑
- 测试未读计算
- 测试项目名提取
- 测试排序规则

---

### Phase 2：实现 Core 层扩展（Storage）

**目标**：实现 IndexedDB 存储，用于本地持久化 `last_view_at`

#### 2.1 实现 Storage 类（core/storage/index.ts）

**功能**：
```typescript
export class Storage {
  private dbName = 'agents-hub-storage';
  private storeName = 'session-views';

  async init(): Promise<void> {
    // 初始化 IndexedDB
  }

  async getLastViewRecords(): Promise<Record<string, string>> {
    // 读取所有 last_view_at 记录
  }

  async setLastView(groupChatId: string, timestamp: string): Promise<void> {
    // 写入单条记录
  }

  async batchSetLastView(records: Array<{ id: string; timestamp: string }>): Promise<void> {
    // 批量写入
  }
}

export const storage = new Storage();
```

**初始化时机**：在 `main.tsx` 中调用 `storage.init()`

---

### Phase 3：实现 Features 层（Session 功能）

**目标**：创建 session feature，包括 hooks、store、components

#### 3.1 创建目录结构

```
features/session/
├── components/
│   ├── SessionList.tsx       # 主列表组件
│   ├── ProjectGroup.tsx      # 项目分组组件
│   ├── SessionItem.tsx       # 单个 session 项
│   └── index.ts
├── hooks/
│   ├── useSessionList.ts     # 核心 hook（API + 聚合）
│   ├── useSessionActions.ts  # 操作 hook（切换、标记已读）
│   └── index.ts
├── store/
│   └── sessionStore.ts       # Zustand store
├── types.ts
└── index.ts
```

#### 3.2 实现 Store（features/session/store/sessionStore.ts）

```typescript
import { create } from 'zustand';
import { ProjectGroup } from '@/shared/adapters/sessionAdapter';

interface SessionState {
  projectGroups: ProjectGroup[];
  activeSessionId: string | null;
  
  // Actions
  setProjectGroups: (groups: ProjectGroup[]) => void;
  selectSession: (sessionId: string) => void;
  updateSession: (sessionId: string, updates: Partial<SessionItem>) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  projectGroups: [],
  activeSessionId: null,
  
  setProjectGroups: (groups) => set({ projectGroups: groups }),
  selectSession: (sessionId) => set({ activeSessionId: sessionId }),
  updateSession: (sessionId, updates) => set((state) => ({
    projectGroups: state.projectGroups.map(group => ({
      ...group,
      sessions: group.sessions.map(s => 
        s.id === sessionId ? { ...s, ...updates } : s
      )
    }))
  })),
}));
```

#### 3.3 实现核心 Hook（features/session/hooks/useSessionList.ts）

```typescript
import { useEffect } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { groupChatApi } from '@/core/api';
import { storage } from '@/core/storage';
import { groupSessionsByProject } from '@/shared/adapters/sessionAdapter';
import { wsManager } from '@/core/websocket';

export function useSessionList() {
  const { projectGroups, setProjectGroups } = useSessionStore();

  useEffect(() => {
    async function fetchSessions() {
      // 1. 并行获取数据
      const [chats, lastViewRecords] = await Promise.all([
        groupChatApi.listGroupChats(),
        storage.getLastViewRecords(),
      ]);

      // 2. 聚合数据
      const groups = groupSessionsByProject(chats, lastViewRecords);

      // 3. 更新 store
      setProjectGroups(groups);
    }

    fetchSessions();

    // 4. 监听 WebSocket 更新
    const unsubscribe = wsManager.on('message', (data) => {
      if (data.type === 'chat_updated') {
        // 更新对应的 session
        fetchSessions(); // 简化实现：重新获取全部
      }
    });

    return unsubscribe;
  }, [setProjectGroups]);

  return { projectGroups };
}
```

#### 3.4 实现操作 Hook（features/session/hooks/useSessionActions.ts）

```typescript
import { useSessionStore } from '../store/sessionStore';
import { storage } from '@/core/storage';

export function useSessionActions() {
  const { selectSession, updateSession } = useSessionStore();

  const handleSelectSession = async (sessionId: string) => {
    // 1. 切换 session
    selectSession(sessionId);

    // 2. 标记为已读
    const now = new Date().toISOString();
    await storage.setLastView(sessionId, now);

    // 3. 更新本地状态
    updateSession(sessionId, { isUnread: false });
  };

  return { handleSelectSession };
}
```

#### 3.5 实现 UI 组件

**SessionList.tsx**（主列表）：
```tsx
import { useSessionList } from '../hooks/useSessionList';
import { ProjectGroup } from './ProjectGroup';

export function SessionList() {
  const { projectGroups } = useSessionList();

  return (
    <div className="session-list">
      {projectGroups.map(group => (
        <ProjectGroup key={group.projectPath} group={group} />
      ))}
    </div>
  );
}
```

**ProjectGroup.tsx**（项目分组）：
```tsx
import { useState } from 'react';
import { ProjectGroup as ProjectGroupType } from '@/shared/adapters/sessionAdapter';
import { SessionItem } from './SessionItem';

export function ProjectGroup({ group }: { group: ProjectGroupType }) {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="project-group">
      <div className="project-header" onClick={() => setIsExpanded(!isExpanded)}>
        <span>{group.projectName}</span>
        <span>{isExpanded ? '▼' : '▶'}</span>
      </div>
      
      {isExpanded && (
        <div className="sessions">
          {group.sessions.map(session => (
            <SessionItem key={session.id} session={session} />
          ))}
        </div>
      )}
    </div>
  );
}
```

**SessionItem.tsx**（单个 session）：
```tsx
import { SessionItem as SessionItemType } from '@/shared/adapters/sessionAdapter';
import { useSessionActions } from '../hooks/useSessionActions';
import { formatRelativeTime } from '@/shared/adapters/sessionAdapter';

export function SessionItem({ session }: { session: SessionItemType }) {
  const { handleSelectSession } = useSessionActions();

  return (
    <div 
      className={`session-item ${session.isUnread ? 'unread' : ''}`}
      onClick={() => handleSelectSession(session.id)}
    >
      <div className="session-title">{session.title}</div>
      <div className="session-preview">{session.preview}</div>
      <div className="session-meta">
        <span>{formatRelativeTime(session.lastUpdateAt)}</span>
        {session.isUnread && <span className="unread-badge">●</span>}
      </div>
    </div>
  );
}
```

---

### Phase 4：集成到布局

**目标**：将 SessionList 集成到 LeftSidebar

#### 4.1 修改 LeftSidebar（layouts/LeftSidebar/LeftSidebar.tsx）

```tsx
import { SessionList } from '@/features/session';

export function LeftSidebar() {
  return (
    <div className="left-sidebar">
      <div className="sidebar-header">
        <button>+ 新对话</button>
      </div>
      
      <SessionList />
    </div>
  );
}
```

---

### Phase 5：添加样式

**目标**：实现两层结构的 UI 样式

#### 5.1 创建样式文件（features/session/components/SessionList.css）

```css
.session-list {
  overflow-y: auto;
  height: 100%;
}

.project-group {
  margin-bottom: 16px;
}

.project-header {
  padding: 8px 16px;
  cursor: pointer;
  font-weight: 600;
  background: var(--bg-secondary);
}

.sessions {
  padding-left: 16px;
}

.session-item {
  padding: 12px 16px;
  cursor: pointer;
  border-left: 3px solid transparent;
  transition: all 0.2s;
}

.session-item:hover {
  background: var(--bg-hover);
}

.session-item.unread {
  font-weight: 600;
  border-left-color: var(--primary-color);
}

.unread-badge {
  color: var(--primary-color);
  font-size: 20px;
}
```

---

## 验证步骤

### 1. 单元测试
```bash
npm test -- sessionAdapter.test.ts
npm test -- useSessionList.test.ts
```

### 2. 手动测试

**测试场景**：
1. **初始加载**：
   - 启动应用，检查 session 列表是否按项目分组
   - 验证未读标记是否正确显示

2. **切换 session**：
   - 点击某个 session，检查是否切换成功
   - 验证未读标记是否消失
   - 检查 IndexedDB 是否存储了 `last_view_at`

3. **实时更新**：
   - 使用另一个客户端发送消息
   - 检查 session 列表是否自动更新预览内容
   - 验证排序是否更新（最新消息在前）

4. **项目分组**：
   - 检查同一项目下的 session 是否聚合在一起
   - 验证项目名提取是否正确
   - 测试折叠/展开项目分组

### 3. 集成测试

**测试流程**：
```bash
# 1. 启动后端
cd backend
python -m uvicorn app.main:app --reload

# 2. 启动前端
cd frontend
npm run dev

# 3. 打开浏览器
# http://localhost:5173

# 4. 检查控制台是否有错误
# 5. 使用 DevTools 查看 IndexedDB
# 6. 使用 WebSocket 工具模拟消息推送
```

---

## 关键文件清单

**新建文件**（按创建顺序）：
1. `shared/adapters/sessionAdapter.ts` - 数据聚合
2. `shared/adapters/sessionAdapter.test.ts` - 单元测试
3. `core/storage/index.ts` - 本地存储
4. `features/session/store/sessionStore.ts` - 状态管理
5. `features/session/hooks/useSessionList.ts` - 核心 hook
6. `features/session/hooks/useSessionActions.ts` - 操作 hook
7. `features/session/components/SessionList.tsx` - UI 组件
8. `features/session/components/ProjectGroup.tsx` - UI 组件
9. `features/session/components/SessionItem.tsx` - UI 组件
10. `features/session/components/SessionList.css` - 样式
11. `features/session/index.ts` - 导出

**修改文件**：
1. `shared/types/api-schemas.ts` - 新增类型
2. `layouts/LeftSidebar/LeftSidebar.tsx` - 集成 SessionList
3. `main.tsx` - 初始化 storage

---

## 架构遵循清单

✅ **单向依赖**：features → shared → core  
✅ **纯函数 Adapter**：无副作用、可测试  
✅ **Hooks 管理副作用**：API 调用、WebSocket 监听在 hooks 中  
✅ **Store 只存状态**：不包含任何副作用  
✅ **类型安全**：所有函数有显式类型签名  
✅ **测试共置**：单元测试文件与源码同目录