# 前端刷新依赖关系调查报告

## 1. 概述

本报告分析前端所有 API mutation 端点、它们修改的实体、受影响的组件，以及当前的刷新机制和缺失的刷新链路。

**核心发现**：修改 Role（尤其是头像）后，Session 列表的群聊头像、消息气泡中的发言人头像等**不会自动刷新**。存在多条断裂的刷新链路。

---

## 2. 实体定义

| 实体 | 标识 | 关键字段 | 所属 Feature |
|------|------|----------|-------------|
| **Role** | `name` | avatar, description, platform, type, skills[] | roles |
| **Team** | `name` | members[] (role names) | roles |
| **GroupChat/Session** | `group_chat_id` | name, project_path, members[], is_active | session |
| **Message** | `id` | speaker, content, pinned | chat |
| **Skill** | `name` | description | skills |
| **Member** | `name` | use_docker, main_session, btw_session | chat |

---

## 3. 所有 API Mutation 端点

### 3.1 Role 相关

| # | API 函数 | HTTP | 端点 | 修改的实体 |
|---|---------|------|------|-----------|
| R1 | `createRole` | POST | `/roles` | Role（新增） |
| R2 | `updateRole` | PATCH | `/roles/{name}` | Role（avatar, description） |
| R3 | `deleteRole` | DELETE | `/roles/{name}` | Role（删除） |
| R4 | `addSkillToRole` | POST | `/roles/{name}/skills` | Role.skills（新增） |
| R5 | `removeSkillFromRole` | DELETE | `/roles/{name}/skills/{id}` | Role.skills（删除） |

### 3.2 Team 相关

| # | API 函数 | HTTP | 端点 | 修改的实体 |
|---|---------|------|------|-----------|
| T1 | `createTeam` | POST | `/teams` | Team（新增） |
| T2 | `updateTeam` | PATCH | `/teams/{name}` | Team（members） |
| T3 | `deleteTeam` | DELETE | `/teams/{name}` | Team（删除） |

### 3.3 GroupChat/Session 相关

| # | API 函数 | HTTP | 端点 | 修改的实体 |
|---|---------|------|------|-----------|
| G1 | `createGroupChat` | POST | `/group-chats` | GroupChat（新增） |
| G2 | `deleteGroupChat` | DELETE | `/group-chats/{id}` | GroupChat（删除） |
| G3 | `addGroupChatMembers` | POST | `/group-chats/{id}/members` | GroupChat.members（新增） |
| G4 | `removeGroupChatMember` | DELETE | `/group-chats/{id}/members/{name}` | GroupChat.members（删除） |
| G5 | `updateMemberDockerMode` | PUT | `/group-chats/{id}/{name}/use-docker` | Member.use_docker |

### 3.4 Message 相关

| # | API 函数 | HTTP | 端点 | 修改的实体 |
|---|---------|------|------|-----------|
| M1 | `sendMessage` | POST | `/group-chats/{id}/messages` | Message（新增） |
| M2 | `pinMessage` | POST | `/group-chats/{id}/pinned-messages` | Message.pinned |
| M3 | `unpinMessage` | DELETE | `/group-chats/{id}/pinned-messages` | Message.pinned |

### 3.5 Skill 相关

| # | API 函数 | HTTP | 端点 | 修改的实体 |
|---|---------|------|------|-----------|
| S1 | `addSkill` | POST | `/skills` | Skill（新增） |
| S2 | `deleteSkill` | DELETE | `/skills/{name}` | Skill（删除） |

---

## 4. 实体 → 显示组件的依赖关系

### 4.1 Role 实体

**Role 的哪些字段显示在哪些组件中：**

| 字段 | 组件 | 来源 Hook |
|------|------|----------|
| avatar | `RoleCard` | useRoles → rolesStore |
| avatar | `RoleMemberRow` | props (from TeamMemberPanel) |
| avatar | `AvatarSelector` (选择器) | useAvatars |
| avatar | `SessionItem` (群聊头像) | useSessionList → buildRoleAvatarMap |
| avatar | `CreateGroupChatDialog` (角色选择) | useCreateGroupChat → listRoles |
| avatar | `ChatArea` MessageBubble (发言人头像) | useChatMessages + useMembers |
| avatar | `RightSidebar` 成员列表头像 | useMembers |
| avatar | `ManageMembersDialog` (角色列表) | useRoles |
| avatar | `AddMemberDialog` (角色列表) | useRoles |
| name | 所有上述组件 | 同上 |
| description | `RoleCard`, `RoleMemberRow`, `ManageMembersDialog`, `AddMemberDialog` | 同上 |
| skills[] | `RoleCard`, `EditRoleDialog` | useRoles, useRoleSkills |
| platform | `RoleCard` | useRoles |
| type | `RoleCard`, `RoleMemberRow` | useRoles |

