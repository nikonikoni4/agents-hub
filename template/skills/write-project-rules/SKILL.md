---
name: write-project-rules
description: 基于现有架构创建或审查编码规则文档（CLAUDE.md）。用于两种场景：(1) 审查现有规则 - 检查是否符合要求（无教学性内容、有明确约束、无重复内容、符合架构）；(2) 创建新规则 - 依据当前架构和现有代码，预测 AI 可能的错误行为，选择最佳实践并编写规则。触发词：审查规则、检查 CLAUDE.md、创建规则、写规则、为 X 创建 CLAUDE.md、规则文档。
---

# Write Project Rules

基于现有架构创建或审查编码规则文档（CLAUDE.md）。

## 使用场景

### 场景 1：审查现有规则
- 用户："审查 frontend/CLAUDE.md"
- 用户："检查规则是否符合要求"

### 场景 2：创建新规则
- 用户："为 backend/ 创建规则"
- 用户："写一个 core/ 的 规则"

---

## 前提检查

创建模式必须满足（否则提示用户）：
- 是否有 `docs/ARCHITECTURE.md`？
- 或者是否有现有代码可参考？

如果都没有：
→ 提示："需要先确定架构，建议先阅读或创建 docs/ARCHITECTURE.md"

---

## 模式判断

```
if 用户提供了现有规则文件路径：
  → 进入审查模式
else：
  → 进入创建模式
```

---

## 审查模式

### 1. 运行行数检查脚本

```bash
python scripts/check_line_count.py <project-root>
```

硬性指标：所有 CLAUDE.md 和 docs/coding-rules/ 下的 md 文档 ≤ 200 行

### 2. 读取文件

- 读取目标 CLAUDE.md
- 读取上级 CLAUDE.md（如果有）
- 读取 docs/ARCHITECTURE.md

### 3. 执行审查

使用 `references/audit-checklist.md` 中的审查清单：

- **结构审查**：行数、元数据、上级链接
- **内容审查**：教学性内容、约束、示例、决策表
- **重复内容审查**：与上级、与 ARCHITECTURE.md
- **架构一致性审查**：符合架构约束、符合现有代码风格

### 4. 输出审查报告

```markdown
## 审查报告：<文件路径>

### ✅ 符合要求
- <列出符合要求的部分>

### ❌ 需要修改
1. <问题描述>（第 X-Y 行）
   - 建议：<修改建议>

### 📊 统计
- 当前行数：X 行
- 建议行数：≤ 200 行
- 需要删除：约 Y 行
```

### 5. 询问是否修改

```
发现 X 处需要修改的问题，是否立即修改？
- 是 → 执行修改
- 否 → 结束
```

---

## 创建模式

### 0. 创建任务清单

**首先使用 TaskCreate 创建任务清单**，将后续步骤分解为可追踪的任务：

```markdown
示例任务清单：
1. 理解架构（读取 ARCHITECTURE.md、现有代码）
2. 收集错误记录（仓库 bugs + 用户 AI 犯错记录）
3. 并行分析（历史错误分析 + 架构约束预测）
4. 综合分析结果，输出规则方案
5. 用户确认规则
6. 创建规则文档
7. 审查规则
8. 写入文件
9. 最终验证
```

### 1. 理解架构

**读取**：
- docs/ARCHITECTURE.md
- 上级 CLAUDE.md（如果有）
- 现有代码（如果有）

**提取架构约束清单**：

```markdown
## 架构约束清单（从 ARCHITECTURE.md 提取）

### 依赖方向
- components → hooks → store → core

### 模块隔离
- features 之间禁止直接依赖

### 数据流向
- 单向数据流（store → components）

### 职责分离
- 组件只负责 UI，业务逻辑在 hooks
```

### 1.5 收集错误记录（增强规则精准度）

**目的**：通过分析 AI 历史犯错记录，让规则更具针对性

**数据来源**：

1. **仓库 Bug 记录**（默认路径：`docs/history-bugs/`）
   - 读取 `index.md` 获取 bug 列表
   - 扫描所有 `.md` 文件提取错误模式

2. **用户 AI 犯错记录**（可选）
   - 询问用户是否有额外的 AI 犯错记录路径
   - 默认路径：`D:\desktop\quackDocs\my_notes\ai_misktake`
   - 如果用户提供了其他路径，使用用户指定的路径

**交互方式**：

```
是否有额外的 AI 犯错记录？
- 使用默认路径（D:\desktop\quackDocs\my_notes\ai_msiktake）
- 提供自定义路径
- 跳过（仅使用仓库 bug 记录）
```

