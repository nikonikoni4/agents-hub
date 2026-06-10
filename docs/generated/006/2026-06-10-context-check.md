所有子任务已完成，正在汇总报告。

---

## CONTEXT.md 一致性检查报告

- 检查日期：2026-06-10

### 术语一致性

#### 核心实体

| 术语名 | 状态 | 详情 |
|--------|------|------|
| **Agent** | ⚠️ 不一致 | 属性列表基本一致，但代码中还有 `message_router`、`agent_call_manager`、`task_manager`、`_run`、`_is_processing`、`_consecutive_no_finish_count`、`max_consecutive_no_finish`、`logger` 等未收录属性 |
| **Manager** | ⚠️ 不一致 | 类存在且继承 Agent，但 `role_type = LEADER` 不是类级别声明，而是由运行时 role.json 配置决定。CONTEXT.md 描述为"角色类型为 LEADER"，暗示类级别固定，实际是运行时属性 |
| **Worker** | ⚠️ 不一致 | 同 Manager，`role_type = TEAM_MEMBER` 不是类级别声明 |
| **TeamInfo** | ✅ 一致 | `name`、`members` 属性完全匹配 |
| **GroupChatContext** | ⚠️ 不一致 | `repository`、`group_chat_session`、`agent_member_info` 是 **property**（只读访问器），不是直接实例属性。`agent_member_info`（单数）是 `agent_member_infos`（复数）的向后兼容别名 |
| **GroupChatSession** | ⚠️ 不一致 | 所有列出的属性存在，但代码中还有未收录的 `next_message_id: int` 属性 |
| **GroupChatRuntime** | ✅ 一致 | 位置和实现匹配 |
| **GroupChatRuntimeState** | ⚠️ 不一致 | 所有列出的属性存在，但代码中还有未收录的 `metadata: GroupMetadata | None` 和 `persistence_error: str | None` 属性 |
| **GroupChat** | ✅ 一致 | 位置和构造函数匹配 |
| **GroupChatManager** | ✅ 一致 | 单例模式，位置匹配 |
| **TaskManager** | ✅ 一致 | 位置和核心方法匹配 |

#### 通信系统

| 术语名 | 状态 | 详情 |
|--------|------|------|
| **AgentMessage** | ⚠️ 不一致 | 7 个核心属性全部存在，但代码中还有未收录的 `files: list[dict[str, Any]] | None` 属性 |
| **AgentCall** | ⚠️ 不一致 | 核心属性和生命周期匹配，但代码中还有未收录的 `created_at`、`started_at`、`completed_at`、`has_agent_response`、`timeout_seconds` 属性 |
| **Task** | ❌ 不一致 | CONTEXT.md 中属性名 `creator`，代码中实际为 `created_by`。另有未收录的 `created_at`、`updated_at` 属性 |
| **TaskList** | ⚠️ 不一致 | 状态枚举匹配，但 CONTEXT.md 只提到 `status` 属性，代码中还有 `list_id`、`group_chat_id`、`tasks`、`created_at`、`archived_at` |
| **AgentCallManager** | ⚠️ 不一致 | `_calls` 字典确认，但代码中还有 `_calls_by_receiver` 二级索引、持久化基础设施和后台清理循环 |
| **MessageRouter** | ✅ 一致 | 消息投递和注册机制匹配 |

#### 渲染层

| 术语名 | 状态 | 详情 |
|--------|------|------|
| **render_for_llm** | ✅ 一致 | 存在且签名匹配 |
| **render_for_chat** | ✅ 一致 | 存在且签名匹配 |
| **parse_chat_input** | ✅ 一致 | 存在，解析失败抛 `InvalidMessageError` |
| **wrap_xml** | ✅ 一致 | 存在且签名匹配 |
| **Tag 常量** | ⚠️ 不一致 | 5 个常量全部存在，但 CONTEXT.md 描述为独立常量，实际代码中是 `class Tag` 命名空间内的类属性 |

#### 上下文管理

