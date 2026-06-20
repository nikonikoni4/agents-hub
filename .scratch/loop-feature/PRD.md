# PRD: Agent 循环执行功能（Loop）

Status: ready-for-agent

## Problem Statement

当前 agents-hub 只支持单次的 Agent 调用模式：Manager 分派任务给 Worker，Worker 执行后返回结果，流程结束。但在实际场景中，许多任务需要**迭代式执行**：

- **代码审查场景**：Executor 实现代码 → Reviewer 审查 → Executor 根据意见修改 → Reviewer 再审查 → ... 直到通过
- **文档优化场景**：Writer 撰写初稿 → Editor 提出修改意见 → Writer 修订 → Editor 再审查 → ... 直到满意
- **数据处理场景**：Processor 处理数据 → Validator 校验结果 → Processor 修正 → Validator 再校验 → ... 直到符合标准

这些场景需要**多轮反馈循环**，当前架构无法支持。用户不得不：
1. 手动监控每轮执行结果
2. 手动判断是否需要继续
3. 手动发起下一轮调用

这导致大量重复操作，无法实现真正的自动化。

---

## Solution

引入 **Loop（循环）** 机制，支持 Agent 之间的自动化迭代执行：

- Manager 定义循环规则：参与的节点、输出格式要求、退出条件、最大循环次数
- 系统自动执行循环：节点 A → 节点 B → 节点 A → ... 直到满足退出条件
- 循环期间隔离：参与的 Agent 进入 `IN_LOOP` 状态，不接收外部任务，专注循环内工作
- 自动校验：每个节点的输出必须符合预定义的格式要求，不符合自动重试
- 明确退出：通过结束节点（TERMINATOR）输出 `<loop_decision>` 标签明确表示是否继续循环
- 全程可追踪：所有循环消息保存到群聊历史，带有循环标记，用户可见完整过程

---

## User Stories

### 循环创建与管理

1. 作为 Manager，我想创建一个执行者-审查者循环，以便自动化代码审查流程
2. 作为 Manager，我想定义每个节点的职责描述（输入、输出、职责），以便节点知道自己该做什么
3. 作为 Manager，我想指定每个节点的输出格式要求（必需字段），以便确保节点输出可被下游解析
4. 作为 Manager，我想设置最大循环次数（如 10 次），以便避免死循环
5. 作为 Manager，我想指定哪个节点负责判断循环是否结束（TERMINATOR 节点），以便明确退出逻辑
6. 作为 Manager，我想在创建循环后先审核再启动，以便确认循环定义正确
7. 作为 Manager，我想查询循环的当前状态（第几轮、当前节点、是否出错），以便监控进度
8. 作为 Manager，我想随时停止循环，以便在发现问题时及时中断
9. 作为 Manager，我想删除已完成或已停止的循环，以便清理历史记录

### 循环执行

10. 作为 Executor，当我在循环中接收任务时，我只想看到循环相关的上下文（职责、上一节点输出、格式要求），而不是整个群聊历史，以便专注当前任务
11. 作为 Executor，我想按照预定义的输出格式输出结果，以便下游节点能正确解析
12. 作为 Executor，当我的输出格式不符合要求时，我想收到明确的错误提示并重试，以便修正输出
13. 作为 Reviewer，当我审查完成后，我想通过 `<loop_decision>` 标签明确表示"通过"或"需修改"，以便系统知道是否继续循环
14. 作为 Reviewer，如果我判断需要继续循环，我想在标签中写明原因，以便 Executor 知道需要改进什么
15. 作为 TERMINATOR 节点，我的输出必须同时包含业务字段（审查意见）和退出决策标签，以便既给出反馈又控制流程

### 循环隔离

16. 作为循环中的 Agent，我不想接收来自群聊的其他任务，以便专注循环内工作
17. 作为循环外的 User，当我 @ 一个正在循环中的 Agent 时，我想收到明确提示"该 Agent 正在循环中，无法接受任务"，以便我知道为什么没有响应
18. 作为循环中的 Agent，我仍然想接收 Manager 的控制信号（停止循环），以便循环可以被中断
19. 作为循环中的 Agent，当循环结束后，我想自动恢复 IDLE 状态，以便继续接收普通任务

