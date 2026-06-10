现在我已经收集了所有 22 个 spec 和对应的代码实现信息。以下是完整的检查报告。

---

## Specs 一致性检查报告

- 检查日期：2026-06-10

---

### 1. agent-bridge (`2026-05-23-agent-bridge.md`)

- **状态**：⚠️ 部分不一致
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| AgentPlatform 枚举 | 仅 CLAUDE、CODEX 两个平台 | 实际有 CLAUDE、CODEX、OPENCODE 三个平台 | 🔴 高 | 更新 spec 加入 OPENCODE |
| AgentEventType 枚举 | INIT、TEXT_DELTA、TOOL_USE、TURN_COMPLETE 四种，且注明"execute() 不使用 RESULT" | 实际有 5 种，包含 RESULT | 🟡 中 | 补充 RESULT 事件类型说明 |
| AgentResult 字段 | text、session_id、timestamp、agent_name、platform、role_type、usage、cwd、modified_files、git_diff_range | 实际额外有 `permission_request`、`web_preview`、`files` 三个字段 | 🔴 高 | 更新 AgentResult 字段表 |
| Usage 数据模型 | spec 未详细定义 Usage 结构 | 实际有 `input_tokens`、`cache_read_input_tokens`、`max_context_window` | 🟡 中 | 补充 Usage 字段定义 |
| execute_stream/execute 签名 | spec 未提及 system_prompt 参数 | 实际两个方法都接受 `system_prompt: str \| None` | 🟡 中 | 更新接口签名 |
| execute 签名 | spec 未提及 use_docker/group_chat_id 参数 | 实际 execute() 接受 `use_docker`、`group_chat_id` | 🟡 中 | 更新接口签名 |
| Executor 协议 | 未包含 fork_from 参数 | 实际 Executor 协议包含 `fork_from: str \| None` | 🟢 低 | 更新协议定义 |
| Docker 集成 | spec 未提及 DockerManager | AgentBridge.__init__ 创建 DockerManager 和 Docker executors | 🟡 中 | 补充 Docker 集成说明 |

---

### 2. roles (`2026-05-24-agents-role.md`)

- **状态**：⚠️ 部分不一致
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| RoleInfo 字段 | name、platform、avatar、abilities、type、description、scope | 实际额外有 `disabled_tools: list[str] \| None` | 🟡 中 | 更新 RoleInfo 字段表 |
| Role.update_avatar | spec 提到更新头像 | 实际还有 `update_disabled_tools()` 方法 | 🟡 中 | 补充方法文档 |
| API 端点 | spec 定义了 CRUD + avatars + skills 共 8 个端点 | 实际额外有 `GET /roles/avatars/files/{filename}`（头像文件服务）和 `GET /roles/tools/catalog`（工具目录） | 🟡 中 | 补充新增端点 |
| RoleUpdateRequest | 仅 avatar、abilities、description | 实际额外有 `enabled_tools: list[str] \| None` | 🟡 中 | 更新 Schema 定义 |
| RoleResponse | spec 未包含 disabled_tools 和 skills | 实际返回包含 `disabled_tools` 和 `skills` 字段 | 🟡 中 | 更新 Response Schema |
| 前缀冲突校验 | 版本说明 1.3 提到新增，但 Core Behavior 未详细描述 | 实际 `_check_name_prefix_conflict()` 方法已实现 | 🟢 低 | 在 Core Behavior 中补充校验规则 |

---

### 3. core-foundation (`2026-05-31-core-foundation.md`)

- **状态**：⚠️ 部分不一致
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| AgentMessage 字段 | call_id、content、send_from、send_to、session_type、message_type | 实际额外有 `timestamp`（datetime）和 `files`（附件列表）字段 | 🔴 高 | 更新 AgentMessage 字段表 |
| render_for_llm 输出 | spec 描述包含 call_id、send_from、send_to、content | 实际还包含 `message_type.value` 和附件信息 `[附件]` | 🟡 中 | 更新渲染输出说明 |
| paths.py 方法 | spec 列出 9 个路径方法 | 实际额外有 `file_snapshots_dir()` 和 `find_project_path_by_group_chat_id()` 方法 | 🟡 中 | 补充路径方法 |
| file_snapshot 模块 | spec 未提及 | 实际存在 `file_snapshot.py`，提供文件快照创建和读取功能 | 🟡 中 | 补充 file_snapshot 模块文档 |
| 异常体系 | spec 列出 8 个异常 | 实际还有 `ValidationError`、`ExternalServiceError`、`DockerConfigError`、`DockerNotAvailableError`、`DockerStartError`、`RecoverableError` 等 | 🟡 中 | 更新异常体系文档 |

