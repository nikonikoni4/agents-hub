# 单聊双位置显示设计

## 概述

本设计实现单聊在右侧栏（快速对话模式）和中间主界面（深度对话模式）之间灵活切换的功能。

**核心原则**：
- 默认显示在右侧栏（轻量级快速对话）
- 通过切换按钮可以移到中间主界面（获得更大空间）
- 单聊和群聊统一消息加载逻辑（代码复用）
- 状态管理简洁清晰

## 问题背景

**当前状态**：
- 单聊只能显示在右侧栏的 SingleChatPanel
- 无法加载历史消息（点击单聊后无反应）
- 右侧空间有限，不适合长对话

**用户需求**：
1. 单聊能加载历史消息
2. 单聊可以在两个位置显示：
   - 右侧栏：快速对话，不遮挡群聊
   - 中间主界面：深度对话，更大空间

## 设计方案

### 1. 架构决策

**方案选择：统一消息组件 + 位置状态**

优势：
- 代码复用最大化（消息列表、输入框、渲染逻辑共享）
- 用户体验一致（群聊和单聊交互一致）
- 状态管理简洁（一个位置标记控制渲染）
- 易于扩展（未来单聊功能直接复用群聊逻辑）

### 2. 状态管理

#### SessionStore 增强

```typescript
interface SessionState {
  // 现有字段
  projectGroups: ProjectGroup[];
  activeSessionId: string | null;
  lastSelectedAt: number;
  
  // 新增字段
  activeSessionType: 'group_chat' | 'single_chat' | null;
  
  // 修改操作
  selectSession: (sessionId: string, type: 'group_chat' | 'single_chat') => void;
}
```

**职责**：
- 管理当前激活的 session（群聊或单聊）
- 通过 `activeSessionType` 标记当前类型

#### SingleChatStore 增强

```typescript
interface SingleChatState {
  // 现有字段
  singleChats: SingleChatApiResponse[];
  activeSingleChatId: string | null;
  
  // 新增字段
  displayLocation: 'sidebar' | 'main';
  
  // 移除字段
  // isPanelOpen: boolean; // 改用 displayLocation 判断
  
  // 新增操作
  toggleLocation: () => void;
  setLocation: (location: 'sidebar' | 'main') => void;
}
```

**职责**：
- 管理单聊列表和当前激活的单聊
- 通过 `displayLocation` 控制单聊显示位置

#### 状态协调规则

| 用户操作 | SessionStore | SingleChatStore | 结果 |
|---------|-------------|----------------|------|
| 点击左侧单聊 | `selectSession(id, 'single_chat')` | `setLocation('sidebar')` | 右侧显示单聊 |
| 点击"移到主界面" | 不变 | `toggleLocation()` → `'main'` | 中间显示单聊 |
| 点击"返回右侧" | 不变 | `setLocation('sidebar')` | 右侧显示单聊 |
| 单聊在中间时点击群聊 | `selectSession(id, 'group_chat')` | `setLocation('sidebar')` | 中间显示群聊，单聊回到右侧 |

### 3. 消息加载逻辑

#### useChatMessages 增强

**核心改动**：根据 `activeSessionType` 调用不同 API

```typescript
export function useChatMessages() {
  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const activeSessionType = useSessionStore((s) => s.activeSessionType);
  
  useEffect(() => {
    if (!activeSessionId || !activeSessionType) {
      setMessages([]);
      return;
    }
    
    const loadMessages = activeSessionType === 'single_chat'
      ? getSingleChatMessages(activeSessionId)
      : getMessages(activeSessionId, PAGE_SIZE, undefined);
    
    loadMessages
      .then((data) => {
        const adapted = activeSessionType === 'single_chat' 
          ? adaptSingleChatMessages(data)
          : data;
        setMessages(adapted);
      })
      .catch((err) => {
        console.error('Failed to load messages:', err);
        setMessages([]);
      });
  }, [activeSessionId, activeSessionType]);
}
```

#### 消息格式适配器

**目的**：统一单聊和群聊的消息格式