### 消息与可见性

20. 作为 User，我想在群聊历史中看到所有循环消息，以便了解循环的完整过程
21. 作为 User，我想看到循环消息的特殊标记（如 `[循环-节点executor-第3轮]`），以便区分循环消息和普通消息
22. 作为 User，我想看到每轮循环的输出内容（包括 `<loop_decision>` 标签），以便理解循环的决策过程
23. 作为 User，我想查询循环的执行历史（共几轮、每轮的结果），以便复盘循环过程

### 错误处理

24. 作为 LoopExecutor，当节点输出格式错误时，我想自动返回错误信息并重试（最多 3 次），以便节点有机会修正
25. 作为 LoopExecutor，当节点重试 3 次仍然失败时，我想标记循环为 FAILED 并记录错误信息，以便 Manager 知道出了问题
26. 作为 LoopExecutor，当达到最大循环次数时，我想标记循环为 FAILED 并记录"达到最大循环次数"，以便 Manager 知道任务未完成
27. 作为 LoopExecutor，当循环执行过程中发生异常时，我想立即停止循环并恢复 Agent 状态，以便避免资源泄漏
28. 作为 Manager，当循环失败时，我想看到明确的失败原因，以便决定是否重新启动循环

### 约束与校验

29. 作为系统，我要确保一个群聊同时只能有一个 RUNNING 状态的循环，以便避免资源竞争
30. 作为系统，当 Manager 尝试创建循环时，如果已有循环存在，我要返回错误并提示先删除旧循环，以便 Manager 明确处理
31. 作为系统，我要确保一个循环有且仅有一个 TERMINATOR 节点，以便退出逻辑明确
32. 作为系统，我要确保循环中的所有 Agent 都存在（通过 RoleManager 验证），以便避免运行时错误
33. 作为系统，我要确保循环中的 Agent 不在其他 RUNNING 的循环中，以便避免冲突

---

## Implementation Decisions

### 架构与分层

- **新增模块**：`agents_hub/core/orchestration/loop_executor.py` 和 `loop_manager.py`
  - `LoopExecutor`：循环执行引擎，负责节点调度、输出校验、退出判断、错误处理
  - `LoopManager`：循环 CRUD 和持久化管理
- **层级定位**：Loop 属于 orchestration 层，位于 GroupChat 之上，复用 GroupChat 的能力（send_message_to_agent、AgentCallManager）
- **依赖注入**：LoopExecutor 不持有 GroupChat 引用，而是通过回调函数（`send_message_callback`）和组件引用（`agent_call_manager`、`completion_queue`）解耦

### 数据模型

**LoopNodeType 枚举**：
```python
class LoopNodeType(str, Enum):
    NORMAL = "normal"           # 普通节点：执行任务
    TERMINATOR = "terminator"   # 结束节点：判断循环是否继续
```

**LoopNode**：
- `node_id`：节点唯一标识
- `node_type`：节点类型（NORMAL / TERMINATOR）
- `agent_name`：执行该节点的 Agent 名称
- `node_prompt`：节点职责描述（Manager 定义，包含角色、输入、输出、职责）
- `output_schema_prompt`：输出格式提示词（给 LLM 看的 Markdown 格式要求）
- `output_schema_fields`：必需字段列表（如 `["# 执行结果", "**任务状态**"]`，用于校验）
- `max_retries`：输出校验失败的最大重试次数（默认 3）

**Loop**：
- `loop_id`：循环唯一标识
- `group_chat_id`：所属群聊
- `nodes`：节点列表（至少 2 个，有且仅有 1 个 TERMINATOR）
- `status`：循环状态（CREATED / RUNNING / PAUSED / COMPLETED / FAILED）
- `current_iteration`：当前循环轮次
- `max_iterations`：最大循环次数
- `initial_task`：初始任务描述（发送给第一个节点）
- `created_at`：创建时间
- `error_message`：错误信息（FAILED 时记录）

