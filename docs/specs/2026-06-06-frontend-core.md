---
version: 1.0
created_at: 2026-06-06
updated_at: 2026-06-06
last_updated: 创建 frontend-core 模块 spec
abstract: 前端核心层规格，定义 WebSocket 连接管理、REST API 客户端、本地存储和主题管理的职责边界与行为契约
id: frontend-core
title: Frontend Core 层
status: draft
module: frontend-core
sourc_spec:
related_plan:
code_scope: frontend/src/core/
contract_refs: frontend/src/core/websocket/WebSocketManager.ts, frontend/src/core/api/client.ts, frontend/src/core/storage/index.ts, frontend/src/core/theme/ThemeManager.ts
---

## 版本

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-06-06 | 初始版本 |

## Overview

Frontend Core 层是业务无关的基础设施层，位于 `frontend/src/core/`，向上为 features 和 shared 模块提供四种基础能力：

1. **WebSocket 连接管理** -- 实时双向通信的生命周期管理
2. **REST API 客户端** -- 统一的 HTTP 请求封装与错误处理
3. **本地存储** -- 基于 IndexedDB 的客户端持久化
4. **主题管理** -- 明暗主题切换与系统偏好同步

Core 层不包含任何业务逻辑，不感知具体 feature 的数据结构。所有 API 函数仅负责请求发起和响应返回，不做数据转换或业务判断。

## Scope

### 子模块职责边界

| 子模块 | 路径 | 职责 | 不做的事 |
|--------|------|------|----------|
| WebSocket | `core/websocket/` | 连接生命周期、重连策略、消息队列、事件分发 | 不处理具体业务消息格式，不实现聊天逻辑 |
| API Client | `core/api/client.ts` | Axios 实例配置、请求/响应拦截、统一错误类型、Mock 开关 | 不定义业务接口，不做数据转换 |
| API 函数 | `core/api/groupChatApi.ts` 等 | 各业务域的 REST 接口封装 | 不包含业务逻辑判断，不做数据聚合 |
| Storage | `core/storage/` | IndexedDB 初始化、last_view_at 记录的读写 | 不定义业务表结构，不做数据校验 |
| Theme | `core/theme/` | 主题状态持久化、DOM 属性注入、系统偏好监听 | 不定义具体 CSS 变量值，不处理组件级样式 |

### 依赖方向

```
features / shared  -->  core  -->  浏览器 API（WebSocket、IndexedDB、localStorage）
```

Core 层禁止反向依赖 features 或 shared 中的业务模块。

## Core Behavior

### WebSocket 连接管理

#### 连接策略

- **单例模式**：全局唯一的 WebSocketManager 实例，通过 `getInstance()` 获取
- **连接对象**：每个 chatId 对应一条 WebSocket 连接，连接 URL 格式为 `{wsBaseUrl}/ws/group_chat/{chatId}`
- **防重复连接**：对同一 chatId 且连接已处于 OPEN 状态时，跳过重复连接
- **连接切换**：连接新 chatId 时，先断开旧连接再创建新连接

#### 重连策略（指数退避）

- 触发条件：非主动断开（`isIntentionalClose === false`）时自动重连
- 退避间隔：`[1000, 2000, 4000, 8000, 16000]` 毫秒（指数递增）
- 最大重试次数：5 次
- 重试耗尽：触发 error 事件，通知上层连接失败
- 主动断开（调用 `disconnect()`）不触发重连，同时清除已调度的重连定时器

#### 消息队列

- 离线缓存：连接未就绪时，发送的消息进入队列
- 队列上限：100 条，超出时丢弃最早的消息并打印警告
- 刷新时机：连接建立成功（onopen）后，自动发送队列中的所有消息
- 队列为空时不执行刷新操作

#### 事件订阅模式

- 支持的事件类型：`connected`、`disconnected`、`message`、`refresh`、`error`
- 订阅：`on(event, callback)` -- 同一事件可注册多个回调
- 取消订阅：`off(event, callback)` -- 精确移除指定回调
- 回调隔离：单个回调的异常不影响其他回调的执行
- 消息分发：收到消息时，`type === 'refresh'` 的消息触发 `refresh` 事件，其余触发 `message` 事件

