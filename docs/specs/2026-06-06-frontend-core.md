---
version: 1.1
created_at: 2026-06-06
updated_at: 2026-06-18
last_updated: 按 spec-write-rules v2.0 重构，添加 key_function 标注和 Design Rationale
abstract: 前端核心层规格，定义 WebSocket 连接管理、REST API 客户端、本地存储和主题管理的职责边界与行为契约
---

# Frontend Core 层

## 版本

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-06-06 | 初始版本 |
| 1.1 | 2026-06-18 | 按 spec-write-rules v2.0 重构，添加 key_function 标注和 Design Rationale |

## Overview

**业务问题**：

前端应用需要与后端实时通信（WebSocket）、发起 HTTP 请求（REST API）、持久化客户端数据（IndexedDB）、管理明暗主题，但这些基础能力不应与具体业务逻辑耦合，否则会导致：
- 每个 feature 都重复实现连接管理和错误处理
- 无法统一控制 Mock 模式和认证注入
- 主题切换逻辑散落在多个组件中

**核心职责**：

Core 层是业务无关的基础设施层，向上为 features 和 shared 模块提供四种标准化能力：

1. **WebSocket 连接管理** -- 实时双向通信的生命周期管理、重连策略、消息队列
2. **REST API 客户端** -- 统一的 HTTP 请求封装、错误转换、Mock 模式切换
3. **本地存储** -- 基于 IndexedDB 的客户端持久化（仅存储 last_view_at）
4. **主题管理** -- 明暗主题切换与系统偏好同步

Core 层不包含任何业务逻辑，不感知具体 feature 的数据结构。所有 API 函数仅负责请求发起和响应返回，不做数据转换或业务判断。

## Scope

### 范围内

- WebSocket 连接生命周期管理（连接、断开、重连）
- WebSocket 消息队列和事件分发机制
- Axios 实例配置、请求/响应拦截器
- 统一的 ApiError 类型和错误转换
- Mock 模式的统一开关（`mockableRequest` 函数）
- 各业务域的 REST 接口封装（groupChat、role、skill、team API）
- IndexedDB 初始化和 last_view_at 记录的读写
- 主题状态持久化和 DOM 属性注入
- 系统主题偏好监听

### 范围外

以下内容不在本模块范围内：

- **业务消息格式处理** -- 由 features 层处理具体消息结构（见 `docs/specs/realtime.md`）
- **数据转换和业务逻辑判断** -- 由 features 层的 hooks 和 store 处理
- **TypeScript 类型定义** -- 由 `frontend/src/shared/types/` 定义
- **CSS 变量值和设计系统** -- 由 `docs/DESIGN.md` 定义
- **业务 hooks 实现** -- 由 `frontend/src/shared/hooks/` 和各 feature 实现

### 依赖方向

```
features / shared  -->  core  -->  浏览器 API（WebSocket、IndexedDB、localStorage）
```

Core 层禁止反向依赖 features 或 shared 中的业务模块。

## Technical Contract

### WebSocketManager

<key_function last_update="2026-06-27T23:39:49+08:00">
- frontend/src/core/websocket/WebSocketManager.ts
  - WebSocketManager.getInstance:41
  - WebSocketManager.connect:18
  - WebSocketManager.disconnect:28
  - WebSocketManager.send:99
  - WebSocketManager.on:121
  - WebSocketManager.off:131
  - WebSocketManager.getState:141
  - WebSocketManager.getReconnectAttempts:148
  - WebSocketManager.emit:158
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| getInstance() | 获取单例实例 | 静态方法 |
| connect(chatId: string) | 连接到指定群聊的 WebSocket | 连接已存在时跳过重复连接 |
| disconnect() | 主动断开连接并清理资源 | 不触发自动重连 |
| send(data: unknown) | 发送消息，连接不可用时入队 | 队列上限 100 条 |
| on(event, callback) | 订阅指定事件 | 同一事件可多个回调 |
| off(event, callback) | 取消订阅指定事件 | 精确移除指定回调 |
| getState() | 获取当前连接状态 | 返回 WebSocketState 枚举 |
| getReconnectAttempts() | 获取当前重连次数 | 用于 UI 显示重连状态 |
| emit(event, data?) | 本地事件分发（不发送到服务器） | 用于 mutation hook 触发刷新 |

**连接策略**：
- 单例模式：全局唯一实例
- 每个 chatId 对应一条 WebSocket 连接，URL 格式 `{wsBaseUrl}/ws/group_chat/{chatId}`
- 防重复连接：同一 chatId 且连接已 OPEN 时跳过
- 连接切换：先断开旧连接再创建新连接

**重连策略（指数退避）**：
- 触发条件：非主动断开（`isIntentionalClose === false`）
- 退避间隔：`[1000, 2000, 4000, 8000, 16000]` 毫秒
- 最大重试次数：5 次
- 主动断开不触发重连，清除已调度的重连定时器

**消息队列**：
- 连接未就绪时，发送的消息进入队列
- 队列上限：100 条，超出时丢弃最早的消息
- 刷新时机：连接建立成功后自动发送队列中的所有消息

