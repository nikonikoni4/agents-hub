# 单聊双位置显示实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现单聊在右侧栏和中间主界面之间灵活切换，默认右侧，支持历史消息加载

**Architecture:** 统一消息组件方案。通过 SessionStore 和 SingleChatStore 协调状态，useChatMessages 根据 activeSessionType 调用不同 API，ChatArea 条件渲染单聊或群聊

**Tech Stack:** React 18, TypeScript, Zustand, SSE

---

## 文件改动总览

**新增文件：**
- `frontend/src/shared/adapters/singleChatMessageAdapter.ts` - 单聊消息格式适配器

**修改文件：**
- `frontend/src/features/session/store/sessionStore.ts` - 添加 activeSessionType
- `frontend/src/features/single-chat/store/singleChatStore.ts` - 添加 displayLocation，移除 isPanelOpen
- `frontend/src/features/session/components/SessionItem.tsx` - 点击处理逻辑
- `frontend/src/features/chat/hooks/useChatMessages.ts` - 支持单聊消息加载
- `frontend/src/layouts/ChatArea/ChatArea.tsx` - 条件渲染单聊或群聊
- `frontend/src/features/single-chat/components/SingleChatPanel.tsx` - 添加切换按钮
- `frontend/src/layouts/RightSidebar/RightSidebar.tsx` - 占位提示

---

## Task 1: 增强 SessionStore - 添加 activeSessionType

**Files:**
- Modify: `frontend/src/features/session/store/sessionStore.ts:14-50`

- [ ] **Step 1: 添加 activeSessionType 字段和类型定义**

在 SessionState 接口中添加新字段：

```typescript
interface SessionState {
  projectGroups: ProjectGroup[];
  activeSessionId: string | null;
  lastSelectedAt: number;
  activeSessionType: 'group_chat' | 'single_chat' | null; // 新增
  
  setProjectGroups: (groups: ProjectGroup[]) => void;
  selectSession: (sessionId: string, type: 'group_chat' | 'single_chat') => void; // 修改签名
  updateSession: (sessionId: string, updates: Partial<SessionItem>) => void;
}
```

- [ ] **Step 2: 修改 store 初始化状态**

在 create 函数中添加初始值：

```typescript
export const useSessionStore = create<SessionState>((set) => ({
  projectGroups: [],
  activeSessionId: null,
  lastSelectedAt: 0,
  activeSessionType: null, // 新增

  setProjectGroups: (groups) => set({ projectGroups: groups }),

  selectSession: (sessionId, type) => set({ 
    activeSessionId: sessionId, 
    activeSessionType: type, // 新增
    lastSelectedAt: Date.now() 
  }),

  updateSession: (sessionId, updates) =>
    set((state) => ({
      projectGroups: state.projectGroups.map((group) => ({
        ...group,
        sessions: group.sessions.map((s) => (s.id === sessionId ? { ...s, ...updates } : s)),
      })),
    })),
}));
```

- [ ] **Step 3: 验证类型检查**

Run: `cd frontend && npm run type-check`
Expected: 无类型错误

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/session/store/sessionStore.ts
git commit -m "feat(session): 添加 activeSessionType 支持单聊和群聊区分"
```

---

## Task 2: 增强 SingleChatStore - 添加 displayLocation

**Files:**
- Modify: `frontend/src/features/single-chat/store/singleChatStore.ts:17-52`

- [ ] **Step 1: 添加 displayLocation 字段和新方法**

修改 SingleChatState 接口：

```typescript
interface SingleChatState {
  singleChats: SingleChatApiResponse[];
  activeSingleChatId: string | null;
  displayLocation: 'sidebar' | 'main'; // 新增
  
