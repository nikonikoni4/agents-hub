---
version: 2.1
created_at: 2026-06-03
updated_at: 2026-06-18
last_updated: 按 spec-write-rules v2.0 清理执行细节，保留业务契约和设计决策
abstract: Group Chat API 模块的正式规格，定义群聊生命周期管理、成员管理、消息交互和 Docker 沙箱控制的 RESTful 接口
---

# Group Chat API 模块

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |
| 1.1 | 修复与代码不一致：MessageCreate 字段 send_to→members；分页 offset→before 游标；GroupChatInfo 补充 last_speaker/last_message/last_update_time |
| 1.2 | 补全端点总览、Schema 定义、异常体系、行为规则，修正与代码的不一致 |
| 1.3 | 补全缺失端点（27+）、补充 Schema 字段与新 Schema、修正异常类为项目标准体系、补充行为规则与查询参数 |
| 2.0 | 重构为新 spec 格式（业务意图 + 技术契约 + 设计决策），添加 key_function 标签，新增 Design Rationale 章节 |
| 2.1 | 按 spec-write-rules v2.0 清理执行细节，移除调用链路和实现步骤，保留业务契约 |

## Overview

**业务问题**：前端需要通过 HTTP API 管理群聊的完整生命周期，包括创建、查询、删除群聊，管理成员，发送和获取消息，以及控制 Docker 沙箱隔离。

**核心职责**：
- 提供群聊生命周期管理的 RESTful 接口
- 暴露成员信息查询和消息历史获取的 HTTP 端点
- 提供 Docker 沙箱开关控制接口
- 作为前端与 core/orchestration 层的 API 网关
- 协调 Service 层完成请求验证、业务编排和响应序列化

## Scope

### 范围内

- 群聊创建、查询、删除的 HTTP 端点
- 群聊成员信息查询接口
- 消息历史获取和发送接口
- Docker 沙箱开关控制接口
- keep_data 模式（仅从内存移除，保留磁盘数据）
- Request/Response 的 Schema 定义和验证
- HTTP 路由处理和异常转换

### 范围外

- 群聊配置动态修改（如修改团队成员、群聊名称等）→ 未来功能
- 消息搜索和高级过滤功能 → 未来功能
- 批量操作接口 → 未来功能
- WebSocket 实时推送 → 参考 `websocket-backend` spec
- 群聊的核心编排逻辑 → 参考 `group-chat-manager` spec
- 认证与授权机制 → 参考未来的 `auth` spec

## Technical Contract

### HTTP API 端点总览

<key_function last_update="2026-06-20T19:01:20+08:00">
- agents_hub/api/routes/group_chat.py
  - group_chat.create_group_chat:30
  - group_chat.list_group_chats:65
  - group_chat.get_group_chat:95
  - group_chat.delete_group_chat:120
  - group_chat.get_group_chat_members:145
  - group_chat.get_group_chat_messages:170
  - group_chat.send_message:200
  - group_chat.update_use_docker:230
</key_function>

