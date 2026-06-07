# Bug Report: 前端 Mutation 后组件刷新链路断裂

## Bug 元信息

| 字段 | 内容 |
|------|------|
| **Bug ID** | BUG-2026-06-07-002 |
| **发现时间** | 2026-06-07 |
| **发现方式** | 前端刷新依赖关系系统性审计 |
| **严重程度** | 🟡 Major（多个 UI 不一致问题）|
| **影响范围** | Role 头像/描述修改后，Session 列表、消息气泡、成员列表等组件显示过时数据 |
| **状态** | Open |
| **责任方** | 架构设计缺陷 — 缺少跨 feature 的刷新协调机制 |

---

## 问题背景

前端采用 Feature-Sliced Design，features 之间禁止直接依赖。数据刷新通过 4 种策略实现：
1. 乐观更新 + 回滚
2. Mutation 后重取自身数据
3. Store 增量写入
4. 全量重取 + WebSocket refresh 信号

**核心问题**：当一个实体被修改后，只有直接消费该实体的组件被刷新，其他间接依赖（通过 adapter 聚合或跨 feature 读取）的组件不会刷新。

---

## Bug 详情

### Bug 1: 修改角色头像后，Session 列表群聊头像不刷新

#### 问题描述

用户在角色管理面板修改角色头像后，左侧 Session 列表中该角色参与的群聊头像仍显示旧头像。

#### 数据流分析

```
Role.avatar 修改
  └─ useUpdateRole → updateRoleInStore → rolesStore ✅ 已更新
  └─ useSessionList → buildRoleAvatarMap() ❌ 未重新调用
       └─ session.memberAvatars[] ❌ 仍为旧值
            └─ SessionItem → CompositeAvatar ❌ 显示旧头像
```

#### 根因

`useUpdateRole` 只更新了 `rolesStore`，但 `useSessionList` 的 `refreshSessions()` 中调用的 `buildRoleAvatarMap()` 独立调用 `listRoles()` API，不会因 store 变化而触发。

#### 受影响组件

- `SessionItem` (左侧栏群聊头像)
- `CreateGroupChatDialog` (角色选择列表头像)

---

### Bug 2: 修改角色头像后，消息气泡发言人头像不刷新

#### 问题描述

修改角色头像后，聊天区域中该角色的历史消息气泡仍显示旧头像。

#### 数据流分析

```
Role.avatar 修改
  └─ useUpdateRole → updateRoleInStore → rolesStore ✅ 已更新
  └─ useMembers.fetchMembers() ❌ 未重新调用
       └─ getMembers(chatId) → getRoleInfo(m.name) ❌ 未执行
            └─ ChatArea MessageBubble ❌ 显示旧头像
```

#### 根因

`useMembers` 将成员信息（含头像）缓存在 local state 中，mutation 后不会自动刷新。

#### 受影响组件

- `ChatArea` MessageBubble (发言人头像)
- `RightSidebar` 成员列表头像

---

### Bug 3: 修改角色头像后，管理成员对话框头像不刷新

#### 问题描述

修改角色头像后，已打开的 `ManageMembersDialog` 中角色头像仍显示旧值。

#### 数据流分析

```
Role.avatar 修改
  └─ useUpdateRole → updateRoleInStore → rolesStore ✅ 已更新
  └─ ManageMembersDialog 使用 useRoles ✅ 已订阅 rolesStore
       └─ 但 useRoles 的 roles 数据来自 store，store 已更新
       └─ ⚠️ 实际上应该会刷新（因为 zustand 订阅）
```

#### 根因

需要验证：`useRoles` 是否正确订阅了 `rolesStore` 的变化。如果 `RoleCard` 直接从 store 读取 avatar，则应该自动刷新。但如果 `ManageMembersDialog` 缓存了 roles 数据在 local state 中，则不会刷新。

#### 受影响组件

- `ManageMembersDialog` (角色列表头像)
- `AddMemberDialog` (角色列表头像)

---

### Bug 4: 增删群成员后，SessionItem 的 CompositeAvatar 不刷新

#### 问题描述

在群聊中添加或删除成员后，左侧 Session 列表中该群聊的头像组合（CompositeAvatar）不更新。

#### 数据流分析

