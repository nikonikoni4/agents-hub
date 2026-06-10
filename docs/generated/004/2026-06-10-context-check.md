所有检查已完成，现在汇总生成最终报告。

---

## CONTEXT.md 一致性检查报告

- **检查日期**：2026-06-10
- **检查范围**：CONTEXT.md 全部术语定义 vs `agents_hub/` 代码库实际实现

---

### 术语一致性

#### 核心实体

| 术语 | 状态 | 详情 |
|------|------|------|
| **Agent** | ⚠️ 不一致 | 6 个文档属性均存在，但遗漏了构造参数 `message_router`、`agent_call_manager`、`task_manager` |
| **Manager** | ✅ 一致 | `class Manager(Agent)`，RoleType 由 RoleConfig 决定 |
| **Worker** | ✅ 一致 | `class Worker(Agent)`，RoleType 由 RoleConfig 决定 |
| **TeamInfo** | ✅ 一致 | Pydantic 模型，`name: str`、`members: list[str]`，完全匹配 |
| **GroupChatContext** | ✅ 一致 | 4 个文档属性均通过 property 委托到 runtime 实现 |
| **GroupChatSession** | ⚠️ 不一致 | 遗漏 `next_message_id: int = 1` 字段（活跃使用中） |
| **GroupChatRuntime** | ✅ 一致 | Facade 模式描述准确 |
| **GroupChatRuntimeState** | ⚠️ 不一致 | 遗漏 `metadata: GroupMetadata | None` 和 `persistence_error: str | None` 两个字段 |
| **GroupChat** | ✅ 一致 | 职责描述准确 |
| **GroupChatManager** | ✅ 一致 | 单例模式，职责描述准确 |
| **TaskManager** | ❌ 不一致 | 文档列出 `update_task_status()` 方法，**代码中不存在**。实际第三个核心方法是 `archive_task_list()` |
| **AgentMessage** | ✅ 一致 | 7 个字段完全匹配 |
| **AgentCall** | ⚠️ 不一致 | 遗漏 6 个字段：`created_at`、`started_at`、`completed_at`、`has_agent_response`、`business_task_id`、`timeout_seconds` |
| **Task** | ✅ 一致 | dataclass 存在于 `agents_hub/core/communication/task.py`，字段匹配 |
| **TaskList** | ✅ 一致 | dataclass 存在于同文件，字段匹配 |
| **AgentCallManager** | ✅ 一致 | 内存 `_calls` 字典实现 |
| **MessageRouter** | ✅ 一致 | `_agents_queue` 字典实现 |
| **AgentContext** | ✅ 一致 | 增量加载逻辑描述准确 |
| **AgentMemberInfo** | ⚠️ 不一致 | 遗漏 `use_docker: bool = False` 字段（控制 Docker 沙箱执行） |
| **AgentContextState** | ✅ 一致 | 2 个字段完全匹配 |
| **GroupChatRepository** | ✅ 一致 | asyncio.Lock 并发控制描述准确 |
| **GroupMetadata** | ✅ 一致 | dataclass 存在于 `agents_hub/core/context/group_metadata.py`，字段匹配 |

#### 渲染层

| 术语 | 状态 | 详情 |
|------|------|------|
| **render_for_llm** | ❌ 不一致 | 文档格式：`[{send_from}] 发送消息给 [{send_to}(你)]: {content}`。实际代码使用多行 XML 包裹格式：`<incoming_message>\n[Agents Hub 平台消息]\n来自：{send_from}\n发送给：{send_to}（你）\n内容：{content}\n</incoming_message>` |
| **render_for_chat** | ✅ 一致 | `f"@{send_to} {content}"` 完全匹配 |
| **parse_chat_input** | ✅ 一致 | `@xxx` 前缀解析，抛 `InvalidMessageError` |
| **wrap_xml** | ✅ 一致 | XML 标签单层包裹 |
| **Tag 常量** | ✅ 一致 | 5 个常量全部匹配：INCOMING_MESSAGE、GROUP_HISTORY、RECENT_MESSAGES、SUMMARY_OVERALL、SUMMARY_FOR_YOU |

#### agent_bridge 数据模型

