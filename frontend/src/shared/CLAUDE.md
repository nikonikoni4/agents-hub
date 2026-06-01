# Shared CLAUDE.md

> 上级规则：[`../../CLAUDE.md`](../../CLAUDE.md)（全局架构约束已在上级定义）

## 编码规则

### Components 规则

**禁止**：
- ❌ 业务相关的组件（如 `ChatMessageItem`）
- ❌ 依赖 feature 的 store 或 hooks

**示例**：
```typescript
// ✅ 正确：通用按钮
export function Button({ onClick, children }: ButtonProps) {
  return <button onClick={onClick}>{children}</button>;
}

// ❌ 错误：业务相关
export function ChatMessageItem({ message }: { message: ChatMessage }) {
  // 应该放在 features/chat/components/
}
```

---

### Hooks 规则

**示例**：
```typescript
// ✅ 正确：通用防抖
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debouncedValue;
}

// ❌ 错误：业务相关
export function useChatMessages() {
  // 应该放在 features/chat/hooks/
}
```

---

### Utils 规则

**示例**：
```typescript
// ✅ 正确：通用工具函数
export function formatDate(date: Date): string {
  return date.toISOString().split('T')[0];
}

// ❌ 错误：业务相关
export function formatChatMessage(msg: ChatMessage): string {
  // 应该放在 features/chat/utils/
}
```

---

### Types 规则

**示例**：
```typescript
// ✅ 正确：全局类型
export interface User {
  id: string;
  name: string;
  avatar: string;
}

// ❌ 错误：模块专属类型
export interface ChatMessage {
  // 应该放在 features/chat/types.ts
}
```