**LoopStatus 枚举**：
```python
class LoopStatus(str, Enum):
    CREATED = "created"       # 已创建，未启动
    RUNNING = "running"       # 运行中
    PAUSED = "paused"         # 已暂停
    COMPLETED = "completed"   # 正常完成
    FAILED = "failed"         # 失败（超时/出错/达到最大次数）
```

### 消息通信机制

**复用现有消息路由**：
- 循环消息通过 `GroupChat.send_message_to_agent()` 发送
- 消息类型使用 `MessageType.NOTIFICATION`（自动保存到群聊历史，不需要 `complete_task` 闭环）
- 消息 metadata 携带循环标识：
  - `loop_id`：循环 ID
  - `loop_context`：循环专用上下文（替代群聊历史）
  - `is_loop_message`：标记为循环消息
  - `loop_iteration`：当前循环轮次

**事件驱动的节点完成通知**：
- LoopExecutor 创建 `completion_queue`（asyncio.Queue）
- Loop 启动时，将队列引用注入到参与的 Agent（`agent.set_loop_completion_queue(queue)`）
- Agent 处理完 NOTIFICATION 消息后，检查是否有 `loop_id`，如果有则向队列发送完成通知
- LoopExecutor 监听队列，收到通知后继续下一个节点

### 循环隔离机制

**Agent 状态扩展**：
- 新增 `AgentStatus.IN_LOOP` 状态
- `AgentMemberInfo` 新增字段：`current_loop_id`（当前所在循环 ID）

**白名单消息过滤**：
- Agent.run() 在处理消息前检查 `_should_accept_message(msg)`
- IN_LOOP 状态下，只接收：
  - 来自同一循环的消息（`msg.metadata.get("loop_id") == self.current_loop_id`）
  - 来自 Manager 的控制信号（`msg.send_from == config.default_manager_name`）
- 拒绝的消息记录 WARNING 日志，不处理

### 循环专用上下文

**完全隔离群聊历史**：
- 循环消息的 `loop_context` 只包含：
  1. 节点职责描述（`<LOOP_NODE_ROLE>`）
  2. 输出格式要求（`<LOOP_OUTPUT_SCHEMA>`）
  3. 上一个节点的输出（`<PREVIOUS_NODE_OUTPUT>`）
  4. TERMINATOR 节点额外附加：退出判断提示（`<LOOP_TERMINATION_CHECK>`）
- Agent.run() 检查 `msg.metadata.get("loop_context")`，如果存在则使用它，否则使用 `agent_context.get_context()`

**TERMINATOR 节点的退出判断提示**：
```xml
<LOOP_TERMINATION_CHECK>
你必须在输出末尾包含以下 XML 标签，明确表示循环是否继续：

<loop_decision>
  <should_continue>true</should_continue>
  <reason>继续/结束的原因</reason>
</loop_decision>

如果缺少此标签，系统会要求你重新输出。
</LOOP_TERMINATION_CHECK>
```

### 输出校验与重试

**校验逻辑**：
- 普通节点：检查 `output_schema_fields` 中的所有字段是否存在（简单字符串匹配 `field in output`）
- TERMINATOR 节点：先校验业务字段，再校验 `<loop_decision>` 标签，再解析 `<should_continue>` 的值

**重试机制**：
- 校验失败时，构造错误提示消息（列出缺失字段）发送回该节点
- 节点重新输出，最多重试 `max_retries` 次（默认 3）
- 超过重试次数，标记循环为 FAILED

### 消息渲染

**修改 `render_for_chat()` 函数**：
- 新增参数：`is_loop_message: bool`、`loop_iteration: int | None`
- 循环消息格式：`[循环-节点{send_from}-第{iteration}轮] @{send_to} {content}`
- 普通消息格式：`@{send_to} {content}`

**调用位置**：
- Agent.run() 第 944 行，保存 NOTIFICATION 消息到群聊历史时
- 从 `msg.metadata` 提取 `is_loop_message` 和 `loop_iteration` 传递给 `render_for_chat()`

### MCP 工具接口

