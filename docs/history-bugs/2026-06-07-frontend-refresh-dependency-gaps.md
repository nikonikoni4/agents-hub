# Bug Report: 前端 Mutation 后组件刷新链路断裂

## Bug 元信息

| 字段 | 内容 |
|------|------|
| **Bug ID** | BUG-2026-06-07-002 |
| **发现时间** | 2026-06-07 |
| **发现方式** | 前端刷新依赖关系系统性审计 |
| **严重程度** | 🟡 Major（多个 UI 不一致问题）|
| **影响范围** | Role 头像/描述修改后，Session 列表、消息气泡、成员列表等组件显示过时数据 |
| **状态** | ✅ Fixed (2026-06-08) |
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

## 修复方案（已实施）

采用方案 A 的变体：**扩展现有 WebSocketManager 作为本地事件总线**。

`useSessionList` 和 `useMembers` 已通过 `wsManager.on('refresh', ...)` 监听刷新事件。只需在 mutation hook 成功后通过 `wsManager.emit('refresh')` 分发本地事件，即可触发关联刷新。零新基础设施，复用现有监听机制。

### 实际修改文件

| 文件 | 改动 |
|------|------|
| `core/websocket/WebSocketManager.ts` | 新增公开 `emit()` 方法，委托给私有 `_emit()` |
| `features/roles/hooks/useUpdateRole.ts` | `updateRoleInStore` 后 `wsManager.emit('refresh')` |
| `features/roles/hooks/useRoleSkills.ts` | `addSkill`/`removeSkill` 后 `getRoleInfo` 更新 store（不 emit，避免级联） |
| `features/roles/hooks/useTeamMembers.ts` | `addMembersToTeam`/`removeMemberFromTeam` 后 `wsManager.emit('refresh')` |
| `features/chat/hooks/useGroupChatMembers.ts` | `addMembers`/`removeMember` 后 `wsManager.emit('refresh', { group_chat_id })` |
| `features/chat/hooks/useMembers.ts` | 扩展监听：`!signal?.group_chat_id` 时也 `fetchMembers()` |
| `shared/hooks/useCreateChatData.ts` | 新增 `refresh()` 方法 + `loading` 状态管理 |

### Code Review 修复

| 问题 | 修复 |
|------|------|
| `useGroupChatMembers` 双重刷新 | 移除 `await refresh()`，仅通过 emit 触发 |
| `useCreateChatData.refresh()` 缺少 loading | 补充 `setLoading(true/false)` |
| `useRoleSkills` bare emit 导致 useMembers 级联 | 移除 emit，仅保留 store 更新 |

---

## 修复状态

| Bug | 修复状态 | 修复方式 |
|-----|---------|---------|
| Bug 1: Session 列表头像 | ✅ 已修复 | `useUpdateRole` emit refresh → `useSessionList` 响应 |
| Bug 2: 消息气泡头像 | ✅ 已修复 | `useUpdateRole` emit refresh → `useMembers` 响应 |
| Bug 3: 管理成员对话框 | ✅ 已修复 | 同 Bug 2，store 更新 + refresh 触发 |
| Bug 4: CompositeAvatar | ✅ 已修复 | `useGroupChatMembers` emit refresh → `useSessionList` 响应 |
| Bug 5: 团队快速选择 | ✅ 已修复 | `useTeamMembers` emit refresh + `useCreateChatData.refresh()` |
| Bug 6: SkillSelectorModal | ⚠️ 部分修复 | store 更新后 `RoleCard` 即时刷新；Modal 需关闭重开 |

---

## 经验教训

### 1. 跨 Feature 数据依赖需要显式声明

当一个 feature 的数据依赖另一个 feature 的数据时，需要在架构层面显式声明这种依赖关系，而不是隐式地通过 API 调用建立依赖。

### 2. 复用现有基础设施优于引入新机制

WebSocketManager 已有 `on/off/_emit` 机制，只需暴露公开 `emit()` 即可作为本地事件总线。不需要引入新的 EventEmitter 或事件总线库。

### 3. 避免 emit 触发自身监听导致双重刷新

当 hook 内部先 `await refresh()` 再 `emit('refresh', ...)` 时，emit 会触发自身的 `handleRefresh` 监听器，导致重复 API 调用。修复：只保留 emit，移除显式 refresh 调用。

### 4. 无差别的 bare emit 会导致不必要的级联

`emit('refresh')` 不带 `group_chat_id` 会触发所有监听者，包括不相关的 `useMembers`。对不需要跨 feature 通知的场景（如 skill 变更），只更新 store 即可，不 emit。

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
