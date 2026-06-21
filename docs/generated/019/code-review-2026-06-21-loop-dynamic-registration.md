# Code Review Report

**审查范围**: Loop 动态注册/注销变更（`agents_hub/core/orchestration/group_chat.py` + 相关 flow/spec 文档）
**审查时间**: 2026-06-21T10:45:00+08:00
**变更文件**:
- `agents_hub/core/orchestration/group_chat.py`（核心变更）
- `docs/flows/loop-lifecycle.md`（时间戳更新）
- `docs/specs/2026-06-21-loop.md`（时间戳更新）

## 架构上下文

### 相关 ADR
- ADR-0005: 多 Agent 消息架构 (accepted) — MessageRouter + 私有队列的点对点路由方案

### 相关 Spec
- docs/specs/2026-06-21-loop.md: Loop 循环执行规格，定义状态机规则和 MCP 工具接口
- docs/specs/2026-05-31-core-agent-orchestration.md: Agent 执行逻辑、GroupChat 编排机制

### 决策覆盖
- 3/3 变更文件有 Spec 关联
- 变更符合 Loop Spec 中"一个群聊同时只能有一个 RUNNING 状态的 Loop"的约束

## 审查结果

Found 4 issues:

### Issue 1: `stop_loop()` 路径未注销 "loop" 系统身份 — 资源泄露

- **类型**: Architecture
- **置信度**: 92
- **位置**: `agents_hub/core/orchestration/group_chat.py:599`
- **详情**: `stop_loop()` 在 line 599 先 `self._loop_tasks.pop(loop_id, None)` 将 task 从字典移除，随后 `await task` (line 603) 触发 `_on_loop_task_done` 回调。但回调中 line 529 的守卫条件 `self._loop_tasks.get(loop_id) is task` 返回 `None`（因为 entry 已被 pop），导致 `unregister("loop")` 永远不会执行。"loop" 身份残留在 MessageRouter 中，形成孤儿队列。同样的问题存在于 `cleanup_loop()` (line 659)。
- **依据**: `_on_loop_task_done` 的守卫逻辑与 `stop_loop`/`cleanup_loop` 的 pop 时序冲突。COMPLETED/FAILED 路径（由 executor 正常结束触发）能正确注销，但 PAUSED 路径（由 `stop_loop` 触发）会泄露。
- **修复建议**: 在 `stop_loop()` 的 `await task` 之后显式调用 `self.message_router.unregister("loop")`，或调整守卫条件不依赖 `_loop_tasks` 字典。

### Issue 2: 硬编码字符串 "loop" 散布在 3 个方法中 — 违反 DRY

- **类型**: Code Quality
- **置信度**: 85
- **位置**: `group_chat.py:485`, `group_chat.py:531`, `group_chat.py:309`
- **详情**: 身份名称 `"loop"` 作为裸字符串出现在 `create_and_start_loop()`、`_on_loop_task_done()` 和 `_register_agents_to_router()` 中。违反 DRY 原则，拼写错误可能导致注册/注销不匹配。应提取为类常量 `_LOOP_SYSTEM_IDENTITY = "loop"`。
- **依据**: CLAUDE.md — DRY（Don't Repeat Yourself）

### Issue 3: 测试 fixture 缺少 `message_router` 属性

- **类型**: Testing
- **置信度**: 95
- **位置**: `tests/core/orchestration/test_group_chat_loop_lifecycle.py`
- **详情**: `_make_group_chat()` 使用 `GroupChat.__new__(GroupChat)` 绕过 `__init__`，未设置 `message_router` 属性。`create_and_start_loop()` line 485 调用 `self.message_router.register("loop", asyncio.Queue())`，缺少 `message_router` 的测试会抛出 `AttributeError`。
- **依据**: 代码变更引入了新的运行时依赖（`message_router.register`），测试 fixture 未同步更新。

### Issue 4: 测试依赖已移除的静态注册行为

- **类型**: Testing
- **置信度**: 80
- **位置**: `tests/core/orchestration/test_group_chat_loop_lifecycle.py` — `test_loop_system_sender_can_deliver_loop_message_through_group_chat_router`
- **详情**: 该测试调用 `_register_agents_to_router()` 后从 "loop" 身份发送消息。旧代码中此方法会静态注册 "loop"，但新代码已移除。测试执行后 "loop" 未注册，`send_message` 会抛出 `AgentNotFoundError`。
- **依据**: 变更移除了 `_register_agents_to_router()` 中对 "loop" 的静态注册，但测试未同步适配。

## 变更摘要

本次变更将 "loop" 系统身份从静态注册（`_register_agents_to_router()` 中注册）改为动态注册/注销：
- **注册**: `create_and_start_loop()` 启动循环时注册
- **注销**: `_on_loop_task_done()` 回调中注销

设计意图合理（避免 Loop 未运行时占用资源），但实现存在一个关键 Bug：`stop_loop()` 路径因 pop 时序问题导致注销逻辑被跳过。文档变更仅为时间戳更新，无实质内容变化。
