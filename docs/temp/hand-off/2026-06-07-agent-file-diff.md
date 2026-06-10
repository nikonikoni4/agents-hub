# Agent 文件展示功能 - 设计与计划完成

**时间**：2026-06-07
**分支**：task-3-file-diff
**状态**：✅ 设计和计划已完成

---

## 一、任务目标

当 Agent 完成代码任务后，消息下方显示修改的文件列表，用户可以预览文件内容和查看 diff。

---

## 二、已完成的工作

### 需求澄清（Brainstorming）
- [x] 探索项目上下文（消息模型、MCP Server、前端架构）
- [x] 通过 9 个关键问题澄清需求细节
- [x] 确认技术方案和数据结构
- [x] 明确边界情况处理策略

### 设计文档编写
- [x] 完整的数据结构设计（GroupChatSession 消息格式、AgentResult 扩展）
- [x] 详细的数据流设计（Agent → MCP Server → 前端）
- [x] 后端实现设计（file_snapshot 工具、API 端点）
- [x] 前端实现设计（FileChangesCard 组件、右侧栏）
- [x] 边界情况和技术风险分析
- [x] 分阶段实现计划

### 设计文档审查
- [x] Subagent 审查（一致性 8.5/10，完整性 9/10）
- [x] 补充 3 个澄清问题的说明
- [x] 提交设计文档到 Git

### 实现计划编写
- [x] 10 个任务的详细实现计划
- [x] 每个任务包含完整的 TDD 流程（测试 → 实现 → 验证 → 提交）
- [x] 后端 5 个任务（AgentResult、file_snapshot、MCP tool、持久化、API）
- [x] 前端 5 个任务（类型定义、组件、API 调用、集成、右侧栏）
- [x] 提交实现计划到 Git

---

## 三、关键决策记录

### 决策 1：文件类型支持范围
- **背景**：需要明确支持哪些文件类型
- **决策**：选项 B - 代码文件 + 文档文件（`.py`, `.ts`, `.md`, `.json` 等）
- **原因**：
  - 代码开发场景最常见
  - Office 文件预览复杂度高，成本收益不匹配
  - 可后续扩展

### 决策 2：文件信息收集方式
- **背景**：多个 Agent 可能在同一仓库工作，如何归属文件修改
- **决策**：Agent 传入文件路径列表 + git_diff_range（可选），后端运行 git diff 生成元数据
- **原因**：
  - Agent 最清楚修改了哪些文件
  - 后端生成 diff 保证一致性和准确性
  - git_diff_range 支持多次 commit 的场景
  - 简单可靠，避免复杂的状态跟踪

### 决策 3：数据缓存位置
- **背景**：文件快照存储在前端还是后端
- **决策**：后端缓存（local_data/teams/.../file_snapshots/）
- **原因**：
  - agents-hub 是本地应用，API 延迟极低
  - 数据可靠性优先于性能优化
  - 前端实现简单，代码清晰
  - 支持多端访问（未来）

### 决策 4：模块设计位置
- **背景**：文件快照工具应该放在哪个模块
- **决策**：`agents_hub/core/foundation/file_snapshot.py`，使用无状态函数
- **原因**：
  - foundation 层定位是零依赖的基础工具
  - 无状态函数更易测试和复用
  - 类似 `renderer.py`，都是工具函数集合
  - 不需要维护运行时状态

### 决策 5：前端组件交互
- **背景**：文件预览和 Diff 的交互方式
- **决策**：折叠卡片（默认折叠），一个文件卡片同时支持「预览」和「Diff」按钮
- **原因**：
  - 简洁清晰，一个文件一个卡片
  - 避免重复（不需要发送两个组件）
  - 用户可自由选择预览或 Diff
  - 参考 Claude Code 的 UI 设计

### 决策 6：git_diff_range 默认行为
- **背景**：Agent 不传 git_diff_range 时如何处理
- **决策**：默认使用 `git diff HEAD`（对比工作区与最新提交）
- **原因**：Agent 通常修改工作区，diff 应该反映实际修改

### 决策 7：文件编码处理
- **背景**：如何处理非 UTF-8 编码的文件
- **决策**：只支持 UTF-8，遇到编码错误时跳过并标记 `encoding_error`
- **原因**：
  - 避免引入额外依赖（chardet）
  - 简单可靠
  - 代码文件通常是 UTF-8
  - 失败时不影响其他文件

---

## 四、重要设计原则和用户观点

### 原则 1：简单性优先
- **观点**：功能实现应该简单直接，避免过度设计
- **体现**：
  - 选择无状态函数而非有状态的类
  - 选择后端缓存而非双层缓存
  - 选择只支持 UTF-8 而非自动检测编码
  - 前端先实现纯文本预览，后续再升级代码高亮

### 原则 2：数据可靠性
- **观点**：文件快照是历史记录，必须完整保存
- **体现**：
  - 快照持久化到磁盘，不依赖前端缓存
  - 即使 git diff 失败，仍保存文件内容
  - snapshot_id 包含 call_id 保证唯一性

### 原则 3：职责清晰
- **观点**：Agent 只负责告知修改了什么，后端负责生成详细信息
- **体现**：
  - Agent 只传文件路径列表
  - 后端运行 git diff、解析行数、判断状态
  - 前端只负责展示，不处理业务逻辑

### 原则 4：用户体验
- **观点**：大量文件不应该影响消息渲染性能
- **体现**：
  - 默认折叠状态
  - 按需加载（点击时才请求内容）
  - 文件数量和大小限制（50 个文件，1MB/文件）

---

## 五、未完成的任务