**create_loop(agent_token, nodes, max_iterations, initial_task)**：
- 权限：只有 Manager（LEADER 角色）可调用
- 校验：至少 2 个节点、有且仅有 1 个 TERMINATOR、所有 agent_name 存在、该群聊无 RUNNING 循环
- 返回：`{"loop_id": "...", "status": "CREATED"}`

**start_loop(agent_token, loop_id)**：
- 权限：只有 Manager 可调用
- 操作：设置参与 Agent 为 IN_LOOP 状态、注入 completion_queue、创建 LoopExecutor、发送初始任务
- 返回：`{"loop_id": "...", "status": "RUNNING"}`

**stop_loop(agent_token, loop_id)**：
- 权限：只有 Manager 可调用
- 操作：停止参与 Agent 的 CLI（`stop_member` + `start_member`）、设置 Loop 状态为 PAUSED、清理队列引用
- 返回：`{"loop_id": "...", "status": "PAUSED"}`

**delete_loop(agent_token, loop_id)**：
- 权限：只有 Manager 可调用
- 约束：只能删除非 RUNNING 状态的循环
- 操作：从 LoopManager 删除循环记录
- 返回：`{"success": true}`

**get_loop_status(agent_token, loop_id)**：
- 权限：任意 Agent 可调用
- 返回：`{"loop_id": "...", "status": "...", "current_iteration": 3, "max_iterations": 10, "current_node": "reviewer", "error": null}`

### 持久化

**Loop 持久化**：
- 文件路径：`local_data/teams/<team_name>/<project_path>/<group_chat_id>/loops.jsonl`
- 格式：append-only JSONL，每次状态变更追加一条记录
- 容错：同一 `loop_id` 取最新记录

**Loop 状态变更触发持久化**：
- 创建循环（CREATED）
- 启动循环（RUNNING）
- 每轮循环开始（`current_iteration` 增加）
- 循环结束（COMPLETED / FAILED / PAUSED）

### 错误处理与清理

**异常自动停止**：
- LoopExecutor.run() 用 try-except 包裹，捕获任何异常
- 异常发生时调用 `_emergency_stop(error)`：设置状态为 FAILED、记录错误、清理资源

**清理流程**（`_cleanup()`）：
1. 恢复 Agent 状态（IN_LOOP → IDLE，清除 `current_loop_id`）
2. 清除 completion_queue 引用（`agent.set_loop_completion_queue(None)`）
3. 持久化 Loop 最终状态

---

## Testing Decisions

### 测试原则

- **只测试外部行为**：测试 LoopExecutor 的输入（Loop 定义）和输出（循环完成、消息记录、Agent 状态变化），不测试内部实现细节
- **使用真实组件**：使用真实的 MessageRouter、AgentCallManager，mock Agent 的 LLM 调用（agent_bridge）
- **覆盖核心场景**：正常完成、校验失败重试、达到最大次数、异常停止

### 测试模块

**LoopExecutor 测试**（`tests/core/orchestration/test_loop_executor.py`）：
- 测试正常循环完成（Executor → Reviewer → Executor → ... → 通过）
- 测试输出校验失败自动重试（缺少必需字段，重试 3 次后失败）
- 测试 TERMINATOR 节点退出判断（`<should_continue>false` 时循环结束）
- 测试达到最大循环次数（状态 FAILED，error_message 正确）
- 测试异常自动停止（模拟 Agent 执行异常，循环标记为 FAILED，Agent 状态恢复）

**LoopManager 测试**（`tests/core/orchestration/test_loop_manager.py`）：
- 测试创建循环校验（至少 2 个节点、有且仅有 1 个 TERMINATOR、agent_name 存在）
- 测试一个群聊只能有一个 RUNNING 循环的约束
- 测试 Loop 持久化和恢复（创建 → 持久化 → 读取 → 数据一致）

**Agent 白名单测试**（`tests/core/agent/test_agent_loop_isolation.py`）：
- 测试 IN_LOOP 状态下拒绝外部消息（记录 WARNING，不处理）
- 测试 IN_LOOP 状态下接收循环内消息（正常处理）
- 测试 IN_LOOP 状态下接收 Manager 控制信号（正常处理）