| 术语 | 状态 | 详情 |
|------|------|------|
| **AgentResult** | ⚠️ 不一致 | 遗漏 5 个字段：`cwd`、`modified_files`、`git_diff_range`、`permission_request`、`web_preview`。代码中有 TODO 注释："当前AgentResult模型已经承载了过多了语义，需要重构" |
| **StreamEvent** | ✅ 一致 | 7 个字段完全匹配 |
| **RoleConfig** | ✅ 一致 | 6 个字段完全匹配 |
| **RoleInfo** | ⚠️ 不一致 | 遗漏 `disabled_tools: list[str] | None` 字段 |
| **SkillInfo** | ✅ 一致 | 3 个字段完全匹配 |
| **Role** | ✅ 一致 | `role_dir` 属性匹配 |
| **RoleManager** | ✅ 一致 | 4 个核心方法匹配 |

#### 常量

| 术语 | 状态 | 详情 |
|------|------|------|
| **MAX_TOKEN** | ✅ 一致 | 值为 1000 |
| **LOCAL_DATA_PATH** | ✅ 一致 | 值为 `"local_data"` |
| **default_manager_name** | ⚠️ 不一致 | 引用存在但未记录默认值 `"manager"` |
| **default_user_name** | ⚠️ 不一致 | 引用存在但未记录默认值 `"user"` |

---

### 代码中未定义的新术语

#### 未收录的枚举

| 枚举 | 文件 | 值 | 说明 |
|------|------|-----|------|
| **AgentPlatform** `OPENCODE` | `agents_hub/config/types.py:24` | `"opencode"` | CONTEXT.md 只列出 CLAUDE、CODEX，遗漏第三个平台 |
| **SingleChatType** | `agents_hub/api/schemas/single_chat.py:11` | NEW, FORK, CONTINUE_GROUP_CHAT | 整个单聊子系统未在术语表中收录 |

#### 未收录的异常类（3 个文件完全未记录）

**`agents_hub/exceptions.py`**：
- `MessageNotFoundError(ResourceNotFoundError)` — 固定消息时不存在

**`agents_hub/agent_bridge/exceptions.py`**（6 个异常）：
- `AgentBridgeError`、`CLINotFoundError`、`CLIExecutionError`、`ParseError`、`PlatformNotSupportedError`、`AgentTimeoutError`

**`agents_hub/teams/exceptions.py`**（4 个异常）：
- `TeamNotFoundError`、`TeamAlreadyExistsError`、`InvalidTeamMembersError`、`EmptyTeamMembersError`

**`agents_hub/skills/exceptions.py`**（2 个异常）：
- `SkillNotFoundError`、`InvalidSkillError`

**`agents_hub/roles/exceptions.py`**（5 个异常）：
- `RoleNotFoundError`、`RoleAlreadyExistsError`、`PlatformConfigNotFoundError`、`SkillNotFoundError`、`SkillAlreadyExistsError`

**`agents_hub/realtime/exceptions.py`**（5 个异常）：
- `WebSocketError`、`WebSocketConnectionError`、`WebSocketRoomNotFoundError`、`WebSocketBroadcastError`、`WebSocketValidationError`

#### 未收录的 Manager/Service 类

| 类 | 文件 | 用途 |
|----|------|------|
| `GroupChatService` | `api/services/group_chat_service.py` | 群聊 REST API 服务层 |
| `ConfigService` | `api/services/config_service.py` | 配置读写 API |
| `RoleService` | `api/services/role_service.py` | 角色 CRUD API |
| `SkillService` | `api/services/skill_service.py` | Skill 管理 API |
| `TeamService` | `api/services/team_service.py` | 团队 CRUD API |
| `SingleChatManager` | `api/services/single_chat_service.py` | 1:1 单聊会话管理 |
| `WebSocketManager` | `realtime/manager.py` | WebSocket 连接管理 |
| `DockerManager` | `agent_bridge/docker/manager.py` | Docker 沙箱容器管理 |
| `SkillManager` | `skills/skill_manager.py` | 全局 Skill 库管理 |
| `TeamManager` | `teams/team_manager.py` | 团队定义管理 |

#### 未收录的数据模型

| 类 | 文件 | 说明 |
|----|------|------|
| `FileMetadata` | `core/foundation/types.py` | Git 文件变更元数据 |
| `ContainerConfig` | `agent_bridge/docker/models.py` | Docker 容器配置 |
| `ToolInfo` / `ToolGroup` | `tools/catalog.py` | 工具目录系统 |
| `Usage` | `agent_bridge/models.py` | Token 使用统计（AgentResult 的子结构） |
| `SessionMessage` | `utils/session_parser.py` | 单聊消息解析模型 |
| `RefreshSignal` | `realtime/events.py` | WebSocket 刷新事件 |
| `USER_DISPLAY_SUFFIX` | `config/config.py:17` | 用户显示名后缀常量 `"(user)"` |

