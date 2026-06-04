# 前端编码规则审查报告

> **审查时间**: 2026-06-04  
> **审查范围**: frontend/ 所有代码和 CLAUDE.md 文件  
> **当前规则文件**: 4 个（全部符合行数要求 ≤200 行）

---

## 📊 现有规则评估

### ✅ 符合要求的规则文件

| 文件路径 | 行数 | 状态 |
|---------|------|------|
| `frontend/CLAUDE.md` | 126 | ✅ 符合 |
| `frontend/src/core/CLAUDE.md` | 72 | ✅ 符合 |
| `frontend/src/features/CLAUDE.md` | 135 | ✅ 符合 |
| `frontend/src/shared/CLAUDE.md` | 82 | ✅ 符合 |

**总结**: 所有规则文件行数符合要求（≤200 行），结构清晰。

---

## 🔍 代码审查发现

### ✅ 已遵守的规则

1. **模块隔离完善** ✅
   - `features/` 目录为空，无跨 feature 依赖风险
   - `core/` 和 `shared/` 完全独立
   - 无反向依赖（core/shared 不导入 features）

2. **类型定义一致性** ✅
   - 统一使用 `export interface` / `export type`
   - 类型按业务分类（models/api/websocket）
   - 无 class 混用

3. **异步处理统一** ✅
   - 所有 API 调用使用 `async/await`
   - 无 `.then()` 链式调用

4. **导入路径一致** ✅
   - 统一使用 `@/` 别名路径
   - 无相对路径混用

---

### ⚠️ 发现的问题

#### 问题 1: 类型断言滥用（高风险）

**位置**: `frontend/src/core/api/roleApi.ts` (多处)

**问题代码**:
```typescript
export async function listRoles(): Promise<Role[]> {
  return apiClient.get('/roles') as Promise<Role[]>;
}

export async function getRoleInfo(name: string): Promise<Role> {
  return apiClient.get(`/roles/${name}`) as Promise<Role>;
}
```

**问题分析**:
- `client.ts` 的响应拦截器已经返回 `response.data`
- 类型系统能自动推断，无需 `as Promise<T>` 强制转换
- **AI 风险**: 会盲目复制这个模式到所有新 API 函数

**影响范围**: roleApi.ts 共 9 处

---

#### 问题 2: response.data 访问不一致

**位置**: `frontend/src/core/api/skillApi.ts`

**问题代码**:
```typescript
export async function listSkills(): Promise<Skill[]> {
  return mockableRequest(
    async () => {
      const response = await apiClient.get<Skill[]>('/skills');
      return response.data;  // ❌ 不必要
    },
    MOCK_SKILLS
  );
}
```

**对比正确做法** (`groupChatApi.ts`):
```typescript
export async function listGroupChats(isActiveOnly = true): Promise<GroupChatSummary[]> {
  return mockableRequest(
    () => apiClient.get('/group-chats', { params: { is_active_only: isActiveOnly } }),
    // ✅ 直接返回，不访问 .data
    isActiveOnly ? MOCK_GROUP_CHATS : MOCK_GROUP_CHATS_WITH_DELETED
  );
}
```

**影响范围**: skillApi.ts 共 4 处

---

#### 问题 3: Mock 数据使用 `let` 可变

**位置**: `frontend/src/core/api/roleApi.ts`

**问题代码**:
```typescript
let mockRoles: Role[] = [
  MOCK_DEVELOPER_ROLE,
  MOCK_REVIEWER_ROLE,
];

export async function createRole(data: CreateRoleRequest): Promise<Role> {
  if (USE_MOCK) {
    const newRole: Role = { ... };
    mockRoles.push(newRole);  // ❌ 修改全局 mock 状态
    return newRole;
  }
  // ...
}
```

**问题分析**:
- Mock 数据应该是不可变的测试夹具
- 修改全局状态会导致测试间污染
- **AI 风险**: 会认为 mock 要实现完整的 CRUD 业务逻辑

**影响范围**: roleApi.ts 的 `createRole` 和 `deleteRole`

---

### 📋 代码风格不一致

#### 不一致 1: mockableRequest 调用风格

**风格 A** (groupChatApi.ts) - 简洁:
```typescript
return mockableRequest(
  () => apiClient.get(`/group-chats/${chatId}`),
  MOCK_GROUP_CHAT
);
```

**风格 B** (skillApi.ts) - 冗长:
```typescript
return mockableRequest(
  async () => {
    const response = await apiClient.get<Skill[]>('/skills');
    return response.data;
  },
  MOCK_SKILLS
);
```

**统计**:
- 风格 A: 8 处 (groupChatApi.ts)
- 风格 B: 4 处 (skillApi.ts)

**建议**: 统一为风格 A（简洁且正确）

---

#### 不一致 2: API 返回类型标记

**风格 A** - 无泛型参数:
```typescript
apiClient.get(`/group-chats/${chatId}`)
```

**风格 B** - 显式泛型:
```typescript
apiClient.get<Skill[]>('/skills')
```

**建议**: 统一为风格 B（显式更清晰）

---

## 🆕 建议新增的规则

### 规则 1: 禁止不必要的类型断言 (优先级: 🔴 高)

