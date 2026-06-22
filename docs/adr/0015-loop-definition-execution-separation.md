---
version: 1.0
created_at: 2026-06-21
updated_at: 2026-06-21
last_updated: 2026-06-21
abstract: Loop 定义与执行状态分离——将 Loop 拆为无状态模板（Loop）和有状态执行实例（LoopExecution），支持同一定义多次启动，同时明确"Loop 无状态"不等于"执行过程无状态"
status: decided
---

# Loop 定义与执行分离

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建文档初稿 |

## 问题界定

### 问题简述

Loop 的 `initial_task` 在 `create_loop()` 时传入并持久化到 Loop 模型中，导致同一 Loop 定义无法复用——每次执行不同任务都必须删除旧 Loop 并创建新 Loop。这违背了 Loop 作为"可编排模板"的设计初衷。

更深层的问题是：Loop 模型同时承载了"定义"（节点列表、最大轮次）和"执行状态"（当前轮次、当前节点、错误信息）两种职责，语义不清。

### 讨论范围

- Loop 和 LoopExecution 的数据模型拆分
- `initial_task` 的归属（定义 vs 执行参数）
- MCP 工具接口的参数调整
- "Loop 无状态"的准确含义——定义无状态 vs 执行有状态
- 前端获取执行进度（`current_node_index`）的数据来源

### 非讨论范围

- LoopExecutor 的内部调度逻辑（不变）
- Agent 的执行行为（不变）
- 群聊消息历史管理（不变）

### 模糊信息的明确定义

- **"Loop 无状态"**：指 Loop **定义**（Loop 模型）不包含任何执行状态字段。Loop 定义只描述"有哪些节点、最大循环几次"，不记录"当前执行到哪了"。
- **"LoopExecution 有状态"**：指每次启动 Loop 时创建的 **执行实例**（LoopExecution 模型）包含完整的执行状态（status、current_iteration、current_node_index、error_message）。
- **"每次从 0 开始加载"**：指 LoopExecutor 每次启动时读取 Loop 定义和 initial_task，从第一个节点（index=0）开始执行，不恢复上次执行的中间状态。

### 问题深度

涉及数据模型设计、API 契约、内存管理和前端交互，属于架构层面的模型拆分决策。

## 现状

### v1.0 设计

Loop 模型包含 11 个字段，混合了定义和执行状态：

```python
@dataclass
class Loop:
    loop_id: str
    group_chat_id: str
    nodes: list[LoopNode]
    status: str                     # 执行状态
    max_iterations: int             # 定义属性
    current_iteration: int          # 执行状态
    current_node_index: int         # 执行状态
    initial_task: str               # 执行参数
    created_at: datetime
    updated_at: datetime
    error_message: str | None       # 执行状态
```

### 存在的问题

1. **复用性差**：`initial_task` 绑定在 Loop 上，同一 Loop 无法执行不同任务
2. **语义不清**：Loop 既是"定义"又是"执行"，阅读代码时难以区分哪些是模板属性、哪些是运行时状态
3. **历史不可追溯**：无法查看同一 Loop 定义的多次执行历史
4. **内存管理矛盾**：单 Loop 保持策略与复用需求冲突

## 可选方案

### 方案 A：Loop + LoopExecution 分离

将 Loop 拆分为两个模型：
- **Loop**：无状态模板，只包含 loop_id、nodes、max_iterations 等定义属性
- **LoopExecution**：有状态执行实例，包含 execution_id、loop_id、initial_task、status、current_iteration、current_node_index 等执行状态

`initial_task` 从 `create_loop()` 移到 `start_loop()`，每次启动创建新的 LoopExecution。

**优势**

- Loop 成为真正的可复用模板
- 语义清晰：定义与执行职责分离
- 支持查询同一 Loop 的多次执行历史
- 前端通过 `get_loop_status(execution_id)` 获取进度，数据来源明确

**劣势**

- 新增一个数据模型和管理器（LoopExecutionManager）
- MCP 工具接口变更，调用方需要适配
- 两个模型的交互增加了理解成本

