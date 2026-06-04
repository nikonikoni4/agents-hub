---
version: 1.1
created_at: 2026-06-04
updated_at: 2026-06-04
last_updated: 移除多方案对比，仅保留 Runtime/State 选定方案
abstract: core runtime 内存 SSOT 重构的 brainstorm 设计稿，聚焦运行态与文件持久化边界、GroupChat 职责收窄、Runtime/State/Repository/Context 的职责划分和依赖注入关系。
id: brainstorm-core-runtime-ssot
title: Core Runtime 内存 SSOT 重构设计
status: draft
module: core
sourc_spec: docs/temp/hand-off/2026-06-04 core-runtime-ssot-design-hand-off.md
related_plan: null
code_scope:
  - agents_hub/core/
contract_refs: []
---

# Core Runtime 内存 SSOT 重构设计

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 brainstorm 设计稿 |
| 1.1 | 移除多方案对比，仅保留 Runtime/State 选定方案 |

## 设计定位

本文是 `superpowers:brainstorming` 生成的 source spec / brainstorm spec，不是正式 `docs/specs/` 规格。

它用于把当前 core 重构讨论沉淀成后续 plan 的输入，重点记录：

1. 内存与文件的一致性原则。
2. `GroupChat`、`GroupChatRuntime`、`GroupChatRuntimeState`、`Repository`、`Context` 的职责边界。
3. core 内部与 core 外部调用者之间的接口边界。
4. 依赖注入方向和第一阶段重构目标。

本文不固化具体函数签名，不固化 query 返回 dict 字段，也不替代正式 core spec。

## 背景问题

当前 core 的主要问题不是单个函数错误，而是运行态状态来源不清晰。

已观察到的现状：

1. `GroupChatContext` 创建并持有 `GroupChatRepository`。
2. `GroupChat`、`Agent`、`AgentContext` 等对象会穿透 `group_chat_context.repository` 访问文件持久化能力或 `project_path`。
3. 同一类状态有时来自内存对象，有时重新从文件读取。
4. API / service 层未来如果继续通过文件读取运行态信息，会扩大不一致风险。

这种结构的风险是：文件和内存都像“权威数据源”，但二者并不能天然保持同步。一旦某个路径只改内存、另一个路径读文件，或者某个路径保存失败但内存继续前进，就会产生难以定位的状态偏差。

## 核心决策

### 决策 1：运行态以内存为 SSOT

core runtime 的运行态采用内存优先：

```text
启动 / 加载：
  file -> repository.load -> runtime state

运行期间：
  read/write runtime state

关键写操作：
  update runtime state -> sync persist file

重启恢复：
  file -> runtime state
```

更准确的定义：

```text
内存是运行期 SSOT。
文件是 durable copy / recovery source。
```

文件不再被视为运行期间的查询权威。运行中的群聊查询应该读内存状态；文件只负责初始化恢复、持久化副本和未加载群聊的历史读取。

### 决策 2：运行态与配置态分开

不是所有模块都要套用内存 SSOT。

推荐划分：

| 类型 | 示例 | 数据来源策略 |
| ---- | ---- | ------------ |
| 长生命周期运行态 | group chat session、agent session、context load state、runtime flags | 内存 SSOT，同步落盘 |
| 配置 / 资源态 | roles、skills | 文件优先，可缓存 |
| 只读列表 / 历史索引 | 未加载群聊列表、历史 metadata | 文件读取或 read model |

`roles` 和 `skills` 没有与运行中对象同等强度的内存状态，它们更像配置或资源模块。它们可以保持文件优先，不需要为了统一而强行进入 `GroupChatRuntimeState`。

### 决策 3：同步持久化优先

当前阶段不引入低频异步快照，也不引入 Event Sourcing / WAL。

每个改变运行态的 command 应遵循：

```text
1. 修改内存状态
2. 同步保存到对应文件
3. 保存失败时抛出错误，或将 runtime 标记为 persistence_error / degraded
```