### 优先级 P0：核心功能实现
- [ ] Task 1: 扩展 AgentResult 模型
- [ ] Task 2: 实现文件快照工具模块
- [ ] Task 3: 扩展 complete_task MCP tool
- [ ] Task 4: 修改 GroupChatContext.add_message
- [ ] Task 5: 新增 API 端点获取文件快照
- [ ] Task 6: 前端类型定义扩展
- [ ] Task 7: 实现 FileChangesCard 组件
- [ ] Task 8: 新增 API 调用函数
- [ ] Task 9: 集成到 ChatArea
- [ ] Task 10: 右侧栏预览和 Diff 面板（简化版）

### 优先级 P1：体验优化
- [ ] 集成代码高亮库（react-syntax-highlighter）
- [ ] 集成专业 Diff 渲染库（react-diff-view）
- [ ] 右侧栏 Tab 切换（预览 / Diff）

### 优先级 P2：边界情况和安全
- [ ] 敏感文件过滤（.env、*.key 等）
- [ ] 大文件截断和提示
- [ ] 非 git 仓库降级处理优化
- [ ] 错误提示优化

---

## 六、下一步行动

**推荐执行方式**：使用 `subagent-driven-development` skill

1. **执行实现计划** - 调用 `superpowers:subagent-driven-development`，传入计划文件路径
2. **逐任务执行** - 为每个任务派出新 subagent，任务间审查
3. **功能验证** - 完成后端（Task 1-5）后先验证 API，再进行前端
4. **集成测试** - 完成 Task 10 后进行完整的端到端测试

**替代方式**：使用 `executing-plans` skill 在当前会话批量执行

---

## 七、相关文件

| 文件 | 状态 | 说明 |
|------|------|------|
| `docs/superpowers/specs/2026-06-07-agent-file-diff-design.md` | ✅ 已创建 | 完整设计文档 |
| `docs/superpowers/plans/2026-06-07-agent-file-diff.md` | ✅ 已创建 | 详细实现计划（10 个任务） |
| `agents_hub/agent_bridge/models.py` | 📝 待修改 | AgentResult 扩展 |
| `agents_hub/core/foundation/file_snapshot.py` | 📝 待创建 | 文件快照工具 |
| `agents_hub/mcp/server.py` | 📝 待修改 | complete_task 扩展 |
| `agents_hub/core/context/group_chat_context.py` | 📝 待修改 | add_message 处理新字段 |
| `agents_hub/api/routes/group_chat.py` | 📝 待修改 | 新增快照 API 端点 |
| `frontend/src/shared/types/api-schemas.ts` | 📝 待修改 | 类型定义扩展 |
| `frontend/src/shared/components/FileChangesCard/` | 📝 待创建 | 文件卡片组件 |
| `frontend/src/core/api/groupChatApi.ts` | 📝 待修改 | API 调用函数 |
| `frontend/src/layouts/ChatArea/ChatArea.tsx` | 📝 待修改 | 集成文件卡片 |
| `frontend/src/layouts/RightSidebar/RightSidebar.tsx` | 📝 待修改 | 预览和 Diff 面板 |

---

## 八、注意事项

### 1. 数据流验证
接手实现时，建议按以下顺序验证数据流：
1. AgentResult 字段是否正确传递到 .jsonl
2. MCP tool 是否正确创建快照文件
3. API 端点是否能正确读取快照
4. 前端是否能正确解析 modified_files 字段

### 2. Git 命令执行环境
- `git diff` 需要在正确的 cwd 中执行
- 注意 worktree 路径处理
- 错误处理要完善（非 git 仓库、权限问题等）

### 3. 前端性能
- 大量文件时要测试渲染性能
- 确认懒加载是否生效
- 考虑虚拟滚动（如果文件列表很长）

### 4. 测试覆盖
实现计划中每个任务都包含测试，务必：
- 先写测试再实现（TDD）
- 测试边界情况（空列表、失败场景）
- 集成测试验证完整流程

### 5. 与现有代码的兼容性
- AgentResult 扩展不影响现有逻辑（字段都是可选的）
- API 端点不破坏现有路由
- 前端组件按需渲染（没有 modified_files 就不显示）

---

## 九、参考文档

- **设计文档**：`docs/superpowers/specs/2026-06-07-agent-file-diff-design.md`
  - 完整的数据结构、数据流、边界情况
  - 技术风险和缓解措施
  - 分阶段实现计划

- **实现计划**：`docs/superpowers/plans/2026-06-07-agent-file-diff.md`
  - 10 个任务的详细步骤
  - 完整的测试代码和实现代码
  - TDD 流程和提交说明

- **架构文档**：`docs/ARCHITECTURE.md`
  - 项目整体架构
  - 分层设计原则
  - 数据持久化路径

- **审查报告**：`D:/desktop/软件开发/agents-hub/.claude/worktrees/task-3-file-diff/audit_report.md`
  - Subagent 审查结果
  - 发现的问题和建议

---

## 十、用户偏好和风格

### 代码风格
- **简单性**：优先选择简单方案，避免过度设计
- **DRY 原则**：不重复代码和逻辑
- **YAGNI 原则**：只实现当前需要的功能
- **TDD**：先写测试再实现

### 决策风格
- **快速决策**：明确选项后快速确认，不过度纠结
- **实用主义**：功能可用优先于完美设计
- **迭代优化**：先实现基本功能，后续再优化体验

### 交互风格
- **直接明确**：喜欢简洁的选项式问题
- **关注核心**：重视核心功能，边界情况可后续处理
- **结果导向**：关注能否实现功能，而非技术细节

---

**备注**：本交接文档涵盖了设计和计划阶段的所有工作。设计文档和实现计划已包含完整的技术细节，本文档主要记录原则性问题、关键决策和用户观点。接手 agent 应优先阅读实现计划，按任务顺序执行。
