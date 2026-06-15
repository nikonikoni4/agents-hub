# 移除 GroupChatContext 中间层重构 - 阶段 2-4 完成

**时间**：2026-06-14
**分支**：task-33-front-improve
**状态**：✅ 阶段 2-4 已完成（70% 完成度）

---

## 一、任务目标

移除 Core 层的 GroupChatContext 中间层（透传层），简化架构为 `Agent → GroupChatRuntime → State/Repository`，消除透传层级，统一访问路径。

**重构前**：`Agent → GroupChatContext → GroupChatRuntime → State/Repository`
**重构后**：`Agent → GroupChatRuntime → State/Repository`

---

## 二、已完成的工作

### 阶段 0：准备工作（✅ 已完成，由前一个 agent 完成）
- [x] 在 GroupChatRuntime 新增 3 个查询方法：`get_agent_member_info()`、`get_group_chat_session()`、`require_group_chat_session()`
- [x] 将 `compact_messages()` 从 GroupChatContext 迁移到 GroupChatRuntime
- [x] 新增 `save_agent_member_infos()` 方法修复封装破坏

### 阶段 1：Agent 层改造（✅ 已完成，由前一个 agent 完成）
- [x] base_agent.py：构造函数参数从 `group_chat_context` 改为 `runtime`
- [x] manager.py：更新构造函数参数
- [x] worker.py：更新构造函数参数

### 阶段 2：Orchestration 层改造（✅ 已完成）
- [x] 删除 GroupChatContext import 和实例化（L18, L74）
- [x] 更新 Manager/Worker 构造函数参数（L207, L224, L286）
- [x] 替换透传方法调用（7 处）：
  - `add_message()` → `runtime.add_message()`
  - `update_agent_member_info()` → `runtime.update_agent_member_info_from_result()`
  - `compact_messages()` → `runtime.compact_messages()`
  - `load()` → `runtime.load()`
  - `close()` → `runtime.close()`
- [x] 替换属性访问（3 处）：`agent_member_info.get()` → `runtime.get_agent_member_info()`
- [x] 修复封装破坏（L299-300）：`runtime.repository.save_agent_member()` → `runtime.save_agent_member_infos()`
- [x] 更新注释中的 GroupChatContext 引用

**提交**：5b71b8f, 0b69e17

### 阶段 3：Context 层清理（✅ 已完成）
- [x] 修改 AgentContext 构造函数：`group_chat_context` → `runtime`
- [x] 替换 AgentContext 中所有访问（12 处）：
  - `group_chat_context.agent_member_info.get()` → `runtime.get_agent_member_info()`
  - `group_chat_context.load_compact_history()` → `runtime.load_compact_history()`
  - `group_chat_context.group_chat_session` → `runtime.get_group_chat_session()`
  - `group_chat_context.runtime.*` → `runtime.*`
  - `group_chat_context.group_chat_id` → `runtime.group_chat_id`
  - `group_chat_context.agent_member_info.items()` → `runtime.state.agent_member_infos.items()`
  - `group_chat_context.repository.group_chat_session_path` → `runtime.repository.group_chat_session_path`（只读访问）
- [x] 删除 GroupChatContext 文件（197 行）
- [x] 更新 __init__.py：删除 GroupChatContext 导出

**提交**：c750c26

### 阶段 4：MCP 层适配（✅ 已完成）
- [x] 替换 3 处 add_message 调用：
  - report_progress (L514)
  - complete_task (L679)
  - request_permission (L777)
- [x] `group_chat.group_chat_context.add_message()` → `group_chat.runtime.add_message()`

**提交**：50d9cbb

### 验证和检查（✅ 已完成）
- [x] 语法检查通过：所有文件编译无错误
- [x] import 检查通过：无遗留的 GroupChatContext import
- [x] 引用检查通过：无遗留的 group_chat_context 变量引用
- [x] 注释更新完成：所有文档注释已更新

---

## 三、未完成的任务

### 优先级 1：阶段 5 - 测试修复（预估 6-8h）

**需要修复的测试文件**（7 个）：
- [ ] `tests/core/context/test_group_chat_context.py` - 删除或合并到 runtime 测试
- [ ] `tests/core/context/test_group_chat_runtime.py` - 调整 FakeRepository（如需）
- [ ] `tests/core/agent/test_agent_runtime_injection.py` - Agent 构造参数改为 runtime
- [ ] `tests/integration/test_group_chat_members_integration.py` - 群聊创建和成员添加测试
- [ ] `tests/integration/test_multi_turn.py` - 多轮交互测试
- [ ] `tests/api/services/test_group_chat_service.py` - 服务层测试
- [ ] `tests/api/routes/test_group_chat.py` - API 路由测试

**修复策略**：
1. 先跑一遍现有测试，看基线状态
2. 按优先级修复（单元测试 → 集成测试）
3. 每修好一批测试就提交