### REST API 客户端

#### Axios 实例配置

- Base URL：由环境变量 `VITE_API_BASE_URL` 决定，默认 `http://localhost:8000/api/v1`
- 超时时间：30 秒
- 默认请求头：`Content-Type: application/json`

#### 请求拦截器

- 认证注入：从 `localStorage` 读取 `auth_token`，存在时添加 `Authorization: Bearer {token}` 请求头
- 开发日志：`VITE_DEBUG=true` 时打印请求方法、URL、请求体

#### 响应拦截器

- 数据解包：直接返回 `response.data`，调用方无需再访问 `.data` 属性
- 错误转换：将 AxiosError 统一转换为 ApiError，保留 `error_code`、`message`、`status`、`data` 四个字段
- 网络错误（无 response）时，status 设为 0，error_code 设为 `NETWORK_ERROR`
- 开发模式下打印错误日志

#### Mock 支持

- 开关：环境变量 `VITE_USE_MOCK=true` 启用 Mock 模式
- 实现：`mockableRequest(realRequest, mockData)` 函数，Mock 模式下返回固定数据并模拟 200-500ms 网络延迟
- 约束：Mock 数据必须不可变（`const`），不实现业务逻辑，仅返回静态测试夹具

### 本地存储（Storage）

- **存储引擎**：IndexedDB，数据库名 `agents-hub-storage`，版本 1
- **存储对象**：`session-views` store，主键为 `group_chat_id`
- **用途**：持久化各群聊的 `last_view_at` 时间戳，用于判断未读状态
- **初始化**：懒初始化，首次调用读写方法时自动打开数据库，通过 Promise 防止重复初始化
- **单例模式**：全局唯一的 Storage 实例

### 主题管理（ThemeManager）

- **单例模式**：全局唯一的 ThemeManager 实例
- **主题类型**：`light` 和 `dark` 两种
- **持久化**：通过 `localStorage` 存储用户选择的 `theme` 键值
- **初始化策略**：优先读取 localStorage 中的保存值，无保存值时跟随系统偏好（`prefers-color-scheme`）
- **DOM 注入方式**：暗色主题通过在 `<html>` 元素设置 `data-theme="dark"` 属性实现，亮色主题移除该属性。CSS 通过 `[data-theme="dark"]` 选择器切换变量值
- **系统偏好监听**：`watchSystemTheme(callback)` 监听系统主题变化，返回取消监听的清理函数

## Technical Contract

### WebSocketManager 接口

| 方法 | 语义 |
|------|------|
| `getInstance()` | 获取单例实例 |
| `connect(chatId)` | 连接到指定群聊的 WebSocket |
| `disconnect()` | 主动断开连接并清理资源 |
| `send(data)` | 发送消息，连接不可用时入队 |
| `on(event, callback)` | 订阅指定事件 |
| `off(event, callback)` | 取消订阅指定事件 |
| `getState()` | 获取当前连接状态 |
| `getReconnectAttempts()` | 获取当前重连次数 |

### API Client 接口

| 方法 | 语义 |
|------|------|
| `apiClient.get(url, config)` | GET 请求，返回解包后的数据 |
| `apiClient.post(url, data, config)` | POST 请求 |
| `apiClient.put(url, data, config)` | PUT 请求 |
| `apiClient.patch(url, data, config)` | PATCH 请求 |
| `apiClient.delete(url, config)` | DELETE 请求 |
| `mockableRequest(realRequest, mockData)` | 根据环境变量决定走真实请求还是返回 Mock 数据 |

### ApiError 接口

| 字段 | 语义 |
|------|------|
| `code` | 错误码（后端 error_code 或 `NETWORK_ERROR`） |
| `message` | 人类可读的错误描述 |
| `status` | HTTP 状态码，网络错误时为 0 |
| `data` | 后端返回的原始错误数据（可选） |

