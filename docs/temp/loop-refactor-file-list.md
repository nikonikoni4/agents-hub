# Loop 定义与执行分离重构 - 修改文件清单

**重构版本**: v2.0  
**完成日期**: 2026-06-21  
**完成阶段**: Phase 1-4（数据层、业务层、接口层、文档）

## 修改文件列表

### Phase 1：数据层（已完成）

#### 1. 新增文件

| 文件路径 | 说明 | 主要内容 |
|---------|------|---------|
| `agents_hub/core/orchestration/loop_execution_manager.py` | LoopExecution 执行实例管理器 | 执行实例的 CRUD、持久化、懒加载、单 execution 保持策略 |

#### 2. 修改文件

| 文件路径 | 修改内容 | 关键变更 |
|---------|---------|---------|
| `agents_hub/core/context/loop_models.py` | 数据模型拆分 | - Loop 移除执行状态字段（status、current_iteration、current_node_index、initial_task、error_message）<br>- 新增 LoopExecution 数据模型<br>- LoopNode.node_prompt → role_description |
| `agents_hub/core/foundation/models.py` | 枚举重命名 | - LoopStatus → LoopExecutionStatus<br>- 添加向后兼容别名 `LoopStatus = LoopExecutionStatus` |
| `agents_hub/core/foundation/exceptions.py` | 新增异常类 | - LoopExecutionNotFoundError<br>- LoopExecutionStateError |
| `agents_hub/core/foundation/paths.py` | 新增路径方法 | - loop_executions_data()：返回 loop_executions.jsonl 路径 |

---

### Phase 2：业务层（已完成）

| 文件路径 | 修改内容 | 关键变更 |
|---------|---------|---------|
| `agents_hub/core/orchestration/loop_manager.py` | 简化为定义管理器 | - create_loop() 移除 initial_task 参数<br>- 移除 update_loop_status() 方法<br>- 移除 clear_other_loops() 方法<br>- delete_loop() 级联删除所有 executions<br>- 移除自动加载历史 Loop 逻辑<br>- list_loops() 废弃 status 参数 |
| `agents_hub/core/orchestration/loop_executor.py` | 接收 execution 参数 | - 构造函数添加 execution: LoopExecution 参数<br>- 构造函数添加 loop_execution_manager 参数<br>- 所有 self.loop.status → self.execution.status<br>- 所有 self.loop.current_iteration → self.execution.current_iteration<br>- 所有 self.loop.current_node_index → self.execution.current_node_index<br>- 所有 self.loop.initial_task → self.execution.initial_task<br>- 状态更新调用 loop_execution_manager.update_execution_status() |
| `agents_hub/core/orchestration/group_chat.py` | 添加 execution 管理 | - 新增 loop_execution_manager 属性（懒加载）<br>- 新增 _get_loop_execution_manager() 方法<br>- create_loop() 移除 initial_task 参数<br>- create_and_start_loop() 添加 initial_task 参数<br>- create_and_start_loop() 创建 LoopExecution 实例<br>- create_and_start_loop() 清空其他 execution（单 execution 保持）<br>- stop_loop() 参数改为 execution_id<br>- get_loop_status() 参数改为 execution_id<br>- cleanup_loop() 参数改为 execution_id<br>- active_loops、_loop_tasks、_loop_queues 字典 key 改为 execution_id |

---

### Phase 3：接口层（已完成）

| 文件路径 | 修改内容 | 关键变更 |
|---------|---------|---------|
| `agents_hub/mcp/server.py` | MCP 工具接口调整 | **create_loop (line 1105-1150)**:<br>- 移除 initial_task 参数<br>- 返回值改为 {"loop_id": "...", "created_at": "..."}<br><br>**start_loop (line 1168-1203)**:<br>- 添加 initial_task 参数<br>- 返回值改为 {"execution_id": "...", "loop_id": "...", "status": "running"}<br><br>**stop_loop (line 1206-1241)**:<br>- 参数从 loop_id 改为 execution_id<br>- 返回值改为 {"execution_id": "...", "status": "paused"}<br><br>**get_loop_status (line 1282-1320)**:<br>- 参数从 loop_id 改为 execution_id<br>- 返回值包含 execution_id 和 loop_id<br><br>**list_loops (line 1323-1379)**:<br>- 文档标记 status 参数已废弃<br>- 返回 Loop 定义摘要（移除执行状态字段）<br><br>**list_loop_executions (line 1382-1443，新增)**:<br>- 查询执行历史<br>- 支持按 loop_id 和 status 过滤<br><br>**异常导入 (line 78-83)**:<br>- 添加 LoopExecutionNotFoundError<br>- 添加 LoopExecutionStateError<br><br>**工具注册 (line 1-16, 1478-1494)**:<br>- 注册 list_loop_executions<br>- 废弃 report_progress/complete_task/request_permission（注释掉注册，函数体内标记已弃用）<br>- 实际注册 11 个 MCP 工具 |
| `agents_hub/core/foundation/renderer.py` | 渲染格式更新 | - render_for_chat() 添加 execution_id 参数<br>- 循环消息格式改为：[循环{exec_id[:8]}-节点{agent}-第{N}轮] |