**事件订阅**：
- 支持的事件：`connected`、`disconnected`、`message`、`refresh`、`error`
- 消息分发：`type === 'refresh'` 的消息触发 `refresh` 事件，其余触发 `message` 事件
- 回调隔离：单个回调的异常不影响其他回调

### API Client

<key_function last_update="2026-06-18T14:30:00+08:00">
- frontend/src/core/api/client.ts
  - client.ApiError.fromResponse:51
  - client.mockableRequest:138
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| apiClient.get<T>(url, config?) | GET 请求 | 返回解包后的数据（T 类型） |
| apiClient.post<T>(url, data?, config?) | POST 请求 | 返回解包后的数据 |
| apiClient.put<T>(url, data?, config?) | PUT 请求 | 返回解包后的数据 |
| apiClient.patch<T>(url, data?, config?) | PATCH 请求 | 返回解包后的数据 |
| apiClient.delete<T>(url, config?) | DELETE 请求 | 返回解包后的数据 |
| mockableRequest<T>(realRequest, mockData) | Mock 模式切换 | 根据 VITE_USE_MOCK 决定走真实请求还是返回 Mock 数据 |

**Axios 实例配置**：
- Base URL：`VITE_API_BASE_URL` 或默认 `http://localhost:8000/api/v1`
- 超时：30 秒
- 默认请求头：`Content-Type: application/json`

**请求拦截器**：
- 认证注入：从 localStorage 读取 `auth_token`，存在时添加 `Authorization: Bearer {token}`
- 开发日志：`VITE_DEBUG=true` 时打印请求方法、URL、请求体

**响应拦截器**：
- 数据解包：直接返回 `response.data`，调用方无需再访问 `.data` 属性
- 错误转换：将 AxiosError 统一转换为 ApiError
- 网络错误（无 response）时，status 设为 0，error_code 设为 `NETWORK_ERROR`

**ApiError 接口**：

| 字段 | 说明 |
|------|------|
| code | 错误码（后端 error_code 或 `NETWORK_ERROR`） |
| message | 人类可读的错误描述 |
| status | HTTP 状态码，网络错误时为 0 |
| data | 后端返回的原始错误数据（可选） |

### API 函数（各业务域）

以下 API 函数由各业务模块导出，均使用 `mockableRequest` 支持 Mock 模式。

#### groupChat API

导出自 `frontend/src/core/api/groupChatApi.ts`

| 函数 | 说明 |
|------|------|
| createGroupChat(data: CreateGroupChatRequest) | 创建并启动新群聊 |
| getGroupChatInfo(chatId: string) | 获取群聊基本信息 |
| listGroupChats(isActiveOnly?: boolean) | 列出所有群聊（可过滤仅活跃） |
| listGroupChatInfos(isActiveOnly?: boolean) | 列出群聊（含最后消息扩展信息） |
| getMessages(chatId: string, limit?: number, before?: string) | 分页获取消息历史（游标分页） |
| getMembers(chatId: string) | 获取群聊成员列表 |
| sendMessage(chatId: string, data: SendMessageRequest) | 向群聊发送消息 |
| updateMemberDockerMode(chatId: string, memberName: string, useDocker: boolean) | 切换成员 Docker 沙箱模式 |
| deleteGroupChat(chatId: string, keepData?: boolean) | 删除群聊（支持保留数据的软删除） |

#### role API

导出自 `frontend/src/core/api/roleApi.ts`

| 函数 | 说明 |
|------|------|
| buildAvatarUrl(filename: string) | 根据头像文件名构建完整访问 URL |
| createRole(data: CreateRoleRequest) | 创建角色 |
| getRoleInfo(name: string) | 获取单个角色信息 |
| listRoles() | 列出所有角色 |
| updateRole(name: string, data: UpdateRoleRequest) | 更新角色信息（`name` 为路径参数） |
| deleteRole(name: string) | 删除角色 |
| getRoleSkills(name: string) | 列出角色关联的 Skills |
| addSkillToRole(name: string, skillId: string) | 为角色添加 Skill |
| removeSkillFromRole(name: string, skillId: string) | 移除角色的 Skill |
| listAvatars() | 列出所有可用头像 |

#### skill API

导出自 `frontend/src/core/api/skillApi.ts`

| 函数 | 说明 |
|------|------|
| listSkills() | 获取所有技能 |
| getSkill(name: string) | 获取单个技能信息 |
| addSkill(data: CreateSkillRequest) | 添加新技能 |
| deleteSkill(name: string) | 删除技能 |

#### team API

导出自 `frontend/src/core/api/teamApi.ts`

| 函数 | 说明 |
|------|------|
| listTeams() | 获取所有团队 |
| getTeam(name: string) | 获取单个团队信息 |
| createTeam(data: CreateTeamRequest) | 创建团队 |
| updateTeam(name: string, data: UpdateTeamRequest) | 更新团队信息 |
| deleteTeam(name: string) | 删除团队 |

### Storage

