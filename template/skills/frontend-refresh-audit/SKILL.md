---
name: frontend-refresh-audit
description: 前端刷新依赖审计流程。用于调查前端数据修改后的组件刷新链路，发现断裂的刷新依赖。触发词：刷新审计、refresh audit、组件刷新、数据刷新调查、前端依赖分析。
---

# Frontend Refresh Audit Skill

## 概述

系统化调查前端 mutation API 调用后，哪些组件需要刷新但没有刷新的问题。

## 适用场景

- 用户反馈"修改了 X 但 Y 没有更新"
- 新增 mutation API 后，检查是否需要触发关联组件刷新
- 定期审计前端数据一致性

## 调查流程

```
Stage 1: 收集 API 端点
  └─ 读取 core/api/ 下所有文件，提取 mutation 端点 (POST/PUT/PATCH/DELETE)

Stage 2: 读取 Hooks 实现 (并行)
  ├─ [Agent A] features/chat/hooks/
  ├─ [Agent B] features/roles/hooks/
  ├─ [Agent C] features/session/hooks/
  ├─ [Agent D] features/skills/hooks/
  └─ [Agent E] shared/hooks/
  → 输出：每个 hook 的 API 调用、store 更新、mutation 后刷新逻辑

Stage 3: 读取 Components 实现 (并行)
  ├─ [Agent A] features/*/components/
  ├─ [Agent B] shared/components/
  └─ [Agent C] layouts/
  → 输出：每个组件消费的 hook、显示的数据、触发的 mutation

Stage 4: 分析依赖关系
  1. 实体定义：识别所有前端实体 (Role, Team, GroupChat, Message, Skill, Member)
  2. 实体→组件映射：每个实体的哪些字段显示在哪些组件中
  3. Mutation→刷新链路：每个 mutation 后，哪些数据被刷新，哪些没有
  4. 断裂点识别：标记所有缺失的刷新链路

Stage 5: 输出报告
  → docs/temp/frontend-refresh-audit-YYYY-MM-DD.md
```

## 关键检查点

### 头像依赖（最容易遗漏）

头像数据流经 3 条独立路径：
1. `rolesStore` → RoleCard, EditRoleDialog, ManageMembersDialog
2. `buildRoleAvatarMap()` → useSessionList → SessionItem (群聊头像)
3. `useMembers` → getRoleInfo → ChatArea 消息气泡、RightSidebar 成员列表

修改 Role.avatar 后必须检查这 3 条路径是否都刷新了。

### 成员列表依赖

群聊成员变化影响：
1. `useGroupChatMembers` → ManageMembersDialog
2. `useSessionList` → SessionItem 的 CompositeAvatar
3. `useMembers` → RightSidebar 成员列表

### 跨 Feature 依赖

由于 feature 间禁止直接依赖，跨 feature 刷新通过：
- WebSocket refresh 信号（后端推送）
- Store 订阅（一个 feature 读另一个 store）
- Props 传递（layout 层）

检查时需特别关注这 3 种通信方式是否覆盖了所有需要刷新的场景。

## 输出格式

报告应包含：
1. 实体定义表
2. 所有 mutation API 端点清单
3. 实体→组件的依赖映射
4. 每个 mutation 的刷新链路分析（✅ 已有 / ❌ 缺失）
5. 断裂刷新链路的问题清单（按严重程度排序）
6. 依赖关系图（ASCII）
7. 建议的修复方案
