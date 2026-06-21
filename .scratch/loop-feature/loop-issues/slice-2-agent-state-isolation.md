# Slice 2: Agent 状态扩展和循环隔离

**类型**: AFK  
**状态**: Ready for implementation

## Parent

PRD: Agent 循环执行功能（Loop）
文件路径: `docs/temp/loop-feature-prd.md`

## What to build

扩展 Agent 状态机以支持循环隔离机制。这是一个完整的垂直切片，从状态定义到消息过滤再到日志记录。

构建以下组件：

1. **状态扩展**：
   - AgentMemberInfo.status 字段支持新值 "in_loop"（字符串类型，不引入枚举）
   - AgentMemberInfo 新增 current_loop_id 字段（记录当前所在循环 ID）
   - Agent 新增 `set_loop_completion_queue(queue)` 方法（设置/清除完成通知队列引用）

2. **白名单消息过滤**：
   - Agent.run() 新增 `_should_accept_message(msg)` 方法
   - status="in_loop" 状态下的白名单规则：
     - 接收：来自同一循环的消息（`msg.metadata.get("loop_id") == self.current_loop_id`）
     - 接收：来自 Manager 的控制信号（`msg.send_from == config.default_manager_name`）
     - 拒绝：其他所有消息
   - 拒绝的消息记录 WARNING 日志，包含：agent_name、msg.call_id、msg.send_from、拒绝原因

3. **状态恢复**：
   - 循环结束后自动恢复 status="idle"、清除 current_loop_id

## Acceptance criteria

- [ ] AgentMemberInfo 可以设置 status="in_loop" 和 current_loop_id
- [ ] AgentMemberInfo 可以清除 current_loop_id（设为 None）
- [ ] Agent 可以设置 completion_queue 引用
- [ ] Agent 可以清除 completion_queue 引用（设为 None）
- [ ] status="in_loop" 状态下，Agent 拒绝循环外的消息（不处理，记录 WARNING）
- [ ] status="in_loop" 状态下，Agent 接收同一循环的消息（正常处理）
- [ ] status="in_loop" 状态下，Agent 接收 Manager 的消息（正常处理）
- [ ] status="idle"/"busy" 状态下，Agent 接收所有消息（行为不变）
- [ ] 单元测试覆盖 `_should_accept_message()` 的所有分支
- [ ] 单元测试覆盖白名单过滤逻辑（接收/拒绝场景）
- [ ] 集成测试验证拒绝的消息记录 WARNING 日志且不被处理

## Blocked by

Slice 1: 基础数据模型和持久化

## Notes

- AgentMemberInfo 定义在 `agents_hub/core/context/group_chat_session.py`
- AgentMemberInfo.status 是字符串类型，支持值："idle"/"busy"/"stopped"/"error"/"in_loop"
- Agent._should_accept_message() 在 Agent.run() 的消息处理循环开头调用
- 参考现有测试：`tests/core/agent/test_base_agent.py`
- 日志级别遵循编码规则：关键流程用 INFO，拒绝消息用 WARNING
