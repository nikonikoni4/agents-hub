# Issue 00: LoopManager 单例重构

Status: completed
Type: AFK
Blocked by: None - can start immediately
User stories covered: 间接支持所有 User Stories（为后续 API 提供正确的内存模型）

## What to build

将 LoopManager 的内存模型从多实例字典改为单例模式，确保内存中同时只能保持一个 Loop。

**重构内容**：
- 修改 `agents_hub/core/orchestration/loop_manager.py`：
  - 将 `self._loops: dict[str, Loop] = {}` 改为 `self._loop: Loop | None = None`
  - 修改 `create_loop()` 方法：创建新 Loop 时，清空旧的 `self._loop`，设置新的
  - 修改 `get_loop()` 方法：检查 `self._loop.loop_id` 是否匹配
  - 修改 `get_loop_with_lazy_load()` 方法：如果 `self._loop` 不存在或不匹配，从文件加载
  - 修改 `delete_loop()` 方法：如果删除的是当前 `self._loop`，设为 `None`
  - 修改 `list_loops()` 方法：保持不变（直接读取文件）
  - **新增** `get_active_loop() -> Loop | None` 方法：返回当前激活的 Loop（`self._loop`），供 API Service 只读查询
- 更新相关测试用例

**设计决策**：
- 参考 `docs/adr/2026-06-23-loop-memory-singleton.md`
- 内存中同时只能保持一个 Loop 实例
- 只有通过 `start_loop` 启动的 Loop 才会加载到内存
- `create_loop` 只创建 Loop 定义并保存到文件，不会加载到内存

**架构约束**：
- 参考 `.scratch/loop-visualization/architecture.md`
- 这是 core 模块内部的重构，不影响 API 层

## Acceptance criteria

- [ ] LoopManager 的 `self._loops` 改为 `self._loop: Loop | None = None`
- [ ] `create_loop()` 创建新 Loop 时，清空旧的 `self._loop`
- [ ] `get_loop()` 检查 `self._loop.loop_id` 是否匹配
- [ ] `get_loop_with_lazy_load()` 支持懒加载
- [ ] `delete_loop()` 删除当前 `self._loop` 时设为 `None`
- [ ] `list_loops()` 保持不变（直接读取文件）
- [ ] **新增** `get_active_loop() -> Loop | None` 方法，返回当前激活的 Loop
- [ ] 所有相关测试用例更新并通过

## Blocked by

None - can start immediately

## 相关文档

- ADR：`docs/adr/2026-06-23-loop-memory-singleton.md`
- Spec：`docs/specs/2026-06-21-loop.md`
- Flow：`docs/flows/loop-lifecycle.md`
