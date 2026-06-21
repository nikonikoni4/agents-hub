# Slice 6: LoopExecutor 核心循环执行

**类型**: AFK  
**状态**: Ready for implementation

## Parent

PRD: Agent 循环执行功能（Loop）
文件路径: `docs/temp/loop-feature-prd.md`

## What to build

实现 LoopExecutor 的核心循环执行引擎。这是最复杂的垂直切片，整合了所有前置组件，实现完整的循环调度、校验、退出判断和错误处理。

构建以下组件：

1. **LoopExecutor 构造函数**：
   - 接收参数：loop、send_message_callback、agent_call_manager、completion_queue、runtime、logger
   - runtime 用于保存循环消息到群聊历史（runtime.add_message）
   - 不持有 GroupChat 引用，完全通过回调和组件引用解耦

2. **主循环逻辑 (run)**：
   - 发送初始任务给第一个节点
   - 进入循环：`while self.loop.status == LoopStatus.RUNNING`
   - 从 completion_queue 接收完成通知（带 5 分钟超时）：
     - `await asyncio.wait_for(self.completion_queue.get(), timeout=300)`
   - 超时处理：检查当前节点 Agent 状态
     - 如果 status="error"：调用 _emergency_stop("Agent CLI 执行失败")
     - 否则：调用 _emergency_stop("节点执行超时")
   - 调用 _handle_node_completion(notification) 处理
   - 捕获所有异常，调用 _emergency_stop(error)

3. **发送消息 (_send_to_node)**：
   - 创建 AgentCall（通过 agent_call_manager.create_call）
   - 构造 AgentMessage（使用 MessageType.LOOP_MESSAGE，携带 loop_context、loop_id、loop_iteration 等 metadata）
   - 通过 send_message_callback 发送

4. **处理完成通知 (_handle_node_completion)**：
   - 从 notification 提取 agent_result（AgentResult 对象）
   - 从 agent_result.text 获取输出内容
   - 找到当前节点（根据 agent_result.agent_name）
   - 调用校验逻辑（Slice 4 的方法）
   - 校验成功：
     - 保存消息到群聊历史：`await self.runtime.add_message(agent_result)`
     - 检查退出条件（TERMINATOR 节点且 should_continue=false）
     - 计算下一个节点索引（循环模式）
     - 更新 current_iteration（完成一轮后 +1）
     - 检查是否达到 max_iterations
   - 校验失败：已在 _execute_node_with_retry 中处理，此处接收的是最终失败

5. **退出条件检查 (_check_exit_condition)**：
   - TERMINATOR 节点返回 should_continue=false → 设置 status=COMPLETED
   - current_iteration > max_iterations → 设置 status=FAILED，记录 error_message

6. **异常停止 (_emergency_stop)**：
   - 设置 loop.status = FAILED
   - 记录 loop.error_message
   - 调用 _cleanup()
   - 记录 ERROR 日志

7. **资源清理 (_cleanup)**：
   - 恢复参与 Agent 状态（status="idle"，清除 current_loop_id）
   - 清除 completion_queue 引用（agent.set_loop_completion_queue(None)）
   - 持久化 Loop 最终状态（通过 LoopManager）

## Acceptance criteria

- [ ] LoopExecutor 可以启动并发送初始任务给第一个节点
- [ ] LoopExecutor 接收完成通知后继续下一个节点
- [ ] LoopExecutor 从 notification 提取 agent_result（AgentResult 对象）
- [ ] LoopExecutor 校验成功后保存消息到群聊历史（runtime.add_message）
- [ ] LoopExecutor 等待完成通知时有 5 分钟超时
- [ ] 超时后检查 Agent.status，如果为 "error" 则判定为 CLI 执行失败
- [ ] 超时且 Agent.status 不为 "error" 则判定为节点执行超时
- [ ] 节点按顺序循环执行（Node0 → Node1 → Node0 → ...）
- [ ] 完成一轮循环后 current_iteration 增加 1
- [ ] TERMINATOR 节点返回 should_continue=false 时循环结束（status=COMPLETED）
- [ ] 达到 max_iterations 时循环结束（status=FAILED，error_message="达到最大循环次数"）
- [ ] 执行异常时立即停止循环（status=FAILED，恢复 Agent 状态）
- [ ] 循环结束后自动清理资源（恢复 Agent 状态、清除队列引用、持久化）
- [ ] 发送的循环消息携带正确的 metadata（loop_id、loop_context、loop_iteration）
- [ ] 发送的循环消息使用 MessageType.LOOP_MESSAGE 类型
- [ ] 发送的循环消息通过 send_message_callback 调用
- [ ] 创建的 AgentCall 使用正确的 MessageType（与循环消息类型一致）
- [ ] 单元测试覆盖 _send_to_node() 逻辑
- [ ] 单元测试覆盖 _handle_node_completion() 的所有分支
- [ ] 单元测试覆盖 _check_exit_condition() 的所有情况
- [ ] 单元测试覆盖 _cleanup() 的资源清理逻辑
- [ ] 集成测试覆盖完整循环流程（正常完成、达到最大次数、异常停止）

## Blocked by

- Slice 4: 输出校验和自动重试
- Slice 5: 事件驱动的节点完成通知

## Notes

- LoopExecutor 定义在 `agents_hub/core/orchestration/loop_executor.py`
- send_message_callback 的签名：`async (AgentMessage) -> None`
- runtime 用于保存循环消息：`await self.runtime.add_message(agent_result)`
- 超时检查 Agent 状态通过 `self.runtime.get_agent_member_info(agent_name).status`
- 超时时间固定为 300 秒（5 分钟），使用 `asyncio.wait_for()`
- 异常停止时需要通过 runtime 访问 Agent 状态信息（清理队列引用）
- 持久化通过 LoopManager.update_loop_status() 完成
- 参考现有编排逻辑：`agents_hub/core/orchestration/group_chat.py`
- 日志记录遵循编码规则：关键流程 INFO，异常 ERROR，调试细节 DEBUG
- 集成测试需要 mock agent_bridge（LLM 调用），参考 `tests/core/agent/test_base_agent.py`