```typescript
// shared/adapters/messageAdapter.ts
export function adaptSingleChatMessages(
  singleChatMessages: SingleChatMessageApiItem[]
): MessageApiItem[] {
  return singleChatMessages.map((m) => ({
    id: parseInt(m.id) || 0,
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

### 4. UI 组件改动

#### A. SessionList（点击处理）

```typescript
const handleSessionClick = (session: SessionItem) => {
  if (session.type === 'single_chat') {
    sessionStore.selectSession(session.id, 'single_chat');
    singleChatStore.setActiveSingleChat(session.id);
    singleChatStore.setLocation('sidebar'); // 默认右侧
  } else {
    sessionStore.selectSession(session.id, 'group_chat');
    singleChatStore.setLocation('sidebar'); // 群聊激活时，单聊回到默认位置
  }
};
```

#### B. ChatArea（条件渲染）

```typescript
export function ChatArea() {
  const activeSessionType = useSessionStore((s) => s.activeSessionType);
  const displayLocation = useSingleChatStore((s) => s.displayLocation);
  
  const showingSingleChat = 
    activeSessionType === 'single_chat' && displayLocation === 'main';
  
  if (!activeSessionType) {
    return <div className={styles.emptyState}>选择一个会话开始对话</div>;
  }
  
  // 单聊在中间主界面
  if (showingSingleChat) {
    return (
      <div className={styles.chatArea}>
        {/* 标题栏：显示单聊名称和切换按钮 */}
        <div className={styles.chatHeader}>
          <h2>{activeSingleChatName}</h2>
          <button onClick={() => singleChatStore.toggleLocation()}>
            📌 返回右侧
          </button>
        </div>
        {/* 消息列表：复用 MessageBubble 组件 */}
        <div className={styles.messageList}>
          {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
        </div>
        {/* 输入框：复用 ChatInput 组件 */}
        <ChatInput onSend={handleSendMessage} />
      </div>
    );
  }
  
  // 群聊（原有逻辑）
  return (
    <div className={styles.chatArea}>
      {/* 现有的消息列表、输入框 */}
    </div>
  );
}
```

#### C. SingleChatPanel（添加切换按钮）

**说明**：SingleChatPanel 只在右侧栏显示（displayLocation === 'sidebar'），标题栏有切换按钮。

```typescript
export function SingleChatPanel() {
  const displayLocation = useSingleChatStore((s) => s.displayLocation);
  const toggleLocation = useSingleChatStore((s) => s.toggleLocation);
  
  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <span className={styles.title}>{activeChat.single_chat_name}</span>
        <button 
          className={styles.toggleButton}
          onClick={toggleLocation}
          title="移到主界面"
        >
          📍
        </button>
      </div>
      {/* 消息列表、输入框 */}
    </div>
  );
}
```

**当单聊在中间时**：
- SingleChatPanel 不渲染（右侧显示占位提示）
- ChatArea 负责渲染单聊内容（包括切换按钮）

#### D. RightSidebar（占位提示）

```typescript
{activeTab === 'single-chat' && (
  <>
    {displayLocation === 'main' ? (
      <div className={styles.placeholder}>
        <p>单聊已移至主界面</p>
        <button onClick={() => singleChatStore.setLocation('sidebar')}>
          返回右侧
        </button>
      </div>
    ) : (
      <SingleChatPanel />
    )}
  </>
)}
```

### 5. 交互流程

#### 流程 1：点击左侧单聊（默认右侧）

```
用户点击左侧单聊
  ↓
SessionList 调用：
  - sessionStore.selectSession(id, 'single_chat')
  - singleChatStore.setActiveSingleChat(id)
  - singleChatStore.setLocation('sidebar')
  ↓
RightSidebar 检测到：
  - activeSessionType === 'single_chat'
  - displayLocation === 'sidebar'
  ↓
自动切换到 'single-chat' Tab，显示 SingleChatPanel
  ↓
useChatMessages 加载单聊消息（通过 getSingleChatMessages）
```

#### 流程 2：点击切换按钮（移到中间）

```
用户在右侧单聊面板点击 📍 按钮
  ↓
调用 singleChatStore.toggleLocation()
  ↓
displayLocation 变为 'main'
  ↓
ChatArea 检测到：
  - activeSessionType === 'single_chat'
  - displayLocation === 'main'
  ↓
ChatArea 渲染单聊消息
  ↓