---

### Phase 4：测试与文档（已完成）

#### 1. 新增文档

| 文件路径 | 说明 | 内容 |
|---------|------|------|
| `docs/temp/loop-refactor-plan.md` | 完整重构计划 | 从 Phase 1 到 Phase 5 的详细实施方案 |
| `docs/temp/loop-refactor-changes.md` | 变更摘要文档 | 数据模型对比、API 接口对比、使用场景示例、设计决策说明 |
| `docs/temp/loop-refactor-file-list.md` | 修改文件清单 | 本文档，所有修改文件的详细列表 |

#### 2. 修改文档

| 文件路径 | 修改内容 | 关键变更 |
|---------|---------|---------|
| `CONTEXT.md` | 术语更新 | - Loop 术语拆分为 Loop（循环定义）和 LoopExecution（执行实例）<br>- 新增 LoopExecution 术语定义<br>- 新增 LoopExecutionManager 术语定义<br>- 更新 LoopManager 职责说明<br>- 更新 LoopExecutor 持有对象<br>- 修正字段名（node_prompt → role_description） |

---

## 文件统计

### 按类型统计

| 类型 | 数量 | 说明 |
|------|------|------|
| 新增代码文件 | 1 | loop_execution_manager.py |
| 修改代码文件 | 9 | 数据模型、管理器、执行器、MCP 接口等 |
| 新增文档文件 | 3 | 计划、变更摘要、文件清单 |
| 修改文档文件 | 1 | CONTEXT.md |
| **总计** | **14** | |

### 按阶段统计

| 阶段 | 新增文件 | 修改文件 | 合计 |
|------|---------|---------|------|
| Phase 1：数据层 | 1 | 4 | 5 |
| Phase 2：业务层 | 0 | 3 | 3 |
| Phase 3：接口层 | 0 | 2 | 2 |
| Phase 4：测试与文档 | 3 | 1 | 4 |
| **总计** | **4** | **10** | **14** |

### 代码行数估算

| 类型 | 行数 | 说明 |
|------|------|------|
| 新增代码 | ~600 行 | loop_execution_manager.py 完整实现 |
| 修改代码 | ~500 行 | 数据模型、管理器、MCP 接口等 |
| 新增文档 | ~800 行 | 计划、变更摘要、文件清单 |
| 修改文档 | ~50 行 | CONTEXT.md 术语更新 |
| **总计** | **~1950 行** | |

---

## 核心变更说明

### 数据模型变更

**Loop 字段变更**：
```
移除字段：
- status: str
- current_iteration: int
- current_node_index: int
- initial_task: str
- error_message: str | None

保留字段：
- loop_id: str
- group_chat_id: str
- nodes: list[LoopNode]
- max_iterations: int
- created_at: datetime
- updated_at: datetime
```

**新增 LoopExecution 模型**：
```
所有字段：
- execution_id: str           # 新增
- loop_id: str                # 关联 Loop
- initial_task: str           # 从 Loop 移过来
- status: str                 # 从 Loop 移过来
- current_iteration: int      # 从 Loop 移过来
- current_node_index: int     # 从 Loop 移过来
- created_at: datetime
- updated_at: datetime
- error_message: str | None   # 从 Loop 移过来
```

### MCP 接口变更

| 工具 | 参数变更 | 返回值变更 |
|------|---------|-----------|
| create_loop | 移除 initial_task | status → created_at |
| start_loop | 添加 initial_task | 添加 execution_id |
| stop_loop | loop_id → execution_id | loop_id → execution_id |
| get_loop_status | loop_id → execution_id | 添加 execution_id |
| list_loops | status 参数废弃 | 移除执行状态字段 |
| list_loop_executions | 新增工具 | 返回执行历史 |