**分析方法**：

从错误记录中提取：
1. **常见错误模式**：AI 反复犯的同类错误
2. **触发条件**：什么情况下 AI 容易犯错
3. **错误代码示例**：具体的错误代码片段
4. **修复方案**：正确的做法

**输出错误模式清单**：

```markdown
## AI 错误模式清单

### 高频错误（必须制定规则）

#### 1. AI 自作主张添加未定义逻辑
- **来源**：docs/history-bugs/2026-06-05-agent-cwd-unspeced-logic.md
- **触发条件**：spec/plan 未明确定义时
- **错误示例**：
  ```python
  # ❌ AI 自行发明「首字母+末尾数字」拼接逻辑
  cwd = project_path + "/" + name[0] + name[-1]
  ```
- **正确做法**：直接使用 project_path

#### 2. AI 倾向就近实例化而非使用全局单例
- **来源**：docs/history-bugs/2026-06-06-api-route-created-separate-group-chat-manager.md
- **触发条件**：需要使用某个 Manager/Service 时
- **错误示例**：
  ```python
  # ❌ AI 在路由中直接创建新实例
  manager = GroupChatManager()
  ```
- **正确做法**：使用全局单例 `get_group_chat_manager()`

---

### 中频错误（推荐制定规则）

#### 1. 状态更新缺少前置检查
- **来源**：docs/history-bugs/2026-06-05-agent-call-status-duplicate-logging.md
- **触发条件**：更新状态时
- **错误示例**：
  ```python
  # ❌ 直接更新，不检查是否变化
  def update_status(self, new_status):
      self.status = new_status
      self.save()
  ```
- **正确做法**：先检查 `if self.status != new_status`

---
```

### 2. 临时规则建立方法（输出给用户审查）

**核心思路**：综合历史错误记录和架构约束预测，制定全面的规则

**规则设计原则**：
1. **减少 AI 的动作空间**：规则的目的是限制 AI 的选择，避免"有多种实现方式"的情况
2. **反面规则优于正面规则**：
   - ✅ 好："❌ 禁止在 components 中直接调用 API"（明确禁止）
   - ❌ 差："✅ 应该通过 hooks 调用 API"（仍有多种实现方式）
3. **统一范式**：规则的目的是让 AI 编写具有统一范式的代码，而不是任凭 AI 发挥
4. **综合分析**：历史错误和架构预测同等重要，两者综合决策

#### 2.1 分析现有代码和错误记录

**代码模式扫描**：
扫描目标目录下的代码，识别代码模式：
- 组件如何调用 API？
- Store 如何管理状态？
- 模块之间如何通信？

**错误记录整合**：
- 将步骤 1.5 中的「AI 错误模式清单」与代码模式对照
- 为 Subagent A 提供历史错误数据

#### 2.2 并行分析：预测 AI 可能的错误行为

**派出两个 Subagent 并行分析**：

使用 Agent 工具同时派出两个 subagent，从不同角度分析：

**Subagent A：历史错误分析**
```
任务：分析历史错误记录，提取 AI 常见错误模式
输入：
- 步骤 1.5 收集的错误记录
- docs/history-bugs/ 下的所有文件
- 用户提供的 AI 犯错记录

输出：
- 高频错误模式列表
- 每个模式包含：触发条件、错误示例、正确做法
```

**Subagent B：架构约束预测**
```
任务：基于架构约束，预测 AI 可能犯的错误
输入：
- docs/ARCHITECTURE.md
- 目标目录的代码
- 上级 CLAUDE.md（如果有）

输出：
- 每个架构约束对应的潜在错误
- 错误代码示例
- 验证结果（是否在现有代码中发现反例）
```

**等待两个 subagent 完成后**，综合两个分析结果：

```markdown
## 综合分析结果

### 来自历史错误（Subagent A）
- 高频错误 1：...
- 高频错误 2：...

### 来自架构预测（Subagent B）
- 潜在错误 1：...
- 潜在错误 2：...

### 综合规则建议
- 规则 1：综合 A 和 B 的分析...
- 规则 2：...
```

**综合原则**：
1. 历史错误和架构预测同等重要，不偏向任何一方
2. 如果两者指向同一类错误，说明该规则特别重要
3. 如果只有一方提到，也应纳入考虑

#### 2.3 规则分级

- 🔴 **强制规则**：来自 ARCHITECTURE.md，违反会导致架构崩溃
- 🟡 **推荐规则**：来自现有代码风格，违反会降低代码质量
- 🟢 **建议规则**：来自最佳实践，可选

