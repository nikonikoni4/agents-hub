# 测试错误分类报告

> 生成时间: 2026-06-03
> 最后更新: 2026-06-03

## 分类概览

| 类别 | 数量 | 优先级 | 状态 |
|------|------|--------|------|
| RoleType 缺少 LEADER 属性 | 20 | P0 | ✅ 已修复（清除 __pycache__） |
| MCP Server 异步函数未 await | 14 | P0 | ✅ 已修复（async/await + AsyncMock） |
| MockRoleConfig 缺少 description | 4 | P1 | ✅ 已修复（清除 __pycache__） |
| RoleConfig 缺少 name 参数 | 2 | P1 | ✅ 已修复（添加 name 参数） |

---

## 1. RoleType 缺少 LEADER 属性（20 个）✅

**修复方式**: 清除 `__pycache__` 缓存目录（stale bytecode）

**错误**: `AttributeError: type object 'RoleType' has no attribute 'LEADER'`

**涉及文件**:

### tests/api/test_roles_api.py（1 个 FAILED）
- [ ] `test_list_roles_success`

### tests/core/orchestration/test_group_chat.py（3 个 FAILED）
- [ ] `test_start_generates_and_registers_tokens`
- [ ] `test_load_restores_and_registers_tokens`
- [ ] `test_cleanup_unregisters_tokens`

### tests/core/orchestration/test_group_chat_manager_enhanced.py（5 个 FAILED）
- [ ] `test_create_with_auto_id`
- [ ] `test_create_with_custom_id`
- [ ] `test_create_with_custom_name`
- [ ] `test_create_and_list`
- [ ] `test_full_lifecycle`

### tests/core/agent/test_agent_runtime_injection.py（3 个 ERROR）
- [ ] `test_manager_generates_runtime_with_team_workboard`
- [ ] `test_inject_runtime_to_claude_md`
- [ ] `test_inject_runtime_updates_existing_content`

### tests/integration/test_mcp_e2e.py（12 个 ERROR）
- [ ] `test_group_chat_generates_tokens`
- [ ] `test_tokens_registered_in_manager`
- [ ] `test_manager_calls_worker`
- [ ] `test_worker_receives_message`
- [ ] `test_worker_completes_and_responds`
- [ ] `test_manager_checks_call_status`
- [ ] `test_check_nonexistent_call`
- [ ] `test_manager_assigns_tasks`
- [ ] `test_worker_cannot_assign_tasks`
- [ ] `test_update_existing_tasks`
- [ ] `test_manager_archives_task_list`
- [ ] `test_worker_cannot_archive_tasks`
- [ ] `test_complete_mcp_workflow`

**原因**: 测试代码使用了 `RoleType.LEADER`，但 `RoleType` 枚举中没有该成员。需要检查 `RoleType` 定义，确认正确的成员名并更新所有测试。

---

## 2. MCP Server 异步函数未 await（14 个）✅

**修复方式**: 测试方法添加 `@pytest.mark.asyncio` + `async def` + `await`；mock fixture 使用 `AsyncMock` 替代 `MagicMock`；`get_group_chat` 改为 `load_group_chat`

**错误**: `TypeError: argument of type 'coroutine' is not iterable` / `AssertionError: assert <coroutine ...> == ...`

**涉及文件**:

### tests/mcp/test_server.py — TestCallAgent（5 个 FAILED）
- [ ] `test_call_agent_success`
- [ ] `test_call_agent_invalid_token`
- [ ] `test_call_agent_group_chat_not_found`
- [ ] `test_call_agent_agent_not_found`
- [ ] `test_call_agent_notification_type`

### tests/mcp/test_server.py — TestAssignTasksToTeam（3 个 FAILED）
- [ ] `test_assign_tasks_success`
- [ ] `test_assign_tasks_invalid_token`
- [ ] `test_assign_tasks_permission_denied`

### tests/mcp/test_server.py — TestArchiveTaskList（3 个 FAILED）
- [ ] `test_archive_task_list_success`
- [ ] `test_archive_task_list_invalid_token`
- [ ] `test_archive_task_list_permission_denied`

### tests/mcp/test_server.py — TestCheckAgentCall（3 个 FAILED）
- [ ] `test_check_agent_call_success`
- [ ] `test_check_agent_call_invalid_token`
- [ ] `test_check_agent_call_not_found`

**原因**: 测试中调用了 `call_agent()`、`assign_tasks_to_team()`、`archive_task_list()`、`check_agent_call()` 等异步函数但没有 `await`。测试函数需标记 `@pytest.mark.asyncio` 并用 `await` 调用。

---

## 3. MockRoleConfig 缺少 description 属性（4 个）✅

**修复方式**: 清除 `__pycache__` 缓存目录（stale bytecode）

**错误**: `AttributeError: 'MockRoleConfig' object has no attribute 'description'`

**涉及文件**:

### tests/core/agent/test_agent_token_redact.py（4 个 ERROR）
- [ ] `test_redact_single_token_in_output`
- [ ] `test_no_token_in_output_unchanged`
- [ ] `test_redact_multiple_tokens_in_output`
- [ ] `test_redact_token_called_at_exit`

**原因**: `MockRoleConfig` mock 对象没有定义 `description` 属性，而被测代码（agent token redact）访问了该属性。需要在 mock 中补充 `description` 字段。

---

## 4. RoleConfig 缺少 name 参数（2 个）✅

**修复方式**: 在 `claude_config` 和 `codex_config` fixture 中添加 `name` 参数

**错误**: `TypeError: RoleConfig.__init__() missing 1 required positional argument: 'name'`

**涉及文件**:

### tests/integration/test_multi_turn.py（2 个 ERROR）
- [ ] `test_claude_multi_turn`
- [ ] `test_codex_multi_turn`

**原因**: `RoleConfig` 构造函数签名变更，新增了必填的 `name` 参数，但测试代码未更新。需要在测试中传入 `name` 参数。
