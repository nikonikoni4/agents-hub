# Slice 1: 基础数据模型和持久化

**类型**: AFK  
**状态**: Ready for implementation

## Parent

PRD: Agent 循环执行功能（Loop）
文件路径: `docs/temp/loop-feature-prd.md`

## What to build

实现 Loop 功能的基础数据层，包括核心数据模型定义和持久化机制。这是一个完整的垂直切片，从数据定义到文件存储再到读取验证。

构建以下组件：

1. **数据模型定义**：
   - Loop 数据类：循环的完整定义，包含 ID、状态、节点列表、迭代控制、初始任务
   - LoopNode 数据类：节点定义，包含类型、Agent 名称、职责描述、输出格式要求
   - LoopStatus 枚举：CREATED / RUNNING / PAUSED / COMPLETED / FAILED
   - LoopNodeType 枚举：NORMAL / TERMINATOR

2. **LoopManager**：
   - 创建循环（校验约束条件，使用 asyncio.Lock 防止并发创建）
   - 查询循环（支持按 loop_id 和 group_chat_id 查询）
   - 删除循环（只能删除非 RUNNING 状态）
   - 持久化到 loops.jsonl（append-only 模式）
   - 从 loops.jsonl 读取并恢复（容错：同一 loop_id 取最新记录）

3. **创建时校验规则**：
   - 至少 2 个节点
   - 有且仅有 1 个 TERMINATOR 节点
   - 所有 agent_name 必须存在（通过 RoleManager 验证）
   - 该 group_chat 没有其他 RUNNING 的 Loop

4. **持久化文件路径**：
   - `local_data/teams/<team_name>/<project_path>/<group_chat_id>/loops.jsonl`
   - 每次状态变更追加一条 JSONL 记录

## Acceptance criteria

- [ ] 可以创建 Loop 并持久化到 loops.jsonl
- [ ] 可以从 loops.jsonl 读取并恢复 Loop
- [ ] 创建时校验通过（节点数量、TERMINATOR 唯一性、agent_name 存在性）
- [ ] 创建时校验失败抛出正确的领域异常（ValidationError）
- [ ] 可以查询特定 loop_id 的 Loop
- [ ] 可以查询特定 group_chat_id 的所有 Loop
- [ ] 可以删除非 RUNNING 状态的 Loop
- [ ] 删除 RUNNING 状态的 Loop 抛出 StateError
- [ ] 一个群聊尝试创建第二个 RUNNING Loop 时抛出 ValidationError
- [ ] LoopManager 使用 asyncio.Lock 防止并发创建（集成测试验证）
- [ ] 单元测试覆盖 LoopManager 的所有 CRUD 操作
- [ ] 单元测试覆盖所有校验规则
- [ ] 单元测试覆盖持久化和恢复逻辑（包括同一 loop_id 多条记录的容错）

## Blocked by

None - 可立即开始

## Notes

- 数据模型定义在 `agents_hub/core/context/group_chat_session.py`（Loop、LoopNode、LoopStatus、LoopNodeType）
- LoopManager 实现在 `agents_hub/core/orchestration/loop_manager.py`
- 遵循现有的异常体系（ValidationError、StateError）
- 遵循现有的持久化模式（JSONL append-only）
- 参考现有测试：`tests/core/communication/test_task_manager.py`
- 并发控制：LoopManager 初始化时创建 `self._lock = asyncio.Lock()`，create_loop() 内使用 `async with self._lock` 包裹校验和创建逻辑
