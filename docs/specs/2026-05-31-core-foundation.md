---
version: 1.4
created_at: 2026-05-31
updated_at: 2026-06-18
last_updated: 重构 spec 结构，添加 Design Rationale，更新 Technical Contract
abstract: core/foundation 层的正式规格，定义系统共享的基础数据模型、消息格式、渲染契约和异常体系
---

# Core Foundation 层规格

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |
| 1.1 | 新增 TaskStatus/TaskListStatus 枚举、token.py 工具函数 |
| 1.2 | 新增 paths.py 路径集中管理模块 |
| 1.3 | 对齐现有路径集中管理中的 metadata 文件和 session 状态字段 |
| 1.4 | 重构 spec 结构，添加 Design Rationale，更新 Technical Contract |

## Overview

**业务问题**：在多 Agent 协作系统中，不同层级的模块需要共享一套统一的"公共语言"——包括数据结构、枚举、常量、异常体系。如果每个模块自行定义这些基础元素，会导致类型不一致、数据转换复杂、异常处理混乱。

**核心职责**：foundation 层是 core 的最底层，零外部依赖，提供：
1. **统一的数据词汇表**：定义所有跨层传递的枚举类型（会话类型、消息类型、调用状态、群聊类型、任务状态）
2. **消息格式契约**：定义 Agent 间消息的标准数据结构（AgentMessage）
3. **渲染边界契约**：定义消息在三个边界（入口、LLM 出口、UI 出口）的渲染规则
4. **统一异常体系**：提供统一的异常基类和各模块专属异常
5. **系统常量和工具函数**：提供路径管理、Token 生成等基础设施

## Scope

### 范围内

- 基础枚举类型（SessionType、MessageType、CallStatus、GroupChatType、TaskStatus、TaskListStatus）
- Agent 间消息的数据结构定义（AgentMessage）
- 消息渲染的三个边界契约（parse_chat_input、render_for_llm、render_for_chat）
- 异常体系（统一基类 AgentsHubError + 模块专属异常）
- 系统常量（MAX_TOKEN、LOCAL_DATA_PATH）
- 路径集中管理（GroupChatPaths 单例）
- Token 工具函数（generate_token、redact_token）
- XML 标签常量（Tag 类）

### 范围外

- 具体的持久化实现 → 参见 `docs/specs/2026-05-31-core-context.md`（context 层的 GroupChatRepository）
- 消息路由逻辑 → 参见 `docs/specs/2026-05-31-core-communication.md`（communication 层的 MessageRouter）
- Agent 执行逻辑 → 参见 `docs/specs/2026-05-31-core-agent-orchestration.md`（agent 层的 Agent 和 agent_bridge）
- AgentCall 数据模型和生命周期管理 → 参见 `docs/specs/2026-05-31-core-communication.md`（communication 层的 AgentCall）
- GroupChatRuntime / GroupChatRepository 等 context 层内部持有关系 → 参见 `docs/specs/2026-05-31-core-context.md`

## Technical Contract

### 枚举模型

foundation 定义六个核心枚举，构成系统的状态词汇表：

| 枚举 | 用途 | 值域 |
|------|------|------|
| SessionType | 区分群聊会话与单聊会话 | MAIN（群聊）、BTW（单聊） |
| MessageType | 区分是否需要自动回复 | TASK（需要回复）、NOTIFICATION（不需要回复） |
| CallStatus | Agent 调用的生命周期状态 | PENDING → RUNNING → COMPLETED / FAILED / TIMEOUT |
| GroupChatType | 群聊的编排模式 | SEQUENCE_EXECUTE（流水线）、MANAGER_ORCHESTRATE（动态编排） |
| TaskStatus | 任务生命周期状态 | PENDING → RUNNING → COMPLETED / FAILED |
| TaskListStatus | 任务列表状态 | ACTIVE / ARCHIVED |

**状态转换规则**（CallStatus）：
- 一次调用的生命周期：PENDING → RUNNING → 终态（COMPLETED / FAILED / TIMEOUT）
- 终态不可逆：到达 COMPLETED / FAILED / TIMEOUT 后不再变更
- 超时判断基于 elapsed > timeout_seconds，仅对非终态生效

### 消息数据模型（AgentMessage）

Agent 间传递的消息结构，核心字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| call_id | str | 调用链 ID，关联 AgentCall |
| content | str | 原始消息内容，投递时不可变 |
| send_from | str | 发送者名称 |
| send_to | str | 接收者名称 |
| session_type | SessionType | MAIN 或 BTW |
| message_type | MessageType | TASK 或 NOTIFICATION |
| timestamp | datetime | 消息时间戳（默认自动生成） |
| files | list[dict]? | 上传文件列表，每个 dict 对应 UploadedFileInfo 序列化 |

