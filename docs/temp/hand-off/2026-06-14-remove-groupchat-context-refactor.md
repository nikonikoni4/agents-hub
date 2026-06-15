# 移除 GroupChatContext 中间层重构

**时间**：2026-06-14
**分支**：task-33-front-improve
**状态**：🚧 进行中（已完成 30%）

---

## 一、任务目标

移除 GroupChatContext 中间层，简化架构为 `Agent → GroupChatRuntime → State/Repository`，消除透传层级，统一访问路径。

---

## 二、已完成的工作

### 阶段 0：准备工作（✅ 已完成）

- [x] 在 GroupChatRuntime 中新增 3 个查询方法：
  - `get_agent_member_info(agent_name)` - 获取 Agent 会话信息（不自动创建）
  - `get_group_chat_session()` - 获取群聊会话
  - `require_group_chat_session()` - 获取群聊会话（必须存在，否则抛出 StateError）
- [x] 将 `compact_messages()` 方法从 GroupChatContext 迁移到 GroupChatRuntime
- [x] 新增 `save_agent_member_infos()` 方法到 GroupChatRuntime（修复封装破坏）

### 阶段 1：Agent 层改造（✅ 已完成）

- [x] base_agent.py：
  - 构造函数参数从 `group_chat_context: GroupChatContext` 改为 `runtime: GroupChatRuntime`
  - 所有属性访问（agent_token、agent_cwd、context_usage、main_session_id）改为调用 `runtime.get_agent_member_info()`
  - 所有穿透访问 `self.group_chat_context.runtime.` 改为 `self.runtime.`
  - 所有透传方法调用改为直接调用 runtime 方法：
    - `add_message()` → `runtime.add_message()`
    - `update_agent_member_info()` → `runtime.update_agent_member_info_from_result()`
  - 其他访问改为 `runtime.project_path`、`runtime.group_chat_id`
- [x] manager.py：更新构造函数参数从 `group_chat_context` 改为 `runtime`
- [x] worker.py：更新构造函数参数从 `group_chat_context` 改为 `runtime`

---

## 三、未完成的任务

### 优先级 1：阶段 2 - Orchestration 层改造（预估 3h）

**文件**：`agents_hub/core/orchestration/group_chat.py`

- [ ] 2.1 删除 `self.group_chat_context = GroupChatContext(self.runtime)` 行（L74）
- [ ] 2.2 更新所有创建 Agent 的代码，将参数从 `group_chat_context` 改为 `runtime`：
  - L205-210：创建 Manager
  - L222-228：创建 Worker
  - L284-290：`add_member()` 中创建新 Worker
- [ ] 2.3 替换所有 `self.group_chat_context.agent_member_info.get()` 为 `self.runtime.get_agent_member_info()`（3 处）：
  - L311：`_initialize_new_members()` - 检查 manager
  - L320：`_initialize_new_members()` - 检查 workers
  - L652：`_cleanup_agent_queue()` - 获取 docker 配置
- [ ] 2.4 替换所有透传方法调用（6 处）：
  - `self.group_chat_context.add_message()` → `self.runtime.add_message()`
  - `self.group_chat_context.update_agent_member_info()` → `self.runtime.update_agent_member_info_from_result()`
  - 位置：L298/299、L347/348、L490、L568
- [ ] 2.5 替换 `compact_messages` 调用（L409）：
  - `await self.group_chat_context.compact_messages()` → `await self.runtime.compact_messages()`
- [ ] 2.6 修复封装破坏（L300）：
  - `await self.runtime.repository.save_agent_member(...)` → `await self.runtime.save_agent_member_infos()`
- [ ] 2.7 统一所有直接访问 `runtime.state` 的位置为 `runtime.get_agent_member_info()`（8 处）：
  - L261、L448、L694、L758、L929、L943

### 优先级 2：阶段 3 - Context 层清理（预估 1h）

**文件**：
- `agents_hub/core/context/agent_context.py`
- `agents_hub/core/context/group_chat_context.py`（删除）
- `agents_hub/core/context/__init__.py`

