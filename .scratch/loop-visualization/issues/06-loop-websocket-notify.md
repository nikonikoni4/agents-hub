# Issue 06: WebSocket 通知集成

Status: ready-for-agent
Type: AFK
Blocked by: 03-loop-status-panel
User stories covered: #11 (实时更新)

## What to build

在 LoopExecutor 状态变化时发送 WebSocket 通知，前端自动刷新 Loop 状态。

**后端（依赖注入方案）**：
- 采用**回调注入方案**（与现有 `_notify_manager_loop_ended` 模式一致）
- 修改 `agents_hub/core/orchestration/loop_executor.py`：
  - `LoopExecutor.__init__()` 增加 `on_state_change: Callable[[str], None] | None = None` 参数
  - 在 `_cleanup()` 方法中调用 `self._on_state_change(group_chat_id)`（如果回调存在）
  - 在 `_emergency_stop()` 方法中调用 `self._on_state_change(group_chat_id)`（如果回调存在，包裹在 try/except 中避免阻止清理逻辑）
  - 在 `_handle_node_completion()` 方法中调用 `self._on_state_change(group_chat_id)`（当 current_node_index 变化时）
- 修改 `agents_hub/core/orchestration/group_chat.py`：
  - `create_and_start_loop()` 创建 LoopExecutor 时传入 `on_state_change` 回调
  - 回调实现：调用 `broadcast_group_chat_refresh(group_chat_id)`

**前端**：
- 在 useLoopStatus Hook 中监听 WebSocket RefreshSignal 事件
- 收到事件后自动重新请求 `GET /loops/active` 获取最新状态
- 保持当前选中的 Loop（如果是通过下拉菜单选择的）

**架构约束**：
- 参考 `.scratch/loop-visualization/architecture.md`
- 复用现有的 WebSocket 通知机制（RefreshSignal）
- 采用回调注入方案，避免 LoopExecutor 直接依赖 realtime 模块
- `_emergency_stop()` 中广播调用包裹在 try/except 中，避免阻止清理逻辑

## Acceptance criteria

- [ ] 后端：LoopExecutor 在 `_cleanup()` 时调用广播
- [ ] 后端：LoopExecutor 在 `_emergency_stop()` 时调用广播
- [ ] 后端：LoopExecutor 在 `_handle_node_completion()` 时调用广播
- [ ] 前端：监听 RefreshSignal 自动刷新 Loop 状态
- [ ] 前端：保持当前选中的 Loop（不因刷新而重置）
- [ ] 测试：集成测试通过

## Blocked by

- 03-loop-status-panel（需要前端 Loop 状态管理逻辑）