### 架构变更

**新增组件**：
- LoopExecutionManager：管理执行实例的 CRUD 和持久化

**修改组件**：
- LoopManager：简化为定义管理器，移除状态管理
- LoopExecutor：接收 execution 参数，委托状态管理
- GroupChat：添加 execution_manager，修改所有 Loop 方法

---

## 持久化文件变更

### 新增文件

| 文件路径 | 格式 | 内容 |
|---------|------|------|
| `loop_executions.jsonl` | JSONL | LoopExecution 执行实例记录 |

### 现有文件变更

| 文件路径 | 变更说明 |
|---------|---------|
| `loops.jsonl` | 只存储 Loop 定义，不再包含执行状态字段 |

---

## 向后兼容说明

### 代码层面

- **枚举别名**：`LoopStatus = LoopExecutionStatus`（向后兼容）
- **MCP 工具**：保留 `list_loops()` 的 `status` 参数（标记废弃）

### 数据迁移

**注意**：旧的 `loops.jsonl` 文件包含执行状态，新代码读取时：
- Loop 定义字段正常读取
- 执行状态字段被忽略（不影响系统运行）

**建议**：
- 如果需要保留旧的执行历史，需要编写数据迁移脚本
- 如果不需要，可以直接使用新代码（旧数据不影响）

---

## 待完成工作（Phase 5）

### 测试验证

- [x] 编写单元测试：test_loop_execution_manager.py（43 个测试，覆盖 CRUD/状态机/持久化/懒加载）
- [x] 修改现有测试：test_loop_manager.py（22 个测试，移除 initial_task/状态字段）
- [x] 修改现有测试：test_loop_executor_context.py（11 个测试，添加 execution 参数）
- [x] 修改现有测试：test_loop_executor_core.py（6 个测试，适配新 Loop/LoopExecution 分离）
- [x] 修改现有测试：test_loop_executor_validation_retry.py（13 个测试，添加 execution 参数）
- [x] 修改现有测试：test_group_chat_loop_lifecycle.py（4 个测试，适配 execution_id）
- [x] 修改现有测试：test_loop_tools.py（9 个测试，适配 MCP 接口变更）
- [ ] 编写集成测试：完整 Loop 创建-启动-停止流程

### 文档完善

- [ ] 完整更新 docs/specs/2026-06-21-loop.md
- [ ] 更新 docs/flows/loop-lifecycle.md
- [ ] 更新 .scratch/loop-feature/PRD.md

### 验证与迁移

- [ ] 手动测试完整流程
- [ ] 编写数据迁移脚本（如需要）
- [ ] 验证向后兼容性

---

## Review 检查点

### 代码 Review

1. **数据模型**：
   - Loop 和 LoopExecution 的字段分离是否合理？
   - LoopNode 的 role_description 命名是否清晰？

2. **管理器**：
   - LoopExecutionManager 的实现是否完整？
   - 单 execution 保持策略是否合理？
   - 懒加载机制是否正确？

3. **执行器**：
   - LoopExecutor 接收 execution 参数的改动是否完整？
   - 状态更新委托给 loop_execution_manager 是否正确？

4. **GroupChat**：
   - create_and_start_loop() 的 initial_task 参数是否合理？
   - 内存索引改为 execution_id 是否正确？
   - 清空其他 execution 的逻辑是否合理？

5. **MCP 接口**：
   - 参数变更是否会破坏现有调用？
   - 返回值变更是否清晰明确？
   - 新增的 list_loop_executions 是否必要？

### 设计 Review

1. **复用性**：同一 Loop 多次启动是否是真实需求？
2. **内存管理**：单 execution 保持策略是否过于激进？
3. **持久化**：loop_executions.jsonl 是否需要单独文件？
4. **向后兼容**：是否需要保留旧接口一段时间？

### 测试 Review

1. **单元测试**：是否需要覆盖所有 CRUD 操作？
2. **集成测试**：是否需要测试多次启动同一 Loop？
3. **边界测试**：是否需要测试级联删除？

---

## 联系方式

如有疑问或需要进一步说明，请参考：
- 完整计划：`docs/temp/loop-refactor-plan.md`
- 变更摘要：`docs/temp/loop-refactor-changes.md`
- 术语定义：`CONTEXT.md`