RightSidebar 的 single-chat Tab 显示占位提示
```

#### 流程 3：单聊在中间时点击群聊

```
当前：单聊在中间显示
用户点击左侧群聊
  ↓
SessionList 调用：
  - sessionStore.selectSession(id, 'group_chat')
  - singleChatStore.setLocation('sidebar') // 自动回到默认位置
  ↓
ChatArea 检测到 activeSessionType === 'group_chat'
  ↓
切换到群聊消息视图
  ↓
单聊回到右侧（下次点击从右侧开始）
```

### 6. 边界情况处理

#### A. 删除当前激活的单聊

```typescript
const handleDeleteSingleChat = async (id: string) => {
  await deleteSingleChat(id);
  
  if (activeSessionId === id) {
    sessionStore.selectSession(null, null);
    singleChatStore.setActiveSingleChat(null);
    singleChatStore.setLocation('sidebar'); // 重置位置
  }
};
```

#### B. 消息加载失败

```typescript
loadMessages
  .then((data) => setMessages(adapted))
  .catch((err) => {
    console.error('Failed to load messages:', err);
    setMessages([]);
    // 可选：toast 错误提示
  });
```

#### C. 单聊消息发送（SSE 流式）

```typescript
const handleSendMessage = async (content: string) => {
  if (activeSessionType === 'single_chat') {
    // 使用 SSE 流式发送
    const eventSource = streamSSE(
      `/single-chats/${activeSessionId}/messages/stream`,
      { content },
      (event) => {
        if (event.type === 'text_delta') {
          setStreamingText((prev) => prev + event.content);
        }
      }
    );
  } else {
    // 群聊 WebSocket 发送
    await sendMessage(activeSessionId, content);
  }
};
```

#### D. 空状态提示

```typescript
{messages.length === 0 && !loading && (
  <div className={styles.emptyState}>
    <p>还没有消息，发送第一条消息开始对话</p>
  </div>
)}
```

## 实现优先级

### Phase 1：状态管理基础
- 增强 sessionStore 和 singleChatStore
- 修改 SessionList 点击逻辑

### Phase 2：消息加载
- 修改 useChatMessages 支持单聊
- 创建消息适配器
- 实现单聊 SSE 发送消息

### Phase 3：UI 切换
- ChatArea 条件渲染
- SingleChatPanel 添加切换按钮
- RightSidebar 显示占位提示

### Phase 4：边界处理
- 错误处理
- 空状态提示
- 删除时的清理逻辑

## 测试验证

- [ ] 点击左侧单聊 → 右侧显示单聊面板
- [ ] 点击"移到主界面" → 中间显示单聊，右侧显示提示
- [ ] 点击"返回右侧" → 单聊回到右侧
- [ ] 单聊在中间时，点击群聊 → 单聊自动回到右侧，中间显示群聊
- [ ] 单聊消息正常加载和显示
- [ ] 单聊消息发送（SSE 流式）正常工作
- [ ] 删除当前激活的单聊 → 状态正确清理
- [ ] 单聊和群聊切换时，消息不会混乱

## 技术约束

1. **前端架构约束**：
   - 遵循 features 模块隔离原则
   - store 不包含副作用（API 调用在 hooks 中）
   - 组件通过 hooks 访问状态和逻辑

2. **API 约束**：
   - 单聊使用 SSE 流式响应（`/single-chats/{id}/messages/stream`）
   - 群聊使用 WebSocket 推送
   - 消息格式需要通过适配器统一

3. **用户体验约束**：
   - 状态切换需要流畅无闪烁
   - 消息加载失败需要友好提示
   - 单聊和群聊切换时不能丢失消息

## 未来扩展

1. **记忆位置偏好**：保存用户上次选择的位置，下次打开时恢复
2. **快捷键支持**：通过快捷键快速切换单聊位置
3. **多单聊支持**：中间和右侧同时显示不同的单聊
4. **拖拽支持**：通过拖拽单聊 Tab 改变位置

## 参考资料

- [单聊 API Spec](../specs/2026-06-08-single-chat.md)
- [Frontend Features Spec](../specs/2026-06-06-frontend-features.md)
- [Frontend Core Spec](../specs/2026-06-06-frontend-core.md)