| 术语名 | 状态 | 详情 |
|--------|------|------|
| **AgentContext** | ✅ 一致 | 增量加载机制匹配 |
| **AgentMemberInfo** | ⚠️ 不一致 | 5 个核心属性存在，但代码中还有未收录的 `use_docker`、`status`、`context_window` 属性 |
| **AgentContextState** | ✅ 一致 | 两个属性完全匹配 |
| **GroupChatRepository** | ⚠️ 不一致 | asyncio.Lock 确认，但 CONTEXT.md 说"使用 asyncio.Lock"（单数），实际代码中有 4 个独立锁分别保护不同资源 |

#### 角色配置体系

| 术语名 | 状态 | 详情 |
|--------|------|------|
| **RoleConfig** | ✅ 一致 | 6 个属性完全匹配 |
| **RoleInfo** | ⚠️ 不一致 | 7 个核心属性存在，但代码中还有未收录的 `disabled_tools: list[str] | None` 属性 |
| **SkillInfo** | ⚠️ 不一致 | `roles/models.py` 中的版本匹配（id/name/description），但 `skills/models.py` 中存在同名但不同结构的类（name/description/path），存在重复定义 |
| **Role** | ✅ 一致 | `role_dir` 属性确认 |
| **RoleManager** | ✅ 一致 | 4 个核心方法全部存在 |

#### agent_bridge 数据模型

| 术语名 | 状态 | 详情 |
|--------|------|------|
| **AgentResult** | ⚠️ 不一致 | 7 个核心属性存在，但 `usage` 类型为 `Usage | None`（typed dataclass）而非 `dict | None`。另有未收录的 `cwd`、`modified_files`、`git_diff_range`、`permission_request`、`web_preview`、`files` 属性 |
| **StreamEvent** | ✅ 一致 | 7 个属性完全匹配 |
| **AgentEventType** | ✅ 一致 | 5 个枚举值完全匹配 |
| **AgentPlatform** | ❌ 不一致 | CONTEXT.md 只列出 `CLAUDE`、`CODEX`，代码中还有 `OPENCODE = "opencode"` |

---

### 代码中未定义的新术语

以下术语在代码中存在但 CONTEXT.md 未收录：

| 术语 | 位置 | 说明 |
|------|------|------|
| `AgentMessage.files` | `core/foundation/message.py` | 文件附件字段 |
| `AgentCall.created_at/started_at/completed_at` | `core/communication/agent_call.py` | 时间戳字段 |
| `AgentCall.has_agent_response` | `core/communication/agent_call.py` | 标记 agent 是否已明确响应 |
| `AgentCall.timeout_seconds` | `core/communication/agent_call.py` | 超时阈值 |
| `GroupChatSession.next_message_id` | `core/context/group_chat_session.py` | 消息 ID 自增计数器 |
| `GroupChatRuntimeState.metadata` | `core/context/group_chat_runtime_state.py` | 群聊元数据 |
| `GroupChatRuntimeState.persistence_error` | `core/context/group_chat_runtime_state.py` | 持久化错误信息 |
| `AgentMemberInfo.use_docker/status/context_window` | `core/context/group_chat_session.py` | Docker/状态/上下文窗口属性 |
| `AgentResult.cwd/modified_files/git_diff_range/permission_request/web_preview/files` | `agent_bridge/models.py` | 执行结果扩展字段 |
| `AgentResult.usage` 类型 `Usage` | `agent_bridge/models.py` | 结构化 usage dataclass |
| `RoleInfo.disabled_tools` | `roles/models.py` | 禁用工具列表 |
| `AgentPlatform.OPENCODE` | `config/types.py` | OpenCode 平台支持 |
| `MessageNotFoundError` | `exceptions.py` | 顶层异常，继承 `ResourceNotFoundError` |
| `TaskList.list_id/group_chat_id/tasks/created_at/archived_at` | `core/communication/task.py` | TaskList 扩展字段 |

---

### 已废弃的术语