<key_function last_update="2026-06-18T14:30:00+08:00">
- frontend/src/core/storage/index.ts
  - Storage.init:28
  - Storage.getLastViewRecords:64
  - Storage.setLastView:95
  - Storage.batchSetLastView:116
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| init() | 初始化 IndexedDB | 懒加载，防重复初始化 |
| getLastViewRecords() | 读取所有群聊的 last_view_at 记录 | 返回 `Record<string, string>` |
| setLastView(groupChatId, timestamp) | 写入单条 last_view_at 记录 | timestamp 为 ISO 8601 格式 |
| batchSetLastView(records) | 批量写入 last_view_at 记录 | 参数为 `{ id, timestamp }[]` |

**存储引擎**：
- IndexedDB，数据库名 `agents-hub-storage`，版本 1
- 存储对象：`session-views` store，主键为 `group_chat_id`
- 用途：持久化各群聊的 `last_view_at` 时间戳，用于判断未读状态

### ThemeManager

<key_function last_update="2026-06-18T14:30:00+08:00">
- frontend/src/core/theme/ThemeManager.ts
  - ThemeManager.getInstance:12
  - ThemeManager.getTheme:35
  - ThemeManager.setTheme:39
  - ThemeManager.toggleTheme:45
  - ThemeManager.watchSystemTheme:50
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| getInstance() | 获取单例实例 | 静态方法 |
| getTheme() | 获取当前主题 | 返回 `'light' \| 'dark'` |
| setTheme(theme: Theme) | 设置指定主题并持久化 | 同步更新 DOM 和 localStorage |
| toggleTheme() | 在明暗主题间切换 | 调用 setTheme 切换 |
| watchSystemTheme(callback) | 监听系统主题偏好变化 | 返回清理函数 |

**主题管理策略**：
- 持久化：通过 localStorage 存储用户选择的 `theme` 键值
- 初始化：优先读取 localStorage，无保存值时跟随系统偏好（`prefers-color-scheme`）
- DOM 注入方式：暗色主题在 `<html>` 元素设置 `data-theme="dark"` 属性，亮色主题移除该属性

## Design Rationale

### 为什么这样设计？

1. **单例模式（WebSocketManager、ThemeManager、Storage）**
   - 确保全局只有一个 WebSocket 连接和主题状态
   - 避免多个组件重复初始化 IndexedDB
   - 简化状态同步，所有组件访问同一个实例

2. **响应拦截器直接返回 data**
   - 简化调用代码，避免 `response.data.data` 嵌套访问
   - 统一错误转换为 ApiError，调用方只需处理一种错误类型

3. **mockableRequest 函数而非 MSW**
   - 轻量级，无需额外的 service worker 配置
   - 通过环境变量统一控制，一键切换 Mock/真实 API
   - Mock 数据与 API 函数共置，便于维护

4. **key_function 标签只标注类的公共方法**
   - 前端的"对外接口"是导出的类和函数
   - 私有方法（`_createConnection`、`_emit` 等）不是契约的一部分，不标注
   - API 函数均为简单封装，无需标注（已在表格中定义契约）

5. **WebSocket 消息队列**
   - 解决连接未就绪时的消息丢失问题
   - 限制队列大小避免内存溢出
   - 连接成功后自动刷新队列，无需上层干预

6. **指数退避重连策略**
   - 避免连接失败时频繁重试导致服务器压力
   - 最大 5 次重试后放弃，避免无限重连
   - 主动断开不触发重连，避免用户关闭后自动重连

### 有哪些约束？

1. **Core 层禁止依赖 features 层**
   - 保持基础设施层的通用性
   - 避免循环依赖

2. **Mock 数据必须不可变（const）**
   - Mock 不实现业务逻辑（不模拟 CRUD）
   - 避免测试间状态污染

3. **API 函数不做数据转换**
   - 保持 Core 层的纯粹性
   - 数据转换由 features 层的 hooks 处理

4. **Storage 只存储 last_view_at**
   - 避免 Core 层定义业务表结构
   - 其他持久化需求由 features 层自行实现

### 有哪些已知限制？

1. **WebSocket 连接限制**
   - 同一时间只能连接一个群聊（设计选择，非技术限制）
   - 切换群聊会断开旧连接

2. **Mock 模式的局限性**
   - Mock 数据是静态的，不支持分页、过滤等动态查询
   - Mock 模式下无法测试网络错误恢复逻辑

3. **IndexedDB 浏览器兼容性**
   - 部分老旧浏览器不支持 IndexedDB
   - 无降级方案（localStorage 无法存储大量数据）

4. **认证 token 存储在 localStorage**
   - 存在 XSS 攻击风险（httpOnly cookie 更安全）
   - 当前为简化实现，后续可迁移到 httpOnly cookie

### 相关 ADR

- 暂无相关架构决策记录

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **WebSocket 消息格式和业务处理** -- 见 `docs/specs/realtime.md`（待创建）
- **TypeScript 类型定义** -- 见 `frontend/src/shared/types/`
- **设计系统和 CSS 变量** -- 见 `docs/DESIGN.md`
- **业务 hooks 实现** -- 见 `frontend/src/shared/hooks/` 和各 feature
- **状态管理（store）** -- 见各 feature 的 store 实现
- **前端架构全局约束** -- 见 `frontend/CLAUDE.md`