| 方法 | 路径 | 说明 | 路由处理函数 |
|------|------|------|-------------|
| POST | `/api/v1/group-chats` | 创建群聊 | create_group_chat |
| GET | `/api/v1/group-chats` | 列出所有群聊 | list_group_chats |
| GET | `/api/v1/group-chats/{group_chat_id}` | 获取群聊详情 | get_group_chat |
| DELETE | `/api/v1/group-chats/{group_chat_id}` | 删除群聊 | delete_group_chat |
| GET | `/api/v1/group-chats/{group_chat_id}/members` | 获取成员列表 | get_group_chat_members |
| GET | `/api/v1/group-chats/{group_chat_id}/messages` | 获取消息历史 | get_group_chat_messages |
| POST | `/api/v1/group-chats/{group_chat_id}/messages` | 发送消息 | send_message |
| PUT | `/api/v1/group-chats/{group_chat_id}/{role_name}/use-docker` | 切换 Docker 开关 | update_use_docker |
| POST | `/api/v1/group-chats/{group_chat_id}/fork` | Fork 群聊 | fork_group_chat |
| GET | `/api/v1/group-chats/projects/summary` | 项目摘要 | get_projects_summary |
| GET | `/api/v1/group-chats/{group_chat_id}/agent-calls` | Agent 调用记录 | get_agent_calls |
| GET | `/api/v1/group-chats/{group_chat_id}/tasks` | 任务列表 | get_tasks |
| GET | `/api/v1/group-chats/{group_chat_id}/pinned-messages` | 获取置顶消息 | get_pinned_messages |
| POST | `/api/v1/group-chats/{group_chat_id}/pinned-messages` | 置顶消息 | pin_message |
| DELETE | `/api/v1/group-chats/{group_chat_id}/pinned-messages` | 取消置顶 | unpin_message |
| POST | `/api/v1/group-chats/{group_chat_id}/members` | 添加成员 | add_members |
| POST | `/api/v1/group-chats/{group_chat_id}/upload` | 文件上传 | upload_file |
| GET | `/api/v1/group-chats/{group_chat_id}/files/{snapshot_id}/content` | 文件快照内容 | get_file_snapshot_content |
| GET | `/api/v1/group-chats/{group_chat_id}/files/{snapshot_id}/diff` | 文件快照 diff | get_file_snapshot_diff |
| GET | `/api/v1/group-chats/{group_chat_id}/files/{file_path:path}` | 获取上传文件 | get_uploaded_file |
| PATCH | `/api/v1/group-chats/{group_chat_id}/messages/{message_id}/permission` | 权限审批 | update_permission |
| POST | `/api/v1/group-chats/{group_chat_id}/members/{agent_name}/compress` | 压缩上下文 | compress_member_context |
| POST | `/api/v1/group-chats/{group_chat_id}/compress-all` | 全量压缩 | compress_all_contexts |
| POST | `/api/v1/group-chats/{group_chat_id}/members/{agent_name}/stop` | 停止成员 | stop_member |
| POST | `/api/v1/group-chats/{group_chat_id}/members/{agent_name}/start` | 启动成员 | start_member |
| POST | `/api/v1/group-chats/{group_chat_id}/members/{agent_name}/reset` | 重置成员 | reset_member |
| GET | `/api/v1/group-chats/{group_chat_id}/members/{agent_name}/history` | 成员历史 | get_member_history |

### Request/Response Schemas

#### 核心请求 Schema

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

#### 核心响应 Schema

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
| status | str | 成员状态（如 "idle", "running", "error"） |
| context_usage | int \| None | 上下文使用量（token 数，如可获取） |
| error_info | dict \| None | 错误信息（如状态为 error 时） |

**MessageCreate**（发送消息请求）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| content | str | 是 | 消息内容（min_length=1） |
| members | list[str] | 是 | 群聊中所有 agent 名称列表（min_length=1） |

**MessageInfo**（消息信息响应）：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 消息唯一标识 |
| speaker | str | 发送者名称（agent 角色名或 "user"） |
| content | str | 消息内容 |
| timestamp | str | 时间戳 |
| platform | str | 来源平台 |
| cwd | str | 消息产生时的工作目录 |
| modified_files | list[str] | 本次消息关联的修改文件列表 |
| git_diff_range | str \| None | Git diff 范围（如存在） |
| permission_request | dict \| None | 权限请求信息（如存在） |
| web_preview | dict \| None | Web 预览信息（如存在） |
| files | list | 关联文件列表 |

**UseDockerUpdate**（Docker 开关请求）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| use_docker | bool | 是 | 是否启用 Docker 沙箱执行 |

#### 扩展 Schema（功能性接口）

**GroupChatForkRequest**（Fork 群聊请求）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| new_project_path | str \| None | 否 | 新项目路径（不填则使用原路径） |
| fork_name | str \| None | 否 | Fork 后的群聊名称 |

**ProjectSummary**（项目摘要响应）：

| 字段 | 类型 | 说明 |
|------|------|------|
| project_path | str | 项目路径 |
| group_chat_count | int | 关联群聊数量 |
| group_chats | list[GroupChatSummary] | 群聊摘要列表 |

**GroupChatListResponse**（群聊列表分页响应）：

| 字段 | 类型 | 说明 |
|------|------|------|
| items | list[GroupChatSummary] | 群聊摘要列表 |
| total | int | 总数 |
| limit | int | 每页数量 |
| offset | int | 偏移量 |

**AddMembersRequest**（添加成员请求）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| members | list[str] | 是 | 要添加的成员角色名列表（min_length=1） |

