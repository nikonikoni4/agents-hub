---
created_at: 2026-06-04
topic: core runtime memory SSOT design hand-off
status: draft
---

# Core Runtime Memory SSOT Design Hand-off

## 背景

本轮讨论围绕 core 重构展开，核心问题是：

1. 当前 `GroupChatContext` 创建并持有 `GroupChatRepository`，但 `GroupChat`、`Agent` 等上层对象又会穿透 `context.repository` 访问 `project_path`、保存 metadata 或 session state。
2. 同一份状态既可能从内存读取，也可能从文件读取，存在内存态和文件态不一致风险。
3. 用户不希望 `GroupChat` 变成超级对象。`GroupChat` 应主要负责群聊生命周期：初始化、创建、加载、激活、销毁。
4. 已达成阶段性共识：core 运行态应采用内存 SSOT，但同步持久化到文件；core 内部使用内部数据模型，core 对外暂定返回稳定结构，但本 hand-off 不固化具体 dict 字段。

## 已明确的设计原则

### 1. 运行态与配置态区别对待

不是所有模块都需要内存 SSOT。

- `GroupChat/core runtime` 是长生命周期运行态对象，包含 Agent 队列、session、token、上下文加载位置、调用状态、任务状态等，适合内存优先。
- `roles`、`skills` 更像配置或资源管理模块，文件系统或配置文件就是权威来源，最多使用读取缓存，不需要套用 GroupChat 的内存 SSOT 模型。

简单规则：

```text
运行态对象：内存优先，同步落盘
配置/资源对象：文件优先，可加缓存
只读索引/列表：可以文件读取或缓存
```

### 2. 内存 SSOT 的含义

推荐模型：

```text
启动/加载时：文件 -> 内存状态
运行期间：读写都以内存状态为准
关键修改后：同步写入文件
重启后：再次从文件恢复内存
```

不推荐把文件定义为运行期 SSOT，因为这会诱导 service 或 manager 在运行期间反复 `repository.load_*`，继续制造“有的地方读文件，有的地方读内存”的边界混乱。

更准确的表达：

```text
内存是运行期 SSOT。
文件是 durable copy / recovery source。
```

### 3. 同步持久化而非低频异步快照

为了减少崩溃丢失窗口，当前阶段不建议低频异步快照。

每个关键 command 应遵循：

```text
1. 修改内存状态
2. 同步保存到对应文件
3. 保存失败时标记 runtime 持久化异常，必要时阻止继续运行或向上抛错
```

注意：不建议把“文件保存失败”简单理解为可完全回滚。Agent 执行、前端广播等外部副作用未必能回滚。更现实的策略是暴露异常、标记 degraded/persistence_error，避免继续扩大不一致。

## 建议的核心对象职责

### GroupChat

定位：群聊生命周期协调器。

职责：

- 创建和组装运行期依赖。
- 执行 `start/load/activate/cleanup`。
- 初始化 Manager 和 Workers。
- 注册 MessageRouter 队列。
- 启动和停止 Agent run tasks。
- 在 cleanup 时协调 Runtime、Context、Router、Managers 的资源释放。

不建议承担：

- 不直接存放大量业务状态。
- 不直接暴露内部状态结构给 api/service。
- 不直接读写 repository 文件细节。

### GroupChatRuntimeState

定位：纯数据对象，core 内部使用，是运行期内存 SSOT。

职责：

- 保存当前群聊运行态所需的数据。
- 可以包含 metadata、group session、agent session state、compact history 等内部模型。
- 作为整体 load/save/checkpoint 的数据来源。

不建议承担：

- 不做 IO。
- 不创建 Agent。
- 不启动/停止任务。
- 不承载复杂业务流程。

概念形态：

```text
GroupChatRuntimeState
  - metadata
  - group_chat_session
  - agent_sessions
  - compact_history
  - runtime flags / persistence status
```

具体字段后续再定，不在本 hand-off 中固化。

### GroupChatRuntime

定位：运行态门面和状态操作入口。

职责：

- 持有 `GroupChatRuntimeState` 和 `GroupChatRepository/Store`。
- 对 core 外部提供统一 query/command 入口。
- 对 core 内部提供状态修改方法。
- 保证所有状态修改后同步持久化。
- 屏蔽 repository 和内部 state 的结构细节。

query：

- 表示只读操作。
- 可供 api、mcp、service 等 core 外部模块调用。
- 返回稳定结构，但本 hand-off 不定义具体 dict 字段。

command：

- 表示任何会改变 core 运行期状态的操作，不只是 group 设置。
- 包括消息追加、session 更新、context load state 更新、agent cwd/docker 设置、token 刷新、task/call 状态修改等。
- command 内部负责修改内存 SSOT，并同步保存。

### GroupChatRepository / Store

定位：持久化适配器。

职责：

- 只负责文件 load/save。
- 负责路径、锁、原子写入等文件层能力。
- 不参与业务判断。
- 不作为运行期查询入口。

重要边界：

```text
运行期间禁止业务层直接 repository.load_* 获取当前状态。
repository.load_* 只用于 Runtime 初始化或明确的只读投影场景。
repository.save_* 只由 Runtime/Context 内部 command 调用，不由 api/service/agent 随意调用。
```