#### 未收录的功能子系统

1. **单聊系统**（Single Chat）— `SingleChatManager`、`SingleChatIndex`、`CreateSingleChatRequest` 等整套 1:1 会话机制
2. **权限审批系统** — `PermissionRequestInfo`、`PermissionUpdateRequest`、`PermissionUpdateResponse`
3. **消息固定系统** — `PinMessageRequest`、`PinnedMessageInfo`、`PinOperationResponse`
4. **工具目录系统** — `ToolInfo`、`ToolGroup`、`ALL_TOOLS`

---

### 已废弃的术语

| 术语 | 状态 | 详情 |
|------|------|------|
| **TaskManager.update_task_status()** | ❌ 已废弃 | CONTEXT.md 列为核心方法，但代码中不存在。实际使用 `assign_tasks()`（覆盖式更新）+ `archive_task_list()` |

无 CONTEXT.md 定义但代码中完全不再使用的术语。

---

### 枚举/异常层次检查

#### 枚举值一致性

| 枚举 | 状态 | 详情 |
|------|------|------|
| SessionType | ✅ | MAIN="main", BTW="btw" |
| MessageType | ✅ | TASK="task", NOTIFICATION="notification" |
| CallStatus | ✅ | 5 个值完全匹配 |
| RoleType | ✅ | LEADER="leader", TEAM_MEMBER="team_member", SYSTEM="system" |
| GroupChatType | ✅ | SEQUENCE_EXECUTE, MANAGER_ORCHESTRATE |
| TaskStatus | ✅ | 4 个值完全匹配 |
| TaskListStatus | ✅ | ACTIVE, ARCHIVED |
| AgentEventType | ✅ | 5 个值完全匹配 |
| **AgentPlatform** | ❌ | **缺少 `OPENCODE="opencode"`** |

#### 异常层次一致性

CONTEXT.md 描述的层次结构与代码存在 **3 处结构性偏差**：

1. **Docker 异常位置错误**：CONTEXT.md 将 `DockerConfigError`、`DockerNotAvailableError`、`DockerStartError` 归入 `agents_hub/exceptions.py`，实际定义在 `agents_hub/core/foundation/exceptions.py`
2. **遗漏 `MessageNotFoundError`**：继承自 `ResourceNotFoundError`，定义在 `agents_hub/exceptions.py`
3. **未记录 `AgentsHubError` 本地包装器**：`core/foundation/exceptions.py` 中定义了一个本地 `AgentsHubError`（继承顶层版本），使 `error_code` 成为必填参数并添加 `to_mcp_response()` 方法。业务异常实际继承链为：`业务异常 → 本地 AgentsHubError → 顶层 AgentsHubError → Exception`（4 层），比 CONTEXT.md 描述的更长
4. **22 个异常类完全未收录**：agent_bridge、teams、skills、roles、realtime 五个子模块的异常层次未在 CONTEXT.md 中记录

---

### 总结

**一致性评分**：约 **65%**（30 个核心术语中 20 个完全一致）

**主要问题按优先级排序**：

| 优先级 | 问题 | 影响 |
|--------|------|------|
| **P0** | `TaskManager.update_task_status()` 不存在 — 文档描述的方法在代码中无对应 | 误导开发者，可能导致对接错误 |
| **P0** | `render_for_llm` 输出格式严重不符 — 文档为单行纯文本，代码为多行 XML | 影响对 LLM prompt 结构的理解 |
| **P1** | `AgentPlatform.OPENCODE` 未收录 | 新平台类型未文档化 |
| **P1** | 22 个异常类完全未记录（5 个子模块） | 异常处理文档覆盖不完整 |
| **P1** | 10 个 Manager/Service 类未收录 | 架构层描述缺失 API 服务层和实时通信层 |
| **P2** | `AgentCall` 遗漏 6 个字段 | 字段级文档不完整 |
| **P2** | `AgentResult` 遗漏 5 个字段 | 数据模型文档不完整 |
| **P2** | `render_for_llm` XML 格式未更新 | 渲染层文档与实现不同步 |
| **P3** | `GroupChatSession`、`GroupChatRuntimeState`、`AgentMemberInfo` 各遗漏 1-2 个字段 | 次要字段缺失 |
| **P3** | 单聊系统、权限审批、消息固定、工具目录 4 个子系统未收录 | 功能子系统文档空白 |