**消息渲染测试**（`tests/core/foundation/test_renderer.py`）：
- 测试 `render_for_chat()` 循环消息格式（`[循环-节点executor-第3轮] @reviewer ...`）
- 测试普通消息格式不变（`@reviewer ...`）

### 测试的先例

参考现有测试：
- `tests/core/communication/test_agent_call_manager.py`：测试调用管理器
- `tests/core/orchestration/test_group_chat.py`：测试群聊生命周期
- `tests/core/agent/test_base_agent.py`：测试 Agent 消息处理

---

## Out of Scope

### MVP 不包含的功能

1. **Manager 判断模式**：循环中间插入 Manager 判断点、分支逻辑（Phase 2）
2. **前端控制台工具**：前端专门的循环创建/管理 UI（MVP 通过 Manager 自然语言创建）
3. **审核/权限控制**：Loop 创建需要 User 审核、权限分级（MVP 默认 Manager 可创建）
4. **Hook 机制**：Before/After Agent Call Hook（避免与未来冲突，先不实现）
5. **嵌套循环**：Loop 中嵌套子 Loop
6. **并行节点**：某些节点可以并行执行
7. **循环执行历史可视化**：前端专门的循环历史查看器
8. **循环暂停后恢复**：`resume_loop()` 工具（MVP 只有 stop 和 delete）
9. **动态调整循环**：循环运行中插入/删除节点（MVP 创建后不可变）

---

## Further Notes

### 关键设计决策

1. **为什么使用 NOTIFICATION 而不是 TASK？**
   - TASK 需要 `complete_task` 闭环，循环流转是自动的，不适合显式闭环
   - NOTIFICATION 自动保存到群聊历史，符合循环消息可见的需求

2. **为什么完全隔离群聊历史？**
   - 循环任务通常是专注的、重复的，群聊历史是噪音
   - 隔离后 Agent 只看到职责、输入、输出要求，更专注

3. **为什么使用事件队列而不是轮询？**
   - 轮询有延迟（0.5 秒），响应不够实时
   - 事件驱动更符合 Agent.run() 的异步架构
   - 通过回调注入解耦，Agent 只增加 2 处修改

4. **为什么限制一个 TERMINATOR 节点？**
   - MVP 保持简单，多个判断点会引入复杂的决策逻辑
   - 未来扩展时可以引入 decision_points 概念

5. **为什么需要 `start_loop` 而不是创建后立即启动？**
   - 预留审核扩展点（未来 User 可以在启动前审核 Loop 定义）
   - 分离创建和启动，责任更清晰

### 可扩展性考虑

**Phase 2 可能的扩展**：
- **LoopType.MANAGED**：Manager 在关键点判断下一步走向（分支逻辑）
- **多个 TERMINATOR 节点**：任何一个返回 `should_continue=false` 即退出
- **循环内子任务**：节点可以调用其他 Agent 完成子任务（不打破循环流程）
- **循环历史分析**：统计平均循环次数、常见失败点、瓶颈节点

### 术语更新

需要在 `CONTEXT.md` 中新增以下术语：

- **Loop（循环）**：一种特殊的编排模式，将多个 Agent 串联成固定序列，反复执行直到满足退出条件
- **LoopNode（循环节点）**：循环中的一个执行单元，包含节点类型、Agent 名称、职责描述、输出格式要求
- **LoopNodeType（循环节点类型）**：NORMAL（普通节点）/ TERMINATOR（结束节点）
- **LoopExecutor（循环执行器）**：循环执行引擎，负责节点调度、输出校验、退出判断、错误处理
- **LoopManager（循环管理器）**：循环 CRUD 和持久化管理
- **IN_LOOP（循环中状态）**：Agent 的一种状态，表示正在参与循环，只接收循环内消息和 Manager 控制信号
- **loop_context（循环上下文）**：循环专用上下文，包含节点职责、输出格式、上一节点输出，隔离群聊历史
- **completion_queue（完成通知队列）**：LoopExecutor 监听的队列，Agent 处理完循环消息后向其发送完成通知