**关键约束**：`content` 在 Agent 之间投递时始终是原始内容，渲染只发生在边界处（见渲染契约）。

### 消息渲染契约

<key_function last_update="2026-06-24T22:26:41+08:00">
- agents_hub/core/foundation/renderer.py
  - renderer.parse_chat_input:100
  - renderer.render_for_llm:49
  - renderer.render_for_chat:69
</key_function>

渲染只发生在三个边界，不在中间环节改写 content：

| 边界 | 函数 | 方向 | 说明 |
|------|------|------|------|
| 入口 | parse_chat_input | 前端 → (send_to, content) | 解析 @xxx 格式，失败抛 InvalidMessageError |
| LLM 出口 | render_for_llm | AgentMessage → LLM prompt | 用 `<incoming_message>` 标签包裹 |
| UI 出口 | render_for_chat | Agent 输出 → 群聊记录 | 非循环消息：`@{send_to} {content}`；循环消息：`[循环-节点{send_from}-第{loop_iteration}轮] @{send_to} {content}` |

**XML 标签常量**（Tag 类）：预定义的 prompt 结构标签，用于 LLM 上下文的结构化输入：

| 常量名 | 值 | 用途 |
|--------|-----|------|
| GROUP_HISTORY | group_chat_history | 历史群聊摘要块 |
| RECENT_MESSAGES | recent_messages | 群聊最新消息块 |
| INCOMING_MESSAGE | incoming_message | 当前传入的消息 |
| SUMMARY_OVERALL | overall_summary | 摘要中的整体内容 |
| SUMMARY_FOR_YOU | summary_for_you | 摘要中针对当前 Agent 的内容 |
| LOOP_NODE_ROLE | LOOP_NODE_ROLE | 循环节点职责描述 |
| LOOP_OUTPUT_SCHEMA | LOOP_OUTPUT_SCHEMA | 循环节点输出格式要求 |
| PREVIOUS_NODE_OUTPUT | PREVIOUS_NODE_OUTPUT | 上一个节点输出 |

### 异常体系

采用**统一基类 + 模块专属异常**的设计：

- `AgentsHubError`：所有异常基类，包含 message、error_code、details，提供 `to_mcp_response()` 转换方法
- 各模块继承基类，定义专属错误码

异常分类：

| 类别 | 异常 | error_code |
|------|------|------------|
| 业务错误 | AgentNotFoundError | AGENT_NOT_FOUND |
| 业务错误 | GroupChatNotFoundError | GROUP_CHAT_NOT_FOUND |
| 业务错误 | MessageDeliveryError | MESSAGE_DELIVERY_FAILED |
| 业务错误 | AgentExecutionError | AGENT_EXECUTION_FAILED |
| 业务错误 | AgentTimeoutError | AGENT_TIMEOUT |
| 验证错误 | InvalidMessageError | INVALID_MESSAGE |
| 系统错误 | FileSystemError | FILE_SYSTEM_ERROR |
| 系统错误 | CompactionError | COMPACTION_FAILED |
| 系统错误 | DockerConfigError | DOCKER_CONFIG_ERROR |
| 系统错误 | DockerNotAvailableError | DOCKER_NOT_AVAILABLE |
| 系统错误 | DockerStartError | DOCKER_START_ERROR |
| 业务错误 | ResourceNotFoundError | RESOURCE_NOT_FOUND |
| 业务错误 | MessageNotFoundError | MESSAGE_NOT_FOUND |
| 系统错误 | StateError | STATE_ERROR |
| 系统错误 | RecoverableError | RECOVERABLE_ERROR |

**MCP 响应契约**：所有 foundation 异常都支持 `to_mcp_response()` 转换，返回格式：

```json
{
  "success": false,
  "error_code": "<ERROR_CODE>",
  "message": "<人类可读错误信息>",
  "details": {}
}
```

### 路径集中管理（GroupChatPaths）

<key_function last_update="2026-06-18T14:23:00+08:00">
- agents_hub/core/foundation/paths.py
  - paths.GroupChatPaths.base_dir:34
  - paths.GroupChatPaths.messages_file:45
  - paths.GroupChatPaths.agent_member_file_path:56
  - paths.GroupChatPaths.compact_history_file:67
  - paths.GroupChatPaths.metadata_file:78
  - paths.GroupChatPaths.agent_calls_log:89
  - paths.GroupChatPaths.agent_calls_data:100
  - paths.GroupChatPaths.tasks_log:111
  - paths.GroupChatPaths.tasks_data:122
</key_function>

`paths.py` 提供群聊相关路径的集中管理，采用单例模式。

**路径方法**：