---

### 4. core-communication (`2026-05-31-core-communication.md`)

- **状态**：✅ 基本一致
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| TaskManager 接口 | spec 定义了 get_active_task_list、assign_tasks、archive_task_list | 实际接口签名一致 | ✅ | - |
| AgentCallManager 清理策略 | 5 分钟/1 小时/24 小时 | 实际默认值一致（300/3600/86400 秒） | ✅ | - |
| MessageRouter | 纯投递层，不依赖 GroupChatContext | 实际实现一致 | ✅ | - |

---

### 5. core-context (`2026-05-31-core-context.md`)

- **状态**：⚠️ 部分不一致
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| AgentMemberInfo 字段 | main_session、btw_session、context_state、token、cwd、use_docker | 实际额外有 `status`（idle/busy/chatting）和 `context_window`（int）字段 | 🔴 高 | 更新字段表 |
| GroupChatRuntime | spec 未提及此类 | 实际存在 GroupChatRuntime 作为中间层，持有 RuntimeState 和 Repository | 🟡 中 | 更新架构描述 |
| GroupChatRuntimeState | spec 未提及 | 实际存在，管理所有内存状态 | 🟡 中 | 补充文档 |
| GroupMetadata | spec 未提及独立类 | 实际有独立的 GroupMetadata dataclass | 🟢 低 | 补充文档 |
| update_message_field | spec 未提及 | 实际存在，用于更新消息嵌套字段（如 permission_request.status） | 🟡 中 | 补充方法文档 |
| 持久化路径 | spec 列出 4 类文件 | 实际还有 `pins.json`（置顶消息）文件 | 🟡 中 | 更新持久化文件列表 |

---

### 6. core-agent-orchestration (`2026-05-31-core-agent-orchestration.md`)

- **状态**：⚠️ 部分不一致
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| MCP 工具 | spec 列出 6 个工具 | 实际注册了 9 个工具：额外有 `create_group_chat`、`create_agent`、`health_check`；`request_permission` 已实现但未注册 | 🔴 高 | 更新 MCP 工具表 |
| Agent._process_message | spec 描述了 TASK 未闭环提醒机制 | 实际还有 `_parse_output_fields()` 自动解析输出中的 modified_files/git_diff_range/web_preview | 🟡 中 | 补充输出解析说明 |
| Agent.run() | spec 描述基本循环 | 实际还有自动将未闭环的 TASK 结果写入群聊历史的 fallback 逻辑 | 🟡 中 | 补充 fallback 行为说明 |
| Agent 属性 | spec 未提及 | 实际有 `agent_token`、`agent_cwd`、`is_processing`、`main_session_id` 等属性 | 🟡 中 | 补充属性文档 |
| Agent 状态同步 | spec 未提及 | 实际有 `_sync_status()` 方法同步 agent 状态（idle/busy/chatting） | 🟡 中 | 补充状态同步说明 |
| AgentContext.build_user_prompt | spec 未提及此方法 | 实际是构造完整 user prompt 的核心方法 | 🟡 中 | 补充方法文档 |

---

### 7. docker-executor (`2026-06-03-docker-executor.md`)

- **状态**：⚠️ 部分不一致
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| 支持平台 | 仅 Claude 和 Codex | 实际 OpenCode 也有 Docker 支持（DockerOpenCodeExecutor） | 🟡 中 | 补充 OpenCode Docker 支持 |
| CLI 路径 | spec 未列出 OPENCODE_COMMAND | 实际有 OPENCODE_COMMAND 常量 | 🟢 低 | 补充路径常量 |

