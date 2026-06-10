---
version: 1.1
created_at: 2026-06-03
updated_at: 2026-06-06
last_updated: 修复 spec 与代码实际状态的不一致
abstract: Group Chat API 模块的正式规格，定义群聊生命周期管理、成员管理、消息交互和 Docker 沙箱控制的 RESTful 接口
id: group-chat-api
title: Group Chat API 模块
status: draft
module: api/group_chat
sourc_spec: 无（从源码直接分析生成）
related_plan: 无（当前无对应执行计划）
code_scope:
  - agents_hub/api/routes/group_chat.py
  - agents_hub/api/schemas/group_chats.py
  - agents_hub/api/services/group_chat_service.py
contract_refs:
  - agents_hub/api/schemas/group_chats.py
---

# Group Chat API 模块

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |
| 1.1 | 修复与代码不一致：MessageCreate 字段 send_to→members；分页 offset→before 游标；GroupChatInfo 补充 last_speaker/last_message/last_update_time |

## Overview

Group Chat API 模块为前端提供群聊管理的 RESTful 接口，涵盖群聊生命周期管理、成员信息查询、消息历史获取和 Docker 沙箱控制。该模块是 core/orchestration 层的 API 入口，通过 Service 层协调核心层的 GroupChatManager 和 Team。

**架构分层**：
- **Route 层**：HTTP 入口，负责参数接收和响应转换
- **Service 层**：业务编排层，协调核心层组件
- **Schema 层**：Pydantic 模型，负责请求验证和响应序列化

## Scope

**当前阶段**：
- 群聊创建、查询、删除
- 群聊成员信息查询
- 消息历史获取和发送
- Docker 沙箱开关控制
- 支持 keep_data 模式（仅从内存移除，保留磁盘数据）

**不在范围内**：
- 群聊配置修改（如修改团队成员、群聊名称等）
- 消息搜索和过滤
- 批量操作
- WebSocket 实时推送（由独立模块处理）

## Core Behavior

### 群聊生命周期

```
创建: POST /api/v1/group-chats
  → 验证 team_members 非空且 roles 存在
  → 生成唯一 group_chat_id
  → 初始化群聊并启动
  → 注册到全局管理器

查询: GET /api/v1/group-chats
  → 获取所有群聊元数据
  → 可选过滤活跃状态

详情: GET /api/v1/group-chats/{group_chat_id}
  → 加载群聊（内存优先，磁盘 fallback）
  → 返回完整信息

删除: DELETE /api/v1/group-chats/{group_chat_id}?keep_data=false
  → keep_data=false: 完全删除（内存 + 磁盘）
  → keep_data=true: 仅从内存移除
```

### 消息交互流程

```
发送消息: POST /api/v1/group-chats/{group_chat_id}/messages
  → 验证消息格式和目标角色
  → 激活群聊（如未激活）
  → 路由消息到目标 agent

获取历史: GET /api/v1/group-chats/{group_chat_id}/messages?limit=30&before=<timestamp>
  → 游标分页读取消息历史（返回 before 时间戳之前的消息）
  → 返回消息列表
```

### Docker 沙箱控制

```
切换开关: PUT /api/v1/group-chats/{group_chat_id}/{role_name}/use-docker
  → 验证角色是群聊成员
  → 检查 Docker 环境可用性（开启时）
  → 更新配置并持久化
```

## Technical Contract

### 端点总览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/group-chats` | 创建群聊 |
| GET | `/api/v1/group-chats` | 列出所有群聊 |
| GET | `/api/v1/group-chats/{group_chat_id}` | 获取群聊详情 |
| DELETE | `/api/v1/group-chats/{group_chat_id}` | 删除群聊 |
| GET | `/api/v1/group-chats/{group_chat_id}/members` | 获取成员列表 |
| GET | `/api/v1/group-chats/{group_chat_id}/messages` | 获取消息历史 |
| POST | `/api/v1/group-chats/{group_chat_id}/messages` | 发送消息 |
| PUT | `/api/v1/group-chats/{group_chat_id}/{role_name}/use-docker` | 切换 Docker 开关 |

### Schema 定义

**GroupChatCreate**（创建请求）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| team_members | list[str] | 是 | 团队成员角色名列表（min_length=1） |
| project_path | str | 是 | 项目路径 |
| group_chat_name | str \| None | 否 | 群聊名称（默认使用 group_chat_id） |

**GroupChatInfo**（群聊详情响应）：

| 字段 | 类型 | 说明 |
|------|------|------|
| group_chat_id | str | 群聊唯一标识（UUID） |
| group_chat_name | str | 群聊显示名称 |
| project_path | str | 关联的项目路径 |
| created_at | datetime | 创建时间 |
| group_type | GroupChatType | 编排模式（MANAGER_ORCHESTRATE / SEQUENCE_EXECUTE） |
| is_active | bool | agent 是否已激活（run() 任务是否在运行） |
| last_speaker | str \| None | 最近一次发言的 agent 角色名 |
| last_message | str \| None | 最近一条消息内容 |
| last_update_time | str \| None | 最近更新时间 |

