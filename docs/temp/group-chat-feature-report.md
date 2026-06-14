# 群聊功能报告

> 生成日期: 2026-06-14
> 范围: 群聊相关 API 端点 + Core 模块

---

## 一、架构概览

```
API Routes (group_chat.py)
  └─ GroupChatService (业务编排层)
       ├─ GroupChatManager (全局单例注册表)
       │    └─ GroupChat (群聊实例)
       │         ├─ GroupChatRuntime (上下文 Facade)
       │         │    ├─ GroupChatRuntimeState (内存状态)
       │         │    └─ GroupChatRepository (磁盘持久化)
       │         ├─ GroupChatContext (消息历史管理)
       │         ├─ MessageRouter (消息路由)
       │         ├─ AgentCallManager (调用追踪)
       │         ├─ TaskManager (任务协作)
       │         ├─ Manager (管理者 Agent)
       │         └─ Worker (执行者 Agent)
       └─ RoleManager (角色配置)
```

**分层职责**:

| 层级 | 模块 | 职责 |
|------|------|------|
| **API 路由** | `api/routes/group_chat.py` | HTTP 入口，参数接收 + 响应转换 |
| **业务编排** | `api/services/group_chat_service.py` | 参数校验 → 组装领域对象 → 调用核心层 → 转换 Schema |
| **编排核心** | `core/orchestration/group_chat.py` | 群聊实例，管理 Agent 生命周期、消息路由 |
| **管理器** | `core/orchestration/group_chat_manager.py` | 全局单例注册表，管理所有 GroupChat 实例 |
| **运行时** | `core/context/group_chat_runtime.py` | 状态 Facade，统一访问内存 State + 磁盘 Repository |
| **通信层** | `core/communication/` | AgentCallManager（调用追踪）、TaskManager（任务协作） |

---

## 二、API 端点清单

### 2.1 群聊生命周期

| 方法 | 端点 | 功能 | 请求体 | 响应 |
|------|------|------|--------|------|
| `POST` | `/group-chats` | 创建并启动新群聊 | `GroupChatCreate` | `GroupChatInfo` |
| `GET` | `/group-chats` | 列出所有群聊 | `?is_active_only=false` | `list[GroupChatInfo]` |
| `GET` | `/group-chats/{id}` | 获取群聊详情 | - | `GroupChatInfo` |
| `DELETE` | `/group-chats/{id}` | 删除群聊 | `?keep_data=false` | `{"message": str}` |

**GroupChatCreate 字段**: `team_members`(成员列表), `project_path`(项目路径), `group_chat_name`(可选名称)

**GroupChatInfo 字段**: `group_chat_id`, `group_chat_name`, `project_path`, `created_at`, `group_type`(MANAGER_ORCHESTRATE/SEQUENCE_EXECUTE), `is_active`, `last_speaker`, `last_message`, `last_update_time`

### 2.2 消息管理

| 方法 | 端点 | 功能 | 请求体 | 响应 |
|------|------|------|--------|------|
| `POST` | `/group-chats/{id}/messages` | 向群聊发送消息 | `MessageCreate` | `{"message": str}` |
| `GET` | `/group-chats/{id}/messages` | 获取消息历史 | `?limit=30&before=` | `list[MessageInfo]` |

**MessageCreate 字段**: `content`(消息内容), `members`(agent 名称列表), `files`(可选文件列表)

**MessageInfo 字段**: `id`, `speaker`, `content`, `timestamp`, `platform`, `cwd`, `modified_files`, `git_diff_range`, `permission_request`, `web_preview`, `files`

**消息路由规则**:
- 消息中包含 `@member` → 路由到该成员
- 无 `@` → 默认路由到 `manager`

### 2.3 成员管理

| 方法 | 端点 | 功能 | 请求体 | 响应 |
|------|------|------|--------|------|
| `GET` | `/group-chats/{id}/members` | 获取成员列表 | - | `list[GroupChatMember]` |
| `POST` | `/group-chats/{id}/members` | 添加群成员 | `AddMembersRequest` | `list[GroupChatMember]` |
| `PUT` | `/group-chats/{id}/{role}/use-docker` | 切换 Docker 沙箱 | `UseDockerUpdate` | `GroupChatMember` |
| `POST` | `/group-chats/{id}/members/{agent}/stop` | 停止成员 | - | `dict` |
| `POST` | `/group-chats/{id}/members/{agent}/start` | 启动成员 | - | `dict` |
| `POST` | `/group-chats/{id}/members/{agent}/reset` | 重置成员 | - | `dict` |

**GroupChatMember 字段**: `name`, `main_session`, `btw_session`, `cwd`, `use_docker`, `status`(idle/busy/stopped), `context_usage`

**成员状态流转**: `idle` ↔ `busy` → `stopped` → `idle`(重启)

### 2.4 上下文压缩