### GroupChatContext / AgentContext

定位：上下文领域逻辑。

职责：

- `GroupChatContext` 负责消息、session、compact 相关领域逻辑。
- `AgentContext` 负责 Agent 增量上下文加载。
- 它们应依赖 `GroupChatRuntimeState` 或 `GroupChatRuntime` 提供的数据和持久化入口。

迁移建议：

- 初期可以让 Agent 继续依赖 `GroupChatContext`，避免一次性大改。
- 后续再把 Agent 实际需要的能力收窄成更小的 `AgentRuntimeView` 或类似接口。

### AgentCallManager / TaskManager

定位：各自领域的运行态管理器。

职责：

- 管理 AgentCall 和 Task 的内存索引/状态机。
- 持久化行为逐步收束到统一 store 或 runtime command。

待决问题：

- 是否把 AgentCall/Task 的状态也纳入同一个 `GroupChatRuntimeState`，还是由各 Manager 自己持有内存态，但通过统一 store 持久化。
- 倾向：短期保留 Manager 自己持有内存态，先统一依赖注入和持久化入口；长期再考虑是否收束到 RuntimeState。

## 建议的依赖注入关系

目标：GroupChat 只组装依赖，不承载状态细节。

```text
GroupChat
  ├── runtime: GroupChatRuntime
  ├── context: GroupChatContext
  ├── message_router: MessageRouter
  ├── agent_call_manager: AgentCallManager
  ├── task_manager: TaskManager
  ├── manager: Manager
  └── workers: dict[str, Worker]
```

```text
GroupChatRuntime
  ├── state: GroupChatRuntimeState
  └── repository/store: GroupChatRepository
```

```text
GroupChatContext
  └── runtime 或 state + 持久化入口
```

```text
Agent
  ├── agent_context
  ├── message_router
  ├── agent_call_manager
  ├── task_manager
  └── context/runtime view
```

推荐创建流程：

```text
GroupChat.__init__
  1. 创建 Repository/Store
  2. 创建空的 RuntimeState 或延迟到 load 时创建
  3. 创建 GroupChatRuntime(repository, state)
  4. 创建 GroupChatContext(runtime 或 state + repository access)
  5. 创建 MessageRouter / AgentCallManager / TaskManager
  6. start/load 时初始化 Agent，并注入所需依赖
```

## 启动和加载流程

```text
GroupChat.start/load
  1. runtime.load()
     - repository 读取文件
     - 构造/填充 GroupChatRuntimeState
  2. GroupChat 初始化 Manager / Workers
  3. Runtime 生成或恢复 token/cwd/session 状态
  4. Runtime 同步持久化必要状态
  5. GroupChat 注册 router、启动 agent tasks
```

## 状态修改规则

所有运行期状态修改必须通过 Runtime 或 Context 的 command 方法。

示例类别：

```text
消息/上下文类
  - add_message
  - compact_history
  - update_context_load_state

Agent 会话/配置类
  - update_agent_session
  - set_agent_cwd
  - set_agent_docker
  - refresh_agent_token

任务/调用类
  - assign_tasks
  - archive_tasks
  - create_agent_call
  - update_agent_call_status

群聊元数据类
  - set_group_name
  - update metadata
```

共同规则：

```text
1. command 是唯一写入口。
2. command 修改 RuntimeState 或对应 manager 内存态。
3. command 负责同步持久化。
4. repository 不暴露给 api/service 作为写入口。
5. 运行期间不允许业务层通过 repository.load_* 刷新局部状态。
```

## Core 对外查询接口的原则

用户已经指出：当前讨论中给出的具体 dict 字段可能有问题，因此本 hand-off 只记录原则，不固定字段。

原则：

- core 内部使用内部领域模型/dataclass。
- core 对外，即 api/mcp/service 等 core 外部模块，不直接返回内部模型。
- core 对外 query 返回稳定结构，初期可以是 dict。
- api 模块再把 core 返回的结构转换成 API schema。
- query 不改变运行态。
- query 不直接读 repository 获取运行期状态；运行中群聊读取 RuntimeState。
- 未加载群聊的列表/历史查询可以另设只读 ReadModel，但必须与运行态写操作隔离。

## 当前不建议做的事

- 不建议把 `GroupChat` 做成状态大仓库。
- 不建议把文件定义为运行期 SSOT。
- 不建议让 api/service 直接依赖 `GroupChatContext.repository`。
- 不建议 core 对外暴露 `AgentMemberInfo`、`GroupChatSession` 等内部模型。
- 不建议第一阶段引入复杂 Event Sourcing/WAL。
- 不建议现在固化具体 query dict 字段，应先把职责和依赖边界定稳。

## 后续可交给下一个 Agent 的任务

1. 基于本 hand-off，整理正式设计草案或更新 core spec。
2. 明确 `GroupChatRuntimeState` 的最小字段集合。
3. 明确 Runtime 与 Context 的边界：哪些 command 放 Runtime，哪些保留在 Context。
4. 盘点当前代码中所有 `context.repository` 穿透访问点，作为后续重构清单。
5. 设计第一阶段迁移计划：先统一持久化入口，再移动 Repository 所有权，再收窄 Agent 依赖。

