# Loop 定义与执行分离重构 - 变更摘要

**版本**: v2.0  
**日期**: 2026-06-21  
**状态**: 已完成 Phase 1-3，待测试验证

## 变更概述

将 Loop 拆分为两个独立的数据模型：
- **Loop**：可复用的循环定义模板
- **LoopExecution**：一次性的执行实例

这样设计的主要好处：
1. 同一个 Loop 可以多次启动，每次传入不同的 `initial_task`
2. 保留完整的执行历史，方便追溯和分析
3. 语义更清晰：定义与执行分离

## 数据模型变更

### Loop（循环定义）

**之前**：
```python
@dataclass
class Loop:
    loop_id: str
    group_chat_id: str
    nodes: list[LoopNode]
    status: str                    # ❌ 移除
    max_iterations: int
    current_iteration: int         # ❌ 移除
    current_node_index: int        # ❌ 移除
    initial_task: str              # ❌ 移除
    created_at: datetime
    updated_at: datetime
    error_message: str | None      # ❌ 移除
```

**现在**：
```python
@dataclass
class Loop:
    loop_id: str
    group_chat_id: str
    nodes: list[LoopNode]
    max_iterations: int
    created_at: datetime
    updated_at: datetime
    # 移除了所有执行状态字段
```

### LoopExecution（执行实例）- 新增

```python
@dataclass
class LoopExecution:
    execution_id: str              # 新增：执行实例唯一标识
    loop_id: str                   # 关联的 Loop 定义 ID
    initial_task: str              # 从 Loop 移过来
    status: str                    # 从 Loop 移过来
    current_iteration: int         # 从 Loop 移过来
    current_node_index: int        # 从 Loop 移过来
    created_at: datetime
    updated_at: datetime
    error_message: str | None      # 从 Loop 移过来
```

### LoopNode（无变更）

节点字段名调整：
- `node_prompt` → `role_description`（语义更清晰）

## MCP 工具接口变更

### create_loop

**之前**：
```python
create_loop(
    agent_token: str,
    nodes: list[dict],
    max_iterations: int,
    initial_task: str,  # ❌ 移除
)
# 返回: {"loop_id": "...", "status": "created"}
```

**现在**：
```python
create_loop(
    agent_token: str,
    nodes: list[dict],
    max_iterations: int,
    # 移除 initial_task 参数
)
# 返回: {"loop_id": "...", "created_at": "..."}
```

### start_loop

**之前**：
```python
start_loop(
    agent_token: str,
    loop_id: str,
)
# 返回: {"loop_id": "...", "status": "running"}
```

**现在**：
```python
start_loop(
    agent_token: str,
    loop_id: str,
    initial_task: str,  # ✅ 新增参数
)
# 返回: {"execution_id": "...", "loop_id": "...", "status": "running"}
```

### stop_loop

**之前**：
```python
stop_loop(agent_token: str, loop_id: str)
# 返回: {"loop_id": "...", "status": "paused"}
```

**现在**：
```python
stop_loop(agent_token: str, execution_id: str)  # 参数改为 execution_id
# 返回: {"execution_id": "...", "status": "paused"}
```

### get_loop_status

**之前**：
```python
get_loop_status(agent_token: str, loop_id: str)
# 返回: {"loop_id": "...", "status": "...", ...}
```

**现在**：
```python
get_loop_status(agent_token: str, execution_id: str)  # 参数改为 execution_id
# 返回: {"execution_id": "...", "loop_id": "...", "status": "...", ...}
```

### list_loops

**之前**：
```python
list_loops(agent_token: str, status: str | None = None)
# 返回 Loop 列表（包含执行状态）
```

**现在**：
```python
list_loops(agent_token: str, status: str | None = None)  # status 参数已废弃
# 返回 Loop 定义列表（不包含执行状态）
# 注意：Loop 定义本身没有状态，status 参数保留仅为向后兼容
```

### list_loop_executions - 新增

```python
list_loop_executions(
    agent_token: str,
    loop_id: str | None = None,    # 可选：过滤特定 Loop 的执行历史
    status: str | None = None,     # 可选：过滤特定状态
)
# 返回: {"executions": [...]}
```

## 架构变更

### 新增组件

**LoopExecutionManager**（新文件）：
- 位置：`agents_hub/core/orchestration/loop_execution_manager.py`
- 职责：管理 LoopExecution 的 CRUD 和持久化
- 持久化文件：`loop_executions.jsonl`

### 修改组件

**LoopManager**：
- 简化为纯定义管理器（移除状态管理方法）
- 删除 Loop 时级联删除所有 executions

**LoopExecutor**：
- 构造函数接收 `loop: Loop` 和 `execution: LoopExecution`
- 所有状态操作委托给 `loop_execution_manager`

**GroupChat**：
- 添加 `loop_execution_manager` 实例
- `create_and_start_loop()` 添加 `initial_task` 参数
- 内存索引改为使用 `execution_id` 而非 `loop_id`

## 渲染格式变更

**之前**：
```
[循环-节点{agent_name}-第{N}轮] @loop ...
```

**现在**：
```
[循环{exec_id[:8]}-节点{agent_name}-第{N}轮] @loop ...
```

添加 execution_id 前 8 位，便于区分不同执行实例。

## 异常体系变更

