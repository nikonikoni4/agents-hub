# Code Review Report

**审查范围**: Slice 3 - 循环上下文构造和消息渲染
**审查时间**: 2026-06-20
**变更文件**: 13 个文件，+513 行，-16 行

## 架构上下文

### 相关 ADR
- ADR-0005: 多 Agent 消息架构（点对点路由）- decided
- ADR-0006: 显式群聊发言 - decided
- ADR-0010: Agent 上下文和提示词架构 - decided

### 相关 Spec
- docs/specs/2026-05-31-core-foundation.md: Foundation 层规格
- docs/specs/2026-05-31-core-agent-orchestration.md: Agent 编排规格
- .scratch/loop-feature/PRD.md: Loop 功能 PRD

### 决策覆盖
- 4/6 变更文件有 ADR 关联
- 2 个文件无文档化决策上下文

## 审查结果

Found 9 issues (置信度 ≥ 80):

### Issue 1: foundation 层被注入了循环领域语义
- **类型**: Architecture
- **置信度**: 90
- **位置**: `agents_hub/core/foundation/models.py:22, 85-93`
- **详情**: `MessageType.LOOP_MESSAGE` 和 `LoopNodeType` 被定义在 foundation 层。foundation 层的定位是"零依赖的公共词汇表"，不应承载特定业务功能的语义。
- **依据**: ADR-0010 Agent 上下文和提示词架构，foundation spec "零依赖、通用词汇表" 定位
- **建议**: `LoopNodeType` 应移至 `agents_hub/core/context/group_chat_session.py` 或新建 `agents_hub/core/orchestration/loop_models.py`。`MessageType.LOOP_MESSAGE` 可保留但需在 spec 中明确说明其为消息路由层面的通用标记。

### Issue 2: Agent 基类承载了循环通知职责（违反 SRP）
- **类型**: Architecture
- **置信度**: 85
- **位置**: `agents_hub/core/agent/base_agent.py:88-94, 959-981`
- **详情**: Agent 基类新增了 `_loop_completion_queue` 字段、`set_loop_completion_queue()` 方法和 `_notify_loop_completion()` 方法。Agent 基类是所有 Agent 的公共基底，不应包含循环编排的特定逻辑。当前 Agent 类已有 1093 行。
- **依据**: SRP 原则，Agent 基类职责是消息循环、执行和状态管理
- **建议**: 将 `_notify_loop_completion` 的逻辑提取为独立的回调/Hook，或移至 `Worker` 子类。

### Issue 3: AgentContext 耦合了循环消息的 metadata 约定
- **类型**: Architecture
- **置信度**: 80
- **位置**: `agents_hub/core/context/agent_context.py:202-208`
- **详情**: `build_user_prompt()` 中通过 `msg.metadata.get("loop_context")` 来判断是否使用循环上下文。这要求 context 层了解 orchestration 层定义的 metadata 约定，形成隐式耦合。
- **依据**: 模块间耦合度原则，context 层和 orchestration 层是同级模块
- **建议**: 在共享常量模块中定义 metadata key 常量，或由调用方决定上下文来源。

### Issue 4: LoopExecutor._build_loop_message 中上下文内容重复存储
- **类型**: Architecture
- **置信度**: 80
- **位置**: `agents_hub/core/orchestration/loop_executor.py:40-56`
- **详情**: `loop_context` 同时出现在 `AgentMessage.content` 和 `metadata["loop_context"]` 中，违反 SSOT 原则。
- **依据**: SSOT (Single Source of Truth) 原则
- **建议**: 从 metadata 中移除 `loop_context`，需要时从 `msg.content` 获取。

### Issue 5: render_for_chat() 中 loop_iteration=None 会渲染为字面量 "None"
- **类型**: Best Practices
- **置信度**: 85
- **位置**: `agents_hub/core/foundation/renderer.py:86`
- **详情**: 当 `is_loop_message=True` 且 `loop_iteration=None` 时，f-string 会渲染为 `[循环-节点worker-第None轮]`，这是一个无意义的输出。
- **依据**: 防御性编程原则
- **建议**: 在 `is_loop_message` 分支中对 `loop_iteration` 做校验或提供默认值。