```
G3/G4 addGroupChatMembers / removeGroupChatMember
  └─ useGroupChatMembers.refresh() → getMembers ✅ 已更新 (local state)
  └─ useSessionList.refreshSessions() ❌ 未触发
       └─ session.memberAvatars[] ❌ 仍为旧成员列表
            └─ SessionItem → CompositeAvatar ❌ 显示旧头像组合
```

#### 根因

`useGroupChatMembers` 只刷新了自己的 local state，没有通知 `useSessionList` 重新获取 session 列表的成员头像数据。

#### 受影响组件

- `SessionItem` (CompositeAvatar 头像组合)

---

### Bug 5: 团队成员变化后，创建群聊对话框的团队快速选择不刷新

#### 问题描述

在角色管理面板修改团队成员后，创建群聊对话框中的团队快速选择 chips 仍显示旧成员。

#### 数据流分析

```
T2 updateTeam (add/remove members)
  └─ useTeamMembers.updateTeamInStore → teamsStore ✅ 已更新
  └─ CreateGroupChatDialog 使用 useCreateGroupChat
       └─ useCreateGroupChat 调用 aggregateAllTeams() 获取团队列表
       └─ 但 aggregateAllTeams() 只在 mount 时调用一次 ❌
       └─ 团队数据缓存在 local state 中，不会自动刷新
```

#### 根因

`useCreateGroupChat` 在 mount 时获取团队列表，之后不会监听 `teamsStore` 的变化。

#### 受影响组件

- `CreateGroupChatDialog` (团队快速选择 chips)

---

### Bug 6: SkillSelectorModal 中角色 skill 状态不刷新

#### 问题描述

在编辑角色面板中添加/移除 skill 后，如果 SkillSelectorModal 仍打开，已选择的 skill 状态不更新。

#### 数据流分析

```
R4/R5 addSkillToRole / removeSkillFromRole
  └─ useRoleSkills.refreshRole → rolesStore ✅ 已更新
  └─ SkillSelectorModal 使用 listSkills() API
       └─ listSkills() 返回的是全局 skill 列表，不是角色的 skill
       └─ SkillSelectorModal 通过 props 接收 selectedSkills
       └─ 但 props 变化不会触发 Modal 内部重新渲染 ⚠️
```

#### 根因

`SkillSelectorModal` 是一个共享组件，通过 props 接收已选中的 skills。如果父组件没有正确传递更新后的 props，Modal 内部不会刷新。

#### 受影响组件

- `SkillSelectorModal` (已选中 skill 的高亮状态)

---

## 根本原因分析

### 1. 缺少跨 Feature 的刷新协调机制

当前每个 hook 独立管理自己的刷新逻辑，没有统一的协调机制。当一个 mutation 影响多个 feature 的数据时，只有发起 mutation 的 feature 会被刷新。

### 2. 数据聚合点没有订阅机制

`useSessionList` 中的 `buildRoleAvatarMap()` 是一个独立的 API 调用，不会因 `rolesStore` 变化而触发。需要建立从 store 变化到聚合函数的订阅链路。

### 3. Local state 缓存没有失效机制

`useMembers`、`useCreateGroupChat` 等 hook 将数据缓存在 local state 中，没有监听上游数据源（如 rolesStore、teamsStore）的变化来触发刷新。

### 4. WebSocket refresh 信号的覆盖范围不足

WebSocket refresh 信号主要用于群聊消息和成员变化，不覆盖角色和团队的修改。需要扩展 refresh 信号的类型和处理逻辑。

---

## 修复方案

### 方案 A: Mutation 后主动触发关联刷新（推荐）

在每个 mutation hook 中，除了更新自身数据外，调用关联 hook 的 refresh 函数：

```typescript
// useUpdateRole.ts
export function useUpdateRole() {
  const { updateRoleInStore } = useRolesStore();
  const { refreshSessions } = useSessionList(); // 新增依赖

  const updateRole = useCallback(async (name: string, data: UpdateRoleRequest) => {
    const result = await updateRoleApi(name, data);
    updateRoleInStore(name, result);
    
    // 新增: 刷新 session 列表（更新头像）
    await refreshSessions();
  }, [updateRoleInStore, refreshSessions]);

  return { updateRole };
}
```

**优点**: 简单直接，改动小
**缺点**: hook 间产生隐式耦合

