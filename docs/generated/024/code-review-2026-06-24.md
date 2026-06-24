# Code Review Report

**审查范围**: 7e05336 - refactor: 将首响检测逻辑从 agent 层移到 agent_bridge 层
**审查时间**: 2026-06-24 22:30:00
**变更文件**:
- agents_hub/agent_bridge/__init__.py
- agents_hub/agent_bridge/bridge.py
- agents_hub/agent_bridge/models.py
- agents_hub/core/agent/base_agent.py

## 架构上下文

### 相关 ADR
- ADR-0006: 群聊发言：从隐式自动写入改为显式工具调用 (decided) - Agent 的 LLM text 输出默认不进入群聊历史，公开群聊发言必须通过 report_progress
- ADR-0008: Realtime 边界决策 (decided) - MCP 不应该依赖 API，core 不应该承担前端实时通知职责

### 相关 Spec
- agent-bridge spec: agent_bridge 是纯执行层模块，负责封装多平台 CLI 调用差异，不负责业务逻辑
- core-agent-orchestration spec: Agent 的 LLM text 输出默认不进入群聊历史，公开群聊发言必须通过 report_progress

### 决策覆盖
- 4/4 变更文件有 ADR 或 Spec 关联
- 核心矛盾：重构将业务逻辑（首句检测）从 agent 层下移到 agent_bridge 层，进一步违反了 agent_bridge 纯执行层边界

## 审查结果

Found 12 issues:

### Issue 1: AgentEventType.FIRST_RESPONSE 枚举值不存在（致命缺陷）
- **类型**: Testing / Bug
- **置信度**: 100
- **位置**: agents_hub/agent_bridge/bridge.py:376
- **详情**: `bridge.py` 中 `execute_with_first_response()` 引用了 `AgentEventType.FIRST_RESPONSE`，但 `models.py` 的 `AgentEventType` 枚举从未定义该值。运行时，当 `execute_stream()` 产出非 `TEXT_DELTA` 事件时，Python 执行 `elif event.type == AgentEventType.FIRST_RESPONSE` 会抛出 `AttributeError`。该方法在任何包含非文本事件的流中都会崩溃。
- **依据**: Python 枚举类型访问未定义属性会抛出 AttributeError

### Issue 2: 三个 Parser 均不产出 FIRST_RESPONSE 事件，首响检测为死代码（致命缺陷）
- **类型**: Testing / Bug
- **置信度**: 100
- **位置**: agents_hub/agent_bridge/parsers/claude.py, codex.py, opencode.py
- **详情**: 检查了 ClaudeParser、CodexParser、OpenCodeParser 的全部解析逻辑，没有任何一个 parser 会生成 `AgentEventType.FIRST_RESPONSE` 事件。即使修复了枚举定义，该事件也永远不会被产出，`first_response_detected` 永远为 `False`，`first_text` 永远为 `""`。首响检测功能是死代码，完全无法工作。
- **依据**: 代码审查确认所有 parser 均未产出 FIRST_RESPONSE 事件

### Issue 3: Agent 直接写入群聊历史，违反 ADR 0006 和 core-agent-orchestration Spec
- **类型**: Architecture
- **置信度**: 90
- **位置**: agents_hub/core/agent/base_agent.py:260-276
- **详情**: `Agent.execute_with_first_response()` 将首句 LLM 输出直接通过 `runtime.add_message()` 写入群聊历史。ADR 0006 明确决策"Agent 的普通 LLM text 输出默认不进入群聊历史。公开群聊发言必须通过 report_progress"。此处"首句响应"是 LLM 的 raw text_delta 拼接结果，不是通过 `report_progress` MCP 工具显式声明的公开内容。
- **依据**: ADR 0006 决策原因；core-agent-orchestration spec "显式公开与闭环规则"

### Issue 4: AgentBridge 职责越界，违反 agent-bridge Spec
- **类型**: Architecture
- **置信度**: 90
- **位置**: agents_hub/agent_bridge/bridge.py:323-414
- **详情**: agent-bridge Spec 定义 agent_bridge 为"纯执行层模块"，不负责业务逻辑。新增的 `execute_with_first_response()` 在执行层引入了"首句语义"这一业务概念——它知道什么是"first response"，知道需要缓冲文本直到检测到 `FIRST_RESPONSE` 事件，知道如何组装 `FirstResponseResult`。这些都是应用层关注点，不属于"封装 CLI 差异"的范畴。
- **依据**: agent-bridge spec Scope 定义（"不负责：业务逻辑"）

### Issue 5: Spec 未同步更新 - agent-bridge spec
- **类型**: Documentation
- **置信度**: 90
- **位置**: docs/specs/2026-05-23-agent-bridge.md
- **详情**: agent-bridge spec 的事件类型表缺少 `FIRST_RESPONSE`，接口表缺少 `execute_with_first_response()`，key_function 标签缺少新方法，缺少 `FirstResponseResult` 数据结构定义。代码已合入但 spec 未更新，后续维护者无法从 spec 了解完整接口契约。
- **依据**: spec 作为技术契约文档，应随代码变更同步更新