**目标文件**: `frontend/src/core/CLAUDE.md`

**规则内容**:
```markdown
### 4. API 函数类型规范

#### 禁止不必要的类型断言
- ❌ **禁止** 使用 `as Promise<T>` 强制转换 apiClient 返回值
- ✅ 使用泛型参数让 TypeScript 自动推断

**错误示例**:
\`\`\`typescript
// ❌ 错误：不必要的类型断言
export async function getUser(id: string): Promise<User> {
  return apiClient.get(`/users/${id}`) as Promise<User>;
}
\`\`\`

**正确做法**:
\`\`\`typescript
// ✅ 正确：使用泛型参数
export async function getUser(id: string): Promise<User> {
  return apiClient.get<User>(`/users/${id}`);
}
\`\`\`

**原因**:
- `client.ts` 的响应拦截器已返回 `response.data`
- 类型断言掩盖了真实的类型推断
- 增加维护成本
```

---

### 规则 2: mockableRequest 统一调用风格 (优先级: 🔴 高)

**目标文件**: `frontend/src/core/CLAUDE.md`

**规则内容**:
```markdown
### 5. Mock 数据规范

#### mockableRequest 调用风格
- ❌ **禁止** 使用 `async/await` 嵌套访问 `response.data`
- ✅ 直接传递 apiClient 调用

**错误示例**:
\`\`\`typescript
// ❌ 错误：冗长的 async 包装
return mockableRequest(
  async () => {
    const response = await apiClient.get<T>('/path');
    return response.data;  // 不必要
  },
  mockData
);
\`\`\`

**正确做法**:
\`\`\`typescript
// ✅ 正确：简洁直接
return mockableRequest(
  () => apiClient.get<T>('/path'),
  mockData
);
\`\`\`
```

---

### 规则 3: Mock 数据不可变 (优先级: 🟡 中)

**目标文件**: `frontend/src/core/CLAUDE.md`

**规则内容**:
```markdown
#### Mock 数据必须不可变
- ❌ **禁止** 使用 `let` 声明 mock 数据
- ❌ **禁止** 在运行时修改 mock 数据
- ✅ 使用 `const` 声明只读 mock 数据

**错误示例**:
\`\`\`typescript
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
\`\`\`

**正确做法**:
\`\`\`typescript
// ✅ 正确：不可变的 mock 数据
const MOCK_ROLE: Role = { name: 'Developer', ... };

export async function createRole(data: CreateRoleRequest): Promise<Role> {
  return mockableRequest(
    () => apiClient.post<Role>('/roles', data),
    MOCK_ROLE  // 返回固定的测试数据
  );
}
\`\`\`

**原因**:
- Mock 数据是测试夹具，应该不可变
- 避免测试间状态污染
- Mock 不应实现业务逻辑
```

---

### 规则 4: API 函数签名完整性 (优先级: 🟡 中)

**目标文件**: `frontend/src/core/CLAUDE.md`

**规则内容**:
```markdown
#### API 函数必须有完整的类型签名
- ✅ 显式声明返回类型 `Promise<T>`
- ✅ 显式声明参数类型
- ✅ 使用泛型参数标注请求/响应类型

**正确做法**:
\`\`\`typescript
// ✅ 完整的类型信息
export async function getUser(id: string): Promise<User> {
  return apiClient.get<User>(`/users/${id}`);
}

export async function createRole(data: CreateRoleRequest): Promise<Role> {
  return apiClient.post<Role>('/roles', data);
}
\`\`\`

**禁止**:
\`\`\`typescript
// ❌ 缺少类型信息
export function getUser(id) {
  return apiClient.get(`/users/${id}`);
}
\`\`\`
```

---

### 规则 5: Mock 不实现业务逻辑 (优先级: 🟢 低)

**目标文件**: `frontend/src/core/CLAUDE.md`

**规则内容**:
```markdown
#### Mock 数据职责
- ❌ **禁止** Mock 中实现 CRUD 业务逻辑
- ✅ Mock 只返回静态测试数据

**错误示例**:
\`\`\`typescript
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
\`\`\`

**正确做法**:
\`\`\`typescript
// ✅ 正确：简单返回固定数据
export async function deleteRole(name: string): Promise<DeleteResponse> {
  return mockableRequest(
    () => apiClient.delete<DeleteResponse>(`/roles/${name}`),
    { message: 'Role deleted successfully' }
  );
}
\`\`\`

**原因**:
- Mock 的目的是测试前端逻辑，不是模拟后端
- 业务逻辑实现会增加维护成本
- 真实 API 返回不同时会产生不一致
```

---

## 📝 需要立即修复的代码

### 修复 1: roleApi.ts 的类型断言

**位置**: `frontend/src/core/api/roleApi.ts`

**需要修改的函数**:
- `listRoles()` (行 20)
- `getRoleInfo()` (行 28)
- `createRole()` (行 55)
- `updateRole()` (行 70)
- `deleteRole()` (行 87)
- `getRoleSkills()` (行 103)
- `addSkillToRole()` (行 120)
- `removeSkillFromRole()` (行 135)
- `listAvatars()` (行 150)