### Issue 6: 缺少 LOOP_MESSAGE 端到端集成测试
- **类型**: Testing
- **置信度**: 85
- **位置**: 缺失
- **详情**: Slice 3 的核心数据流是 `LoopExecutor._build_loop_message` -> `Agent._process_message` -> `AgentContext.build_user_prompt` -> `Agent._notify_loop_completion` -> `LoopExecutor._save_loop_result`。当前测试分别覆盖了各环节的单元测试，但没有一个集成测试验证完整链路。
- **依据**: PRD 测试要求，验收标准
- **建议**: 增加端到端集成测试，模拟完整的循环消息处理流程。

### Issue 7: _notify_loop_completion 缺少多个边界分支测试
- **类型**: Testing
- **置信度**: 80
- **位置**: `tests/core/agent/test_agent_loop_isolation.py`
- **详情**: 缺少以下分支测试：`result is None` 时不应发送通知、`_loop_completion_queue is None` 时不应报错、`msg.metadata` 中缺少 `loop_id` 时不发送通知。
- **依据**: 测试覆盖率要求
- **建议**: 增加 3 个测试用例分别覆盖以上分支。

### Issue 8: MessageType 枚举缺少 LOOP_MESSAGE
- **类型**: Documentation
- **置信度**: 85
- **位置**: `CONTEXT.md:248-249`
- **详情**: `loop_executor.py` 使用了 `MessageType.LOOP_MESSAGE`，但 CONTEXT.md 的 MessageType 枚举定义只列出了 TASK 和 NOTIFICATION。
- **依据**: 文档完整性要求
- **建议**: 在 MessageType 枚举中添加 `LOOP_MESSAGE` 条目。

### Issue 9: 类型注解缺失
- **类型**: Code Quality
- **置信度**: 80
- **位置**: `agents_hub/core/orchestration/loop_executor.py:25, 58`
- **详情**: `LoopExecutor.__init__` 的 `runtime` 参数和 `_save_loop_result` 的 `result` 参数缺少类型注解，影响 IDE 补全和代码可读性。
- **依据**: Python 类型提示最佳实践
- **建议**: 添加 `runtime: GroupChatRuntime | None = None` 和 `result: AgentResult` 类型注解。

## 变更摘要

### 核心变更
1. **MessageType 扩展**: 新增 `LOOP_MESSAGE = "loop_message"` 枚举值
2. **Tag 常量扩展**: 新增 4 个循环相关标签（LOOP_NODE_ROLE、LOOP_OUTPUT_SCHEMA、PREVIOUS_NODE_OUTPUT、LOOP_TERMINATION_CHECK）
3. **render_for_chat() 扩展**: 新增 `is_loop_message` 和 `loop_iteration` 参数，支持循环消息格式
4. **LoopExecutor 新增**: 实现循环上下文构造（`_build_loop_context`、`_build_loop_message`、`_save_loop_result`）
5. **AgentContext 修改**: `build_user_prompt()` 支持 loop_context 替代群聊历史
6. **GroupChat 修改**: `send_message_to_agent()` LOOP_MESSAGE 不自动保存
7. **Agent 修改**: 新增 `_notify_loop_completion()` 方法

### 测试覆盖
- 新增 4 个测试文件，覆盖循环隔离、上下文构造、消息渲染等场景
- 测试覆盖主要路径，但缺少端到端集成测试和边界分支测试

### 文档更新
- CONTEXT.md 已更新循环相关术语
- 缺少 MessageType.LOOP_MESSAGE 的文档定义

## 风险评估

**高风险**:
- foundation 层被注入循环领域语义，影响架构纯净性
- Agent 基类违反 SRP，增加维护复杂度

**中风险**:
- 缺少端到端集成测试，可能遗漏集成问题
- SSOT 违反，可能导致数据不一致

**低风险**:
- 类型注解缺失，影响代码质量
- 文档不完整，影响可维护性

## 建议优先级

1. **P0 (必须修复)**: Issue 1-4（架构问题）
2. **P1 (应该修复)**: Issue 5-7（测试和最佳实践）
3. **P2 (建议修复)**: Issue 8-9（文档和代码质量）
