---
version: 2.0
created_at: 2026-06-06
updated_at: 2026-06-18
last_updated: 按新 spec 规则重构：业务意图 + 技术契约 + 设计决策
abstract: 前端功能层规格，定义 chat/session/roles/skills 四个业务模块的职责边界、状态管理模式和模块间通信规则
id: frontend-features
title: Frontend Features 层
status: draft
module: frontend-features
code_scope: frontend/src/features/, frontend/src/shared/
contract_refs: frontend/src/shared/types/api-schemas.ts, frontend/src/shared/adapters/index.ts
---

# Frontend Features 层

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 2.0 | 按新 spec 规则重构：移除执行细节，添加 key_function 标注和 Design Rationale |
| 1.0 | 创建 spec 初稿 |

## Overview

**业务问题**：前端需要按业务领域组织功能模块，使每个模块拥有独立的 UI、状态和交互逻辑，同时保证模块间低耦合、可独立演进。

**核心职责**：Features 层是前端按业务领域划分的功能模块集合。每个 feature 封装一个独立的业务领域，遵循统一分层架构（components -> hooks -> store -> core），feature 之间禁止直接 import，必须通过 store 订阅或 props 通信。

当前包含以下 feature 模块：

- **chat** — 对话交互，管理消息收发和成员展示
- **session** — 会话管理，管理群聊/单聊会话列表和当前活跃会话
- **roles** — 角色与团队管理，管理角色 CRUD、团队编排和头像
- **skills** — 技能管理，管理全局技能库的浏览和删除
- **single-chat** — 单聊交互，管理单聊消息收发
- **chat-history** — 聊天历史，管理历史消息查看

## Scope

### 范围内

- feature 模块的分层架构规则（components / hooks / store / types）
- feature 间的通信模式与禁止规则
- 各 feature 的状态管理模式（独立 Zustand store）
- shared 层的定位与职责（types / adapters / components）
- adapter 层的转换规则与类型转发机制

### 范围外

- 各 feature 的组件树结构和组件内部实现细节
- hooks 的具体函数签名、参数和返回值
- store 的完整字段定义和 TypeScript 接口
- 样式细节（颜色、间距、字体）
- WebSocket 消息协议细节 — 由 `websocket-backend` spec 覆盖
- 后端 API 的路由和实现 — 由各后端 spec 覆盖
- core 层的内部架构 — 由 `core-overview` spec 覆盖

## Technical Contract

### 分层架构规则

依赖方向严格单向：

```
components -> hooks -> store -> core
                 -> shared/adapters（数据转换）
                 -> shared/types（API 契约类型）
```

**约束**：
- 反向依赖禁止：core 不得依赖 features，store 不得调用 API，components 不得直接操作 store 或调用 core
- 每个 feature 拥有独立的 Zustand store，不存在全局大 store
- 跨 feature 状态共享通过订阅实现（如 chat 模块订阅 session store 的 activeSessionId）

### Store 层公共接口

<key_function last_update="2026-06-26T18:23:55+08:00">
- frontend/src/features/session/store/sessionStore.ts
  - sessionStore.useSessionStore
- frontend/src/features/roles/store/rolesStore.ts
  - rolesStore.useRolesStore
- frontend/src/features/roles/store/teamsStore.ts
  - teamsStore.useTeamsStore
- frontend/src/features/single-chat/store/singleChatStore.ts
  - singleChatStore.useSingleChatStore
- frontend/src/features/chat/store/pinnedMessagesStore.ts
  - pinnedMessagesStore.usePinnedMessagesStore
- frontend/src/features/chat/store/compressStatusStore.ts
  - compressStatusStore.useCompressStatusStore
</key_function>

**状态管理模式**：

| Store | 职责 | 约束 |
|-------|------|------|
| session store | 按项目分组的会话列表 + 当前活跃会话 ID | 纯状态，API 调用在 hooks 中 |
| roles store | 角色列表 + 加载/错误状态 | 纯状态，提供增删改操作 |
| teams store | 团队列表 + 选中团队 + 加载状态 | 与 roles store 独立 |
| single-chat store | 单聊消息状态 | 通过 WebSocket 接收 |
| chat（消息） | 消息通过 WebSocket 实时接收 | 在 hooks 中处理消息分发 |

### Adapter 层公共接口