**关键改动点**：
- 所有创建 Agent 的测试需要修改构造函数参数：`group_chat_context` → `runtime`
- 测试框架的 mock/fixture 可能需要重构
- FakeRepository 可能需要调整

### 优先级 2：阶段 6 - 文档和规范更新（预估 1h）

- [ ] 更新 `agents_hub/core/CLAUDE.md`：
  - 删除所有提到 GroupChatContext 的部分
  - 明确禁止直接访问 `runtime.state`（除了遍历场景）
  - 添加新的访问规范：必须使用 `runtime.get_*()` 查询方法
- [ ] 更新 `docs/ARCHITECTURE.md`：
  - 移除 GroupChatContext 层的描述
  - 更新 Core 模块的分层图
- [ ] 更新 `docs/specs/2026-05-31-core-context.md`：
  - 移除 GroupChatContext 的 spec
  - 更新 GroupChatRuntime 的职责描述，包含 compact_messages

### 优先级 3：阶段 7 - 回归测试（预估 1-2h）

- [ ] 运行所有测试：
  ```bash
  pytest tests/core/ -v
  pytest tests/integration/ -v
  pytest tests/api/ -v
  ```
- [ ] 手动端到端测试：
  - 启动后端服务
  - 创建新群聊
  - 添加成员
  - 发送消息
  - 压缩历史
  - 停止/启动/重置 agent
  - 验证前端显示正常

---

## 四、下一步行动

1. **运行现有测试**：
   ```bash
   pytest tests/ -v --tb=short
   ```
   查看有多少测试失败，失败原因是什么

2. **优先修复单元测试**：
   - `tests/core/context/` 下的测试
   - `tests/core/agent/` 下的测试
   
3. **修复集成测试**：
   - `tests/integration/` 下的测试
   
4. **修复 API 测试**：
   - `tests/api/` 下的测试

5. **每修好一批测试就提交**，便于回滚

6. **文档更新**：在所有测试通过后更新文档

---

## 五、相关文件

### 核心改动文件

| 文件 | 修改状态 | 改动点 | 说明 |
|------|----------|--------|------|
| `agents_hub/core/orchestration/group_chat.py` | ✅ 已修改 | 18 处 | 删除 GroupChatContext 依赖，替换所有访问 |
| `agents_hub/core/context/agent_context.py` | ✅ 已修改 | 12 处 | 构造函数和所有访问改为 runtime |
| `agents_hub/core/context/group_chat_context.py` | ❌ 已删除 | - | 整个文件删除（197 行） |
| `agents_hub/core/context/__init__.py` | ✅ 已修改 | 2 处 | 删除 GroupChatContext 导出 |
| `agents_hub/mcp/server.py` | ✅ 已修改 | 3 处 | 替换 add_message 调用 |

### 前置改动文件（阶段 0-1）

| 文件 | 修改状态 | 说明 |
|------|----------|------|
| `agents_hub/core/context/group_chat_runtime.py` | ✅ 已修改 | 新增查询方法和 save_agent_member_infos |
| `agents_hub/core/agent/base_agent.py` | ✅ 已修改 | 构造函数参数改为 runtime |
| `agents_hub/core/agent/manager.py` | ✅ 已修改 | 构造函数参数改为 runtime |
| `agents_hub/core/agent/worker.py` | ✅ 已修改 | 构造函数参数改为 runtime |

### 待修改文件（阶段 5-7）

| 文件 | 修改状态 | 说明 |
|------|----------|------|
| `tests/core/context/test_group_chat_context.py` | 📝 待修改 | 可能删除或合并 |
| `tests/core/context/test_group_chat_runtime.py` | 📝 待修改 | 调整 mock |
| `tests/core/agent/test_agent_runtime_injection.py` | 📝 待修改 | 构造参数 |
| `tests/integration/test_group_chat_members_integration.py` | 📝 待修改 | 集成测试 |
| `tests/integration/test_multi_turn.py` | 📝 待修改 | 多轮测试 |
| `tests/api/services/test_group_chat_service.py` | 📝 待修改 | 服务层测试 |
| `tests/api/routes/test_group_chat.py` | 📝 待修改 | API 测试 |
| `agents_hub/core/CLAUDE.md` | 📝 待更新 | 删除 GroupChatContext 引用 |
| `docs/ARCHITECTURE.md` | 📝 待更新 | 更新分层图 |
| `docs/specs/2026-05-31-core-context.md` | 📝 待更新 | 更新 spec |

---

## 六、改动统计

| 指标 | 数量 |
|------|------|
| **总改动点** | 34 处 |
| **修改文件** | 5 个 |
| **删除文件** | 1 个 |
| **删除代码** | 290 行 |
| **提交次数** | 4 次 |