---

### 8. websocket-backend (`2026-06-03-websocket-backend.md`)

- **状态**：✅ 基本一致
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| WebSocket 端点 | `/ws/group_chat/{group_chat_id}` | 实际一致 | ✅ | - |
| 广播 API | `POST /api/v1/ws/broadcast/{group_chat_id}` | 实际一致 | ✅ | - |
| RefreshSignal | type、group_chat_id、timestamp | 实际一致 | ✅ | - |
| contract_refs | 引用 `agents_hub/api/websocket/exceptions.py` | 实际 WebSocket 异常定义在 `agents_hub/realtime/exceptions.py` 和 `agents_hub/api/websocket/exceptions.py`（两处） | 🟢 低 | 确认异常定义位置 |

---

### 9. group-chat-api (`2026-06-03-group-chat-api.md`)

- **状态**：❌ 严重不一致
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| API 端点数量 | spec 定义 8 个端点 | 实际有约 18 个端点 | 🔴 高 | 全面更新端点表 |
| 缺失端点：agent-calls | 未定义 | `GET /group-chats/{id}/agent-calls` 返回调用记录 | 🔴 高 | 补充端点文档 |
| 缺失端点：tasks | 未定义 | `GET /group-chats/{id}/tasks` 返回任务列表 | 🔴 高 | 补充端点文档 |
| 缺失端点：pinned-messages | 未定义 | GET/POST/DELETE 三个置顶端点 | 🔴 高 | 补充端点文档或引用 pinned-messages spec |
| 缺失端点：permission | 未定义 | `PATCH /messages/{id}/permission` 审批端点 | 🔴 高 | 补充端点文档或引用 permission-request spec |
| 缺失端点：file-snapshots | 未定义 | `GET /files/{snapshot_id}/content` 和 `/diff` | 🟡 中 | 补充端点文档 |
| 缺失端端点：members add | 未定义 | `POST /group-chats/{id}/members` 添加成员 | 🟡 中 | 补充端点文档 |
| 缺失端点：upload | 未定义 | `POST /group-chats/{id}/upload` 文件上传 | 🟡 中 | 补充端点文档 |
| GroupChatMember 字段 | name、main_session、btw_session、cwd、use_docker | 实际额外有 `status`、`context_window` | 🟡 中 | 更新字段表 |
| Pin 操作 | spec 使用 speaker+timestamp | 实际使用 `message_id`（int） | 🔴 高 | 更新 Schema 定义 |

---

### 10. skills-api (`2026-06-03-skills-api.md`)

- **状态**：✅ 基本一致
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| 端点 | GET/GET/DELETE/POST 四个 | 实际一致 | ✅ | - |
| SkillResponse | name、description | 实际一致（无 path 字段，与 spec 一致） | ✅ | - |
| 错误响应 | spec 使用 error_code/message/type 格式 | 实际使用 `{"error": {"code": ..., "message": ...}}` 嵌套格式 | 🟢 低 | 统一错误响应格式描述 |

---

### 11. teams (`2026-06-06-teams.md`)

- **状态**：✅ 一致
- **不一致详情**：无

---

### 12. realtime (`2026-06-06-realtime.md`)

- **状态**：✅ 一致
- **不一致详情**：无

---

### 13. production-deployment (`2026-06-06-production-deployment.md`)

- **状态**：⚠️ 无法完全验证
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| Dockerfile/docker-compose | spec 引用 `docker/Dockerfile` 和 `docker/docker-compose.prod.yml` | 未验证文件是否存在 | 🟡 中 | 确认部署文件存在 |

---

### 14. config (`2026-06-06-config.md`)

- **状态**：⚠️ 部分不一致
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| AgentPlatform 枚举 | 仅 CLAUDE、CODEX | 实际有 CLAUDE、CODEX、OPENCODE | 🔴 高 | 更新枚举定义 |
| CLI 路径 | 仅 CODEX_COMMAND、CLAUDE_COMMAND | 实际还有 OPENCODE_COMMAND | 🟡 中 | 补充路径常量 |
| 配置项 | spec 列出 6 个配置项 | 实际还有 `team_id`（"default"）和 `assistant_token`（"agents-hub-system"） | 🟡 中 | 补充配置项 |
| use_docker 默认值 | spec 说默认 False | 实际默认值为 `True` | 🔴 高 | 修正默认值 |

