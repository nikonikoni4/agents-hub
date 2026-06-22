# Code Review Report

**审查范围**: `.scratch/loop-visualization/` 设计文档（architecture.md + 6 个 issue 文件）
**审查时间**: 2026-06-22
**审查文件**:
- `.scratch/loop-visualization/architecture.md`
- `.scratch/loop-visualization/issues/01-loop-list-api.md`
- `.scratch/loop-visualization/issues/02-loop-active-api.md`
- `.scratch/loop-visualization/issues/03-loop-status-panel.md`
- `.scratch/loop-visualization/issues/04-loop-detail-modal.md`
- `.scratch/loop-visualization/issues/05-loop-node-detail.md`
- `.scratch/loop-visualization/issues/06-loop-websocket-notify.md`

## 架构上下文

### 相关 ADR
- ADR-0015: Loop 定义与执行分离 (accepted) — `docs/ADR/0015-loop-definition-execution-separation.md`

### 相关 Spec
- `docs/specs/2026-06-21-loop.md`: Loop 循环执行规格（v2.0，定义/执行分离）
- `docs/specs/2026-06-06-realtime.md`: Realtime 模块规格（WebSocket 广播机制）
- `docs/specs/2026-06-06-frontend-core.md`: 前端 Core 层规格

### 相关 Flow
- `docs/flows/loop-lifecycle.md`: Loop 生命周期数据流

### 编码规则
- `docs/coding-rules/frontend-style-layers.md`: 前端样式层级规则
- `docs/coding-rules/backend-concurrency.md`: 后端并发与状态管理规则

## 审查结果

Found 6 issues:

---

### Issue 1: architecture.md 模块职责表遗漏 LoopExecutionManager
- **类型**: Architecture
- **置信度**: 90
- **位置**: `.scratch/loop-visualization/architecture.md:5-16`
- **详情**: 模块职责表列出了 `LoopManager`（Loop 定义 CRUD）和 `LoopExecutor`（Loop 执行逻辑），但遗漏了 `LoopExecutionManager`（执行实例管理）。然而同一文件的依赖关系树（第 94 行）明确引用了 `LoopExecutionManager (loop_execution_manager.py)`，Issue 02 也依赖它获取执行状态。该文件已存在于 `agents_hub/core/orchestration/loop_execution_manager.py`。
- **依据**: 架构文档内部不一致 — 依赖树引用了模块职责表未列出的模块。ADR-0015 定义了 Loop/LoopExecution 分离，LoopExecutionManager 是该分离的核心承载者。
- **建议**: 在模块职责表中添加一行：

  | `agents_hub/core/orchestration/loop_execution_manager.py` | LoopExecution 执行实例的 CRUD 和内存管理 | **新增**：供 API Service 查询执行状态 |

---

### Issue 2: LoopDetail 接口混入了 LoopExecution 执行状态字段
- **类型**: Architecture
- **置信度**: 85
- **位置**: `.scratch/loop-visualization/architecture.md:121-139`（LoopDetail 接口定义）
- **详情**: architecture.md 定义的 `LoopDetail` 接口仅包含 `loop_id`、`name`、`nodes`、`max_iterations`，这是正确的 — 这些是 Loop 定义字段。但 Issue 02 定义的 `LoopExecution` 接口包含了 `status`、`current_iteration`、`current_node_index`、`error_message`，这些字段在 `Loop` 数据模型中并不存在（`loop_models.py` 的 `Loop` dataclass 没有 `status` 字段）。`LoopStatus` 是独立枚举，执行状态由 `LoopExecutionManager` 管理。
  
  这个分离设计本身是正确的（符合 ADR-0015），但 **Issue 02 的 `ActiveLoopResponse` 需要从两个不同数据源拼装**（LoopManager 读定义 + LoopExecutionManager 读状态），API Service 层的实现复杂度被低估。Issue 02 的 Acceptance Criteria 没有明确测试"从两个数据源拼装"这个关键路径。
- **依据**: `docs/specs/2026-06-21-loop.md` 中 Loop 数据结构没有 `status` 字段；ADR-0015 定义了定义/执行分离。
- **建议**: 在 Issue 02 的 "What to build" 部分明确标注：
  1. API Service 需要调用 `LoopManager.list_loops()` + `LoopExecutionManager` 两个数据源
  2. Acceptance Criteria 增加："后端：`GET /loops/active` 正确拼装来自两个数据源的数据（定义 + 执行状态）"
  3. 明确处理 `LoopExecutionManager` 中找不到执行实例时的 fallback 逻辑

---

### Issue 3: Issue 04 "loopBack 区域"描述模糊
- **类型**: Code Quality
- **置信度**: 82
- **位置**: `.scratch/loop-visualization/issues/04-loop-detail-modal.md:19`
- **详情**: Issue 04 在节点图描述中提到 "loopBack 区域：显示循环信息"，但未定义：
  1. "循环信息" 具体指什么（当前迭代次数？循环连线？回到起点的箭头？）
  2. 在垂直节点图中如何布局（底部？右侧？连线形式？）
  3. 与节点图的视觉关系
  
  这是 Loop 可视化的核心 UI 元素，描述模糊会导致实现者自由发挥，与设计意图不符。