### API 函数分组

#### groupChat API

| 函数 | 语义 |
|------|------|
| `createGroupChat(data)` | 创建并启动新群聊 |
| `getGroupChatInfo(chatId)` | 获取群聊基本信息 |
| `listGroupChats(isActiveOnly)` | 列出所有群聊（可过滤仅活跃） |
| `listGroupChatInfos(isActiveOnly)` | 列出群聊（含最后消息扩展信息） |
| `getMessages(chatId, limit, before)` | 分页获取消息历史（游标分页） |
| `getMembers(chatId)` | 获取群聊成员列表 |
| `sendMessage(chatId, data)` | 向群聊发送消息 |
| `updateMemberDockerMode(chatId, memberName, useDocker)` | 切换成员 Docker 沙箱模式 |
| `deleteGroupChat(chatId, keepData)` | 删除群聊（支持保留数据的软删除） |

#### role API

| 函数 | 语义 |
|------|------|
| `buildAvatarUrl(filename)` | 根据头像文件名构建完整访问 URL |
| `createRole(data)` | 创建角色 |
| `getRoleInfo(name)` | 获取单个角色信息 |
| `listRoles()` | 列出所有角色 |
| `updateRole(name, data)` | 更新角色信息 |
| `deleteRole(name)` | 删除角色 |
| `getRoleSkills(name)` | 列出角色关联的 Skills |
| `addSkillToRole(name, skillId)` | 为角色添加 Skill |
| `removeSkillFromRole(name, skillId)` | 移除角色的 Skill |
| `listAvatars()` | 列出所有可用头像 |

#### skill API

| 函数 | 语义 |
|------|------|
| `listSkills()` | 获取所有技能 |
| `getSkill(name)` | 获取单个技能信息 |
| `addSkill(data)` | 添加新技能 |
| `deleteSkill(name)` | 删除技能 |

#### team API

| 函数 | 语义 |
|------|------|
| `listTeams()` | 获取所有团队 |
| `getTeam(name)` | 获取单个团队信息 |
| `createTeam(data)` | 创建团队 |
| `updateTeam(name, data)` | 更新团队信息 |
| `deleteTeam(name)` | 删除团队 |

### Storage 接口

| 方法 | 语义 |
|------|------|
| `init()` | 初始化 IndexedDB（懒加载，防重复） |
| `getLastViewRecords()` | 读取所有群聊的 last_view_at 记录 |
| `setLastView(groupChatId, timestamp)` | 写入单条 last_view_at 记录 |
| `batchSetLastView(records)` | 批量写入 last_view_at 记录 |

### ThemeManager 接口

| 方法 | 语义 |
|------|------|
| `getInstance()` | 获取单例实例 |
| `getTheme()` | 获取当前主题 |
| `setTheme(theme)` | 设置指定主题并持久化 |
| `toggleTheme()` | 在明暗主题间切换 |
| `watchSystemTheme(callback)` | 监听系统主题偏好变化，返回清理函数 |

### WebSocket 事件类型

| 事件 | 触发时机 | 数据 |
|------|----------|------|
| `connected` | 连接建立成功 | 无 |
| `disconnected` | 主动断开连接 | 无 |
| `message` | 收到非 refresh 类型消息 | 消息对象 |
| `refresh` | 收到 type=refresh 的消息 | RefreshSignal |
| `error` | 连接错误或重试耗尽 | Error 对象 |

## Out of Spec

以下内容不在本 spec 范围内，由其他文档或上层模块定义：

- TypeScript 类型定义的具体字段和结构（见 `frontend/src/shared/types/`）
- API 函数的具体请求/响应数据结构（见各业务 spec）
- CSS 变量的具体值和设计系统规范（见 `docs/DESIGN.md`）
- hooks 层如何调用 core 层的实现细节（见 `frontend/src/shared/hooks/`）
- store 层的状态字段定义（见各 feature 的 store）
- 各 feature 的业务逻辑和组件实现
- WebSocket 消息的具体业务格式（见 realtime spec）