---

### 15. message-flow-and-persistence (`2026-06-05-message-flow-and-persistence.md`)

- **状态**：✅ 基本一致
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| MessageRouter 职责 | 纯投递层 | 实际一致 | ✅ | - |
| GroupChat.send_message_to_agent | 统一包装投递和保存 | 实际一致 | ✅ | - |
| complete_task 保存规则 | user 调用保存到群聊，agent 调用发 NOTIFICATION | 实际一致 | ✅ | - |

---

### 16. frontend-core (`2026-06-06-frontend-core.md`)

- **状态**：✅ 基本一致
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| WebSocketManager | spec 列出 8 个方法 | 实际还多一个 `emit()` 方法用于本地事件分发 | 🟢 低 | 补充 emit 方法 |
| API 函数分组 | groupChat/role/skill/team 四组 | 实际还有 `singleChatApi` 和 `sseClient` | 🟡 中 | 补充 API 函数分组 |
| Storage | spec 描述 IndexedDB 存储 | 实际一致 | ✅ | - |

---

### 17. agent-prompt-system (`2026-06-06-agent-prompt-system.md`)

- **状态**：✅ 基本一致
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| Runtime 注入 | `<AGENT_RUNTIME>` 标记 | 实际使用 `<runtime>` 标记（在 AgentContext._build_runtime 中） | 🟡 中 | 统一标记名称 |
| pinned_messages 注入 | spec 描述在 `<AGENT_RUNTIME>` 内的 `<pinned_messages>` | 实际在 `_build_runtime` 中生成 `<user_pin_message>` | 🟡 中 | 统一标签名称 |
| ROLE_INSTRUCTIONS | Manager 6 个工具、Worker 2 个工具 | 实际一致 | ✅ | - |
| SHARED_RULES | 群聊消息显示规则 | 实际一致 | ✅ | - |

---

### 18. frontend-features (`2026-06-06-frontend-features.md`)

- **状态**：⚠️ 部分不一致
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| Feature 模块 | spec 列出 chat/session/roles/skills 四个 | 实际有 5 个：额外有 **single-chat** 模块 | 🔴 高 | 补充 single-chat 模块文档 |
| chat store | spec 未提及 pinnedMessagesStore | 实际有独立的 `pinnedMessagesStore` | 🟡 中 | 补充 store 文档 |

---

### 19. pinned-messages (`2026-06-06-pinned-messages.md`)

- **状态**：❌ 严重不一致
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| 消息标识方案 | 使用 `timestamp + speaker` 复合键 | 实际使用 `message_id`（int）作为标识 | 🔴 高 | 重写 Schema 定义 |
| PinMessageRequest | `{ speaker, timestamp }` | 实际为 `{ message_id: int }` | 🔴 高 | 更新请求 Schema |
| PinnedMessageInfo | speaker、content、timestamp、platform、pinned_at | 实际额外有 `message_id: int` 字段 | 🔴 高 | 更新响应 Schema |
| DELETE 请求 | body: `{ speaker, timestamp }` | 实际使用 query 参数 `?message_id=<int>` | 🔴 高 | 更新删除端点文档 |
| API 端点路径 | `/api/v1/group-chats/{id}/pinned-messages` | 实际一致 | ✅ | - |

---

### 20. message-reply-quote (`2026-06-07-message-reply-quote.md`)

- **状态**：✅ 一致
- **不一致详情**：前端纯实现，无后端代码可对比。组件 Props 定义与 spec 一致。

---

### 21. permission-request (`2026-06-08-permission-request.md`)

- **状态**：⚠️ 部分不一致
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| MCP 工具 | spec 定义 `request_permission` 工具 | 实际代码存在但**被注释掉**（`# mcp.tool()(request_permission)`），未注册 | 🔴 高 | 确认是否应启用，更新 spec 状态 |
| 审批端点 | `PATCH /messages/{id}/permission` | 实际一致 | ✅ | - |
| PermissionRequest 组件 | 前端存在 | 实际一致 | ✅ | - |

