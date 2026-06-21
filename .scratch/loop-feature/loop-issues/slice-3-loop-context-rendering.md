# Slice 3: 循环上下文构造和消息渲染

**类型**: AFK  
**状态**: Ready for implementation

## Parent

PRD: Agent 循环执行功能（Loop）
文件路径: `docs/temp/loop-feature-prd.md`

## What to build

实现循环专用上下文构造和消息渲染机制。这是一个完整的垂直切片，从上下文构造到 metadata 注入再到群聊历史可见。

构建以下组件：

1. **MessageType 扩展**：
   - 新增 MessageType.LOOP_MESSAGE（循环内部消息，不自动保存）
   - 区别于 NOTIFICATION（自动保存）和 TASK（需要响应）

2. **循环上下文构造**：
2. **循环上下文构造**：
   - LoopExecutor._build_loop_context(node, previous_output) 方法
   - 构造内容包含：
     - `<LOOP_NODE_ROLE>`：节点职责描述（node.node_prompt）
     - `<LOOP_OUTPUT_SCHEMA>`：输出格式要求（node.output_schema_prompt）
     - `<PREVIOUS_NODE_OUTPUT>`：上一个节点的输出
     - `<LOOP_TERMINATION_CHECK>`：TERMINATOR 节点额外附加退出判断提示
   - 完全隔离群聊历史（不包含任何群聊上下文）

3. **消息 metadata 注入**：
   - 循环消息使用 MessageType.LOOP_MESSAGE
   - 携带 metadata：
     - `loop_id`：循环 ID
     - `loop_context`：循环专用上下文（完整字符串）
     - `is_loop_message`：True（标记为循环消息）
     - `loop_iteration`：当前循环轮次

4. **Agent 上下文切换**：
4. **Agent 上下文切换**：
   - Agent.run() 检查 `msg.metadata.get("loop_context")`
   - 如果存在：使用 loop_context 替代 agent_context.get_context()
   - 如果不存在：使用原有的 agent_context.get_context()

5. **消息渲染扩展**：
   - render_for_chat() 新增可选参数：is_loop_message=False、loop_iteration=None
   - 循环消息格式：`[循环-节点{send_from}-第{iteration}轮] @{send_to} {content}`
   - 普通消息格式不变：`@{send_to} {content}`
   - 向后兼容：不传新参数时行为不变

6. **XML 标签常量**：
   - 新增 Tag.LOOP_NODE_ROLE、Tag.LOOP_OUTPUT_SCHEMA、Tag.PREVIOUS_NODE_OUTPUT、Tag.LOOP_TERMINATION_CHECK

## Acceptance criteria

- [ ] MessageType.LOOP_MESSAGE 枚举值已定义
- [ ] Agent.run() 处理 LOOP_MESSAGE 消息：不自动保存，只发送完成通知
- [ ] LoopExecutor._build_loop_context() 返回完整的循环上下文字符串
- [ ] NORMAL 节点的上下文包含：职责、输出格式、上一节点输出
- [ ] TERMINATOR 节点的上下文额外包含退出判断提示（`<LOOP_TERMINATION_CHECK>`）
- [ ] 循环消息使用 MessageType.LOOP_MESSAGE 类型
- [ ] 循环消息携带完整的 metadata（loop_id、loop_context、is_loop_message、loop_iteration）
- [ ] Agent 接收循环消息时使用 loop_context（不调用 agent_context.get_context()）
- [ ] Agent 接收普通消息时使用群聊上下文（行为不变）
- [ ] render_for_chat() 支持新参数 is_loop_message 和 loop_iteration（默认值为 False 和 None）
- [ ] render_for_chat() 渲染循环消息格式正确（包含循环标记和轮次）
- [ ] render_for_chat() 渲染普通消息格式不变（向后兼容）
- [ ] Agent.run() 处理 LOOP_MESSAGE 后不自动保存（与 NOTIFICATION 的区别）
- [ ] LoopExecutor 保存循环消息时调用 runtime.add_message()（控制权在 LoopExecutor）
- [ ] 单元测试覆盖 _build_loop_context() 的所有场景（NORMAL/TERMINATOR 节点）
- [ ] 单元测试覆盖 render_for_chat() 的循环/普通消息渲染
- [ ] 集成测试验证循环消息保存到群聊历史时格式正确

## Blocked by

Slice 2: Agent 状态扩展和循环隔离

## Notes

- MessageType 定义在 `agents_hub/core/foundation/message.py`
- render_for_chat() 定义在 `agents_hub/core/foundation/renderer.py`
- Tag 常量定义在 `agents_hub/core/foundation/renderer.py`
- Agent.run() 约第 941-945 行处理 NOTIFICATION 消息保存，需要在此之前增加 LOOP_MESSAGE 的分支处理
- render_for_chat() 新增参数向后兼容：现有调用方不传新参数，行为不变
- 上下文构造逻辑在 LoopExecutor 中，但本切片可以先实现纯函数测试
- 参考现有测试：`tests/core/foundation/test_renderer.py`