- **依据**: PRD 中 User Story #2（节点列表）和 #9（迭代次数）应约束此区域的展示内容。
- **建议**: 明确 loopBack 区域的设计：
  - 展示内容：当前迭代/最大迭代、循环连线（从最后一个节点回到第一个节点的箭头）
  - 布局位置：节点图底部，用弧线箭头表示循环回路
  - 样式：与节点状态颜色一致（运行中=蓝色，完成=绿色）

---

### Issue 4: ⚠️ WebSocket 广播异常处理（降级为风险项）
- **类型**: Performance
- **置信度**: 65（降级）
- **位置**: `.scratch/loop-visualization/issues/06-loop-websocket-notify.md:14-16`
- **详情**: 现有代码中所有 `broadcast_group_chat_refresh` 调用均使用 `await` 直接调用（共 7 处：group_chat_service.py 4 处、mcp/server.py 3 处），无 `create_task` 模式。Issue 06 应保持一致，使用 `await` 直接调用。

  唯一需要注意的是 `_emergency_stop()` 路径：广播失败不应阻止清理逻辑执行。建议在 `_emergency_stop()` 中将广播包裹在 try/except 中。
- **依据**: 现有代码全部使用 `await` 模式，保持一致性优先。
- **建议**: Issue 06 中统一使用 `await broadcast_group_chat_refresh()`，与现有模式一致。`_emergency_stop()` 中加 try/except 容错即可。

---

### Issue 5: Issue 06 缺少 broadcast 依赖注入方案
- **类型**: Architecture
- **置信度**: 80
- **位置**: `.scratch/loop-visualization/issues/06-loop-websocket-notify.md:17`
- **详情**: Issue 06 写道 "需要注入 `broadcast_group_chat_refresh` 回调或直接调用"，但没有做出选择。这是一个架构决策点：
  - **直接调用**：LoopExecutor 直接 import `broadcast_group_chat_refresh`，简单但增加 LoopExecutor 对 realtime 模块的耦合
  - **回调注入**：通过构造函数传入回调，解耦但增加 GroupChat 的构造复杂度
  
  当前 `LoopExecutor` 没有对 `realtime` 模块的依赖。直接调用会引入新的跨层依赖。
- **依据**: `docs/coding-rules/core-runtime-boundary.md` 规定 core 模块的边界规则；SRP 原则。
- **建议**: 采用回调注入方案（与现有 `_notify_manager_loop_ended` 模式一致）：
  1. `LoopExecutor.__init__()` 增加 `on_state_change: Callable | None = None` 参数
  2. `GroupChat.create_and_start_loop()` 创建 LoopExecutor 时传入 `broadcast_group_chat_refresh` 的包装函数
  3. 在 Issue 06 中明确此决策

---

### Issue 6: Issue 03 依赖声明不完整
- **类型**: Architecture
- **置信度**: 80
- **位置**: `.scratch/loop-visualization/issues/03-loop-status-panel.md:3`
- **详情**: Issue 03 声明 `Blocked by: 02-loop-active-api`，但 LoopStatusPanel 的下拉菜单需要 Loop 列表数据（来自 Issue 01 的 `getLoops()` API），节点列表需要 Loop 详情 + 执行状态（来自 Issue 02 的 `getActiveLoop()` API）。虽然 Issue 02 已依赖 Issue 01（传递依赖），但 Issue 03 的 Acceptance Criteria 第 2 项"下拉菜单可以切换不同的 Loop 定义"直接依赖 `getLoops()`，应在 Blocked by 中显式声明。
- **依据**: 设计文档应明确依赖关系，避免实现时发现遗漏。
- **建议**: 将 Issue 03 的 Blocked by 修改为：
  ```
  - 01-loop-list-api（需要 getLoops() 获取 Loop 列表用于下拉菜单）
  - 02-loop-active-api（需要 getActiveLoop() 和 Loop Store）
  ```

## 审查总结

| 类别 | 通过 | 问题 | 风险 |
|------|------|------|------|
| 设计一致性 | ✅ 依赖链 01→02→03→04/05→06 合理 | ❌ 模块表遗漏 LoopExecutionManager | ⚠️ Issue 03 依赖声明不完整 |
| 架构合规 | ✅ 数据分离设计符合 ADR-0015 | ❌ LoopDetail 字段混入执行状态 | ⚠️ broadcast 注入方案未明确 |
| 接口契约 | ✅ API 端点设计合理 | — | ⚠️ 两数据源拼装复杂度被低估 |
| 实现可行性 | ✅ 文件路径与实际代码结构匹配 | ❌ loopBack 区域描述模糊 | ⚠️ 广播异常处理（`_emergency_stop` 路径） |

**总体评价**：设计文档整体质量较高，架构方向正确（定义/执行分离、复用 RefreshSignal）。主要问题集中在细节层面：模块表遗漏、接口字段混淆、UI 描述模糊。建议在实现前修复 ❌ 项，⚠️ 项可在实现时处理。
