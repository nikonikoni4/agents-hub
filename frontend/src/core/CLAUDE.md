# Core CLAUDE.md

> 上级规则：[`../../CLAUDE.md`](../../CLAUDE.md)（全局架构约束已在上级定义）

## 编码规则

### 1. 职责范围

**禁止**：
- ❌ WebSocket 管理器处理具体业务消息（如 `sendChatMessage`）
- ❌ API 客户端定义具体的业务接口（如 `getChatMessages`）
- ❌ 本地存储定义具体的存储 schema（如 `ChatMessage` 表）

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

### 2. API 函数类型规范

#### 禁止不必要的类型断言
- ❌ **禁止** 使用 `as Promise<T>` 强制转换 apiClient 返回值
- ✅ 使用泛型参数让 TypeScript 自动推断

**错误示例**：
```typescript
// ❌ 错误：不必要的类型断言
export async function getUser(id: string): Promise<User> {
  return apiClient.get(`/users/${id}`) as Promise<User>;
}
```

**正确做法**：
```typescript
// ✅ 正确：使用泛型参数
export async function getUser(id: string): Promise<User> {
  return apiClient.get<User>(`/users/${id}`);
}
```

**原因**：
- `client.ts` 的响应拦截器已返回 `response.data`
- 类型断言掩盖了真实的类型推断
- AI 会盲目复制这个模式

---

#### API 函数必须有完整的类型签名
- ✅ 显式声明返回类型 `Promise<T>`
- ✅ 显式声明参数类型
- ✅ 使用泛型参数标注请求/响应类型

**正确做法**：
```typescript
// ✅ 完整的类型信息
export async function getUser(id: string): Promise<User> {
  return apiClient.get<User>(`/users/${id}`);
}

export async function createRole(data: CreateRoleRequest): Promise<Role> {
  return apiClient.post<Role>('/roles', data);
}
```

**禁止**：
```typescript
// ❌ 缺少类型信息
export function getUser(id) {
  return apiClient.get(`/users/${id}`);
}
```

---

### 3. Mock 数据规范

#### mockableRequest 调用风格
- ❌ **禁止** 使用 `async/await` 嵌套访问 `response.data`
- ✅ 直接传递 apiClient 调用

**错误示例**：
```typescript
// ❌ 错误：冗长的 async 包装
return mockableRequest(
  async () => {
    const response = await apiClient.get<T>('/path');
    return response.data;  // 不必要，拦截器已返回 data
  },
  mockData
);
```

**正确做法**：
```typescript
// ✅ 正确：简洁直接
return mockableRequest(
  () => apiClient.get<T>('/path'),
  mockData
);
```

---

#### Mock 数据必须不可变
- ❌ **禁止** 使用 `let` 声明 mock 数据
- ❌ **禁止** 在运行时修改 mock 数据
- ✅ 使用 `const` 声明只读 mock 数据

**错误示例**：
```typescript
// ❌ 错误：可变的 mock 数据
let mockRoles: Role[] = [...];

export async function createRole(data: CreateRoleRequest): Promise<Role> {
  if (USE_MOCK) {
    const newRole = { ...data, ... };
    mockRoles.push(newRole);  // 修改全局状态
    return newRole;
  }
  return apiClient.post('/roles', data);
}
```

**正确做法**：
```typescript
// ✅ 正确：不可变的 mock 数据
const MOCK_ROLES: Role[] = [...];
const MOCK_NEW_ROLE: Role = { name: 'New Role', ... };

export async function createRole(data: CreateRoleRequest): Promise<Role> {
  return mockableRequest(
    () => apiClient.post<Role>('/roles', data),
    MOCK_NEW_ROLE  // 返回固定的测试数据
  );
}
```

**原因**：
- Mock 数据是测试夹具，应该不可变
- 避免测试间状态污染
- Mock 不应实现业务逻辑

---

#### Mock 数据职责
- ❌ **禁止** Mock 中实现 CRUD 业务逻辑
- ✅ Mock 只返回静态测试数据

**错误示例**：
```typescript
// ❌ 错误：Mock 中模拟数据库操作
export async function deleteRole(name: string) {
  if (USE_MOCK) {
    const index = mockRoles.findIndex(r => r.name === name);
    if (index >= 0) {
      mockRoles.splice(index, 1);  // 模拟删除
    }
    return { message: 'Deleted' };
  }
  return apiClient.delete(`/roles/${name}`);
}
```

**正确做法**：
```typescript
// ✅ 正确：简单返回固定数据
const MOCK_DELETE_RESPONSE: DeleteResponse = {
  message: 'Successfully deleted',
};

export async function deleteRole(name: string): Promise<DeleteResponse> {
  return mockableRequest(
    () => apiClient.delete<DeleteResponse>(`/roles/${name}`),
    MOCK_DELETE_RESPONSE
  );
}
```

**原因**：
- Mock 的目的是测试前端逻辑，不是模拟后端
- 业务逻辑实现会增加维护成本
- 真实 API 返回不同时会产生不一致