**AgentCallInfo**（Agent 调用记录响应）：

| 字段 | 类型 | 说明 |
|------|------|------|
| call_id | str | 调用唯一标识 |
| caller | str | 发起方角色名 |
| target | str | 目标角色名 |
| content | str | 调用内容 |
| status | str | 调用状态 |
| created_at | str | 创建时间 |

**TaskInfo**（任务信息）：

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | str | 任务唯一标识 |
| owner | str | 负责人角色名 |
| content | str | 任务内容 |
| status | str | 任务状态 |

**TaskListInfo**（任务列表响应）：

| 字段 | 类型 | 说明 |
|------|------|------|
| tasks | list[TaskInfo] | 任务列表 |

**PinMessageRequest**（置顶消息请求）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message_id | int | 是 | 要置顶的消息 ID |

**PinnedMessageInfo**（置顶消息信息）：

| 字段 | 类型 | 说明 |
|------|------|------|
| message_id | int | 消息 ID |
| speaker | str | 发送者名称 |
| content | str | 消息内容 |
| pinned_at | str | 置顶时间 |

**PinOperationResponse**（置顶操作响应）：

| 字段 | 类型 | 说明 |
|------|------|------|
| success | bool | 操作是否成功 |
| message | str | 操作结果描述 |

**PermissionUpdateRequest**（权限审批请求）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| approved | bool | 是 | 是否批准 |

**PermissionUpdateResponse**（权限审批响应）：

| 字段 | 类型 | 说明 |
|------|------|------|
| success | bool | 操作是否成功 |
| message_id | int | 消息 ID |
| approved | bool | 审批结果 |

**UploadedFileInfo**（上传文件响应）：

| 字段 | 类型 | 说明 |
|------|------|------|
| file_path | str | 文件路径 |
| snapshot_id | str | 快照 ID |
| size | int | 文件大小（字节） |

**MemberHistoryMessage**（成员历史消息）：

| 字段 | 类型 | 说明 |
|------|------|------|
| speaker | str | 发送者名称 |
| content | str | 消息内容 |
| timestamp | str | 时间戳 |

**MemberHistoryResponse**（成员历史响应）：

| 字段 | 类型 | 说明 |
|------|------|------|
| messages | list[MemberHistoryMessage] | 消息历史列表 |

**CompressResponse**（压缩上下文响应）：

| 字段 | 类型 | 说明 |
|------|------|------|
| success | bool | 操作是否成功 |
| message | str | 操作结果描述 |

**CompressAllResponse**（全量压缩响应）：

| 字段 | 类型 | 说明 |
|------|------|------|
| success | bool | 操作是否成功 |
| results | list[CompressResponse] | 各成员压缩结果 |

### 查询参数规则

**GET /api/v1/group-chats**：

| 参数 | 类型 | 默认值 | 约束 |
|------|------|--------|------|
| project_path | str \| None | None | 按项目路径过滤 |
| is_active_only | bool | false | 是否只返回活跃群聊 |
| limit | int | 20 | 返回数量上限 |
| offset | int | 0 | 偏移量 |

响应结构为 `GroupChatListResponse`（含 items、total、limit、offset 分页字段）。

**GET /api/v1/group-chats/{group_chat_id}/messages**：

| 参数 | 类型 | 默认值 | 约束 |
|------|------|--------|------|
| limit | int | 30 | 返回消息数量上限（1-500） |
| before | str \| None | None | 游标时间戳，返回此时间之前的消息 |

**DELETE /api/v1/group-chats/{group_chat_id}**：

| 参数 | 类型 | 默认值 | 约束 |
|------|------|--------|------|
| keep_data | bool | false | true=仅从内存移除，false=完全删除 |

### 业务规则

**群聊生命周期**：
- 创建：验证 team_members 非空且 roles 存在 → 生成唯一 group_chat_id → 初始化并启动 → 注册到全局管理器
- 查询：获取所有群聊元数据 → 可选过滤活跃状态
- 详情：加载群聊（内存优先，磁盘 fallback） → 返回完整信息
- 删除：keep_data=false 完全删除（内存 + 磁盘），keep_data=true 仅从内存移除