CONTEXT.md 中定义但代码中已不再使用或不准确的术语：

| 术语 | 问题 |
|------|------|
| **Task.creator** | CONTEXT.md 使用 `creator`，代码中实际字段名为 `created_by` |

---

### 枚举/异常层次检查

#### 枚举值一致性

| 枚举 | 状态 | 详情 |
|------|------|------|
| SessionType | ✅ 一致 | MAIN, BTW |
| MessageType | ✅ 一致 | TASK, NOTIFICATION |
| CallStatus | ✅ 一致 | PENDING, RUNNING, COMPLETED, FAILED, TIMEOUT |
| RoleType | ✅ 一致 | LEADER, TEAM_MEMBER, SYSTEM |
| GroupChatType | ✅ 一致 | SEQUENCE_EXECUTE, MANAGER_ORCHESTRATE |
| TaskStatus | ✅ 一致 | PENDING, RUNNING, COMPLETED, FAILED |
| TaskListStatus | ✅ 一致 | ACTIVE, ARCHIVED |
| AgentEventType | ✅ 一致 | INIT, TEXT_DELTA, TOOL_USE, TURN_COMPLETE, RESULT |
| AgentPlatform | ❌ 不一致 | 缺少 `OPENCODE = "opencode"` |

#### 异常层次一致性

| 异常类 | 状态 | 详情 |
|--------|------|------|
| 顶层 AgentsHubError | ✅ 一致 | 继承 Exception |
| ValidationError（顶层） | ✅ 一致 | |
| ResourceNotFoundError | ✅ 一致 | |
| StateError | ✅ 一致 | |
| ExternalServiceError（顶层） | ✅ 一致 | |
| RecoverableError | ✅ 一致 | |
| foundation AgentsHubError | ⚠️ 注意 | 实际是顶层 AgentsHubError 的子类，形成二级继承结构，CONTEXT.md 未说明此层级关系 |
| AgentNotFoundError | ✅ 一致 | |
| GroupChatNotFoundError | ✅ 一致 | |
| MessageDeliveryError | ✅ 一致 | |
| AgentExecutionError | ✅ 一致 | |
| AgentTimeoutError | ✅ 一致 | |
| InvalidMessageError | ✅ 一致 | |
| FileSystemError | ✅ 一致 | |
| CompactionError | ✅ 一致 | |
| ValidationError（foundation） | ⚠️ 注意 | 与顶层同名类形成遮蔽关系，CONTEXT.md 未说明 |
| ExternalServiceError（foundation） | ⚠️ 注意 | 同上 |
| DockerConfigError | ✅ 一致 | 继承 foundation ValidationError |
| DockerNotAvailableError | ✅ 一致 | 继承 foundation ExternalServiceError |
| DockerStartError | ✅ 一致 | 继承 foundation ExternalServiceError |
| MessageNotFoundError | ❌ 未收录 | 代码中存在，继承 ResourceNotFoundError，CONTEXT.md 未收录 |

---

### 总结

**一致性评分：72/100**

**主要问题：**

1. **属性遗漏（高频）**：多个核心实体（AgentMessage、AgentCall、AgentMemberInfo、AgentResult、GroupChatRuntimeState 等）在 CONTEXT.md 中只记录了部分属性，代码中实际有更多字段。建议补充。

2. **字段名错误**：`Task.creator` 应为 `Task.created_by`。

3. **枚举值遗漏**：`AgentPlatform.OPENCODE` 未收录。

4. **异常类遗漏**：`MessageNotFoundError` 未收录；foundation 层与顶层的同名类遮蔽关系未说明。

5. **实现细节偏差**：GroupChatContext 的属性实际是 property 而非直接属性；Manager/Worker 的 role_type 是运行时决定而非类级别固定；GroupChatRepository 有 4 个独立锁而非"一个 asyncio.Lock"。

6. **重复定义**：`SkillInfo` 在 `roles/models.py` 和 `skills/models.py` 中存在两个不同版本，CONTEXT.md 只记录了一个。