**修改方案**:
```typescript
// 修改前
return apiClient.get('/roles') as Promise<Role[]>;

// 修改后
return apiClient.get<Role[]>('/roles');
```

---

### 修复 2: skillApi.ts 的 response.data

**位置**: `frontend/src/core/api/skillApi.ts`

**需要修改的函数**:
- `listSkills()` (行 25)
- `getSkill()` (行 40)
- `addSkill()` (行 55)
- `deleteSkill()` (行 70)

**修改方案**:
```typescript
// 修改前
return mockableRequest(
  async () => {
    const response = await apiClient.get<Skill[]>('/skills');
    return response.data;
  },
  MOCK_SKILLS
);

// 修改后
return mockableRequest(
  () => apiClient.get<Skill[]>('/skills'),
  MOCK_SKILLS
);
```

---

### 修复 3: roleApi.ts 的可变 mock

**位置**: `frontend/src/core/api/roleApi.ts`

**修改方案**:

**修改前**:
```typescript
let mockRoles: Role[] = [
  MOCK_DEVELOPER_ROLE,
  MOCK_REVIEWER_ROLE,
];

export async function createRole(data: CreateRoleRequest): Promise<Role> {
  if (USE_MOCK) {
    const newRole: Role = { ... };
    mockRoles.push(newRole);
    return newRole;
  }
  return apiClient.post('/roles', data) as Promise<Role>;
}
```

**修改后**:
```typescript
const MOCK_ROLES: Role[] = [
  MOCK_DEVELOPER_ROLE,
  MOCK_REVIEWER_ROLE,
];

const MOCK_NEW_ROLE: Role = {
  name: 'New Role',
  description: 'Mock created role',
  skills: [],
};

export async function createRole(data: CreateRoleRequest): Promise<Role> {
  return mockableRequest(
    () => apiClient.post<Role>('/roles', data),
    MOCK_NEW_ROLE
  );
}
```

---

## 📋 行动计划

### 第一阶段：修复现有代码 (优先级: 🔴 最高)

1. **修复 roleApi.ts** (预计 15 分钟)
   - 移除所有 `as Promise<T>` 强制转换
   - 改用泛型参数 `apiClient.get<T>()`
   - 修复可变 mock 数据

2. **修复 skillApi.ts** (预计 10 分钟)
   - 移除 `response.data` 访问
   - 统一为简洁的 mockableRequest 调用

---

### 第二阶段：更新规则文档 (优先级: 🔴 高)

1. **更新 frontend/src/core/CLAUDE.md** (预计 20 分钟)
   - 添加规则 1: 禁止不必要的类型断言
   - 添加规则 2: mockableRequest 统一调用风格
   - 添加规则 3: Mock 数据不可变
   - 添加规则 4: API 函数签名完整性
   - 添加规则 5: Mock 不实现业务逻辑

2. **验证行数** (预计 5 分钟)
   - 运行 `scripts/check_line_count.py`
   - 确保 `frontend/src/core/CLAUDE.md` ≤ 200 行

---

### 第三阶段：预防未来问题 (优先级: 🟡 中)

1. **创建 layouts 规则** (当目录创建后)
   - 布局组件的职责范围
   - 与 features 的交互方式

2. **创建 shared/components 规则** (当目录创建后)
   - 通用组件的设计原则
   - Props 接口设计规范

---

## 📊 总结

### 当前状态
| 维度 | 评分 | 说明 |
|------|------|------|
| **规则文档完整性** | ⭐⭐⭐⭐ | 4/5 - 缺少 layouts 和 shared/components |
| **规则执行情况** | ⭐⭐⭐ | 3/5 - 存在类型断言滥用 |
| **代码一致性** | ⭐⭐⭐ | 3/5 - mock 风格不统一 |
| **AI 友好度** | ⭐⭐ | 2/5 - 现有问题会被 AI 复制 |

### 修复后预期
| 维度 | 评分 | 说明 |
|------|------|------|
| **规则文档完整性** | ⭐⭐⭐⭐⭐ | 5/5 - 覆盖所有现有代码 |
| **规则执行情况** | ⭐⭐⭐⭐⭐ | 5/5 - 所有代码符合规则 |
| **代码一致性** | ⭐⭐⭐⭐⭐ | 5/5 - 统一的代码风格 |
| **AI 友好度** | ⭐⭐⭐⭐⭐ | 5/5 - AI 能写出符合规范的代码 |

---

### 关键发现

1. **好消息** ✅
   - 现有规则文档质量高，结构清晰
   - 核心架构约束执行良好（模块隔离、依赖方向）
   - 类型系统和异步处理非常一致

2. **需要改进** ⚠️
   - 类型断言滥用会被 AI 复制（高风险）
   - Mock 数据风格不统一
   - 缺少明确的 API 函数规范

3. **建议** 💡
   - 立即修复 roleApi.ts 和 skillApi.ts
   - 更新 core/CLAUDE.md 添加 5 条新规则
   - 在创建 UI 层时同步创建对应规则

---

**报告生成时间**: 2026-06-04  
**下一步行动**: 等待用户确认是否执行修复和规则更新