**消息交互**：
- 发送消息：验证消息格式和目标角色 → 激活群聊（如未激活） → 路由消息到目标 agent
- 获取历史：游标分页读取消息历史（返回 before 时间戳之前的消息） → 返回消息列表
- @member 解析：从 content 中用正则提取 `@member` 作为 send_to 目标；若无 `@` 标记，则默认发给 default_manager_name

**Docker 沙箱控制**：
- 切换开关：验证角色是群聊成员 → 检查全局 Docker 开关（config.use_docker），若全局禁用则抛 ValidationError → 检查 Docker 环境可用性（开启时） → 更新配置并持久化

**project_path 校验**：
- 必须是绝对路径
- 目录必须存在于文件系统中
- 不满足条件时抛出 ValidationError

### 异常处理规则

所有异常由全局异常处理器统一处理，路由层不捕获异常。

**错误响应格式**（统一）：
```json
{
  "error_code": "ERROR_CODE",
  "message": "人类可读错误信息"
}
```

**HTTP 状态码映射**：

| HTTP 状态码 | 触发场景 | 异常类 |
|-------------|----------|--------|
| 400 | 请求参数格式错误、校验失败 | ValidationError |
| 404 | 群聊、成员、消息不存在 | ResourceNotFoundError, MessageNotFoundError |
| 409 | 群聊状态冲突、Agent 繁忙 | StateError, AgentBusyError |
| 422 | 业务规则违反（如 team_members 为空、平台不支持 fork） | ValidationError, ForkNotSupportedError |
| 500 | 服务器内部错误（启动失败、加载失败） | 未捕获异常 |
| 502 | 外部服务不可用（如 Docker 未运行） | ExternalServiceError |

## Design Rationale

**为什么这样设计？**

1. **Route/Service/Schema 三层架构**：
   - Route 层专注 HTTP 协议处理（路径、参数、状态码）
   - Service 层封装业务逻辑和核心层协调
   - Schema 层使用 Pydantic 提供自动验证和序列化
   - 好处：分离关注点，测试更容易，复用性更高

2. **游标分页而非偏移量分页**：
   - 使用 `before` 时间戳作为游标，而非 `offset`
   - 原因：消息列表实时变化，偏移量分页会导致重复或遗漏
   - 游标分页保证一致性，支持无限滚动

3. **keep_data 模式**：
   - 删除群聊时可选择保留磁盘数据
   - 场景：临时清理内存，但保留历史记录供后续分析
   - 好处：灵活性，避免误删重要数据

4. **异常不在 Route 层捕获**：
   - 所有业务异常由 Service 层抛出，全局异常处理器统一转换
   - 好处：Route 层代码更简洁，异常处理逻辑集中维护

**有哪些约束？**

1. **全局 Docker 开关优先级高于单个 Agent 设置**：
   - 如果 config.use_docker=false，任何 Agent 都不能开启 Docker
   - 原因：全局配置是系统级安全策略，不能被绕过

2. **project_path 必须存在**：
   - 创建群聊时必须验证项目路径存在
   - 原因：避免创建无效群聊，减少后续错误

3. **team_members 不能为空**：
   - 群聊必须至少有一个成员
   - 原因：空群聊没有业务意义

**有哪些已知限制？**

1. **不支持群聊配置修改**：
   - 当前无法动态修改团队成员、群聊名称等
   - 原因：核心层尚未实现相应接口
   - 后续计划：添加 PATCH 端点支持增量修改

2. **消息搜索功能缺失**：
   - 当前只能按时间顺序获取消息历史
   - 原因：未实现索引和搜索引擎集成
   - 后续计划：集成全文搜索

3. **批量操作支持不足**：
   - 每次只能操作单个群聊或发送单条消息
   - 原因：优先实现核心功能，批量操作后续优化
   - 后续计划：添加批量创建、删除、发送接口

**相关 ADR**：
- 无（当前无相关架构决策记录）

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **WebSocket 实时推送**：`docs/specs/websocket-backend.md`（未创建） - 消息实时推送到前端
- **群聊核心编排逻辑**：`docs/specs/group-chat-manager.md`（未创建） - GroupChatManager 的内部实现
- **认证与授权**：未来的 `auth` spec - API 访问控制和权限管理
- **消息持久化**：`docs/specs/message-storage.md`（未创建） - 消息存储和检索机制