#### 2.4 输出临时规则方案

```markdown
## 临时规则方案（请审查）

### 🔴 强制规则

#### 1. 禁止 feature 之间直接依赖
- **来源**：ARCHITECTURE.md 第 23 行
- **AI 可能的错误**：
  ```typescript
  // ❌ AI 可能会这样写
  import { SessionList } from '@/features/session/components/SessionList';
```
- **验证**：✅ 现有代码符合（未发现反例）

#### 2. 组件禁止直接调用 API
- **来源**：ARCHITECTURE.md 第 45 行
- **AI 可能的错误**：
  ```typescript
  // ❌ AI 可能会这样写
  function ChatWindow() {
    wsManager.send(...);
  }
  ```
- **验证**：❌ 发现反例（SessionList.tsx:45）

---

### 🟡 推荐规则

#### 1. Store 不包含副作用
- **来源**：现有代码风格（95% 的 store 遵循）
- **AI 可能的错误**：
  ```typescript
  // ❌ AI 可能会这样写
  const useStore = create((set) => ({
    sendMessage: (text) => {
      wsManager.send(text);  // 副作用
    },
  }));
  ```
- **验证**：✅ 现有代码基本符合（1 个反例）

---

### 🟢 建议规则

#### 1. 使用 useCallback 避免重新创建
- **来源**：React 官方文档
- **AI 可能的错误**：
  ```typescript
  // ❌ AI 可能会这样写
  function useChat() {
    const sendMessage = (text) => { ... };  // 每次重新创建
  }
  ```
- **验证**：⚠️ 现有代码未统一

---

❓ 是否接受这些规则？
- 是 → 继续创建规则
- 否 → 请指出需要修改的部分


### 3. 用户确认

等待用户反馈，根据反馈调整规则

### 4. 创建临时规则文档

使用 `docs/temp/rule-template.md` 中的模板，填充内容：
- 强制约束（❌ 禁止项）
- 代码示例（✅ 正确 vs ❌ 错误）
- 决策表

### 5. Subagent 审查临时规则

派出 subagent，使用审查模式的审查清单审查临时规则

### 6. 确认引用情况

**判断高频 vs 低频**：

问题："如果 AI 不看这条规则，会不会写出不符合架构的代码？"
- 会 → 高频（放 CLAUDE.md）
- 不会 → 低频（放 docs/coding-rules/，CLAUDE.md 只给链接）

**重复内容检测**：
1. 读取上级 CLAUDE.md
2. 提取上级的所有约束
3. 对比当前规则
4. 删除重复内容
5. 添加上级链接（如果是子模块）

**层级检查**：
- 当前是第几级？（最多 2 级）
- 如果超过 2 级 → 提示用户重新设计层级

### 7. 写入文件
编写对应的文件位置的CLAUDE.md（如果需要），和`docs/coding-rules`下的文件

### 8. 运行行数检查脚本

```bash
python scripts/check_line_count.py <project-root>
```

确保新创建的文件 ≤ 200 行

### 9. 最终审查

再次派出 subagent，使用审查模式审查新创建的规则

### 10. 输出总结

```markdown
✅ 规则创建完成

## 创建的文件
- <path>/CLAUDE.md (X 行)

## 规则来源
- 架构约束：X 条（从 ARCHITECTURE.md）
- 现有代码风格：X 条
- 最佳实践：X 条

## 审查结果
- ✅ 无教学性内容
- ✅ 有明确的 ✅/❌ 示例
- ✅ 无重复内容
- ✅ 符合架构约束
- ✅ 行数符合要求（X/200 行）
```

---

## 重要约束

1. **行数硬性限制**：所有 CLAUDE.md 和 docs/coding-rules/ 下的 md 文档 ≤ 200 行
2. **不写上下级索引**：CLAUDE.md 内部不需要写其他 CLAUDE.md 的索引（Claude Code 自动加载）
3. **子模块必须有上级链接**：格式 `> 上级规则：[../CLAUDE.md]`
4. **禁止教学性内容**：不写概念解释、技术教学、历史背景
5. **必须有具体示例**：✅ 正确 vs ❌ 错误的代码对比
6. **规则基于错误预测**：预测 AI 可能犯的错误，而不是列举所有最佳实践
7. **并行分析综合决策**：历史错误和架构预测同等重要，综合两者制定规则

---

## 参考文件

- `references/audit-checklist.md` - 完整的审查清单
- `references/rule-template.md` - 规则文档模板和反模式示例
- `scripts/check_line_count.py` - 行数检查脚本
