# Adapters 聚合层

## 概述

Adapters 层负责 API 响应类型与前端业务模型之间的转换和聚合。

## 职责

1. **类型转换**：将 API schemas 类型转换为前端友好的 Domain 类型
2. **数据聚合**：组合多个 API 响应，提供高层次的数据聚合函数
3. **格式适配**：处理数据格式转换（如 `string` → `Date`、snake_case → camelCase）

## 使用时机

### 何时创建 Adapter？

当以下情况发生时，创建对应的 Adapter：

1. **组件需要不同于 API 的数据结构**
   - API 返回 `created_at: string`，组件需要 `Date` 对象
   - API 字段名不符合前端语义（如 `abilities` → `skills`）

2. **需要聚合多个 API 响应**
   - 显示角色详情页：需要 Role + Skills
   - 显示会话列表：需要 GroupChat + Members + 最后一条消息

3. **需要派生/计算属性**
   - `isExpired`、`canEdit`、`displayName` 等

### 何时使用 Adapter？

- ✅ 在 hooks 中调用 API 后，使用 Adapter 转换数据
- ✅ 在需要聚合数据时，调用 Adapter 的聚合函数
- ❌ 不要在 API 层调用 Adapter（API 层应返回原始类型）

## 命名规范

### 函数命名

- **基础转换函数**：`adapt{资源名}()`
  - 例如：`adaptRole()`、`adaptMessage()`
  - 1:1 转换，处理类型和字段名转换

- **聚合函数**：`aggregate{场景描述}()`
  - 例如：`aggregateRoleWithSkills()`、`aggregateConversationWithMessages()`
  - 调用多个 API，组合结果

- **列表转换函数**：`adapt{资源名}List()`
  - 例如：`adaptRoleList()`
  - 批量转换数组

### 文件命名

- `{资源名}Adapter.ts`
- 例如：`roleAdapter.ts`、`chatAdapter.ts`

## 目录结构

```
adapters/
├── README.md           # 本文件
├── index.ts            # 统一导出
├── roleAdapter.ts      # 角色相关转换
├── chatAdapter.ts      # 群聊相关转换
├── skillAdapter.ts     # Skill 相关转换
└── messageAdapter.ts   # 消息相关转换
```

## 使用示例

### 基础转换

```typescript
import { adaptRole } from '@/shared/adapters/roleAdapter';
import { getRoleInfo } from '@/core/api/roleApi';

// 在 hooks 中使用
export function useRole(name: string) {
  const [role, setRole] = useState<TeamMember | null>(null);
  
  useEffect(() => {
    getRoleInfo(name).then(apiRole => {
      setRole(adaptRole(apiRole));  // API 类型 → Domain 类型
    });
  }, [name]);
  
  return role;
}
```

### 数据聚合

```typescript
import { aggregateRoleWithSkills } from '@/shared/adapters/roleAdapter';

// 在 hooks 中使用
export function useRoleDetails(name: string) {
  const [roleDetails, setRoleDetails] = useState(null);
  
  useEffect(() => {
    aggregateRoleWithSkills(name).then(setRoleDetails);
  }, [name]);
  
  return roleDetails;
}
```

## 注意事项

1. **保持 Adapter 纯函数**
   - 不要在 Adapter 中包含副作用（API 调用除外）
   - 不要在 Adapter 中访问全局状态

2. **类型安全**
   - 所有 Adapter 函数必须有明确的类型签名
   - 输入类型：API schemas
   - 输出类型：Domain 类型

3. **错误处理**
   - 聚合函数应该处理 API 调用失败的情况
   - 考虑部分数据加载失败的场景

4. **性能考虑**
   - 聚合函数应该使用 `Promise.all()` 并行调用多个 API
   - 避免不必要的数据转换

## 扩展指南

### 添加新的 Adapter

1. 在 `adapters/` 目录下创建 `{资源名}Adapter.ts`
2. 实现基础转换函数 `adapt{资源名}()`
3. 根据需要实现聚合函数 `aggregate{场景}()`
4. 在 `index.ts` 中导出
5. 在使用的 hooks 中调用

### 添加新的 Domain 类型

1. 在 `shared/types/domain.ts` 中定义新的 Domain 类型
2. 在对应的 Adapter 中实现转换函数
3. 更新类型导出 `shared/types/index.ts`

## 参考

- [重构计划](../../../../../docs/temp/plan/frontend-data-model-refactor.md)
- [API Schemas 类型](../types/api-schemas.ts)
- [编码规范](../CLAUDE.md)
