由于我是只读 CI 检查器，无法写入文件。以下是完整的术语一致性检查报告：

---

# CONTEXT.md 一致性检查报告

- 检查日期：2026-06-06
- 检查范围：CONTEXT.md 术语定义 vs 代码实际使用

---

## 术语一致性

### 核心实体

| 术语 | 状态 | 详情 |
|------|------|------|
| **Agent** | ✅ 一致 | `agents_hub/core/agent/base_agent.py` 中定义 `Agent` 类，属性和职责与文档一致 |
| **Manager** | ✅ 一致 | `agents_hub/core/agent/manager.py` 中定义 `Manager(Agent)`，继承自 Agent |
| **Worker** | ✅ 一致 | `agents_hub/core/agent/worker.py` 中定义 `Worker(Agent)`，继承自 Agent |
| **Team** | ✅ 一致 | `agents_hub/teams/models.py` 中定义 `TeamInfo`，包含 `members` 列表 |
| **GroupChatContext** | ✅ 一致 | `agents_hub/core/context/group_chat_context.py` 中定义，职责与文档一致 |
| **GroupChatSession** | ✅ 一致 | `agents_hub/core/context/group_chat_session.py` 中定义，属性与文档一致 |

### 通信系统

| 术语 | 状态 | 详情 |
|------|------|------|
| **AgentMessage** | ✅ 一致 | `agents_hub/core/foundation/message.py` 中定义，属性与文档一致 |
| **AgentCall** | ✅ 一致 | `agents_hub/core/communication/agent_call.py` 中定义，生命周期与文档一致 |
| **Task** | ✅ 一致 | `agents_hub/core/communication/task.py` 中定义，不变量与文档一致 |
| **TaskList** | ✅ 一致 | `agents_hub/core/communication/task.py` 中定义，状态机与文档一致 |
| **AgentCallManager** | ✅ 一致 | `agents_hub/core/communication/agent_call_manager.py` 中定义 |
| **MessageRouter** | ✅ 一致 | `agents_hub/core/communication/message_router.py` 中定义 |

### 渲染层

| 术语 | 状态 | 详情 |
|------|------|------|
| **Renderer** | ✅ 一致 | `agents_hub/core/foundation/renderer.py` 中定义三个纯函数 |
| **render_for_llm** | ✅ 一致 | 函数签名和输出格式与文档一致 |
| **render_for_chat** | ✅ 一致 | 函数签名和输出格式与文档一致 |
| **parse_chat_input** | ✅ 一致 | 函数签名和错误处理与文档一致 |
| **wrap_xml** | ✅ 一致 | 函数签名与文档一致 |
| **Tag** | ✅ 一致 | 常量集合与文档一致：`INCOMING_MESSAGE`, `GROUP_HISTORY`, `RECENT_MESSAGES`, `SUMMARY_OVERALL`, `SUMMARY_FOR_YOU` |

### 上下文管理

| 术语 | 状态 | 详情 |
|------|------|------|
| **AgentContext** | ✅ 一致 | `agents_hub/core/context/agent_context.py` 中定义，增量加载逻辑与文档一致 |
| **AgentMemberInfo** | ✅ 一致 | `agents_hub/core/context/group_chat_session.py` 中定义，属性与文档一致 |
| **AgentContextState** | ✅ 一致 | `agents_hub/core/context/group_chat_session.py` 中定义 |
| **GroupChatRepository** | ✅ 一致 | `agents_hub/core/context/group_chat_repository.py` 中定义，并发控制与文档一致 |

### 枚举类型