<key_function last_update="2026-06-18T14:00:00+08:00">
- frontend/src/shared/adapters/sessionAdapter.ts
  - sessionAdapter.groupSessionsByProject
- frontend/src/shared/adapters/roleAdapter.ts
  - roleAdapter.aggregateRoleWithSkills
  - roleAdapter.aggregateAllRolesWithSkills
- frontend/src/shared/adapters/chatAdapter.ts
  - chatAdapter.adaptGroupChat
- frontend/src/shared/adapters/messageAdapter.ts
  - messageAdapter.adaptMessage
- frontend/src/shared/adapters/teamAdapter.ts
  - teamAdapter.adaptTeam
</key_function>

**adapter 职责**：

| 职责 | 说明 | 命名规范 |
|------|------|----------|
| 基础转换 | API 响应 -> 前端领域模型 | `adapt{资源名}` |
| 列表转换 | 批量转换 | `adapt{资源名}List` |
| 数据聚合 | 多个 API 响应聚合为单一领域对象 | `aggregate{场景}` |
| 类型转发 | 在 `adapters/index.ts` 统一导出 API schema 类型 | — |

**约束**：
- adapter 必须是纯函数，禁止副作用
- adapter 之间禁止相互调用，嵌套组合在 hooks 层完成
- feature 模块不直接引用 `api-schemas.ts`，通过 `shared/adapters` 统一入口引用

### 跨 feature 通信规则

**允许的通信方式**：

1. **store 订阅** — feature A 的 hooks 订阅 feature B 的 store（如 chat 订阅 session 的 activeSessionId）
2. **props 传递** — 在 layout 层通过 props 向子组件传递数据
3. **core 层中转** — 通过 WebSocket 消息分发实现跨模块事件通知

**禁止的通信方式**：
- feature A 直接 import feature B 的组件或 hooks

### shared 层定位

| 子层 | 职责 | 约束 |
|------|------|------|
| types | API 契约类型（与后端 Pydantic schema 一一对应），保持 snake_case | 前后端对齐的单一事实来源 |
| adapters | API 响应到领域模型的转换 + API schema 类型统一转发入口 | 纯函数，禁止副作用 |
| components | 业务无关的通用 UI 组件（如 Button） | 不含任何 feature 的业务逻辑 |

### API 契约类型

`shared/types/api-schemas.ts` 定义与后端 Pydantic schema 严格对应的 TypeScript 类型：

- 响应类型命名为 `{Resource}ApiResponse`（完整响应）或 `{Resource}ApiItem`（列表项）
- 保持后端字段命名（snake_case）和数据类型（日期为 string）
- 覆盖角色、技能、群聊、会话、消息、配置等核心资源

## Design Rationale

**为什么每个 feature 独立 store 而不是全局大 store？**
- 独立 store 保证模块边界清晰，避免"上帝 store"导致的耦合
- 每个 store 只管理自己领域的状态，职责单一
- 跨模块共享通过订阅实现，保持依赖方向可控

**为什么禁止 feature 间直接 import？**
- 直接 import 会导致编译时耦合，一个模块的修改可能影响其他模块
- 通过 store 订阅和 props 通信，保持运行时依赖，降低耦合度
- 便于独立开发和测试

**为什么 adapter 必须是纯函数且禁止相互调用？**
- 纯函数保证可测试性和可预测性
- 禁止相互调用避免 adapter 层出现隐式依赖链
- 嵌套组合在 hooks 层完成，hooks 层是业务逻辑的天然编排点

**为什么通过 adapters 转发 API schema 类型？**
- 统一入口避免 feature 模块直接依赖 `api-schemas.ts` 的路径
- 如果 API schema 路径变化，只需修改 adapters 的转发，不影响 feature 模块
- 保持"一个事实来源"原则

**已知限制**：
- 当前 Zustand store 不支持持久化（需要时可添加 `persist` 中间件）
- 跨 feature 通信仅支持单向数据流，不支持双向绑定

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **Core 层**：`docs/specs/2026-06-06-frontend-core.md` — WebSocket 管理、API 客户端、存储
- **WebSocket 协议**：websocket-backend spec — 消息格式、连接管理
- **后端 API**：各后端模块 spec — 路由、Service、数据模型
- **前端 UI/UX 设计规范**：`docs/DESIGN.md` — 样式、交互规范