这里不承诺完整回滚。原因是 Agent 执行、消息广播、外部工具调用等副作用未必可回滚。更现实的目标是：保存失败要被显式暴露，避免系统继续在“内存已前进、文件没跟上”的状态下静默运行。

### 决策 4：GroupChat 不做状态大仓库

`GroupChat` 不应该吸收所有状态，也不应该成为对外查询大对象。

它的定位应收窄为群聊生命周期协调器：

1. 创建和组装运行期依赖。
2. 执行 create / load / start / activate / cleanup。
3. 初始化 Manager 和 Workers。
4. 注册消息队列和启动 Agent run tasks。
5. 在 cleanup 时协调 Runtime、Context、Router、Managers 释放资源。

它不负责：

1. 直接保存大量业务状态。
2. 直接暴露内部 state 给 api / service。
3. 直接读写 repository 文件细节。

## 选定方案：引入 Runtime/State，Repository 归 Runtime 管理

做法：

1. 新增 `GroupChatRuntimeState` 作为 core 内部运行态数据对象。
2. 新增 `GroupChatRuntime` 作为运行态查询和 command 门面。
3. Repository / Store 只负责 load/save，不再作为运行期查询入口。
4. Context 依赖 Runtime 或 State + 持久化入口。
5. GroupChat 只负责组装和生命周期协调。

优点：

1. 内存 SSOT 边界清楚。
2. GroupChat 不会变成超级对象。
3. Repository 从业务层穿透访问中退出。
4. 后续 API / service 可以通过 core 对外 query 获取稳定 dict。
5. 迁移可以分阶段进行。

缺点：

1. 需要新增一层运行态抽象。
2. 需要重新梳理 Context 与 Runtime 的 command 边界。
3. 短期会增加一些转发方法。

## 推荐架构

目标不是增加层数，而是把现在混在一起的三件事拆开：

1. **生命周期**：谁创建、加载、启动、清理群聊。
2. **运行态**：当前状态到底在哪里。
3. **持久化**：状态如何保存到文件、如何恢复。

推荐依赖关系：

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

## 组件职责

### GroupChat

职责：

1. 作为单个群聊的生命周期协调器。
2. 创建 Repository / Runtime / Context / Router / Managers / Agents。
3. 在 start / load 时初始化或恢复运行期组件。
4. 在 cleanup 时协调释放资源。

边界：

1. 不作为状态大仓库。
2. 不直接读写文件。
3. 不向 api / service 暴露内部 state。

### GroupChatRuntimeState

职责：

1. 保存运行期内存 SSOT。
2. 承载 group chat session、agent sessions、compact history、metadata、runtime flags 等内部数据。
3. 作为 Runtime command 修改和 query 读取的内存来源。

边界：

1. 不做 IO。
2. 不创建 Agent。
3. 不启动任务。
4. 不承载复杂业务流程。

说明：

具体字段不在本文固化。后续 plan 中应先定义最小字段集合，避免把所有 manager 状态一次性塞进去。

### GroupChatRuntime

职责：

1. 持有 `GroupChatRuntimeState`。
2. 持有 Repository / Store。
3. 负责运行态 load / checkpoint / close。
4. 提供 core 内部 command 入口。
5. 提供 core 外部 query 入口。
6. 保证 command 修改内存后同步持久化。

边界：

1. 不执行 Agent 业务逻辑。
2. 不取代 Context 的上下文领域逻辑。
3. 不直接返回内部 dataclass 给 core 外部模块。

### GroupChatRepository / Store

职责：

1. 文件 load/save。
2. 路径管理。
3. 文件锁。
4. 原子写入和文件格式兼容。

边界：

1. 不参与业务判断。
2. 不作为运行期查询入口。
3. 不被 api / service / agent 随意持有。

运行期规则：

```text
repository.load_*:
  只用于 Runtime 初始化、恢复或明确的未加载群聊只读查询。

repository.save_*:
  只由 Runtime 或被 Runtime 授权的 command 路径调用。
```

### GroupChatContext

职责：

1. 负责消息、session、compact 相关的上下文领域逻辑。
2. 通过 Runtime / State 读取当前运行态。
3. 通过 Runtime command 或受控持久化入口保存变更。