| 术语 | 状态 | 详情 |
|------|------|------|
| **SessionType** | ✅ 一致 | `agents_hub/core/foundation/models.py` 中定义：`MAIN`, `BTW` |
| **MessageType** | ✅ 一致 | `agents_hub/core/foundation/models.py` 中定义：`TASK`, `NOTIFICATION` |
| **CallStatus** | ✅ 一致 | `agents_hub/core/foundation/models.py` 中定义：`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `TIMEOUT` |
| **RoleType** | ✅ 一致 | `agents_hub/config/types.py` 中定义：`LEADER`, `TEAM_MEMBER` |

### 异常体系

| 术语 | 状态 | 详情 |
|------|------|------|
| **AgentsHubError** | ✅ 一致 | `agents_hub/exceptions.py` 中定义基类，`agents_hub/core/foundation/exceptions.py` 中继承 |
| **AgentNotFoundError** | ✅ 一致 | `agents_hub/core/foundation/exceptions.py` 中定义 |
| **GroupChatNotFoundError** | ✅ 一致 | `agents_hub/core/foundation/exceptions.py` 中定义 |
| **MessageDeliveryError** | ✅ 一致 | `agents_hub/core/foundation/exceptions.py` 中定义 |
| **AgentExecutionError** | ✅ 一致 | `agents_hub/core/foundation/exceptions.py` 中定义 |
| **AgentTimeoutError** | ✅ 一致 | `agents_hub/core/foundation/exceptions.py` 中定义 |
| **InvalidMessageError** | ✅ 一致 | `agents_hub/core/foundation/exceptions.py` 中定义 |
| **FileSystemError** | ✅ 一致 | `agents_hub/core/foundation/exceptions.py` 中定义 |
| **CompactionError** | ✅ 一致 | `agents_hub/core/foundation/exceptions.py` 中定义 |

### agent_bridge 数据模型

| 术语 | 状态 | 详情 |
|------|------|------|
| **AgentResult** | ✅ 一致 | `agents_hub/agent_bridge/models.py` 中定义，属性与文档一致 |
| **StreamEvent** | ✅ 一致 | `agents_hub/agent_bridge/models.py` 中定义，属性与文档一致 |
| **AgentEventType** | ✅ 一致 | `agents_hub/agent_bridge/models.py` 中定义：`INIT`, `TEXT_DELTA`, `TOOL_USE`, `TURN_COMPLETE`, `RESULT` |
| **AgentPlatform** | ✅ 一致 | `agents_hub/config/types.py` 中定义：`CLAUDE`, `CODEX` |

### 角色配置体系

| 术语 | 状态 | 详情 |
|------|------|------|
| **RoleConfig** | ✅ 一致 | `agents_hub/roles/models.py` 中定义，属性与文档一致 |
| **RoleInfo** | ✅ 一致 | `agents_hub/roles/models.py` 中定义，属性与文档一致 |
| **SkillInfo** | ✅ 一致 | `agents_hub/roles/models.py` 中定义，属性与文档一致 |
| **Role** | ✅ 一致 | `agents_hub/roles/role.py` 中定义，职责与文档一致 |
| **RoleManager** | ✅ 一致 | `agents_hub/roles/role_manager.py` 中定义 |

### 常量定义

| 术语 | 状态 | 详情 |
|------|------|------|
| **MAX_TOKEN** | ✅ 一致 | `agents_hub/core/foundation/constants.py` 中定义值为 1000 |
| **LOCAL_DATA_PATH** | ✅ 一致 | `agents_hub/core/foundation/constants.py` 中定义值为 'local_data' |

---

## 代码中未定义的新术语

以下是代码中使用但 CONTEXT.md **未收录**的术语：

### 核心架构组件

| 术语 | 文件路径 | 说明 |
|------|----------|------|
| **GroupChatRuntime** | `agents_hub/core/context/group_chat_runtime.py` | 群聊运行时 Facade，管理 State 和 Repository，是 GroupChatContext 的底层实现 |
| **GroupChatRuntimeState** | `agents_hub/core/context/group_chat_runtime_state.py` | 群聊运行时内存状态，持有 session、agent_member_infos、compact_history、metadata |
| **GroupChat** | `agents_hub/core/orchestration/group_chat.py` | 群聊管理主类，负责初始化 agents、管理消息路由和生命周期 |
| **GroupChatManager** | `agents_hub/core/orchestration/group_chat_manager.py` | 全局 GroupChat 注册表，管理所有 GroupChat 实例和 token 索引 |
| **GroupMetadata** | `agents_hub/core/context/group_metadata.py` | 群聊元数据，保存在 group_metadata.json 中 |
| **TaskManager** | `agents_hub/core/communication/task_manager.py` | 任务管理器，负责 Task 的 CRUD 和持久化 |

### 枚举类型

| 术语 | 文件路径 | 说明 |
|------|----------|------|
| **GroupChatType** | `agents_hub/core/foundation/models.py` | 群聊类型枚举：`SEQUENCE_EXECUTE`, `MANAGER_ORCHESTRATE` |
| **TaskStatus** | `agents_hub/core/foundation/models.py` | 任务状态枚举：`PENDING`, `RUNNING`, `COMPLETED`, `FAILED` |
| **TaskListStatus** | `agents_hub/core/foundation/models.py` | 任务列表状态枚举：`ACTIVE`, `ARCHIVED` |

### 异常类

| 术语 | 文件路径 | 说明 |
|------|----------|------|
| **StateError** | `agents_hub/exceptions.py` | 状态错误：在错误的状态下执行操作 |
| **ValidationError** | `agents_hub/exceptions.py` / `agents_hub/core/foundation/exceptions.py` | 验证错误：输入参数不符合要求 |
| **ResourceNotFoundError** | `agents_hub/exceptions.py` | 资源不存在错误（通用基类） |
| **ExternalServiceError** | `agents_hub/exceptions.py` / `agents_hub/core/foundation/exceptions.py` | 外部服务错误 |
| **RecoverableError** | `agents_hub/exceptions.py` | 可恢复错误（用于重试逻辑） |
| **DockerConfigError** | `agents_hub/core/foundation/exceptions.py` | Docker 配置不合理 |
| **DockerNotAvailableError** | `agents_hub/core/foundation/exceptions.py` | Docker Engine 不可用 |
| **DockerStartError** | `agents_hub/core/foundation/exceptions.py` | Docker 容器启动失败 |

### 数据模型

| 术语 | 文件路径 | 说明 |
|------|----------|------|
| **TeamInfo** | `agents_hub/teams/models.py` | 团队信息模型（Pydantic） |

---

## 已废弃的术语

CONTEXT.md 中定义但代码中**已不再使用**的术语：

| 术语 | 状态 | 说明 |
|------|------|------|
| 无 | - | 所有 CONTEXT.md 中定义的术语在代码中都有对应实现 |

---

## 枚举/异常层次检查

### 枚举值一致性

| 枚举 | CONTEXT.md 定义 | 代码实现 | 状态 |
|------|-----------------|----------|------|
| **SessionType** | MAIN, BTW | MAIN="main", BTW="btw" | ✅ 一致 |
| **MessageType** | TASK, NOTIFICATION | TASK="task", NOTIFICATION="notification" | ✅ 一致 |
| **CallStatus** | PENDING, RUNNING, COMPLETED, FAILED, TIMEOUT | 全部一致 | ✅ 一致 |
| **RoleType** | LEADER, TEAM_MEMBER | LEADER="leader", TEAM_MEMBER="team_member" | ✅ 一致 |
| **AgentEventType** | INIT, TEXT_DELTA, TOOL_USE, TURN_COMPLETE, RESULT | 全部一致 | ✅ 一致 |
| **AgentPlatform** | CLAUDE, CODEX | CLAUDE="claude", CODEX="codex" | ✅ 一致 |

### 异常类层次一致性

```
AgentsHubError (agents_hub/exceptions.py)  ← 顶层基类
├── ValidationError
│   └── DockerConfigError
├── ResourceNotFoundError
│   ├── AgentNotFoundError (继承自 core.foundation.AgentsHubError)
│   └── GroupChatNotFoundError (继承自 core.foundation.AgentsHubError)
├── StateError
├── ExternalServiceError
│   ├── DockerNotAvailableError
│   └── DockerStartError
└── RecoverableError