**提交记录**：
```
0b69e17 docs: 修复注释中的 GroupChatContext 引用
50d9cbb refactor(mcp): 阶段 4 - MCP 层适配
c750c26 refactor(core): 阶段 3 - Context 层清理
5b71b8f refactor(core): 阶段 2 - Orchestration 层改造
```

---

## 七、决策记录

### 决策 1：选择"移除 GroupChatContext"方案
- **背景**：通过独立 subagent 评估发现 Context 层 90% 都是透传，无实际价值
- **决策**：移除 GroupChatContext 中间层，Agent 直接持有 Runtime
- **原因**：
  1. 简化调用链，提高代码清晰度
  2. 统一访问路径，消除认知负担
  3. 唯一的业务逻辑 `compact_messages` 可以移入 Runtime
  4. 减少透传层级，降低出错风险

### 决策 2：分阶段提交，而非一次性提交
- **背景**：改动范围大（34 处），一次性提交风险高
- **决策**：按阶段分批提交（阶段 2 → 阶段 3 → 阶段 4）
- **原因**：
  1. 便于回滚：如果某个阶段出问题，可以回滚到上一个阶段
  2. 便于审查：每次提交改动清晰，容易 review
  3. 便于追踪：出问题时可以快速定位到具体阶段

### 决策 3：AgentContext 的 L279 保持 runtime.repository 访问
- **背景**：L279 访问 `runtime.repository.group_chat_session_path`（只读操作）
- **决策**：保持此访问，不添加新的查询方法
- **原因**：
  1. 这是只读操作（读取路径），不违反封装原则
  2. CLAUDE.md 中禁止的是修改操作，不是读取操作
  3. 为了读取一个路径而新增方法，增加接口复杂度

---

## 八、注意事项

### 1. 测试修复的关键点
- **构造函数参数**：所有创建 Agent 的测试都需要修改构造函数参数
- **FakeRepository**：测试框架可能需要调整 mock 或 fixture
- **连锁反应**：改一个测试可能触发其他测试失败，需要逐个排查

### 2. 访问规范
- **禁止**：直接访问 `runtime.state`（除了遍历 `agent_member_infos.items()` 场景）
- **正确**：使用 `runtime.get_agent_member_info(agent_name)` 查询
- **只读访问**：`runtime.repository.xxx_path` 是允许的（读取路径）

### 3. 文档更新
- 必须删除所有文档中的 GroupChatContext 引用
- 架构图需要更新，删除中间层
- spec 需要更新 GroupChatRuntime 的职责描述

### 4. 测试策略
- **先跑基线**：看看有多少测试失败
- **按优先级修复**：单元测试 → 集成测试 → API 测试
- **每批提交**：修好一批就提交，不要等全部修好

### 5. 可能的陷阱
- 测试框架的异步问题：可能需要调整 fixture 的异步处理
- Mock 对象的属性访问：可能需要调整 mock 的 return_value
- 集成测试的环境依赖：可能需要调整 Docker 或数据库配置

---

## 九、参考文档

- **实施计划**：`D:\数据文档\claude_yunyi\plans\kind-dreaming-blossom.md`
- **前一次交接文档**：`docs/temp/hand-off/2026-06-14-remove-groupchat-context-refactor.md`
- **架构评估报告**：`docs/generated/context-runtime-architecture-review.md`
- **任务清单**：`docs/task-check-list/2026-06-14-core-module-fix-or-refactor.md`
- **CLAUDE.md**：`agents_hub/core/CLAUDE.md`（Core 层编码规则）
- **ARCHITECTURE.md**：`docs/ARCHITECTURE.md`（项目架构文档）

---

## 十、预估工作量

| 阶段 | 状态 | 预估时间 | 实际耗时 |
|------|------|---------|---------|
| 阶段 0：准备工作 | ✅ 已完成 | 1h | ~1h |
| 阶段 1：Agent 层改造 | ✅ 已完成 | 4h | ~2h |
| 阶段 2：Orchestration 层改造 | ✅ 已完成 | 3h | ~1.5h |
| 阶段 3：Context 层清理 | ✅ 已完成 | 1h | ~0.5h |
| 阶段 4：MCP 和 API 层调整 | ✅ 已完成 | 1h | ~0.5h |
| 阶段 5：测试修复 | ⏸️ 待执行 | 3h（原估计） | 建议 6-8h |
| 阶段 6：文档和规范更新 | ⏸️ 待执行 | 1h | - |
| 阶段 7：回归测试 | ⏸️ 待执行 | 1h | 建议 1-2h |
| **总计** | **70% 完成** | **15h** | **已耗时 ~5.5h，剩余 9-11h** |

**完成度**：70%（阶段 0-4 完成，阶段 5-7 待执行）
**剩余工作量**：约 9-11 小时（预估 1-1.5 个工作日）