边界：

1. 不再作为 Repository 的拥有者。
2. 不向外暴露 repository。
3. 不让外部调用者绕过 Runtime 获取当前状态。

### AgentContext

职责：

1. 为单个 Agent 生成增量上下文。
2. 更新该 Agent 的 context load state。

边界：

1. 不直接调用 repository 保存 agent session state。
2. 不自行决定运行态与文件态谁是权威。

### AgentCallManager / TaskManager

职责：

1. 继续管理各自领域的内存索引和状态机。
2. 通过统一 store 或 Runtime command 持久化关键状态。

待决：

1. 短期是否仍由 Manager 自己持有内存态。
2. 长期是否把 AgentCall / Task 状态也纳入 `GroupChatRuntimeState`。

当前倾向：

```text
短期：保留 Manager 自己持有内存态，先统一依赖注入和持久化入口。
长期：根据一致性需要，再决定是否收束到 RuntimeState。
```

## Core 内部与外部接口

这里的“内部”和“外部”按 core 边界划分：

```text
core 内部：
  agents_hub/core/**

core 外部：
  api / mcp / service / frontend-facing backend 等调用 core 的模块
```

### Core 内部

core 内部可以使用内部领域模型和 dataclass。

原因：

1. 内部模型表达力更强。
2. Runtime、Context、Agent 之间需要共享业务语义。
3. 内部模型变更可以由 core 自己控制。

### Core 外部

core 对外 query 返回稳定 dict-like 结构，不直接暴露内部数据模型。

原因：

1. 内部 dataclass 可能随重构变化。
2. api / mcp / service 不应被 core 内部模型绑死。
3. API 模块可以再把 core 返回结构转换成 Pydantic schema。

注意：

本文不定义具体 dict 字段。字段设计需要等 Runtime 最小状态集合和 API 真实需求明确后再定。

## Query 与 Command 原则

### Query

query 表示只读操作：

1. 不改变运行态。
2. 不推进 context load state。
3. 不触发保存。
4. 运行中群聊从 RuntimeState 读取。
5. 未加载群聊可以走只读文件扫描或 read model。

query 的调用者可以是 api / mcp / service。

### Command

command 表示会改变 core 运行态的操作，不限于群聊设置。

可能包括：

1. 追加消息。
2. 更新 agent session。
3. 推进 context load state。
4. 更新 cwd / docker 设置。
5. 刷新 token。
6. 更新 task / agent call 状态。
7. 更新群聊 metadata。

共同规则：

```text
1. command 是运行态唯一写入口。
2. command 修改内存 SSOT。
3. command 同步持久化。
4. repository 不暴露给 api/service 作为写入口。
5. 运行期间业务层不通过 repository.load_* 刷新局部状态。
```

## 启动和加载流程

推荐流程：

```text
GroupChat.start/load
  1. 创建 Repository / Store
  2. 创建 GroupChatRuntime
  3. runtime.load()
     - repository 读取文件
     - 构造 / 填充 GroupChatRuntimeState
  4. 创建 GroupChatContext(runtime)
  5. 创建 MessageRouter / AgentCallManager / TaskManager
  6. 初始化 Manager / Workers
  7. Runtime 生成或恢复 token / cwd / session 状态
  8. Runtime 同步持久化必要状态
  9. GroupChat 注册 router，启动 agent tasks
```

这里的重点是：启动加载时可以读文件，运行期间不把文件作为当前状态查询源。

## 一致性处理

### 正常写入

```text
command received
  -> update runtime state
  -> save durable copy
  -> return success
```

### 保存失败

```text
command received
  -> update runtime state
  -> save durable copy failed
  -> mark persistence_error / degraded
  -> raise error or block risky follow-up operations
```

后续需要明确哪些 command 属于“失败后必须阻止继续运行”的高风险操作。例如 agent session、context load state、message append 可能比纯 metadata 更新更关键。

### 并发写入

Repository 仍可保留文件锁，但业务层不应该依赖文件锁来解决运行态一致性。