**GroupChatSummary**（列表摘要响应）：

| 字段 | 类型 | 说明 |
|------|------|------|
| group_chat_id | str | 群聊唯一标识 |
| group_chat_name | str | 群聊显示名称 |
| project_path | str | 关联的项目路径 |
| is_active | bool | 是否活跃 |
| created_at | datetime | 创建时间 |

**GroupChatMember**（成员信息响应）：

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | 角色名称（如 "pm", "architect"） |
| main_session | str \| None | 主会话 ID |
| btw_session | list[str] | 额外的临时会话 ID 列表 |
| cwd | str \| None | 该成员的工作目录 |
| use_docker | bool | 是否使用 Docker 隔离运行（默认 False） |

**MessageCreate**（发送消息请求）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| content | str | 是 | 消息内容（min_length=1） |
| members | list[str] | 是 | 群聊中所有 agent 名称列表（min_length=1） |

**MessageInfo**（消息信息响应）：

| 字段 | 类型 | 说明 |
|------|------|------|
| speaker | str | 发送者名称（agent 角色名或 "user"） |
| content | str | 消息内容 |
| timestamp | str | 时间戳 |
| platform | str | 来源平台 |

**UseDockerUpdate**（Docker 开关请求）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| use_docker | bool | 是 | 是否启用 Docker 沙箱执行 |

### 查询参数

**GET /api/v1/group-chats**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| is_active_only | bool | false | 是否只返回活跃群聊 |

**GET /api/v1/group-chats/{group_chat_id}/messages**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| limit | int | 30 | 返回消息数量上限（1-500） |
| before | str \| None | None | 游标时间戳，返回此时间之前的消息 |

**DELETE /api/v1/group-chats/{group_chat_id}**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| keep_data | bool | false | true=仅从内存移除，false=完全删除 |

### 异常处理

所有异常由全局异常处理器统一处理，路由层不捕获异常。

**错误响应格式**（统一）：
```json
{
  "error_code": "ERROR_CODE",
  "message": "人类可读错误信息"
}
```

**HTTP 状态码使用规则**：
- **400**：请求格式/语法错误（如 JSON 解析失败、路径参数非法、文件格式错误）
- **404**：资源不存在（群聊、角色、项目路径）
- **422**：请求格式正确但业务规则违反（如 team_members 为空、content 包含非法字符、目标角色不是成员）
- **500**：服务器内部错误（启动失败、加载失败、文件操作失败）
- **503**：外部服务不可用（如 Docker 未运行）

| HTTP 状态码 | 触发场景 |
|-------------|----------|
| 400 | 请求参数格式错误 |
| 404 | 群聊不存在、角色不存在、项目路径不存在 |
| 422 | 业务规则违反（如 team_members 为空、content 包含非法字符、目标角色不是成员） |
| 500 | 服务器内部错误（启动失败、加载失败、文件操作失败） |
| 503 | 外部服务不可用（如 Docker 未运行）

**异常类定义**（遵循项目双重继承模式）：

| 异常类 | 继承自 | 场景 |
|--------|--------|------|
| GroupChatServiceError | AgentsHubError | Group Chat API 模块基类 |
| GroupChatNotFoundError | GroupChatServiceError, ResourceNotFoundError | 群聊不存在 |
| MemberNotFoundError | GroupChatServiceError, ResourceNotFoundError | 成员不存在 |
| InvalidMessageError | GroupChatServiceError, ValidationError | 消息格式错误 |
| GroupChatAlreadyActiveError | GroupChatServiceError, StateError | 群聊已激活时重复启动 |
| DockerNotAvailableError | GroupChatServiceError, ExternalServiceError | Docker 环境不可用 | |

## Interaction / UX Notes

- 群聊创建后自动启动，无需手动激活
- 发送消息时自动激活群聊，无需手动启动
- 删除群聊时默认完全删除，可通过参数保留磁盘数据
- Docker 开关切换后立即生效
- 消息历史支持分页查询

## Acceptance Notes

1. 群聊创建成功后返回完整信息，包含 group_chat_id
2. 群聊列表支持过滤活跃状态
3. 成员信息正确返回（包含会话信息和 Docker 配置）
4. 消息发送后正确路由到目标 agent
5. Docker 开关切换后状态正确持久化
6. 异常情况返回正确的 HTTP 状态码和错误信息

## Out of Spec

以下内容不在本 spec 中长期维护：

1. WebSocket 实时推送机制（由 websocket-backend spec 处理）
2. 群聊配置动态修改（如修改团队成员、群聊名称等）
3. 消息搜索和高级过滤功能
4. 批量操作接口
5. 认证与授权机制
6. 前端实现细节