---

### 22. single-chat (`2026-06-08-single-chat.md`)

- **状态**：⚠️ 部分不一致
- **不一致详情**：

| 位置 | 文档描述 | 实际情况 | 严重程度 | 建议修复 |
|------|---------|---------|---------|---------|
| 发送消息端点 | `POST /single-chats/{id}/messages/stream` | 实际为 `POST /single-chats/messages/stream`（无 `/{id}`），single_chat_id 在请求体中 | 🔴 高 | 修正端点路径 |
| 创建单聊端点 | spec 有独立 `POST /single-chats` | 实际无独立创建端点，创建逻辑合并到 `/messages/stream` | 🔴 高 | 更新端点定义 |
| 缺失端点 | spec 未提及 | 实际有 `GET /single-chats` 和 `GET /single-chats/{id}` 端点 | ✅ | 与 spec 一致 |

---

### 代码中未被 Spec 覆盖的功能

| 功能 | 模块 | 说明 |
|------|------|------|
| OPENCODE 平台支持 | agent_bridge、config、roles | 第三个 AI 平台，spec 仅描述 Claude 和 Codex |
| 文件上传 API | group_chat | `POST /group-chats/{id}/upload` 端点 |
| 文件快照 API | group_chat | `GET /files/{snapshot_id}/content` 和 `/diff` 端点 |
| Config API | api/routes | `GET/PUT /api/v1/config` 端点无对应 spec |
| Files API | api/routes | `GET /api/v1/files/preview` 端点无对应 spec |
| MCP create_group_chat | mcp | 系统级创建群聊工具 |
| MCP create_agent | mcp | 系统级创建角色工具 |
| MCP health_check | mcp | 健康检查工具 |
| single-chat 前端模块 | frontend/features | 独立的 single-chat feature 模块无 spec 覆盖 |
| Toast 组件 | frontend/shared | 通知组件无 spec 覆盖 |
| UploadArea 组件 | frontend/shared | 上传组件无 spec 覆盖 |
| file_snapshot 模块 | core/foundation | 文件快照功能无 spec 覆盖 |
| GroupChatRuntime | core/context | 中间层运行时状态管理类 |

---

### 已过期的 Spec 内容

| Spec | 过期内容 | 说明 |
|------|---------|------|
| agent-bridge | AgentPlatform 仅两个值 | OPENCODE 已加入但 spec 未更新 |
| config | use_docker 默认 False | 实际默认 True |
| pinned-messages | timestamp+speaker 标识方案 | 实际已改为 message_id |
| single-chat | `/single-chats/{id}/messages/stream` 路径 | 实际路径无 `/{id}` |
| permission-request | request_permission MCP 工具已注册 | 实际被注释掉未注册 |
| group-chat-api | 仅 8 个端点 | 实际已扩展到约 18 个 |

---

### 总结

**整体一致性评分：6.5/10**

**主要问题：**

1. **OPENCODE 平台未文档化**：agent-bridge、config、roles 三个 spec 均未覆盖 OPENCODE 平台支持，这是最大的系统性遗漏（影响 3 个 spec）

2. **group-chat-api 严重滞后**：实际端点数量是 spec 定义的 2 倍以上，大量新增功能（pinned-messages、permission、file-snapshots、agent-calls、tasks、upload）未反映在 spec 中

3. **pinned-messages 标识方案已变更**：spec 使用 `timestamp+speaker` 复合键，实际代码使用 `message_id`，这是根本性的设计变更未同步

4. **core-context 架构演进**：GroupChatRuntime/GroupChatRuntimeState 作为新增的中间层未在 spec 中描述

5. **AgentResult 字段扩展**：permission_request、web_preview、files 三个重要字段未在 agent-bridge spec 中记录

**一致性较好的 spec**：teams、realtime、websocket-backend、message-flow-and-persistence、message-reply-quote — 这些 spec 与代码保持了良好的对齐。
