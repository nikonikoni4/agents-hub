# Slice 4: 输出校验和自动重试

**类型**: AFK  
**状态**: Ready for implementation

## Parent

PRD: Agent 循环执行功能（Loop）
文件路径: `docs/temp/loop-feature-prd.md`

## What to build

实现节点输出校验和自动重试机制。这是一个完整的垂直切片，从输出检查到错误提示再到重试控制。

构建以下组件：

1. **基础校验逻辑**：
   - LoopExecutor._validate_schema_fields(output, required_fields) 方法
   - 简单字符串匹配：检查每个 required_field 是否在 output 中（`field in output`）
   - 返回：(is_valid: bool, error_message: str)
   - 错误信息格式：列出所有缺失字段

2. **TERMINATOR 节点特殊校验**：
   - LoopExecutor._validate_terminator_output(output, node) 方法
   - 校验步骤：
     1. 校验业务字段（调用 _validate_schema_fields）
     2. 校验 `<loop_decision>` 标签存在（忽略大小写、空格）
     3. 解析 `<should_continue>` 的值（true/false，忽略大小写、空格）
   - 返回：(is_valid: bool, error_message: str, should_continue: bool | None)
   - 正则表达式：`r'<loop_decision[^>]*>(.*?)</loop_decision>'`（re.DOTALL | re.IGNORECASE）

3. **自动重试机制**：
   - LoopExecutor._execute_node_with_retry(node, input_data, call_id) 方法
   - AgentCall 只创建一次（在调用方创建），通过 call_id 参数传入
   - 最多重试 node.max_retries 次（默认 3）
   - 每次重试时：
     - 发送消息给节点（复用同一个 call_id，消息格式标记重试次数）
     - 等待节点输出（通过 completion_queue）
     - 调用相应的校验方法
     - 如果校验失败，构造错误提示消息作为下一次重试的输入
   - 重试消息格式：`[循环-节点{agent}-第{iteration}轮-重试{retry_count}]`
   - 超过重试次数后，更新 AgentCall 状态为 FAILED，抛出 LoopExecutionError

4. **错误提示格式**：
   - 明确列出缺失的字段
   - 提示节点按照要求重新输出
   - 示例：`"输出不符合要求：缺少以下必需字段：\n- # 执行结果\n- **任务状态**\n\n请重新输出。"`

## Acceptance criteria

- [ ] _validate_schema_fields() 正确检测缺失字段
- [ ] _validate_schema_fields() 所有字段存在时返回 (True, "")
- [ ] _validate_schema_fields() 缺失字段时返回 (False, error_message)，error_message 包含所有缺失字段
- [ ] _validate_terminator_output() 校验业务字段 + `<loop_decision>` 标签
- [ ] _validate_terminator_output() 正确解析 `<should_continue>` 的值（true/false，忽略大小写和空格）
- [ ] _validate_terminator_output() 缺少 `<loop_decision>` 时返回错误
- [ ] _validate_terminator_output() `<should_continue>` 格式错误时返回错误
- [ ] _execute_node_with_retry() 第一次输出正确时立即返回（不重试）
- [ ] _execute_node_with_retry() 输出错误时自动重试（最多 3 次）
- [ ] _execute_node_with_retry() 重试消息复用同一个 call_id
- [ ] _execute_node_with_retry() 重试消息格式包含重试次数标记
- [ ] _execute_node_with_retry() 重试消息包含明确的错误提示
- [ ] _execute_node_with_retry() 超过 3 次重试后，AgentCall 状态更新为 FAILED
- [ ] _execute_node_with_retry() 超过 3 次重试后抛出 LoopExecutionError
- [ ] 单元测试覆盖 _validate_schema_fields() 的所有场景
- [ ] 单元测试覆盖 _validate_terminator_output() 的所有场景（包括 XML 解析）
- [ ] 单元测试覆盖 _execute_node_with_retry() 的重试逻辑

## Blocked by

Slice 3: 循环上下文构造和消息渲染

## Notes

- LoopExecutor 定义在 `agents_hub/core/orchestration/loop_executor.py`
- LoopExecutionError 是新增异常，继承自 AgentsHubError
- XML 解析使用 Python 标准库 `re` 模块，正则表达式忽略大小写和空格
- 重试机制的关键：AgentCall 只创建一次，所有重试消息复用同一个 call_id
- 重试消息保存到群聊历史（由 LoopExecutor 控制保存时机）
- 重试逻辑中的"发送消息"部分在本切片可以用 mock，完整实现在 Slice 6
- 参考现有异常定义：`agents_hub/core/foundation/exceptions.py`