- [ ] 3.1 修改 AgentContext 构造函数，从接收 `group_chat_context` 改为接收 `runtime`
- [ ] 3.2 替换 AgentContext 中所有访问（3 处）：
  - L56：`_get_context_state()`
  - L167：`reload_context()`
  - L229/239：`generate_active_agent_calls_section()`
- [ ] 3.3 删除 `group_chat_context.py` 文件
- [ ] 3.4 更新 `__init__.py`，删除 GroupChatContext 导出

### 优先级 3：阶段 4 - MCP 和 API 层调整（预估 1h）

- [ ] 4.1 检查 `agents_hub/mcp/server.py` 是否有 `group_chat.group_chat_context` 访问
- [ ] 4.2 如有，替换为 `group_chat.runtime`

### 优先级 4：阶段 5 - 测试修复（预估 3h）

**需要修复的测试文件**：
- `tests/core/context/test_group_chat_context.py` - 删除或合并到 runtime 测试
- `tests/core/context/test_group_chat_runtime.py` - 调整 FakeRepository（如需）
- `tests/core/agent/test_agent_runtime_injection.py` - Agent 构造参数改为 runtime
- `tests/integration/test_group_chat_members_integration.py` - 群聊创建和成员添加测试
- `tests/integration/test_multi_turn.py` - 多轮交互测试
- `tests/api/services/test_group_chat_service.py` - 服务层测试
- `tests/api/routes/test_group_chat.py` - API 路由测试

### 优先级 5：阶段 6 - 文档和规范更新（预估 1h）

- [ ] 6.1 更新 `agents_hub/core/CLAUDE.md`：
  - 删除所有提到 GroupChatContext 的部分
  - 明确禁止直接访问 `runtime.state`
  - 添加新的访问规范：必须使用 `runtime.get_*()` 查询方法
- [ ] 6.2 更新 `docs/ARCHITECTURE.md`：
  - 移除 GroupChatContext 层的描述
  - 更新 Core 模块的分层图
- [ ] 6.3 更新 `docs/specs/2026-05-31-core-context.md`：
  - 移除 GroupChatContext 的 spec
  - 更新 GroupChatRuntime 的职责描述，包含 compact_messages

### 优先级 6：阶段 7 - 回归测试（预估 1h）

- [ ] 7.1 运行所有测试：
  ```bash
  pytest tests/core/ -v
  pytest tests/integration/ -v
  pytest tests/api/ -v
  ```
- [ ] 7.2 手动端到端测试：
  - 启动后端服务
  - 创建新群聊
  - 添加成员
  - 发送消息
  - 压缩历史
  - 停止/启动/重置 agent
  - 验证前端显示正常

---

## 四、下一步行动

1. **继续阶段 2**：修改 `group_chat.py`，这是工作量最大的部分（约 15 处修改）
2. **运行测试**：完成阶段 2-3 后，运行测试查看哪些地方报错
3. **根据测试结果修复**：修复测试中发现的问题
4. **提交第一批改动**：阶段 0-3 完成后提交一次，便于回滚
5. **继续阶段 4-7**：完成 MCP/API 调整、测试修复、文档更新、回归测试
6. **最终提交**：所有改动完成后，使用计划中的 commit 信息提交

---

## 五、相关文件

