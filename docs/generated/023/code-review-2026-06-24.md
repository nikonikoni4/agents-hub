# Code Review Report

**审查范围**: 3a631cc - feat: 实现 execute_with_first_response() 方法支持群聊首响
**审查时间**: 2026-06-24 21:44:14
**变更文件**:
- agents_hub/agent_bridge/models.py
- agents_hub/agent_bridge/parsers/claude.py
- agents_hub/agent_bridge/parsers/codex.py
- agents_hub/core/agent/base_agent.py
- tests/agent_bridge/parsers/test_codex_parser_concurrency.py

## 架构上下文

### 相关 ADR
- ADR-0002: Agent Bridge 输出模式与 session_id 策略决策 (decided)
- ADR-0006: 群聊发言：从隐式自动写入改为显式工具调用 (decided)
- ADR-0008: Realtime 边界决策 (decided)

### 相关 Spec
- docs/specs/2026-05-23-agent-bridge.md: agent_bridge 模块规格（纯执行层，不负责业务逻辑）
- docs/specs/2026-05-31-core-agent-orchestration.md: Core Agent & Orchestration 层规格（显式公开与闭环规则）

### 决策覆盖
- 5/5 变更文件有 ADR 或 Spec 关联
- 核心矛盾：agent_bridge 是纯执行层，不应感知群聊语义；core/agent 不应自动将 LLM 输出写入群聊历史

## 审查结果

Found 8 issues:

### Issue 1: execute_with_first_response() 违反"LLM 输出默认不进入群聊历史"原则
- **类型**: Architecture
- **置信度**: 90
- **位置**: agents_hub/core/agent/base_agent.py:275-291
- **详情**: core-agent-orchestration spec 明确规定"Agent 的 LLM text 输出默认不进入群聊历史"，"公开群聊发言必须通过 report_progress"。ADR 0006 的动机就是解决"Agent 的中间思考过程污染群聊历史"的问题。`execute_with_first_response()` 在检测到 FIRST_RESPONSE 后立即调用 `runtime.add_message(first_result)`，将 LLM 的第一段 text 输出自动、隐式地写入群聊历史，与 ADR 0006 的核心原则直接矛盾。
- **依据**: core-agent-orchestration spec "显式公开与闭环规则"；ADR 0006 决策原因

### Issue 2: Claude parser 缺少 FIRST_RESPONSE 事件的单元测试
- **类型**: Testing
- **置信度**: 90
- **位置**: tests/utils/agent_bridge/parsers/test_claude_parser.py
- **详情**: `test_parse_text_block_stop_returns_none` 测试了"无文本增量时 content_block_stop 返回 None"，但没有任何测试覆盖"有文本增量后 content_block_stop 生成 FIRST_RESPONSE"的核心路径。缺失场景：text_delta 到达后再收到 content_block_stop -> 应产出 FIRST_RESPONSE 事件；连续两次 text block 的行为验证。
- **依据**: docs/coding-rules/testing.md - 核心业务逻辑必须真实测试

### Issue 3: Codex parser 缺少 FIRST_RESPONSE 事件的单元测试
- **类型**: Testing
- **置信度**: 90
- **位置**: tests/utils/agent_bridge/parsers/test_codex_parser.py
- **详情**: `test_parse_agent_message` 只断言了 TEXT_DELTA 事件，完全没有验证 FIRST_RESPONSE 事件被缓存并在下次调用时返回。缺失场景：agent_message 事件解析后第二次 `parse_event()` 调用返回 FIRST_RESPONSE；FIRST_RESPONSE 事件的 session_id 与 TEXT_DELTA 一致。
- **依据**: docs/coding-rules/testing.md - 核心业务逻辑必须真实测试

### Issue 4: execute_with_first_response() 完全没有测试
- **类型**: Testing
- **置信度**: 90
- **位置**: 无对应测试文件
- **详情**: `base_agent.py` 新增了 `execute_with_first_response()` 方法，包含复杂的流式事件处理逻辑（文本缓冲、首句发送、Docker 回退、usage 提取），但整个 `tests/` 目录中没有任何针对此方法的测试。缺失场景：Docker 模式回退、正常流式执行、纯工具调用（无文本）、TURN_COMPLETE 事件正确提取 usage、`runtime.add_message()` 在首句完成时被正确调用。
- **依据**: docs/coding-rules/testing.md - 关键路径必须有集成测试

### Issue 5: 核心业务逻辑 add_message() 无集成测试（testing.md 规则违规）
- **类型**: Testing
- **置信度**: 90
- **位置**: agents_hub/core/agent/base_agent.py:290
- **详情**: `execute_with_first_response()` 内部调用 `runtime.add_message()` 写入群聊历史，这是核心业务逻辑。按 testing.md 规则应有集成测试验证首句确实写入了群聊历史，而非仅 mock 验证调用发生。
- **依据**: docs/coding-rules/testing.md - "核心业务逻辑必须真实测试"、"关键路径必须有集成测试"

### Issue 6: agent-bridge spec 事件类型表缺少 FIRST_RESPONSE
- **类型**: Documentation
- **置信度**: 90
- **位置**: docs/specs/2026-05-23-agent-bridge.md:115-124
- **详情**: 事件类型（AgentEventType）表列出了 INIT、TEXT_DELTA、TOOL_USE、TURN_COMPLETE、RESULT 五种类型，缺少新增的 `FIRST_RESPONSE`。spec 作为技术契约文档，应随代码变更同步更新。
- **依据**: agent-bridge spec 是 agent_bridge 模块的正式技术契约

### Issue 7: core-agent-orchestration spec 的 key_function 缺少 execute_with_first_response
- **类型**: Documentation
- **置信度**: 90
- **位置**: docs/specs/2026-05-31-core-agent-orchestration.md:72-84
- **详情**: `key_function` 标签列出了 `base_agent.Agent.execute:178` 和 `base_agent.Agent.btw_execute:209`，但未包含新增的 `base_agent.Agent.execute_with_first_response:211`。该方法是 MAIN 会话的实际执行入口（`_process_message` 已改为调用此方法而非 `execute`），是理解 Agent 执行链路的关键节点。
- **依据**: key_function 标签用于自动同步函数行号，是 spec 的核心索引

### Issue 8: core-agent-orchestration spec 对外接口表缺少 execute_with_first_response
- **类型**: Documentation
- **置信度**: 90
- **位置**: docs/specs/2026-05-31-core-agent-orchestration.md:86-96
- **详情**: 对外接口表只列出了 `Agent.execute()` 和 `Agent.btw_execute()`。新增的 `execute_with_first_response()` 方法未登记，但它是 MAIN 会话的实际调用入口。当前 spec 声明 "Agent.execute(prompt, session_id) | 执行 MAIN 会话" 与代码实际行为不符。
- **依据**: spec 中的接口表是理解 Agent 对外能力的权威参考

## 变更摘要

本次变更为群聊场景添加"首响"能力：新增 `FIRST_RESPONSE` 事件类型，修改 Claude/Codex parser 生成该事件，在 `base_agent.py` 中实现 `execute_with_first_response()` 方法，使前端能更快看到 Agent 的第一条响应。涉及 5 个文件，+179/-13 行。

核心风险：该实现违反了 agent_bridge 纯执行层边界和"LLM 输出默认不进入群聊历史"的架构原则，且缺乏充分的测试覆盖和文档同步。