| 方法 | 端点 | 功能 | 响应 |
|------|------|------|------|
| `POST` | `/group-chats/{id}/members/{agent}/compress` | 压缩单个 Agent 上下文 | `dict`(含 old/new session_id, usage 前后对比) |
| `POST` | `/group-chats/{id}/compress-all` | 全量压缩所有 Agent | `dict`(含每个 Agent 的压缩结果) |

### 2.5 置顶消息

| 方法 | 端点 | 功能 | 请求体 | 响应 |
|------|------|------|--------|------|
| `GET` | `/group-chats/{id}/pinned-messages` | 获取置顶消息列表 | - | `list[PinnedMessageInfo]` |
| `POST` | `/group-chats/{id}/pinned-messages` | 置顶消息 | `PinMessageRequest` | `PinnedMessageInfo` |
| `DELETE` | `/group-chats/{id}/pinned-messages` | 取消置顶 | `?message_id=` | `PinOperationResponse` |

### 2.6 Agent 调用记录 & 任务

| 方法 | 端点 | 功能 | 响应 |
|------|------|------|------|
| `GET` | `/group-chats/{id}/agent-calls` | 获取所有 Agent 调用记录 | `list[AgentCallInfo]` |
| `GET` | `/group-chats/{id}/tasks` | 获取当前 ACTIVE 任务列表 | `TaskListInfo \| None` |

**AgentCallInfo 字段**: `call_id`, `send_from`, `send_to`, `content`, `message_type`(task/notification), `status`(pending/running/completed/failed/timeout), `created_at`, `started_at`, `completed_at`, `error`

**TaskListInfo 字段**: `list_id`, `status`(active/archived), `tasks`[], `created_at`, `archived_at`

### 2.7 权限管理

| 方法 | 端点 | 功能 | 请求体 | 响应 |
|------|------|------|--------|------|
| `PATCH` | `/group-chats/{id}/messages/{msg_id}/permission` | 更新权限请求状态 | `PermissionUpdateRequest` | `PermissionUpdateResponse` |

### 2.8 文件管理

| 方法 | 端点 | 功能 | 响应 |
|------|------|------|------|
| `POST` | `/group-chats/{id}/upload` | 上传文件 | `UploadedFileInfo` |
| `GET` | `/group-chats/{id}/files/{path}` | 获取上传的文件 | `FileResponse` |
| `GET` | `/group-chats/{id}/files/{snapshot_id}/content` | 获取文件快照内容 | `{"content": str}` |
| `GET` | `/group-chats/{id}/files/{snapshot_id}/diff` | 获取文件快照 diff | `{"diff": str}` |

**文件限制**: 最大 50MB，支持图片/PDF/文本/Office/代码/压缩包等 30+ 种 MIME 类型

---

## 三、Core 模块功能详解

### 3.1 GroupChat (`core/orchestration/group_chat.py`)

群聊核心实例，管理 Agent 生命周期和消息路由。

**生命周期方法**:

| 方法 | 功能 | 说明 |
|------|------|------|
| `start()` | 启动群聊 | 首次创建：加载上下文 → 保存元数据 → 初始化 agents → 注册 tokens → 初始化新成员(打招呼) → 启动 run() |
| `load()` | 加载已有群聊 | 只读：加载上下文 → 初始化 agents → 注册 tokens → 初始化新成员，不启动 run() |
| `activate()` | 激活群聊 | 在 load() 后调用，启动所有 agent.run() 任务，已激活时幂等 |
| `stop()` | 停止群聊 | 停止所有 agent 的 run() 任务 |
| `cleanup()` | 清理资源 | 停止 Agent → 等待任务完成 → 停止 AgentCallManager → 清空 MessageRouter → 关闭 Context → 注销 tokens |

**成员操作**:

| 方法 | 功能 |
|------|------|
| `add_member(role_name)` | 增量添加单个成员（热重载安全），包含幂等检查 |
| `stop_member(agent_name)` | 停止成员：更新状态 → 终止 CLI 进程 → 停止 run() → 取消 Task → 清理队列 → 注销路由 |
| `start_member(agent_name)` | 重启已停止成员：验证 stopped 状态 → 重置 _run → 创建新 Task |
| `reset_member(agent_name)` | 重置成员：stop → 清空 session/队列 → 重置 context_usage → 重新初始化(打招呼) → 自动启动 |
| `compress_all()` | 全量压缩所有 Agent 上下文，忙碌的 Agent 被跳过 |
| `compact_history()` | 压缩群聊历史消息，生成摘要 |

**消息投递**:

| 方法 | 功能 |
|------|------|
| `send_message_to_agent(msg)` | 统一消息投递入口：检查 Agent 状态(stopped 阻止) → 路由投递 → 格式化内容 → 保存历史 |
| `_cleanup_agent_queue(agent_name)` | 清空消息队列并闭环所有未完成 AgentCall（标记 FAILED + 通知调用方） |

**Heartbeat 机制**: 每 20 分钟定时唤醒 Manager 检查任务进度，报告自动停止的 worker。