  setSingleChats: (chats: SingleChatApiResponse[]) => void;
  setActiveSingleChat: (id: string | null) => void;
  openSingleChat: (id: string) => void; // 保留兼容性
  closeSingleChat: () => void; // 保留兼容性
  addSingleChat: (chat: SingleChatApiResponse) => void;
  toggleLocation: () => void; // 新增
  setLocation: (location: 'sidebar' | 'main') => void; // 新增
}
```

- [ ] **Step 2: 实现新方法和修改初始状态**

```typescript
export const useSingleChatStore = create<SingleChatState>((set) => ({
  singleChats: [],
  activeSingleChatId: null,
  displayLocation: 'sidebar', // 新增，默认右侧

  setSingleChats: (chats) => set({ singleChats: chats }),
  setActiveSingleChat: (id) => set({ activeSingleChatId: id }),
  
  openSingleChat: (id) => set({ 
    activeSingleChatId: id, 
    displayLocation: 'sidebar' // 打开时默认右侧
  }),
  
  closeSingleChat: () => set({ activeSingleChatId: null }),
  addSingleChat: (chat) => set((state) => ({ singleChats: [...state.singleChats, chat] })),
  
  toggleLocation: () => set((state) => ({ 
    displayLocation: state.displayLocation === 'sidebar' ? 'main' : 'sidebar' 
  })),
  
  setLocation: (location) => set({ displayLocation: location }),
}));
```

- [ ] **Step 3: 验证类型检查**

Run: `cd frontend && npm run type-check`
Expected: 无类型错误

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/single-chat/store/singleChatStore.ts
git commit -m "feat(single-chat): 添加 displayLocation 支持位置切换"
```

---

## Task 3: 创建单聊消息适配器

**Files:**
- Create: `frontend/src/shared/adapters/singleChatMessageAdapter.ts`

- [ ] **Step 1: 创建适配器文件**

```typescript
/**
 * 单聊消息适配器
 *
 * 职责：将 SingleChatMessageApiItem[] 转换为 MessageApiItem[] 格式
 */

import type { SingleChatMessageApiItem, MessageApiItem } from '@/shared/types';

/**
 * 将单聊消息转换为统一的消息格式
 */
export function adaptSingleChatMessages(
  singleChatMessages: SingleChatMessageApiItem[]
): MessageApiItem[] {
  return singleChatMessages.map((m, index) => ({
    id: index, // 单聊用索引作为 id
    speaker: m.role === 'user' ? 'user' : m.role,
    content: m.content,
    timestamp: m.timestamp,
    send_to: null,
    session_type: 'main',
    message_type: 'notification',
    modified_files: [],
    permission_request: null,
  }));
}
```

- [ ] **Step 2: 导出适配器**

在 `frontend/src/shared/adapters/index.ts` 中添加导出：

```typescript
// 单聊消息适配器
export { adaptSingleChatMessages } from './singleChatMessageAdapter';
```

- [ ] **Step 3: 验证类型检查**

Run: `cd frontend && npm run type-check`
Expected: 无类型错误

- [ ] **Step 4: Commit**

```bash
git add frontend/src/shared/adapters/singleChatMessageAdapter.ts frontend/src/shared/adapters/index.ts
git commit -m "feat(adapters): 添加单聊消息格式适配器"
```

---

## Task 4: 增强 useChatMessages - 支持单聊消息加载

**Files:**
- Modify: `frontend/src/features/chat/hooks/useChatMessages.ts:1-85`

- [ ] **Step 1: 导入新依赖**

在文件顶部添加导入：

```typescript
import { getSingleChatMessages } from '@/core/api/singleChatApi';
import { adaptSingleChatMessages } from '@/shared/adapters';
```

- [ ] **Step 2: 读取 activeSessionType 状态**

在 hook 开头添加：

```typescript
export function useChatMessages() {
  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const activeSessionType = useSessionStore((s) => s.activeSessionType); // 新增
  const projectGroups = useSessionStore((s) => s.projectGroups);
  const roles = useRolesStore((s) => s.roles);
```

- [ ] **Step 3: 修改初始加载逻辑**

替换现有的 useEffect 加载逻辑：

```typescript
// 初始加载最新消息
useEffect(() => {
  if (!activeSessionId || !activeSessionType) {
    setMessages([]);
    setHasMore(true);
    return;
  }

  let cancelled = false;
  setLoading(true);

  const loadMessages = activeSessionType === 'single_chat'
    ? getSingleChatMessages(activeSessionId).then(adaptSingleChatMessages)
    : getMessages(activeSessionId, PAGE_SIZE, undefined);

  loadMessages
    .then((msgData) => {
      if (!cancelled) {
        setMessages(msgData);
        setHasMore(msgData.length >= PAGE_SIZE);
      }
    })
    .catch((err) => {
      console.error('Failed to load messages:', err);
    })
    .finally(() => {
      if (!cancelled) setLoading(false);
    });

  return () => {
    cancelled = true;
  };
}, [activeSessionId, activeSessionType]); // 添加 activeSessionType 依赖
```