### 4.2 Team 实体

| 字段 | 组件 | 来源 Hook |
|------|------|----------|
| name | `TeamList` | useTeams |
| name | `TeamListDialog` | useTeamManagement |
| name | `CreateGroupChatDialog` (快速选择) | useCreateGroupChat |
| members[] | `TeamMemberPanel` | useTeamMembers |

### 4.3 GroupChat/Session 实体

| 字段 | 组件 | 来源 Hook |
|------|------|----------|
| name | `SessionItem` | useSessionStore |
| name | `ChatArea` header | useSessionStore |
| members[] | `ManageMembersDialog` | useGroupChatMembers |
| members[] | `RightSidebar` 成员列表 | useMembers |
| is_active | `SessionList` | useSessionList |

### 4.4 Message 实体

| 字段 | 组件 | 来源 Hook |
|------|------|----------|
| content | `ChatArea` MessageBubble | useChatMessages |
| pinned | `ChatArea` (pin indicator) | usePinnedMessages |
| pinned | `RightSidebar` 置顶列表 | usePinnedMessages |

### 4.5 Skill 实体

| 字段 | 组件 | 来源 Hook |
|------|------|----------|
| name, description | `SkillSquare` SkillCard | useSkillList |
| name, description | `SkillDetailModal` | props |
| name, description | `SkillSelectorModal` | 直接调用 listSkills API |
| name | `RoleCard` skills list | useRoles |
| name | `EditRoleDialog` skills list | useRoleSkills |

---

## 5. Mutation 后的刷新链路分析

### 5.1 当前已有的刷新链路

```
R1 createRole
  └─ useCreateRole: addRole → rolesStore ✅ (增量)
  └─ RoleManagementPanel: refreshRoles() 被调用 ✅

R2 updateRole
  └─ useUpdateRole: updateRoleInStore → rolesStore ✅ (增量)
  └─ ❌ 不刷新 session 列表头像
  └─ ❌ 不刷新 chat 成员头像

R3 deleteRole
  └─ ❌ 未实现 (RoleCard 显示 alert('not supported'))

R4 addSkillToRole
  └─ useRoleSkills: refreshRole → rolesStore ✅
  └─ ❌ 不刷新 SkillSelectorModal (如果打开中)

R5 removeSkillFromRole
  └─ useRoleSkills: refreshRole → rolesStore ✅
  └─ ❌ 同上

T1 createTeam
  └─ useTeamActions: addTeam → teamsStore ✅
  └─ useTeamManagement: refresh() ✅

T2 updateTeam (add/remove members)
  └─ useTeamMembers: updateTeamInStore → teamsStore ✅
  └─ ❌ 不刷新 session 列表

T3 deleteTeam
  └─ useTeamActions: removeTeam → teamsStore ✅
  └─ useTeamManagement: 乐观删除 ✅

G1 createGroupChat
  └─ useCreateGroupChat: refreshSessions() ✅
  └─ selectSession → 切换到新 session ✅

G2 deleteGroupChat
  └─ useDeleteGroupChat: 乐观删除 → sessionStore ✅
  └─ 失败时 refreshSessions() 回滚 ✅

G3 addGroupChatMembers
  └─ useGroupChatMembers: refresh() → getMembers ✅
  └─ ❌ 不刷新 session 列表的成员头像

G4 removeGroupChatMember
  └─ useGroupChatMembers: refresh() → getMembers ✅
  └─ ❌ 不刷新 session 列表的成员头像

G5 updateMemberDockerMode
  └─ useMembers: 乐观更新 ✅
  └─ 失败时 fetchMembers() 回滚 ✅

M1 sendMessage
  └─ ChatArea: 直接调用 API ⚠️ (绕过 hooks 层)
  └─ WebSocket refresh 信号触发 useChatMessages 刷新 ✅

M2 pinMessage
  └─ usePinnedMessages: refresh() → getPinnedMessages ✅

M3 unpinMessage
  └─ usePinnedMessages: refresh() → getPinnedMessages ✅

S1 addSkill
  └─ ❌ 无自动刷新 (SkillSquare 不监听)

S2 deleteSkill
  └─ useSkillDelete: onSuccess 回调 → refreshSkills ✅ (手动)
```