### 3.2 GroupChatManager (`core/orchestration/group_chat_manager.py`)

全局单例注册表，管理所有 GroupChat 实例。

| 方法 | 功能 |
|------|------|
| `register(id, chat)` | 注册 GroupChat 到内存 |
| `unregister(id)` | 注销 GroupChat，调用 cleanup() 释放资源 |
| `load_group_chat(id)` | 获取 GroupChat，优先内存 → 磁盘加载 |
| `activate_group_chat(id)` | 激活 GroupChat（启动 agent.run()） |
| `load_group_chat_from_disk(id)` | 从磁盘加载：扫描 project_path → 读取 metadata → 读取 agent_member → 创建实例 → load() |
| `list_all_group_chats()` | 扫描 teams/*/*/group_metadata.json 列出所有群聊 |
| `register_token(token, agent, id)` | 注册 token（MCP 身份验证），线程安全 |
| `resolve_token(token)` | 解析 token → (agent_name, group_chat_id)，线程安全 |

### 3.3 GroupChatRuntime (`core/context/group_chat_runtime.py`)

群聊上下文 Facade，统一访问 State + Repository。

| 方法 | 功能 |
|------|------|
| `load()` | 从持久化加载所有状态到内存 |
| `get_info_dict(is_active)` | 获取群聊信息字典 |
| `get_member_dicts()` | 获取成员列表 |
| `get_message_dicts(limit, before)` | 获取消息历史 |
| `update_agent_status(name, status)` | 更新 Agent 状态 |
| `set_agent_use_docker(name, use_docker)` | 切换 Docker 沙箱 |
| `set_agent_token_and_default_cwd(name, token)` | 设置 Agent token 和工作目录 |
| `update_message_field(id, field, value)` | 更新消息字段（如权限状态） |
| `wait_for_new_message(timeout)` | 等待新消息（用于 send_message_and_wait） |

### 3.4 AgentCallManager (`core/communication/agent_call_manager.py`)

统一管理所有跨 Agent 的异步调用。

| 方法 | 功能 |
|------|------|
| `create_call(from, to, content, type)` | 创建新调用，生成唯一 call_id |
| `mark_agent_response(call_id, content, success)` | 标记调用完成/失败 |
| `list_all_calls()` | 获取所有调用记录 |
| `get_runtime_calls_for_agent(agent)` | 获取指定 Agent 的 PENDING/RUNNING 调用 |
| `stop_cleanup()` | 停止自动清理定时任务 |

**调用状态流转**: `PENDING` → `RUNNING` → `COMPLETED` / `FAILED` / `TIMEOUT`

### 3.5 TaskManager (`core/communication/task_manager.py`)

任务管理器，实现覆盖式更新语义。

| 方法 | 功能 |
|------|------|
| `get_active_task_list(id)` | 获取当前 ACTIVE 任务列表 |
| `assign_tasks(tasks)` | 覆盖式更新任务（创建/更新/保持不变） |
| `archive_task_list()` | 归档当前 ACTIVE 列表 |

**持久化**: `tasks.jsonl`（每行一个 TaskList JSON）

---

## 四、数据持久化

群聊数据存储在 `{data_path}/teams/{team_id}/{group_chat_id}/` 下：

| 文件 | 内容 |
|------|------|
| `group_metadata.json` | 群聊元数据（名称、类型、项目路径、创建时间） |
| `agent_member.json` | Agent 成员信息（session_id、cwd、use_docker、token、status） |
| `messages.jsonl` | 消息历史（每行一条消息 JSON） |
| `compact_history.jsonl` | 压缩后的消息摘要 |
| `agent_calls.jsonl` | Agent 调用记录 |
| `tasks.jsonl` | 任务列表历史 |
| `pins.json` | 置顶消息 |
| `file_snapshots/` | 文件快照目录 |

---

## 五、关键设计模式

### 5.1 懒加载激活

群聊创建后 Agent 不立即运行。`load()` 只加载状态，`activate()` 才启动 `run()` 任务。发消息时自动触发激活（`send_message_to_agent` 内部调用 `activate()`）。

### 5.2 Token 认证

每个 Agent 分配唯一 token，用于 MCP 工具的身份验证。GroupChatManager 维护 `token → (agent_name, group_chat_id)` 的线程安全索引。

### 5.3 消息路由

MessageRouter 统一管理消息分发。所有 Agent 间消息必须通过 `GroupChat.send_message_to_agent()` 投递，禁止直接操作队列。

### 5.4 AgentCall 闭环

停止 Agent 时，自动将所有 PENDING/RUNNING 的 AgentCall 标记为 FAILED，并向调用方发送 NOTIFICATION 通知。

### 5.5 增量成员添加

`add_member()` 只创建新 Agent，不影响现有 Agent 的运行时状态。内部包含幂等检查和立即持久化。

### 5.6 Heartbeat

每 20 分钟定时向 Manager 发送心跳消息，检查任务进度和 worker 状态。
