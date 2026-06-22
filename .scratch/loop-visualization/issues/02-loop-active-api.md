# Issue 02: 激活的 Loop API + 指定 Loop API

Status: ready-for-agent
Type: AFK
Blocked by: 01-loop-list-api
User stories covered: #1 (看到Loop状态), #4 (执行状态)

## What to build

创建激活的 Loop API 和指定 Loop API，支持获取 Loop 执行状态。

**后端**：
- 创建 `GET /api/v1/group-chats/{group_chat_id}/loops/active` API 端点
  - 返回当前群聊中激活的 Loop 的节点定义和执行状态
  - 如果没有激活的 Loop，返回 `list_loops` 中的第一个 Loop 的节点定义（无执行状态）
- 创建 `GET /api/v1/group-chats/{group_chat_id}/loops/{loop_id}` API 端点
  - 返回指定 Loop 的节点定义和执行状态（如果激活了）

**数据分离策略（关键实现细节）**：
- **Loop 定义**：从 `loops.jsonl` 文件读取（复用 `LoopManager.list_loops()` 或 `LoopManager.get_loop_with_lazy_load()`）
- **Loop 执行状态**：从 `LoopExecutionManager` 获取（仅当 Loop 激活时）
- **数据拼装逻辑**：
  1. 调用 `LoopManager` 获取 Loop 定义（loop_id、name、nodes、max_iterations）
  2. 调用 `LoopExecutionManager.get_execution_by_loop_id(loop_id)` 尝试获取执行实例
  3. 如果找到执行实例，拼装 `LoopExecution`（execution_id、status、current_iteration、current_node_index、error_message）
  4. 如果未找到执行实例，`execution` 字段设为 `null`（表示未激活）

**前端**：
- 在 `core/api/groupChatApi.ts` 中添加 `getActiveLoop()` 和 `getLoop()` API 函数
- 在 `features/chat/store/loopStore.ts` 中创建 Loop Store（Zustand）
- 在 `features/chat/hooks/useLoopStatus.ts` 中创建 Loop 状态管理 Hook

**架构约束**：
- 参考 `.scratch/loop-visualization/architecture.md`
- 数据分离：Loop 定义从文件获取，执行状态从 core 获取
- 只有激活的 Loop 才有执行状态（execution 不为 null）

## Acceptance criteria

- [ ] 后端：`GET /loops/active` 在有激活 Loop 时正确拼装来自两个数据源的数据（定义 + 执行状态）
- [ ] 后端：`GET /loops/active` 在无激活 Loop 时返回第一个 Loop 的节点定义（execution 为 null）
- [ ] 后端：`GET /loops/{loop_id}` 返回指定 Loop 的节点定义和执行状态
- [ ] 后端：API Service 正确调用 `LoopManager` 和 `LoopExecutionManager` 两个数据源
- [ ] 后端：当 `LoopExecutionManager` 中找不到执行实例时，`execution` 字段正确设为 `null`
- [ ] 前端：getActiveLoop() 和 getLoop() API 函数正常工作
- [ ] 前端：loopStore 正确管理 Loop 状态（列表、当前选中、执行状态）
- [ ] 前端：useLoopStatus Hook 封装 Loop 状态查询和切换逻辑
- [ ] 测试：API 单元测试通过（包括数据拼装和 fallback 逻辑）

## Blocked by

- 01-loop-list-api（需要 Loop 类型定义和基础 API 函数）
