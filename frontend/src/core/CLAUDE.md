# Core CLAUDE.md

> 上级规则：[`../../CLAUDE.md`](../../CLAUDE.md)（全局架构约束已在上级定义）

## 编码规则

### WebSocket 管理器

**禁止**：
- ❌ 处理具体业务消息（如 `sendChatMessage`）

**示例**：
```typescript
// ✅ 正确：通用的消息分发
class WebSocketManager {
  on(event: string, callback: (data: any) => void) { ... }
  send(event: string, data: any) { ... }
}

// ❌ 错误：包含业务逻辑
class WebSocketManager {
  sendChatMessage(text: string) {
    this.send('chat', { content: text, sender: 'me' });
  }
}
```

---

### API 客户端

**禁止**：
- ❌ 定义具体的业务接口（如 `getChatMessages`）

**示例**：
```typescript
// ✅ 正确：通用的 HTTP 客户端
class ApiClient {
  get<T>(url: string): Promise<T> { ... }
  post<T>(url: string, data: any): Promise<T> { ... }
}

// ❌ 错误：包含业务接口
class ApiClient {
  getChatMessages(sessionId: string) {
    return this.get(`/chat/${sessionId}/messages`);
  }
}
```

---

### 本地存储

**禁止**：
- ❌ 定义具体的存储 schema（如 `ChatMessage` 表）

**示例**：
```typescript
// ✅ 正确：通用的存储接口
class Storage {
  set(key: string, value: any): Promise<void> { ... }
  get(key: string): Promise<any> { ... }
}

// ❌ 错误：包含业务 schema
class Storage {
  saveChatMessage(msg: ChatMessage) {
    return this.set(`chat:${msg.id}`, msg);
  }
}
```
