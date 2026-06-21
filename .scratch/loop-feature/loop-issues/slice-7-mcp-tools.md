# Slice 7: MCP 工具接口（全部 5 个工具）

**类型**: AFK  
**状态**: Ready for implementation

## Parent

PRD: Agent 循环执行功能（Loop）
文件路径: `docs/temp/loop-feature-prd.md`

## What to build

实现完整的 MCP 工具接口，提供循环的创建、启动、监控、停止、删除功能。这是最后的集成切片，可以端到端验证完整的循环流程。

构建以下组件：

1. **create_loop MCP 工具**：
   - 参数：agent_token、nodes（list[dict]）、max_iterations、initial_task
   - 权限校验：只有 LEADER 角色可调用
   - 参数校验：nodes 格式正确、max_iterations > 0
   - 调用 LoopManager.create_loop()（复用 Slice 1 的校验逻辑）
   - 返回：`{"loop_id": "...", "status": "CREATED"}`

2. **start_loop MCP 工具**：
   - 参数：agent_token、loop_id
   - 权限校验：只有 LEADER 角色可调用
   - 状态校验：Loop 必须是 CREATED 状态
   - 操作流程：
     1. 创建 completion_queue（asyncio.Queue）
     2. 注入队列到参与的 Agent（agent.set_loop_completion_queue）
     3. 设置 Agent 状态为 "in_loop"，设置 current_loop_id
     4. 创建 LoopExecutor（注入 send_message_callback、agent_call_manager、runtime、completion_queue）
     5. 启动 LoopExecutor.run()（asyncio.create_task）
     6. 更新 Loop 状态为 RUNNING
   - 返回：`{"loop_id": "...", "status": "RUNNING"}`

3. **stop_loop MCP 工具**：
   - 参数：agent_token、loop_id
   - 权限校验：只有 LEADER 角色可调用
   - 状态校验：Loop 必须是 RUNNING 状态
   - 操作流程：
     1. 向 completion_queue 发送终止信号：`{"loop_id": loop_id, "is_termination_signal": True}`
     2. 停止参与 Agent 的 CLI（GroupChat.stop_member）
     3. 重启参与 Agent 的 CLI（GroupChat.start_member，清理进程）
     4. 设置 Loop 状态为 PAUSED
     5. 清除队列引用（agent.set_loop_completion_queue(None)）
     6. 恢复 Agent 状态（status="idle"，清除 current_loop_id）
   - 返回：`{"loop_id": "...", "status": "PAUSED"}`

4. **delete_loop MCP 工具**：
   - 参数：agent_token、loop_id
   - 权限校验：只有 LEADER 角色可调用
   - 状态校验：Loop 不能是 RUNNING 状态
   - 调用 LoopManager.delete_loop()
   - 返回：`{"success": true}`

5. **get_loop_status MCP 工具**：
   - 参数：agent_token、loop_id
   - 权限校验：任意 Agent 可调用
   - 查询 LoopManager 获取 Loop 状态
   - 返回：`{"loop_id": "...", "status": "...", "current_iteration": 3, "max_iterations": 10, "current_node": "reviewer", "error": null}`

6. **GroupChat 生命周期管理**：
   - GroupChat 新增 active_loops 字典（loop_id → LoopExecutor）
   - GroupChat 新增 create_and_start_loop()、stop_loop()、cleanup_loop() 方法
   - 提供 send_message_to_agent 作为回调给 LoopExecutor

## Acceptance criteria

- [ ] Manager 可以调用 create_loop 创建循环（返回 loop_id 和 status=CREATED）
- [ ] Worker/User 调用 create_loop 返回权限错误
- [ ] 创建循环时校验失败返回错误（已有 RUNNING 循环、节点校验失败等）
- [ ] Manager 可以调用 start_loop 启动 CREATED 状态的循环
- [ ] start_loop 将参与 Agent 状态设置为 "in_loop"，注入 completion_queue
- [ ] start_loop 创建 LoopExecutor（注入 runtime）并通过 asyncio.create_task 启动
- [ ] start_loop 返回后循环在后台运行（不阻塞 MCP 调用）
- [ ] Manager 可以调用 stop_loop 停止 RUNNING 循环
- [ ] stop_loop 向 completion_queue 发送终止信号（防止 LoopExecutor 阻塞）
- [ ] stop_loop 停止并重启 Agent CLI（清理进程）
- [ ] stop_loop 将循环状态设置为 PAUSED，清理队列引用，恢复 Agent 状态
- [ ] Manager 可以调用 delete_loop 删除非 RUNNING 循环
- [ ] delete_loop 删除 RUNNING 循环返回错误
- [ ] 任意 Agent 可以调用 get_loop_status 查询状态
- [ ] get_loop_status 返回正确的循环状态（包括 current_iteration、current_node、error）
- [ ] 集成测试覆盖端到端流程：create_loop → start_loop → 执行 → stop_loop → delete_loop
- [ ] 集成测试覆盖完整的正常完成流程：create_loop → start_loop → 自动完成（status=COMPLETED）
- [ ] 集成测试覆盖达到最大循环次数：create_loop → start_loop → 自动失败（status=FAILED）

## Blocked by

Slice 6: LoopExecutor 核心循环执行

## Notes

- MCP 工具定义在 `agents_hub/mcp/server.py`
- GroupChat 方法扩展在 `agents_hub/core/orchestration/group_chat.py`
- 权限校验复用现有机制：通过 agent_token 解析出 agent_name，查询 RoleType
- MCP 工具实现遵循现有模式：resolve_token() → load_group_chat() → 执行操作 → 返回结果
- asyncio.create_task 启动 LoopExecutor.run()，确保不阻塞 MCP 调用返回
- stop_loop 的终止信号格式：`{"loop_id": loop_id, "is_termination_signal": True}`
- stop_loop 的 stop_member + start_member 机制复用现有的 Agent CLI 管理
- 参考现有 MCP 工具：`call_agent`、`assign_tasks_to_team`
- 集成测试需要完整的 GroupChat 环境，参考 `tests/core/orchestration/test_group_chat.py`
- 错误返回格式遵循 MCP 规范：`{"success": false, "error": "..."}`