| 方法 | 路径格式 | 存储内容 |
|------|---------|---------|
| `base_dir()` | `local_data/teams/<project>/<id>/` | 群聊基础目录 |
| `messages_file()` | `local_data/teams/<project>/<id>/<id>.jsonl` | 群聊消息历史 |
| `agent_member_file_path()` | `local_data/teams/<project>/<id>/agent_member.json` | Agent session 状态、上下文加载状态、token、cwd、Docker 开关 |
| `compact_history_file()` | `local_data/teams/<project>/<id>/memory/compact_history.jsonl` | 压缩历史 |
| `metadata_file()` | `local_data/teams/<project>/<id>/group_metadata.json` | 群聊元数据 |
| `agent_calls_log()` | `local_data/teams/<project>/<id>/agent_calls.log` | Agent 调用日志 |
| `agent_calls_data()` | `local_data/teams/<project>/<id>/agent_calls.jsonl` | Agent 调用数据 |
| `tasks_log()` | `local_data/teams/<project>/<id>/tasks.log` | 任务管理日志 |
| `tasks_data()` | `local_data/teams/<project>/<id>/tasks.jsonl` | 任务数据 |

**路径规则**：
- project_path 中的 `/ : \` 转换为 `-`，连续 `-` 合并为单个
- 所有群聊相关文件统一存放在 `local_data/teams/<sanitized_project>/<group_chat_id>/` 下

### Token 工具函数

<key_function last_update="2026-06-18T14:23:00+08:00">
- agents_hub/core/foundation/token.py
  - token.generate_token:12
  - token.redact_token:23
</key_function>

`token.py` 提供 Agent Token 的生成和安全处理（详见 `2026-05-31-mcp-tools-design.md`）：

| 函数 | 说明 |
|------|------|
| `generate_token()` | 生成 `tok_<32位hex>` 格式的唯一 Token |
| `redact_token(text)` | 替换文本中所有 token 为 `[REDACTED]` |

### 系统常量

- `MAX_TOKEN`：压缩阈值，用于判断是否需要压缩群聊历史
- `LOCAL_DATA_PATH`：本地数据存储根路径

### 持久化文件格式定义

| 文件 | 格式 | 说明 |
|------|------|------|
| `<group_chat_id>.jsonl` | JSONL | 群聊消息历史，首行为 meta_data |
| `agent_member.json` | JSON | Agent session 映射、上下文加载状态、token、cwd、Docker 开关 |
| `compact_history.jsonl` | JSONL | 压缩历史，每条包含 summary 和 per-agent 关键信息 |
| `group_metadata.json` | JSON | 群聊元数据，包含群聊 ID、名称、项目路径、创建时间和群聊类型 |

## Design Rationale

**为什么采用零依赖设计？**
- foundation 是所有 core 层的基础，如果它依赖其他层会形成循环依赖
- 零依赖保证 foundation 可以被任意层安全导入
- 降低模块间耦合，提高系统可维护性

**为什么消息渲染只在三个边界发生？**
- 保证消息内容在传递过程中的不可变性，避免中间环节篡改导致调试困难
- 清晰的边界契约让每个层级职责明确：入口负责解析、LLM 出口负责格式化、UI 出口负责展示
- 避免渲染逻辑散落在各个模块，降低维护成本

**为什么采用统一异常体系？**
- 统一的 error_code 和 to_mcp_response() 方法让 API 层可以统一处理所有异常
- 模块专属异常让错误分类清晰，便于定位问题
- 统一的 details 字段支持附加上下文信息，便于调试

**为什么路径管理采用单例模式？**
- 避免重复创建路径管理对象，节省内存
- 保证所有模块使用同一套路径规则，避免路径不一致
- 集中管理路径规则，便于统一修改

**有哪些约束？**
- foundation 层不能依赖其他 core 层（零依赖原则）
- 所有数据结构必须支持序列化（用于持久化和跨进程传递）
- 所有枚举值必须是字符串类型（便于持久化和 API 传递）

**有哪些已知限制？**
- 当前 MAX_TOKEN 阈值为固定值，未来可能需要支持动态配置
- 路径管理只支持群聊相关路径，不支持其他类型的路径
- Token 生成格式固定，未来可能需要支持自定义 Token 格式

**相关 ADR**：
- 暂无（foundation 层是系统基础，暂无重大架构决策）

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **持久化实现**：`docs/specs/2026-05-31-core-context.md` - GroupChatRepository 的读写逻辑
- **消息路由**：`docs/specs/2026-05-31-core-communication.md` - MessageRouter 的路由规则
- **Agent 执行**：`docs/specs/2026-05-31-core-agent-orchestration.md` - Agent 的 run() 循环和 LLM 调用
- **AgentCall 管理**：`docs/specs/2026-05-31-core-communication.md` - AgentCall 的生命周期管理
- **群聊编排**：`docs/specs/2026-05-31-core-agent-orchestration.md` - GroupChat 的编排逻辑