| 文件 | 修改状态 | 说明 |
|------|----------|------|
| `agents_hub/core/context/group_chat_runtime.py` | ✅ 已修改 | 新增查询方法、迁移 compact_messages、新增 save_agent_member_infos |
| `agents_hub/core/agent/base_agent.py` | ✅ 已修改 | 构造函数和所有访问改为 runtime |
| `agents_hub/core/agent/manager.py` | ✅ 已修改 | 构造函数参数改为 runtime |
| `agents_hub/core/agent/worker.py` | ✅ 已修改 | 构造函数参数改为 runtime |
| `agents_hub/core/orchestration/group_chat.py` | 📝 待修改 | 需要约 15 处修改 |
| `agents_hub/core/context/agent_context.py` | 📝 待修改 | 构造函数和访问改为 runtime |
| `agents_hub/core/context/group_chat_context.py` | ❌ 待删除 | 整个文件删除 |
| `agents_hub/core/context/__init__.py` | 📝 待修改 | 删除 GroupChatContext 导出 |
| `agents_hub/mcp/server.py` | 📝 待检查 | 检查是否有 group_chat_context 访问 |
| `agents_hub/core/CLAUDE.md` | 📝 待修改 | 更新访问规范 |
| `docs/ARCHITECTURE.md` | 📝 待修改 | 更新分层图 |
| `docs/specs/2026-05-31-core-context.md` | 📝 待修改 | 更新 spec |

---

## 六、决策记录

### 决策 1：选择"移除 GroupChatContext"方案

- **背景**：通过独立 subagent 评估发现 Context 层 90% 都是透传，无实际价值
- **决策**：移除 GroupChatContext 中间层，Agent 直接持有 Runtime
- **原因**：
  1. 简化调用链，提高代码清晰度
  2. 统一访问路径，消除认知负担
  3. 唯一的业务逻辑 `compact_messages` 可以移入 Runtime
  4. 减少透传层级，降低出错风险

### 决策 2：选择"渐进式重构"而非"推倒重来"

- **背景**：Core 模块存在 P0 阻塞性问题（已修复）和架构问题
- **决策**：选择路径 A（渐进式重构），预估 1-2 周
- **原因**：
  1. P0 问题已修复，系统可正常工作
  2. 并发安全问题可以通过加锁解决
  3. 系统处于开发阶段，可以承受重构风险
  4. 渐进式重构可以在修复问题的同时优化架构

---

## 七、注意事项

1. **测试优先**：完成每个阶段后都应该运行测试，不要等到全部完成
2. **分批提交**：建议阶段 0-3 完成后提交一次，便于出问题时回滚
3. **导入检查**：修改后要检查所有文件的 import 语句，确保没有遗漏
4. **类型检查**：可以运行 mypy 发现遗漏的改动
5. **AgentContext 依赖**：AgentContext 也依赖 GroupChatContext，需要一起修改
6. **测试构造函数**：所有创建 Agent 的测试都需要修改构造函数参数
7. **MCP 服务器**：虽然 MCP 通过 group_chat 对象访问，但仍需检查确认
8. **封装破坏**：`group_chat.py:L300` 直接调用 `runtime.repository`，已通过新增 `save_agent_member_infos()` 方法修复

---

## 八、参考文档

- **实施计划**：`D:\数据文档\claude_yunyi\plans\async-foraging-locket.md`
- **架构评估报告**：`docs/generated/context-runtime-architecture-review.md`
- **任务清单**：`docs/task-check-list/2026-06-14-core-module-fix-or-refactor.md`
- **P0 修复提交**：commit `d9ad8b2`（日志级别、清理循环、注册和幂等性）

---

## 九、预估工作量

| 阶段 | 状态 | 预估时间 | 实际耗时 |
|------|------|---------|---------|
| 阶段 0：准备工作 | ✅ 已完成 | 1h | ~1h |
| 阶段 1：Agent 层改造 | ✅ 已完成 | 4h | ~2h |
| 阶段 2：Orchestration 层改造 | 🚧 待执行 | 3h | - |
| 阶段 3：Context 层清理 | ⏸️ 待执行 | 1h | - |
| 阶段 4：MCP 和 API 层调整 | ⏸️ 待执行 | 1h | - |
| 阶段 5：测试修复 | ⏸️ 待执行 | 3h | - |
| 阶段 6：文档和规范更新 | ⏸️ 待执行 | 1h | - |
| 阶段 7：回归测试 | ⏸️ 待执行 | 1h | - |
| **总计** | **30% 完成** | **15h** | **~3h** |

**剩余工作量**：约 12h（预估 1.5 个工作日）
