# Features CLAUDE.md

> 上级规则：[`../../CLAUDE.md`](../../CLAUDE.md)（全局架构约束已在上级定义）

## 标准结构（强制）

```
features/<name>/
├── components/  # UI 组件，只调用本模块 hooks
├── hooks/       # 业务逻辑，调用 core 和 store
├── store/       # 状态管理，只管理状态
└── types.ts     # 模块专属类型
```

---

## 编码规则

### Components 规则

**禁止**：
- ❌ 直接调用 `wsManager.send()` 或 `api.xxx()`
- ❌ 直接操作 store（必须通过 hooks）

**示例**：
```typescript
// ✅ 正确
function ChatWindow() {
  const { messages, sendMessage } = useChat();
  return <div>{messages.map(...)}</div>;
}

// ❌ 错误
function ChatWindow() {
  wsManager.send(...);  // 必须通过 hooks
}
```

---

### Hooks 规则

**强制**：
- ✅ 所有 API/WebSocket 调用必须在 hooks 中
- ✅ 使用 `useCallback` 避免重新创建

**示例**：
```typescript
// ✅ 正确
function useChat() {
  const store = useChatStore();
  
  const sendMessage = useCallback((text: string) => {
    wsManager.send({ type: 'message', content: text });
    store.addMessage({ content: text, sender: 'me' });
  }, [store]);
  
  useEffect(() => {
    const handleMessage = (msg) => store.addMessage(msg);
    wsManager.on('message', handleMessage);
    return () => wsManager.off('message', handleMessage);
  }, [store]);
  
  return { messages: store.messages, sendMessage };
}
```

---

### Store 规则

**禁止**：
- ❌ 包含 API 调用、WebSocket 操作、任何副作用

**示例**：
```typescript
// ✅ 正确
const useChatStore = create<ChatStore>()(
  persist(
    (set) => ({
      messages: [],
      addMessage: (msg) => set((state) => ({
        messages: [...state.messages, msg]
      })),
    }),
    { name: 'chat-storage' }
  )
);

// ❌ 错误
const useChatStore = create<ChatStore>((set) => ({
  sendMessage: (text) => {
    wsManager.send(text);  // 副作用必须在 hooks 中
  },
}));
```

---

### Types 规则

**强制**：
- ✅ 只定义本模块使用的类型
- ✅ 多个 feature 使用时移到 `shared/types/`

---

## Feature 间通信

**允许**：
1. 通过 core 层（WebSocket 消息分发）
2. 通过 store 订阅
3. 通过 props（在 layout 中传递）

**示例**：
```typescript
// ✅ 正确：通过 store 订阅
function useChat() {
  const activeSession = useSessionStore((state) => state.activeSession);
}

// ❌ 错误：直接 import
import { SessionList } from '@/features/session/components/SessionList';
```

---

## 创建新 Feature

**何时创建**：独立的业务功能（有自己的 UI + 状态 + 交互）

**步骤**：
1. `mkdir -p features/<name>/{components,hooks,store}`
2. 创建 `types.ts`
3. 创建 store → hooks → components
