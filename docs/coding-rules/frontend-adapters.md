# Frontend Adapters 层编码规则

> **触发场景**：修改 `frontend/src/shared/adapters/` 下的代码时

---

## 规则来源

- 🔴 强制规则：来自架构设计和数据流约束
- 🟡 推荐规则：来自性能和可维护性最佳实践
- 🟢 建议规则：来自前端命名惯例

---

## 🔴 强制规则

### 1. Adapter 必须是纯函数

**禁止包含副作用**：
- ❌ console.log
- ❌ localStorage / sessionStorage
- ❌ 修改全局状态
- ❌ 发起网络请求（除了 aggregate 函数）

```typescript
// ❌ 错误
export function adaptRole(apiRole: RoleApiResponse) {
  console.log('Converting:', apiRole.name);
  localStorage.setItem('lastRole', apiRole.name);
  return { ... };
}

// ✅ 正确
export function adaptRole(apiRole: RoleApiResponse) {
  return {
    id: apiRole.name,
    displayName: apiRole.name,
  };
}
```

---

### 2. 禁止 Adapter 之间相互调用

Adapter 应该保持扁平，嵌套转换在外部处理。

```typescript
// ❌ 错误：在 Adapter 内部调用其他 Adapter
export function adaptGroupChat(apiChat: GroupChatApiResponse) {
  return {
    id: apiChat.group_chat_id,
    members: apiChat.members.map(adaptMember), // 调用其他 Adapter
  };
}

// ✅ 正确：只转换当前层级
export function adaptGroupChat(apiChat: GroupChatApiResponse) {
  return {
    id: apiChat.group_chat_id,
    memberCount: apiChat.members.length,
  };
}

// 在外部（hooks）组合
const chat = adaptGroupChat(apiChat);
const members = apiChat.members.map(adaptMember);
```

---

### 3. 统一从 adapters 引用类型

所有 API Schemas 类型必须从 `@/shared/adapters` 引用。

```typescript
// ❌ 错误：直接引用 api-schemas
import type { RoleApiResponse } from '@/shared/types/api-schemas';

// ✅ 正确：从 adapters 引用
import type { RoleApiResponse } from '@/shared/adapters';
```

**实现**：`adapters/index.ts` 转发导出所有 API Schemas。

---

## 🟡 推荐规则

### 1. 聚合函数使用 Promise.all

并行调用多个 API，避免串行等待。

```typescript
// ❌ 不推荐：串行
const role = await getRoleInfo(name);
const skills = await getRoleSkills(name);

// ✅ 推荐：并行
const [role, skills] = await Promise.all([
  getRoleInfo(name),
  getRoleSkills(name),
]);
```

---

### 2. 严格遵守命名规范

| 函数类型 | 命名格式 | 示例 |
|---------|---------|------|
| 基础转换 | `adapt{资源名}` | `adaptRole`, `adaptMessage` |
| 列表转换 | `adapt{资源名}List` | `adaptRoleList` |
| 聚合函数 | `aggregate{场景}` | `aggregateRoleWithSkills` |

```typescript
// ❌ 错误命名
export function convertRole(...) { }
export function getRoleWithSkills(...) { }

// ✅ 正确命名
export function adaptRole(...) { }
export function aggregateRoleWithSkills(...) { }
```

---

## 🟢 建议规则

### 1. Domain 类型使用 camelCase

区分 API 的 snake_case 和前端的 camelCase。

```typescript
// ❌ 不推荐
interface TeamMember {
  created_at: Date;
  is_leader: boolean;
}

// ✅ 推荐
interface TeamMember {
  createdAt: Date;
  isLeader: boolean;
}
```

---

### 2. 按需创建 Domain 类型

在实际需要前，Adapter 可以直接返回 API 类型。

```typescript
// ✅ 初期暂不转换
export function adaptRole(apiRole: RoleApiResponse) {
  return apiRole;
}

// 等实际需要时再转换
export function adaptRole(apiRole: RoleApiResponse): TeamMember {
  return {
    id: apiRole.name,
    createdAt: new Date(apiRole.created_at),
  };
}
```

---

## 参考

- [Adapters 层 CLAUDE.md](../../frontend/src/shared/adapters/CLAUDE.md)
- [Adapters 使用指南](../../frontend/src/shared/adapters/README.md)
- [前端架构](../ARCHITECTURE.md#前端架构)