### 方案 B：保持 Loop 有状态，增加"LoopTemplate"概念

引入 LoopTemplate 作为可复用模板，Loop 仍然是有状态的执行实例。

**优势**

- Loop 的语义不变，减少认知变化
- 不需要修改 LoopExecutor 的内部逻辑

**劣势**

- LoopTemplate 和 Loop 的关系不直观——"从模板创建 Loop"比"从定义启动执行"更绕
- 与现有代码中 Loop 的使用方式冲突（LoopManager 管理的是"定义"还是"实例"？）
- 实际上只是换了名字，没有解决根本的语义问题

### 方案 C：在 Loop 上增加 execution_history 列表

保持 Loop 单一模型，增加一个 `executions: list[LoopExecution]` 字段记录执行历史。

**优势**

- 模型数量不变
- 执行历史集中在 Loop 上，查询方便

**劣势**

- Loop 模型越来越重，混合了定义、当前执行、历史执行
- 内存管理更复杂（需要决定哪些 execution 保留在内存）
- 违反单一职责原则

## 最终决策

选择 **方案 A：Loop + LoopExecution 分离**。

## 决策原因

1. **复用性**：`initial_task` 移到 `start_loop()` 后，同一 Loop 定义可以多次启动，每次传入不同任务。这是触发本次重构的直接原因。

2. **语义清晰**：Loop 定义只描述"结构"（节点、轮次上限），LoopExecution 只描述"运行"（状态、进度、错误）。阅读代码时可以立即区分模板属性和运行时状态。

3. **历史追溯**：每次启动都创建新的 LoopExecution，执行历史自然累积，支持 `list_loop_executions()` 查询。

4. **前端进度展示**：`current_node_index` 在 LoopExecution 上，前端通过 `get_loop_status(execution_id)` 获取。这与"Loop 定义无状态"不矛盾——定义确实无状态，执行实例有状态。

5. **内存管理简化**：Loop 定义可以长期保留在内存（小且不变），LoopExecution 采用单实例保持策略（只保留当前活跃的 execution）。

### 关于"Loop 无状态"的澄清

"Loop 无状态"指的是 **Loop 定义模型** 不包含执行状态字段。这不等于"执行过程没有状态"——LoopExecution 模型承载了所有执行状态。

类比：
- **Loop** = 函数定义（`def process(items, max_iter):`）
- **LoopExecution** = 函数调用栈（`process(items=[...], max_iter=10)` 的一次具体执行）

函数定义没有"当前执行到第几行"的概念，但每次函数调用都有。Loop 同理。

### 关于 `current_node_index` 的数据来源

前端需要显示"当前执行到哪个节点"。这个信息来自 LoopExecution.current_node_index，通过 `get_loop_status(execution_id)` API 获取。

设计要点：
- `current_node_index` 是 LoopExecution 的字段，不是 Loop 的字段
- LoopExecutor 每次启动从 index=0 开始，中间状态不持久化到文件（只在内存中推进）
- 执行完成后，最终状态通过 `loop_execution_manager.update_execution_status()` 持久化
- 前端看到的是"最后持久化的状态"，不是实时内存状态（可接受的延迟）

## 后续影响

### 代码变更

- 新增 LoopExecution 数据模型和 LoopExecutionManager
- LoopManager 简化为纯定义管理器
- LoopExecutor 接收 loop + execution 两个参数
- MCP 工具接口调整：create_loop 移除 initial_task，start_loop 添加 initial_task，stop_loop/get_loop_status 参数改为 execution_id
- 新增 list_loop_executions 工具查询执行历史

### 数据持久化

- 新增 `loop_executions.jsonl` 文件存储执行历史
- 现有 `loops.jsonl` 只存储定义（旧数据中的执行状态字段被忽略）

### 已知限制

- LoopExecutor 每次从 index=0 启动，不支持从中间状态恢复（PAUSED 重启后从头开始）
- 前端看到的 `current_node_index` 是最后持久化的快照，不是实时状态
- `list_loop_executions()` 直接读 JSONL，数据量大时可能有性能问题（当前预期可接受）