运行态一致性优先由 Runtime command 串行化或受控并发策略保证；文件锁只保护文件不损坏。

## 未加载群聊查询

运行中群聊的查询应读 RuntimeState。

未加载群聊的列表、metadata 或历史查询可以读取文件，但必须把它定义成只读 read model，而不是运行态 SSOT。

推荐区分：

```text
active group query:
  GroupChatManager -> GroupChat -> Runtime query -> dict

inactive group query:
  GroupChatCatalog / ReadModel -> repository scan -> dict
```

这样 API / service 层可以统一拿到 dict，但 core 内部知道数据来源不同。

## 第一阶段重构目标

第一阶段不追求一次性把所有状态迁入 RuntimeState。

优先目标：

1. 明确 Repository 不再由 Context 拥有。
2. 新增 Runtime / State 概念。
3. 把 `context.repository` 穿透访问替换为 Runtime / Context 的受控接口。
4. 让 GroupChat 只负责组装和生命周期。
5. 建立“运行中查询读内存，修改走 command，同步保存”的代码路径。

非目标：

1. 不重写所有 Manager 状态机。
2. 不马上引入复杂事务、WAL 或 Event Sourcing。
3. 不立即固化所有 core 对外 query dict 字段。
4. 不把 roles / skills 纳入 GroupChat runtime。

## 当前已知穿透点

当前代码中已观察到的 repository 穿透访问类别：

1. `GroupChat` 读取 metadata、保存 metadata、保存 agent session state。
2. `Agent` 通过 `group_chat_context.repository.project_path` 获取项目路径。
3. `AgentContext` 直接保存 agent session state。
4. `GroupChatContext` 内部大量直接调用 repository load/save。

这些点可以作为后续 implementation plan 的清单来源，但本文不写具体替换代码。

## 待决问题

### 1. Runtime 与 Context 的 command 边界

需要进一步决定：

1. 哪些 command 放在 Runtime。
2. 哪些保留在 Context，但由 Runtime 授权持久化。
3. AgentContext 更新 context load state 时，是调用 Runtime command，还是调用 Context 内部受控方法。

建议方向：

```text
跨领域状态修改放 Runtime。
上下文领域内部流程保留 Context。
所有持久化最终经过 Runtime / Store 边界。
```

### 2. AgentCall / Task 状态是否进入 RuntimeState

短期建议不强行迁入。

原因：

1. AgentCallManager / TaskManager 已有自己的领域状态。
2. 一次性迁入会扩大重构范围。
3. 当前最紧迫问题是 Repository 所有权和运行态 SSOT。

长期可以再评估：如果它们的状态也出现文件/内存混读，就纳入同一套 runtime state 或统一 store 约束。

### 3. Core 对外 query 字段

目前只确定原则：

1. core 内部使用领域模型。
2. core 对外返回稳定 dict。
3. api 模块再转换成 API schema。

具体字段暂不定义，避免把早期讨论中的有问题字段固化。

## 验收标准

后续 plan / implementation 可以用以下标准判断重构是否达到第一阶段目标：

1. `GroupChatContext` 不再创建并拥有 Repository。
2. 运行中的群聊状态查询不通过 repository 重新读取当前状态。
3. API / service 不能直接访问 `context.repository`。
4. Agent / AgentContext 不直接保存 repository 文件。
5. GroupChat 只组装依赖和管理生命周期，不成为状态大仓库。
6. 所有运行态写操作都有明确 command 路径。
7. command 修改内存后同步持久化，保存失败有显式错误或 degraded 标记。
8. roles / skills 保持配置/资源模块定位，不被强行纳入 runtime state。

## 后续步骤

建议后续使用 `superpowers:writing-plans` 基于本文创建 implementation plan。

计划中应重点拆分：

1. 定义 `GroupChatRuntimeState` 的最小字段集合。
2. 定义 `GroupChatRuntime` 的 load/query/command 边界。
3. 调整 Repository 所有权。
4. 替换 `context.repository` 穿透访问。
5. 为内存 SSOT 和同步持久化补充聚焦测试。