### 方案 B: 引入事件总线

mutation 完成后发布事件，其他 hook 订阅并响应：

```typescript
// 在 core 层新增事件总线
const eventBus = new EventEmitter();

// useUpdateRole.ts
await updateRoleApi(name, data);
updateRoleInStore(name, result);
eventBus.emit('role:updated', { roleName: name });

// useSessionList.ts
useEffect(() => {
  const handler = () => refreshSessions();
  eventBus.on('role:updated', handler);
  return () => eventBus.off('role:updated', handler);
}, [refreshSessions]);
```

**优点**: 解耦，可扩展
**缺点**: 引入新的基础设施

### 方案 C: 扩展 WebSocket refresh 信号

确保后端在所有 mutation 后发送 WebSocket refresh 信号，前端统一响应：

```typescript
// 后端: 角色修改后发送 refresh 信号
await ws_manager.broadcast_refresh({
  type: 'role_updated',
  role_name: name,
  affected_chats: [...]
});

// 前端: useSessionList 监听所有 refresh 信号
wsManager.on('refresh', (data) => {
  if (data.type === 'role_updated') {
    refreshSessions();
  }
});
```

**优点**: 前后端一致，实时性好
**缺点**: 依赖后端配合，延迟更高

---

## 修复优先级

| 优先级 | Bug | 影响范围 | 修复难度 |
|--------|-----|---------|---------|
| **P1** | Bug 1: Session 列表头像 | 所有角色修改场景 | 中等 |
| **P1** | Bug 2: 消息气泡头像 | 所有角色修改场景 | 中等 |
| **P1** | Bug 4: CompositeAvatar | 所有成员变化场景 | 低 |
| **P2** | Bug 3: 管理成员对话框 | 需要验证是否真有问题 | 低 |
| **P2** | Bug 5: 团队快速选择 | 团队修改场景 | 低 |
| **P3** | Bug 6: SkillSelectorModal | Skill 修改场景 | 低 |

---

## 经验教训

### 1. 跨 Feature 数据依赖需要显式声明

当一个 feature 的数据依赖另一个 feature 的数据时，需要在架构层面显式声明这种依赖关系，而不是隐式地通过 API 调用建立依赖。

### 2. 数据聚合点需要订阅机制

`buildRoleAvatarMap()` 这样的聚合函数需要订阅上游数据源的变化，而不是只在 mount 时调用一次。

### 3. Local state 缓存需要失效策略

将数据缓存在 local state 中时，需要考虑上游数据源变化时的失效策略，避免显示过时数据。

### 4. 测试需要覆盖跨 Feature 场景

当前测试主要覆盖单个 feature 内的逻辑，缺少跨 feature 的集成测试，导致刷新链路断裂的问题未被发现。

---

## 附录

### A. 相关代码位置

| 文件 | 说明 |
|------|------|
| `frontend/src/features/roles/hooks/useUpdateRole.ts` | 角色更新 hook |
| `frontend/src/features/session/hooks/useSessionList.ts` | Session 列表 hook |
| `frontend/src/features/chat/hooks/useMembers.ts` | 成员信息 hook |
| `frontend/src/shared/adapters/roleAvatarAdapter.ts` | 角色头像聚合 |
| `frontend/src/shared/components/CompositeAvatar/CompositeAvatar.tsx` | 组合头像组件 |

### B. 参考文档

- [前端刷新依赖关系调查报告](../temp/frontend-refresh-audit-2026-06-07.md)
- [前端架构文档](../ARCHITECTURE.md)

---

## 总结

这是一个典型的"单个 feature 内逻辑正确，但跨 feature 刷新链路断裂"的问题，根本原因是：

1. **架构缺陷**: 缺少跨 feature 的刷新协调机制
2. **数据聚合点没有订阅**: `buildRoleAvatarMap()` 等聚合函数不监听上游变化
3. **Local state 缓存没有失效**: 成员信息等缓存数据不会自动刷新
4. **测试覆盖不足**: 缺少跨 feature 的集成测试

**修复建议**:
- 优先修复 P1 级别的头像刷新问题（影响用户体验最大）
- 采用方案 A（Mutation 后主动触发关联刷新）作为短期修复
- 长期考虑引入事件总线或扩展 WebSocket refresh 信号
