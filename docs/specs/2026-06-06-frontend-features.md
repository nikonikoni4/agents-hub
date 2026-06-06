---
version: 1.0
created_at: 2026-06-06
updated_at: 2026-06-06
last_updated: 创建 frontend-features 模块 spec
abstract: 前端功能层规格，定义 chat/session/roles/skills 四个业务模块的职责边界、状态管理模式和模块间依赖规则
id: frontend-features
title: Frontend Features 层
status: draft
module: frontend-features
sourc_spec:
related_plan:
code_scope: frontend/src/features/, frontend/src/shared/
contract_refs: frontend/src/shared/types/api-schemas.ts, frontend/src/shared/adapters/index.ts
---

# Frontend Features 层

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |

## Overview

Features 层是前端按业务领域划分的功能模块集合。每个 feature 封装一个独立的业务领域，拥有自己的 UI、状态和交互逻辑。当前包含四个 feature 模块：

- **chat** — 对话交互，管理消息收发和成员展示
- **session** — 会话管理，管理群聊会话列表和当前活跃会话
- **roles** — 角色与团队管理，管理角色 CRUD、团队编排和头像
- **skills** — 技能管理，管理全局技能库的浏览和删除

所有 feature 模块共享同一套分层架构规则：`components → hooks → store → core`，禁止反向依赖。feature 之间禁止直接 import，必须通过 store 订阅或 props 通信。

## Scope

### chat 模块

**职责**：对话交互场景。

- 展示当前会话的消息列表
- 提供消息发送能力
- 展示当前群聊的成员信息（含角色关联）

**不负责**：会话切换、会话列表维护（由 session 模块负责）。

### session 模块

**职责**：会话生命周期与导航。

- 管理按项目分组的群聊会话列表
- 维护当前活跃会话的选中状态
- 提供创建群聊的入口

**不负责**：群聊内部的消息交互（由 chat 模块负责）。

### roles 模块

**职责**：角色与团队的管理。

- 角色的创建、编辑、查询
- 角色与 Skill 的关联管理
- 团队的创建、编辑、删除
- 团队成员的增删
- 角色头像管理

**不负责**：角色的运行时执行（由 core 层负责）。

### skills 模块

**职责**：全局技能库的浏览与管理。

- 技能列表的获取与展示
- 技能详情查看
- 技能删除

**不负责**：角色级 Skill 关联（由 roles 模块负责）、Skill 的后端执行（由 core 层负责）。

## Core Behavior

### 分层职责

每个 feature 内部遵循统一分层：

1. **components** — 纯 UI 渲染，只调用本模块 hooks，不包含业务逻辑
2. **hooks** — 业务逻辑层，负责 API/WebSocket 调用、数据转换、调用 store 更新状态
3. **store** — 纯状态管理，只存储状态和同步更新操作，不包含任何副作用
4. **types** — 模块专属类型定义

### 状态管理模式

每个 feature 拥有独立的 Zustand store，不存在全局大 store：

- **session store** — 存储按项目分组的会话列表和当前活跃会话 ID，提供会话选择和数据更新操作。store 纯净无副作用，API 调用在 hooks 中完成。
- **roles store** — 存储角色列表、加载状态和错误状态，提供角色的增删改操作。
- **teams store** — 存储团队列表、选中团队、加载状态，提供团队 CRUD 和成员更新操作。roles store 与 teams store 是独立的两个 store。
- **chat** — 消息状态通过 WebSocket 实时接收，在 hooks 中处理消息分发。

跨 feature 状态共享通过订阅实现：例如 chat 模块通过订阅 session store 获取当前活跃会话 ID，而非直接 import session 模块。

### 跨 feature 通信模式

允许的通信方式：

1. **store 订阅** — feature A 的 hooks 订阅 feature B 的 store（如 chat 订阅 session 的 activeSessionId）
2. **props 传递** — 在 layout 层通过 props 向子组件传递数据
3. **core 层中转** — 通过 WebSocket 消息分发实现跨模块事件通知

禁止的通信方式：

- feature A 直接 import feature B 的组件或 hooks

### shared 层的定位

shared 层提供跨 feature 的复用能力，分为三个子层：

1. **types** — 定义 API 契约类型（与后端 Pydantic schema 一一对应），保持 snake_case 字段名和后端数据类型，作为前后端对齐的单一事实来源
2. **adapters** — 提供 API 响应到领域模型的转换（纯函数），包含基础转换（adapt*）、列表转换（adapt*List）和聚合函数（aggregate*）。同时作为 API schema 类型的统一转发入口，所有 feature 通过 `@/shared/adapters` 引用 API 类型
3. **components** — 提供业务无关的通用 UI 组件（如 Button），不含任何 feature 的业务逻辑

## Technical Contract

### 模块边界与依赖方向

依赖方向严格单向：

```
components → hooks → store → core
                 → shared/adapters（数据转换）
                 → shared/types（API 契约类型）
```

反向依赖禁止：core 不得依赖 features，store 不得调用 API，components 不得直接操作 store 或调用 core。

### API 契约类型的作用

`shared/types/api-schemas.ts` 定义了与后端 Pydantic schema 严格对应的 TypeScript 类型。这些类型是前后端对齐的契约层：

- 响应类型命名为 `{Resource}ApiResponse`（完整响应）或 `{Resource}ApiItem`（列表项）
- 保持后端字段命名（snake_case）和数据类型（日期为 string）
- 覆盖角色、技能、群聊、会话、消息、配置等核心资源

feature 模块不直接引用 `api-schemas.ts`，而是通过 `shared/adapters` 统一入口引用。

### adapter 层的职责

`shared/adapters/` 承担三类职责：

1. **基础转换** — 将 API 响应类型转换为前端领域模型（如 `adaptRole`、`adaptMessage`）
2. **数据聚合** — 将多个 API 响应聚合为单一领域对象（如 `aggregateRoleWithSkills`）
3. **类型转发** — 在 `adapters/index.ts` 中统一导出所有 API schema 类型，作为 feature 模块引用 API 类型的唯一入口

adapter 必须是纯函数，禁止副作用；adapter 之间禁止相互调用，嵌套组合在 hooks 层完成。

## Out of Spec

以下内容不在本 spec 中维护：

1. 各 feature 的组件树结构、组件内部实现细节
2. hooks 的具体函数签名、参数和返回值
3. store 的完整字段定义和 TypeScript 接口
4. 样式细节（颜色、间距、字体）
5. WebSocket 消息协议细节（由 websocket-backend spec 覆盖）
6. 后端 API 的路由和实现（由各后端 spec 覆盖）
7. core 层的内部架构（由 core-overview spec 覆盖）
