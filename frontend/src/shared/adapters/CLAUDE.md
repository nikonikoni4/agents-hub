# Adapters 层编码规则

> 上级规则：[`../CLAUDE.md`](../CLAUDE.md)（全局架构约束已在上级定义）

## 职责

1. API 响应类型转换为 Domain 类型
2. 多个 API 响应的聚合
3. 类型引用的统一入口（转发 API Schemas）

---

## 强制约束

### 1. Adapter 必须是纯函数（禁止副作用）

```typescript
// ❌ 错误：包含副作用
export function adaptRole(apiRole: RoleApiResponse) {
  console.log('Converting:', apiRole.name);
  localStorage.setItem('last', apiRole.name);
  return { id: apiRole.name };
}

// ✅ 正确：纯函数
export function adaptRole(apiRole: RoleApiResponse) {
  return {
    id: apiRole.name,
    displayName: apiRole.name,
    isLeader: apiRole.type === 'leader',
  };
}
```

---

### 2. 禁止 Adapter 间相互调用

```typescript
// ❌ 错误：嵌套调用
export function adaptGroupChat(apiChat: GroupChatApiResponse) {
  return {
    members: apiChat.members.map(adaptMember), // 调用其他 Adapter
  };
}

// ✅ 正确：在外部组合
export function adaptGroupChat(apiChat: GroupChatApiResponse) {
  return {
    id: apiChat.group_chat_id,
    memberCount: apiChat.members.length,  // 不转换嵌套
  };
}

// 在 hooks 中组合
const chat = adaptGroupChat(apiChat);
const members = apiChat.members.map(adaptMember);
```

---

### 3. 统一从 adapters 引用

```typescript
// ❌ 错误：直接引用 api-schemas
import type { RoleApiResponse } from '@/shared/types/api-schemas';

// ✅ 正确：从 adapters 引用
import type { RoleApiResponse } from '@/shared/adapters';
```

**实现**：`adapters/index.ts` 转发所有 API Schemas

```typescript
export type { RoleApiResponse, GroupChatApiResponse } from '@/shared/types/api-schemas';
```

---

## 推荐规范

### 1. 聚合函数并行调用

❌ **串行调用**

```typescript
// ❌ 串行
const role = await getRoleInfo(name);
const skills = await getRoleSkills(name);
```

✅ **并行调用**

```typescript
// ✅ 并行
const [role, skills] = await Promise.all([
  getRoleInfo(name),
  getRoleSkills(name),
]);
```

---

### 2. 命名规范

| 类型 | 格式 | 示例 |
|-----|------|------|
| 基础转换 | `adapt{资源名}` | `adaptRole`, `adaptMessage` |
| 列表转换 | `adapt{资源名}List` | `adaptRoleList` |
| 聚合函数 | `aggregate{场景}` | `aggregateRoleWithSkills` |

❌ **错误命名**

```typescript
export function convertRole(...) { }
export function getRoleWithSkills(...) { }
```

✅ **正确命名**

```typescript
export function adaptRole(...) { }
export function aggregateRoleWithSkills(...) { }
```

---

## 建议

### 1. Domain 类型用 camelCase

```typescript
// ❌ snake_case
interface TeamMember {
  created_at: Date;
  is_leader: boolean;
}

// ✅ camelCase
interface TeamMember {
  createdAt: Date;
  isLeader: boolean;
}
```

---

### 2. 按需创建 Domain 类型

初期可直接返回 API 类型，实际需要时再转换。

```typescript
// ✅ 初期
export function adaptRole(apiRole: RoleApiResponse) {
  return apiRole;
}

// ✅ 需要时转换
export function adaptRole(apiRole: RoleApiResponse): TeamMember {
  return { id: apiRole.name, ... };
}
```

---

## 快速决策

| 场景 | 决策 |
|------|------|
| 转换 API 类型 | 实现 `adapt{资源名}()` |
| 调用多个 API | 创建 `aggregate{场景}()` |
| 引用 API 类型 | 从 `@/shared/adapters` 引用 |
| 转换嵌套对象 | 在外部（hooks）组合多个 Adapter |
| 创建 Domain 类型 | 在 `types/domain.ts` 定义，用 camelCase |

---

## 参考

- [Adapters 使用指南](README.md)
- [API Schemas](../types/api-schemas.ts)
- [Domain 类型框架](../types/domain.ts)
