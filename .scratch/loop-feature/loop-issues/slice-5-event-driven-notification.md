# Slice 5: 事件驱动的节点完成通知

**类型**: AFK  
**状态**: Ready for implementation

## Parent

PRD: Agent 循环执行功能（Loop）
文件路径: `docs/temp/loop-feature-prd.md`

## What to build

实现事件驱动的节点完成通知机制。这是一个完整的垂直切片，从 Agent 完成后发送通知到 LoopExecutor 接收并继续下一步。

构建以下组件：

1. **Agent 发送完成通知**：
   - Agent.run() 在处理完 LOOP_MESSAGE 消息后新增逻辑
   - 检查 msg.metadata.get("loop_id")
   - 如果是循环消息且 self._loop_completion_queue 非空：
     - 构造完成通知字典：`{"loop_id": ..., "agent_result": result, "call_id": msg.call_id}`
     - 通过 `await self._loop_completion_queue.put(notification)` 发送
   - 注意：LOOP_MESSAGE 消息不自动保存到群聊历史（与 NOTIFICATION 的区别）

2. **LoopExecutor 接收通知**：
   - LoopExecutor 持有 completion_queue 引用（通过构造函数注入）
   - LoopExecutor.run() 使用 `await self.completion_queue.get()` 监听
   - 接收到通知后调用 _handle_node_completion(notification)

3. **队列生命周期管理**：
   - Loop 启动时：GroupChat 创建 asyncio.Queue，通过 agent.set_loop_completion_queue(queue) 注入到参与的 Agent
   - Loop 清理时：通过 agent.set_loop_completion_queue(None) 移除队列引用

4. **完成通知格式**：
   ```python
   {
       "loop_id": str,              # 循环 ID
       "agent_result": AgentResult, # 完整的 Agent 执行结果（包含 text、timestamp、platform 等）
       "call_id": str,              # AgentCall ID
   }
   ```

## Acceptance criteria

- [ ] Agent 处理完 LOOP_MESSAGE 消息后发送完成通知
- [ ] 完成通知包含所有必需字段（loop_id、agent_result、call_id）
- [ ] agent_result 是完整的 AgentResult 对象（不仅仅是 output 字符串）
- [ ] Agent 处理完普通消息后不发送通知（行为不变）
- [ ] Agent 的 _loop_completion_queue 为 None 时不发送通知（不报错）
- [ ] LoopExecutor 可以从 completion_queue 接收通知
- [ ] LoopExecutor 接收到通知后可以提取所有字段
- [ ] Loop 清理时自动移除 Agent 的队列引用
- [ ] 单元测试覆盖 Agent 发送通知的逻辑
- [ ] 单元测试覆盖 LoopExecutor 接收通知的逻辑
- [ ] 集成测试验证端到端通知流程（Agent 发送 → LoopExecutor 接收）

## Blocked by

Slice 2: Agent 状态扩展和循环隔离

## Notes

- Agent.run() 约第 941-945 行处理 NOTIFICATION 消息保存，需要在此之前增加 LOOP_MESSAGE 的分支处理
- LOOP_MESSAGE 消息不自动保存（由 LoopExecutor 控制保存时机）
- 完成通知传递完整的 AgentResult 对象，解决"LoopExecutor 如何获取完整结果"的问题
- asyncio.Queue 是 Python 标准库，无需额外依赖
- LoopExecutor._handle_node_completion() 的完整实现在 Slice 6，本切片可以用简单的接收测试
- 依赖 Slice 3 定义的 loop_id metadata（实施时确保 Slice 3 先完成）
- 参考现有的异步队列使用：Agent.message_queue
- 日志记录：Agent 发送通知时用 DEBUG，LoopExecutor 接收通知时用 INFO