---

## 6. 断裂的刷新链路（问题清单）

### 🔴 严重问题（用户可感知的 UI 不一致）

| # | 场景 | 问题描述 | 受影响组件 |
|---|------|---------|-----------|
| **P1** | R2 `updateRole` 修改头像 | SessionItem 的群聊头像不刷新 | `SessionItem`, `CreateGroupChatDialog` |
| **P2** | R2 `updateRole` 修改头像 | ChatArea 消息气泡中发言人头像不刷新 | `ChatArea` MessageBubble |
| **P3** | R2 `updateRole` 修改头像 | RightSidebar 成员列表头像不刷新 | `RightSidebar` 成员列表 |
| **P4** | R2 `updateRole` 修改头像 | ManageMembersDialog 角色头像不刷新 | `ManageMembersDialog` |
| **P5** | R2 `updateRole` 修改描述 | SessionItem 群聊描述不刷新 | `SessionItem` |
| **P6** | R4/R5 角色 skill 变化 | SkillSelectorModal 中的角色 skill 状态不刷新 | `SkillSelectorModal`, `RoleCard` |
| **P7** | G3/G4 成员变化 | SessionItem 的成员头像组合不刷新 | `SessionItem` CompositeAvatar |
| **P8** | T2 团队成员变化 | CreateGroupChatDialog 的团队快速选择不刷新 | `CreateGroupChatDialog` |

### 🟡 中等问题（边界场景）

| # | 场景 | 问题描述 |
|---|------|---------|
| **P9** | R1 createRole | 新角色不会出现在其他已打开的 AddMemberDialog 中（直到关闭重开） |
| **P10** | S1 addSkill | 新 skill 不会出现在已打开的 SkillSelectorModal 中 |
| **P11** | G5 docker 模式变化 | 不刷新 session 列表（可能需要显示 docker 状态） |

---

## 7. 依赖关系图

```
                    ┌──────────────┐
                    │   Role 实体   │
                    │ (name,avatar, │
                    │  desc,skills) │
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────────┐
          │                │                    │
          ▼                ▼                    ▼
   ┌─────────────┐ ┌──────────────┐   ┌──────────────────┐
   │ rolesStore   │ │ buildRole    │   │ listRoles() 直接  │
   │ (useRoles)   │ │ AvatarMap()  │   │ 调用              │
   └──────┬──────┘ └──────┬───────┘   └────────┬─────────┘
          │                │                    │
          ▼                ▼                    ▼
   ┌─────────────┐ ┌──────────────┐   ┌──────────────────┐
   │ RoleCard     │ │ SessionItem  │   │ CreateGroupChat  │
   │ EditRole     │ │ (群聊头像)    │   │ Dialog           │
   │ ManageMembers│ └──────────────┘   │ (角色选择+头像)   │
   │ AddMember    │                    └──────────────────┘
   └─────────────┘
                           │
                    ┌──────┴───────┐
                    │  Team 实体    │
                    │ (name,       │
                    │  members[])  │
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │ teamsStore   │
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │ TeamList     │
                    │ TeamMember   │
                    │ Panel        │
                    └──────────────┘

   ┌──────────────────┐
   │ GroupChat 实体    │
   │ (id, name,       │
   │  members[],      │
   │  is_active)      │
   └────────┬─────────┘
            │
     ┌──────┴──────────────────────┐
     │                             │
     ▼                             ▼
  ┌──────────────┐         ┌──────────────┐
  │ sessionStore │         │ useMembers   │
  │ (projectGroups)        │ (local state)│
  └──────┬───────┘         └──────┬───────┘
         │                        │
         ▼                        ▼
  ┌──────────────┐         ┌──────────────┐
  │ SessionList  │         │ RightSidebar │
  │ SessionItem  │         │ (成员列表)    │
  │ ProjectGroup │         │ ManageMembers│
  └──────────────┘         └──────────────┘
```

---

## 8. 头像刷新链路的详细分析