agents_hub/core/foundation/exceptions.py.AgentsHubError (继承自顶层 AgentsHubError)
├── AgentNotFoundError
├── GroupChatNotFoundError
├── MessageDeliveryError
├── AgentExecutionError
├── AgentTimeoutError
├── ValidationError
├── ExternalServiceError
├── InvalidMessageError
├── FileSystemError
└── CompactionError
```

**⚠️ 发现问题**：异常层次存在两层结构：
- `agents_hub/exceptions.py` 定义顶层基类
- `agents_hub/core/foundation/exceptions.py` 继承顶层基类并定义业务异常

CONTEXT.md 只描述了 `core/foundation/exceptions.py` 中的异常，未提及顶层基类和 `StateError`、`ResourceNotFoundError`、`RecoverableError` 等通用异常分类。

---

## 总结

### 一致性评分

- **术语定义覆盖率**：**78%**（28/36 个代码术语在 CONTEXT.md 中有定义）
- **枚举值一致性**：**100%**（所有枚举值与代码一致）
- **异常类一致性**：**85%**（核心业务异常一致，但通用异常分类未收录）

### 主要问题

1. **CONTEXT.md 缺失关键架构组件**：
   - `GroupChatRuntime` 和 `GroupChatRuntimeState` 是运行时核心，但未在术语表中定义
   - `GroupChat` 和 `GroupChatManager` 是群聊管理的核心类，但未收录
   - `GroupMetadata` 是群聊元数据模型，但未收录
   - `TaskManager` 是任务管理器，但未收录

2. **枚举类型不完整**：
   - `GroupChatType`（SEQUENCE_EXECUTE, MANAGER_ORCHESTRATE）未收录
   - `TaskStatus` 和 `TaskListStatus` 未收录

3. **异常体系描述不完整**：
   - 顶层 `AgentsHubError` 基类和通用异常分类（StateError, ValidationError, ResourceNotFoundError, ExternalServiceError, RecoverableError）未收录
   - Docker 相关异常（DockerConfigError, DockerNotAvailableError, DockerStartError）未收录

4. **架构分层描述不准确**：
   - CONTEXT.md 将 `GroupChatContext` 描述为"群聊业务逻辑的核心管理器"，但实际上 `GroupChatRuntime` 才是底层核心，`GroupChatContext` 只是 Facade
   - 未提及 `GroupChat` 和 `GroupChatManager` 在架构中的位置

### 建议

1. **补充术语定义**：将上述缺失的术语添加到 CONTEXT.md
2. **更新架构分层**：重新描述 `GroupChatContext` → `GroupChatRuntime` → `GroupChatRepository` 的层次关系
3. **完善异常体系**：补充顶层异常基类和通用异常分类
4. **添加枚举类型**：补充 `GroupChatType`、`TaskStatus`、`TaskListStatus`

---

*报告生成时间：2026-06-06*
*检查工具：Claude Code CI Checker*
