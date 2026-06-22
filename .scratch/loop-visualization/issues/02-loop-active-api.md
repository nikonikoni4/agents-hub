# Issue 02: 激活的 Loop API + 指定 Loop API

Status: ready-for-agent
Type: AFK
Blocked by: 01-loop-list-api
User stories covered: #1 (看到Loop状态), #4 (执行状态)

## What to build

创建激活的 Loop API 和指定 Loop API，支持获取 Loop 执行状态。

**后端（只读设计，不依赖 core 模块）**：
- 创建 `GET /api/v1/group-chats/{group_chat_id}/loops/active` API 端点
  - 返回当前群聊中激活的 Loop 的节点定义和执行状态
  - 如果没有激活的 Loop，返回文件中第一个 Loop 的节点定义（无执行状态）
- 创建 `GET /api/v1/group-chats/{group_chat_id}/loops/{loop_id}` API 端点
  - 返回指定 Loop 的节点定义和执行状态（如果激活了）

**实现细节**：
- 复用 Issue 01 中的辅助函数 `_read_loops_from_file(group_chat_id: str) -> list[dict]`
- `GET /loops/active` 实现逻辑：
  1. 调用 `_read_loops_from_file()` 获取所有 Loop 定义
  2. 调用 `LoopManager.get_active_loop()` 获取当前激活的 Loop（公开方法，不直接访问私有属性）
  3. 如果 `get_active_loop()` 返回 Loop：
     - 从返回的 Loop 获取定义
     - 从 `LoopExecutionManager` 获取执行状态（如果存在）
     - 返回 `{ loop: LoopDetail, execution: LoopExecution | null }`
  4. 如果 `get_active_loop()` 返回 `None`：
     - 返回文件中第一个 Loop 的定义
     - `execution` 设为 `null`（表示未激活）
  5. 如果文件中没有 Loop，返回空

- `GET /loops/{loop_id}` 实现逻辑：
  1. 调用 `_read_loops_from_file()` 获取所有 Loop 定义
  2. 查找指定 `loop_id` 的 Loop
  3. 如果找到，调用 `LoopManager.get_active_loop()` 检查是否是当前激活的 Loop
  4. 如果是激活的 Loop，从 `LoopExecutionManager` 获取执行状态
  5. 如果不是激活的 Loop，`execution` 设为 `null`
  6. 如果未找到，返回 404

**为什么不使用 core 的已有功能？**
- **解耦设计**：API 层直接读取文件，避免与 core 模块耦合
- **避免干扰**：core 模块的 `LoopManager` 有内存管理逻辑（单例、懒加载），API 层只需要只读访问
- **有意设计**：这不是重复编写代码，而是有意的分层隔离，确保 API 层不会意外修改 core 状态
- **AI 安全**：耦合在一起时，AI 容易出错（如误调用会修改状态的方法）

**前端**：
- 在 `core/api/groupChatApi.ts` 中添加 `getActiveLoop()` 和 `getLoop()` API 函数
- 在 `features/chat/store/loopStore.ts` 中创建 Loop Store（Zustand）
- 在 `features/chat/hooks/useLoopStatus.ts` 中创建 Loop 状态管理 Hook

**架构约束**：
- 参考 `.scratch/loop-visualization/architecture.md`
- **只读约束**：API 层不能修改 core loop 本身的状态
- 数据分离：Loop 定义从文件获取，执行状态从 core 获取（仅读取，不修改）
- 只有激活的 Loop 才有执行状态（execution 不为 null）

## Acceptance criteria

- [ ] 后端：`GET /loops/active` 在有激活 Loop 时正确拼装来自两个数据源的数据（定义 + 执行状态）
- [ ] 后端：`GET /loops/active` 在无激活 Loop 时返回第一个 Loop 的节点定义（execution 为 null）
- [ ] 后端：`GET /loops/active` 通过 `LoopManager.get_active_loop()` 获取激活状态（不直接访问私有属性）
- [ ] 后端：`GET /loops/{loop_id}` 返回指定 Loop 的节点定义和执行状态
- [ ] 后端：API 直接从文件读取 Loop 定义，不调用 `LoopManager` 的查询方法
- [ ] 后端：API 只读取 `LoopExecutionManager` 的状态，不修改
- [ ] 后端：当 `LoopExecutionManager` 中找不到执行实例时，`execution` 字段正确设为 `null`
- [ ] 后端：service 中有注释说明"为什么不使用 core 的已有功能"
- [ ] 前端：getActiveLoop() 和 getLoop() API 函数正常工作
- [ ] 前端：loopStore 正确管理 Loop 状态（列表、当前选中、执行状态）
- [ ] 前端：useLoopStatus Hook 封装 Loop 状态查询和切换逻辑
- [ ] 测试：API 单元测试通过（包括数据拼装和 fallback 逻辑）

## Blocked by

- 01-loop-list-api（需要 `_read_loops_from_file()` 辅助函数和 Loop 类型定义）

## 相关文档

- ADR：`docs/adr/2026-06-23-loop-memory-singleton.md`（单例策略）
- PRD：`.scratch/loop-visualization/PRD.md`（数据获取策略说明、激活的定义）