### Issue 6: execute_with_first_response() 无任何测试
- **类型**: Testing
- **置信度**: 90
- **位置**: 无对应测试文件
- **详情**: `AgentBridge` 的新方法没有任何测试。根据 testing.md 的规则（"核心业务逻辑必须真实测试"），以下关键路径完全未覆盖：正常流式执行、纯工具调用、空流、多段 TEXT_DELTA 拼接正确性、TURN_COMPLETE 中 usage 提取、session_id 回退逻辑。
- **依据**: docs/coding-rules/testing.md - 核心业务逻辑必须真实测试

### Issue 7: FirstResponseResult 数据类无测试
- **类型**: Testing
- **置信度**: 90
- **位置**: 无对应测试文件
- **详情**: `FirstResponseResult` 是新的公共数据类型（已通过 `__init__.py` 导出），但没有测试验证其构造、字段赋值、以及 `first_text` 为空字符串时的行为。
- **依据**: docs/coding-rules/testing.md - 核心业务逻辑必须真实测试

### Issue 8: Codex 回退路径无测试
- **类型**: Testing
- **置信度**: 90
- **位置**: agents_hub/agent_bridge/bridge.py:353-358
- **详情**: `execute_with_first_response()` 中有一条 Codex 回退路径，条件是 `config.platform == AgentPlatform.CODEX and not session_id`，返回值是 `FirstResponseResult(first_text="", result=result)`。该路径的条件和返回值均无测试覆盖。
- **依据**: docs/coding-rules/testing.md - 关键路径必须有集成测试

### Issue 9: Docker 模式未实现回退，docstring 与实际行为不符
- **类型**: Best Practices / Bug
- **置信度**: 85
- **位置**: agents_hub/agent_bridge/bridge.py:340-353
- **详情**: docstring 写道"Docker 模式不支持流式输出，将回退到 execute() 方法"，但实际代码只对 Codex 无 session 做了回退。`execute_with_first_response()` 的签名没有 `use_docker` 参数，当 Docker 模式的 Claude agent 调用该方法时，会走 `execute_stream()` 路径，静默绕过 Docker executor。
- **依据**: docstring 与代码行为不一致；Docker 隔离设计意图被违背

### Issue 10: bridge.py docstring 与实际代码逻辑不符
- **类型**: Documentation / Code Comments
- **置信度**: 85
- **位置**: agents_hub/agent_bridge/bridge.py:340 vs 353
- **详情**: docstring 声称"Docker 模式回退"，但实际代码的回退条件是"Codex 首次调用（无 session_id）"。注释描述的行为与代码实际行为存在偏差，会导致维护者按错误的心智模型理解代码。
- **依据**: 代码注释应准确描述代码行为

### Issue 11: base_agent.py 与 bridge.py 重复的回退逻辑，注释指向不一致
- **类型**: Documentation / Code Comments
- **置信度**: 85
- **位置**: agents_hub/core/agent/base_agent.py:230-238 vs agents_hub/agent_bridge/bridge.py:352-353
- **详情**: 两处注释文字完全相同（"Docker 模式不支持流式输出，回退到 execute()"），但对应的代码条件完全不同。base_agent.py 检查 `use_docker`，bridge.py 检查的是 Codex 首次调用。同一个注释描述两种不同行为，后续维护者极易混淆。
- **依据**: 代码注释一致性要求

### Issue 12: core-agent-orchestration spec "与 agent_bridge 的协作"描述过时
- **类型**: Documentation
- **置信度**: 85
- **位置**: docs/specs/2026-05-31-core-agent-orchestration.md:258-260
- **详情**: 该章节写"Agent.execute() 和 Agent.btw_execute() 委托给 agent_bridge"，但现在 MAIN 会话走的是 `Agent.execute_with_first_response()` 而非 `Agent.execute()`。描述未反映首响机制引入后的执行路径变化。
- **依据**: spec 应准确反映代码实际行为

## 变更摘要

本次变更是将首响检测逻辑从 agent 层移到 agent_bridge 层的重构。新增 `FirstResponseResult` 数据类和 `AgentBridge.execute_with_first_response()` 方法，简化了 `base_agent.py` 的实现。涉及 4 个文件，+141/-73 行。

**核心风险**：
1. **致命缺陷**：`AgentEventType.FIRST_RESPONSE` 枚举值未定义，运行时会崩溃；三个 Parser 均不产出该事件，首响检测为死代码
2. **架构违规**：重构将业务逻辑（首句检测）下移到 agent_bridge 纯执行层，进一步违反了 agent_bridge spec 边界
3. **ADR 违规**：Agent 直接写入群聊历史绕过了 report_progress 显式发言机制
4. **测试缺失**：新方法和新数据类型零测试覆盖
5. **文档未同步**：两个 spec 文档均未更新