头像是最复杂的跨实体依赖，因为它涉及多个数据源的聚合：

### 头像数据流

```
角色头像 (Role.avatar)
    │
    ├──[1]──→ rolesStore.roles[].avatar
    │              │
    │              ├──→ RoleCard (直接读取 rolesStore)
    │              ├──→ EditRoleDialog (直接读取 rolesStore)
    │              ├──→ ManageMembersDialog (通过 useRoles)
    │              └──→ AddMemberDialog (通过 useRoles)
    │
    ├──[2]──→ buildRoleAvatarMap() [roleAvatarAdapter.ts]
    │              │
    │              └──→ useSessionList.refreshSessions()
    │                        │
    │                        └──→ session.memberAvatars[]
    │                                  │
    │                                  └──→ SessionItem (CompositeAvatar)
    │                                  └──→ CreateGroupChatDialog (角色选择)
    │
    ├──[3]──→ useMembers.fetchMembers()
    │              │
    │              └──→ getMembers(chatId) → getRoleInfo(m.name)
    │                        │
    │                        └──→ ChatArea MessageBubble (发言人头像)
    │                        └──→ RightSidebar 成员列表头像
    │
    └──[4]──→ listRoles() 直接调用
                   │
                   └──→ CreateGroupChatDialog (角色选择列表)
```

### 关键断裂点

**断裂点 A**: `updateRole` 修改 avatar 后
- rolesStore 被更新 ✅
- 但 `buildRoleAvatarMap()` 不会被重新调用 ❌
- 导致 SessionItem 群聊头像过时

**断裂点 B**: `updateRole` 修改 avatar 后
- rolesStore 被更新 ✅
- 但 `useMembers` 的 local state 不会被重新获取 ❌
- 导致 ChatArea 消息气泡头像过时

**断裂点 C**: `addGroupChatMembers` / `removeGroupChatMember` 后
- `useGroupChatMembers` 刷新了自己的 local state ✅
- 但 `useSessionList` 不会刷新 session 的 memberAvatars ❌
- 导致 SessionItem 的 CompositeAvatar 过时

---

## 9. 刷新策略总结

当前代码中使用了 4 种刷新策略：

| 策略 | 描述 | 使用场景 |
|------|------|---------|
| **乐观更新 + 回滚** | 先更新 UI，失败时回滚 | deleteGroupChat, toggleDockerMode |
| **Mutation 后重取自身** | 调用 API 后重新获取本 hook 数据 | groupChatMembers, pinnedMessages, roleSkills |
| **Store 增量写入** | 直接 patch store 中的单条记录 | createRole, updateRole, teamActions, teamMembers |
| **全量重取** | 重新获取整个列表 | createGroupChat → refreshSessions |

**WebSocket refresh 信号**：`useSessionList` 监听所有 refresh 事件并全量重取 session 列表；chat hooks 监听匹配 `group_chat_id` 的 refresh 信号。

---

## 10. 建议的修复方案

### 方案 A：Mutation 后主动触发关联刷新（推荐）

在每个 mutation hook 中，除了更新自身数据外，调用关联 hook 的 refresh 函数：

```
updateRole 成功后：
  ├── updateRoleInStore (已有)
  ├── refreshSessions() (新增 - 刷新 session 列表头像)
  └── 触发 chat hooks 的成员刷新 (新增 - 刷新消息气泡头像)

addGroupChatMembers / removeGroupChatMember 成功后：
  ├── refresh() (已有)
  └── refreshSessions() (新增 - 刷新 session 列表成员头像)
```

**优点**：简单直接，改动小
**缺点**：hook 间产生隐式耦合

### 方案 B：引入事件总线 / 发布-订阅

mutation 完成后发布事件，其他 hook 订阅并响应：

```
updateRole 完成 → publish('role:updated', { roleName })
  ├── useSessionList 订阅 → refreshSessions()
  ├── useMembers 订阅 → fetchMembers()
  └── useRoles 订阅 → 已通过 store 更新
```

**优点**：解耦，可扩展
**缺点**：引入新的基础设施

### 方案 C：依赖 WebSocket refresh 信号（当前部分使用）

确保后端在所有 mutation 后发送 WebSocket refresh 信号，前端统一响应。

**优点**：前后端一致
**缺点**：依赖后端配合，延迟更高