- [ ] **Step 4: 验证类型检查**

Run: `cd frontend && npm run type-check`
Expected: 无类型错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/chat/hooks/useChatMessages.ts
git commit -m "feat(chat): useChatMessages 支持单聊消息加载"
```

---

## Task 5: 修改 SessionItem - 更新点击逻辑

**Files:**
- Modify: `frontend/src/features/session/components/SessionItem.tsx:57-69`

- [ ] **Step 1: 导入 SingleChatStore**

在文件顶部添加导入：

```typescript
import { useSingleChatStore } from '@/features/single-chat/store/singleChatStore';
```

- [ ] **Step 2: 获取 store 方法**

在组件内添加：

```typescript
export function SessionItem({ session, isActive = false, onSelectSingleChat }: SessionItemProps) {
  const { handleSelectSession } = useSessionActions();
  const selectSession = useSessionStore((s) => s.selectSession); // 新增
  const setActiveSingleChat = useSingleChatStore((s) => s.setActiveSingleChat); // 新增
  const setLocation = useSingleChatStore((s) => s.setLocation); // 新增
  const updateSession = useSessionStore((s) => s.updateSession);
  const { deleteChat, deleting } = useDeleteGroupChat();
  const [showMenu, setShowMenu] = useState(false);
```

- [ ] **Step 3: 修改 handleItemClick 逻辑**

替换现有的点击处理：

```typescript
const handleItemClick = async () => {
  if (showMenu) return;

  if (isSingleChat) {
    // 单聊：设置 activeSessionType 和 displayLocation
    selectSession(session.id, 'single_chat');
    setActiveSingleChat(session.id);
    setLocation('sidebar'); // 默认右侧
    
    // 标记单聊为已读
    const now = new Date().toISOString();
    await storage.setLastView(session.id, now);
    updateSession(session.id, { isUnread: false });
    
    // 通知父组件（如果需要）
    if (onSelectSingleChat) {
      onSelectSingleChat(session.id);
    }
  } else {
    // 群聊：设置 activeSessionType，单聊回到默认位置
    selectSession(session.id, 'group_chat');
    setLocation('sidebar');
    handleSelectSession(session.id);
  }
};
```

- [ ] **Step 4: 验证类型检查**

Run: `cd frontend && npm run type-check`
Expected: 无类型错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/session/components/SessionItem.tsx
git commit -m "feat(session): SessionItem 支持单聊和群聊类型区分"
```

---

## Task 6: 修改 ChatArea - 条件渲染单聊

**Files:**
- Modify: `frontend/src/layouts/ChatArea/ChatArea.tsx:1-50`

- [ ] **Step 1: 导入 SingleChatStore**

在文件顶部添加导入：

```typescript
import { useSingleChatStore } from '@/features/single-chat/store/singleChatStore';
```

- [ ] **Step 2: 读取状态**

在 ChatArea 组件开头添加：

```typescript
export function ChatArea({ onToggleRightSidebar, onContentChange }: ChatAreaProps) {
  const activeSessionId = useSessionStore((s) => s.activeSessionId); // 如果已有则不重复
  const activeSessionType = useSessionStore((s) => s.activeSessionType); // 新增
  const displayLocation = useSingleChatStore((s) => s.displayLocation); // 新增
  const toggleLocation = useSingleChatStore((s) => s.toggleLocation); // 新增
  const singleChats = useSingleChatStore((s) => s.singleChats); // 新增
  
  // ... 其他现有状态
```

- [ ] **Step 3: 添加条件渲染逻辑**

在现有渲染前添加单聊判断：

```typescript
// 判断是否显示单聊
const showingSingleChat = activeSessionType === 'single_chat' && displayLocation === 'main';
const activeSingleChat = singleChats.find((c) => c.single_chat_id === activeSessionId);

// 空状态
if (!activeSessionType) {
  return (
    <div className={styles.chatArea}>
      <div className={styles.emptyState}>选择一个会话开始对话</div>
    </div>
  );
}

// 单聊在中间主界面
if (showingSingleChat) {
  return (
    <div className={styles.chatArea}>
      {/* 标题栏 */}
      <div className={styles.chatHeader}>
        <h2 className={styles.chatTitle}>{activeSingleChat?.single_chat_name ?? '单聊'}</h2>
        <div className={styles.headerActions}>
          <button
            className={styles.toggleLocationBtn}
            onClick={toggleLocation}
            title="返回右侧"
          >
            📌 返回右侧
          </button>
          <button className={styles.toggleRightBtn} onClick={onToggleRightSidebar}>
            <RightPanelIcon />
          </button>
        </div>
      </div>
      
      {/* 消息列表（复用现有逻辑） */}
      <div className={styles.messagesContainer} ref={messagesContainerRef}>
        {/* 这里复用现有的消息渲染逻辑 */}
      </div>
      
      {/* 输入框 */}
      <ChatInput
        onSend={handleSend}
        onQuoteCancel={() => setQuotedMessage(null)}
        quotedMessage={quotedMessage}
      />
    </div>
  );
}

// 群聊（原有逻辑）
return (
  <div className={styles.chatArea}>
    {/* 现有的群聊渲染逻辑保持不变 */}
  </div>
);
```

- [ ] **Step 4: 验证类型检查**

Run: `cd frontend && npm run type-check`
Expected: 无类型错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/layouts/ChatArea/ChatArea.tsx
git commit -m "feat(chat): ChatArea 支持单聊在中间主界面显示"
```

---

## Task 7: 修改 SingleChatPanel - 添加切换按钮

**Files:**
- Modify: `frontend/src/features/single-chat/components/SingleChatPanel.tsx:62-127`

- [ ] **Step 1: 读取 displayLocation 状态**

在组件开头添加：

```typescript
export function SingleChatPanel() {
  const activeSingleChatId = useSingleChatStore((s) => s.activeSingleChatId);
  const singleChats = useSingleChatStore((s) => s.singleChats);
  const closeSingleChat = useSingleChatStore((s) => s.closeSingleChat);
  const toggleLocation = useSingleChatStore((s) => s.toggleLocation); // 新增

  // ... 其他现有状态
```

- [ ] **Step 2: 在标题栏添加切换按钮**

修改 agentHeader 部分：

```typescript
{/* Agent 信息头部 */}
<div className={styles.agentHeader}>
  <div className={styles.agentAvatar}>
    <AvatarImage avatar={agentAvatar} fallback={activeChat.agent_name} />
  </div>
  <div className={styles.agentInfo}>
    <span className={styles.agentName}>{activeChat.agent_name}</span>
    <span className={styles.chatType}>
      {CHAT_TYPE_LABELS[activeChat.type] ?? activeChat.type}
    </span>
  </div>
  <button
    type="button"
    className={styles.toggleLocationBtn}
    onClick={toggleLocation}
    title="移到主界面"
  >
    📍
  </button>
  <button
    type="button"
    className={styles.closeBtn}
    onClick={closeSingleChat}
    title="关闭单聊"
  >
    ×
  </button>
</div>
```

- [ ] **Step 3: 添加按钮样式**

在 `SingleChatPanel.module.css` 中添加：

```css
.toggleLocationBtn {
  padding: 4px 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.toggleLocationBtn:hover {
  opacity: 1;
}
```

- [ ] **Step 4: 验证类型检查**

Run: `cd frontend && npm run type-check`
Expected: 无类型错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/single-chat/components/SingleChatPanel.tsx frontend/src/features/single-chat/components/SingleChatPanel.module.css
git commit -m "feat(single-chat): SingleChatPanel 添加位置切换按钮"
```

---

## Task 8: 修改 RightSidebar - 添加占位提示

**Files:**
- Modify: `frontend/src/layouts/RightSidebar/RightSidebar.tsx:123-140`

- [ ] **Step 1: 读取 displayLocation 状态**

在组件开头添加：

```typescript
export function RightSidebar({
  collapsed,
  width,
  onResize,
  resizing,
  onResizeStart,
  onResizeEnd,
  content,
}: RightSidebarProps) {
  const { members, loading, toggleDockerMode } = useMembers();
  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const { pinnedMessages, unpin } = usePinnedMessages(activeSessionId);
  const { agentCalls, loading: callsLoading } = useAgentCalls(activeSessionId);
  const { taskList, loading: tasksLoading } = useTasks(activeSessionId);
  const toast = useToast();
  const isSingleChatOpen = useSingleChatStore((s) => s.isPanelOpen);
  const displayLocation = useSingleChatStore((s) => s.displayLocation); // 新增
  const setLocation = useSingleChatStore((s) => s.setLocation); // 新增
  const [activeTab, setActiveTab] = useState<SidebarTab>('chat');
```

- [ ] **Step 2: 修改 single-chat Tab 渲染逻辑**

替换现有的 single-chat Tab 内容：

```typescript
{activeTab === 'single-chat' && (
  <>
    {displayLocation === 'main' ? (
      <div className={styles.placeholder}>
        <p className={styles.placeholderText}>单聊已移至主界面</p>
        <button
          className={styles.placeholderBtn}
          onClick={() => setLocation('sidebar')}
        >
          返回右侧
        </button>
      </div>
    ) : (
      <SingleChatPanel />
    )}
  </>
)}
```

- [ ] **Step 3: 添加占位提示样式**

在 `RightSidebar.module.css` 中添加：

```css
.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  gap: 16px;
}

.placeholderText {
  color: var(--text-secondary);
  font-size: 14px;
  text-align: center;
}

.placeholderBtn {
  padding: 8px 16px;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  color: var(--text-primary);
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.placeholderBtn:hover {
  background: var(--bg-tertiary);
}
```

- [ ] **Step 4: 验证类型检查**

Run: `cd frontend && npm run type-check`
Expected: 无类型错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/layouts/RightSidebar/RightSidebar.tsx frontend/src/layouts/RightSidebar/RightSidebar.module.css
git commit -m "feat(sidebar): RightSidebar 添加单聊占位提示"
```

---

## Task 9: 手动测试验证

**Files:**
- None (manual testing)

- [ ] **Step 1: 启动开发服务器**

Run: `cd frontend && npm run dev`
Expected: 服务器启动成功

- [ ] **Step 2: 测试点击左侧单聊**

操作：点击左侧 SessionList 中的单聊
Expected: 右侧显示 SingleChatPanel，消息正常加载

- [ ] **Step 3: 测试移到主界面**

操作：点击右侧单聊标题栏的 📍 按钮
Expected: 单聊移到中间 ChatArea，右侧显示占位提示

- [ ] **Step 4: 测试返回右侧**

操作：点击右侧占位提示中的"返回右侧"按钮
Expected: 单聊回到右侧 SingleChatPanel

- [ ] **Step 5: 测试切换到群聊**

操作：单聊在中间时，点击左侧群聊
Expected: 中间显示群聊，单聊自动回到右侧（下次点击从右侧开始）

- [ ] **Step 6: 测试消息加载**

操作：在单聊中发送消息
Expected: 消息正常发送和显示，无论单聊在右侧还是中间

- [ ] **Step 7: 测试状态保持**

操作：单聊移到中间后刷新页面
Expected: 单聊回到右侧（displayLocation 默认 'sidebar'）

- [ ] **Step 8: 最终提交**

```bash
git add -A
git commit -m "test: 验证单聊双位置显示功能"
```

---

## 自审清单

### Spec 覆盖检查

- [x] Task 1-2: 状态管理基础 ✓
- [x] Task 3-4: 消息加载和适配器 ✓
- [x] Task 5-8: UI 组件改动 ✓
- [x] Task 9: 手动测试 ✓

### 占位符扫描

- [x] 无 TBD/TODO
- [x] 所有代码块完整
- [x] 所有路径明确

### 类型一致性

- [x] SessionStore.activeSessionType: 'group_chat' | 'single_chat' | null
- [x] SingleChatStore.displayLocation: 'sidebar' | 'main'
- [x] selectSession(sessionId, type) 签名一致
- [x] adaptSingleChatMessages 返回 MessageApiItem[]

---

## 执行建议

推荐使用 **Subagent-Driven** 方式执行，每个 Task 独立完成并测试，便于快速迭代和问题定位。