**新增异常**：
- `LoopExecutionNotFoundError`：执行实例不存在
- `LoopExecutionStateError`：执行实例状态转换非法

**保留异常**：
- `LoopNotFoundError`：Loop 定义不存在
- `LoopValidationError`：创建校验失败
- `LoopExecutionError`：执行失败

## 持久化变更

**新增文件**：
- `loop_executions.jsonl`：存储 LoopExecution 执行历史

**现有文件**：
- `loops.jsonl`：只存储 Loop 定义（不再包含执行状态）

## 内存管理策略

**Loop 定义**：
- 可以长期保留在内存中
- 懒加载：需要时从 JSONL 加载

**LoopExecution 实例**：
- 单 execution 保持策略：内存中同时只保持一个活跃的 execution
- 启动新 execution 时清空其他 execution
- 懒加载：查询历史时从 JSONL 加载

## 使用场景示例

### 场景 1：创建并多次启动

```python
# 1. 创建 Loop 定义
loop = await mcp.create_loop(
    agent_token=manager_token,
    nodes=[executor_node, reviewer_node],
    max_iterations=10,
)

# 2. 第一次启动（审查 user_service.py）
exec1 = await mcp.start_loop(
    agent_token=manager_token,
    loop_id=loop["loop_id"],
    initial_task="审查 user_service.py",
)
# 等待完成...

# 3. 第二次启动（审查 payment_service.py）
exec2 = await mcp.start_loop(
    agent_token=manager_token,
    loop_id=loop["loop_id"],
    initial_task="审查 payment_service.py",
)
# execution_id 不同，但 loop_id 相同
```

### 场景 2：查询执行历史

```python
# 查询特定 Loop 的所有执行历史
executions = await mcp.list_loop_executions(
    agent_token=manager_token,
    loop_id=loop["loop_id"],
)

# 查看每次执行的 initial_task 和结果
for exec in executions["executions"]:
    print(f"Execution: {exec['execution_id']}")
    print(f"Task: {exec['initial_task']}")
    print(f"Status: {exec['status']}")
```

### 场景 3：停止和删除

```python
# 停止执行实例（使用 execution_id）
await mcp.stop_loop(
    agent_token=manager_token,
    execution_id=exec2["execution_id"],
)

# 删除 Loop 定义（级联删除所有 executions）
await mcp.delete_loop(
    agent_token=manager_token,
    loop_id=loop["loop_id"],
)
```

## 向后兼容

**枚举别名**：
```python
LoopStatus = LoopExecutionStatus  # 向后兼容
```

**MCP 工具**：
- 保留 `list_loops()` 的 `status` 参数（标记为废弃，不实际过滤）
- 旧的 MCP 调用会因参数不匹配而失败，需要更新调用方（Manager Agent）

## 待完成工作

### Phase 4：测试与文档（当前阶段）
- [ ] 编写单元测试（test_loop_execution_manager.py）
- [ ] 修改现有测试（test_loop_manager.py, test_loop_executor.py, test_group_chat.py）
- [ ] 编写集成测试（完整 Loop 创建-启动-停止流程）
- [ ] 更新 spec 文档（docs/specs/2026-06-21-loop.md）
- [ ] 更新 flow 文档（docs/flows/loop-lifecycle.md）
- [ ] 更新 PRD 文档（.scratch/loop-feature/PRD.md）

### Phase 5：验证与迁移
- [ ] 手动测试完整流程
- [ ] 数据迁移脚本（如果需要）
- [ ] 向后兼容处理

## 文件清单

### 新增文件
- `agents_hub/core/orchestration/loop_execution_manager.py`
- `docs/temp/loop-refactor-plan.md`
- `docs/temp/loop-refactor-changes.md`（本文档）

### 修改文件
- `agents_hub/core/context/loop_models.py`
- `agents_hub/core/foundation/models.py`
- `agents_hub/core/foundation/exceptions.py`
- `agents_hub/core/foundation/paths.py`
- `agents_hub/core/foundation/renderer.py`
- `agents_hub/core/orchestration/loop_manager.py`
- `agents_hub/core/orchestration/loop_executor.py`
- `agents_hub/core/orchestration/group_chat.py`
- `agents_hub/mcp/server.py`
- `CONTEXT.md`

## 关键设计决策

### 为什么 initial_task 从 create_loop 移到 start_loop？

**问题**：在 v1.0 中，`initial_task` 在创建 Loop 时传入，导致无法复用同一个 Loop 定义。

**解决方案**：将 `initial_task` 移到 `start_loop()` 参数，每次启动时传入不同的任务。

**收益**：
- Loop 成为真正的可复用模板
- 支持查询同一 Loop 的多次执行历史
- 语义更清晰：定义与执行分离

### 为什么需要 LoopExecutionManager？

**设计对称性**：
- LoopManager 管理 Loop 定义
- LoopExecutionManager 管理 LoopExecution 实例
- 职责清晰，易于维护

**独立持久化**：
- Loop 定义可以长期保留
- LoopExecution 可以独立删除（清理旧历史）

### 为什么保留单 execution 内存策略？

**内存优化**：
- 避免内存累积（每个群聊可能有多次执行）
- 只保持当前活跃的 execution

**懒加载**：
- 查询历史时从 JSONL 加载
- 不影响性能（历史查询不频繁）
