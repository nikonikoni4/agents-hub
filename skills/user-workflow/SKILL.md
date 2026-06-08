---
name: user-workflow
description: 用户工作流概览，每次会话加载。简洁展示用户的 skill 体系和使用时机，让 Claude 主动询问是否需要使用某个 skill。
---

# User Workflow

**每次会话加载此文档**，了解用户的工作流和可用 skill。

---

## 成对 Skill 体系

用户的核心 skill 以**成对**形式组织，形成闭环工作流：

### 1. 决策记录组

```
用户决策 → 记录决策 → AI 分析 → 记录知识负债
   ↓           ↓           ↓           ↓
ai-decision  write-    ai-decision   knowledge
-making      decisions  -making      -debt
```

| Skill | 角色 | 触发时机 |
|-------|------|---------|
| `ai-decision-making` | 决策过程辅助 | 用户面临选择、不确定怎么做 |
| `write-decisions` | 决策结果记录 | 用户做出最终决策后 |

**工作流**：
1. 用户遇到决策问题 → 触发 `ai-decision-making`
2. AI 列出方案、分析优缺点、给出推荐
3. 用户做出决策 → 触发 `write-decisions`
4. 记录决策内容 + 知识负债 + AI 决策过程

---

### 2. 规则与错误组

```
AI 犯错 → 记录错误 → 提取规则 → 写入 CLAUDE.md
   ↓           ↓           ↓           ↓
ai-mistake   ai-mistake  write-     write-project
-recorder    -recorder   project    -rules
                          -rules
```

| Skill | 角色 | 触发时机 |
|-------|------|---------|
| `ai-mistake-recorder` | 错误记录 | AI 犯错或可改进时 |
| `write-project-rules` | 规则编写 | 积累足够错误模式后 |

**工作流**：
1. AI 犯错 → 触发 `ai-mistake-recorder` 记录错误
2. 积累多个同类错误 → 触发 `write-project-rules`
3. 从错误中提取规则，写入 CLAUDE.md 防止再犯

---

### 3. 交接组

```
任务中断 → 生成交接文档 → 其他 agent 接手 → 恢复上下文
   ↓           ↓              ↓              ↓
hand-off    hand-off        hand-on         hand-on
```

| Skill | 角色 | 触发时机 |
|-------|------|---------|
| `hand-off` | 生成交接文档 | 任务中断、session 结束 |
| `hand-on` | 接手任务 | 从其他 agent 接手任务 |

**工作流**：
1. 任务需要中断 → 触发 `hand-off` 生成交接文档
2. 其他 agent 接手 → 触发 `hand-on` 读取交接文档
3. 恢复上下文继续执行

---

### 4. 任务执行组

```
想法收集 → 整理任务 → 创建 WorkTree → 并行执行
   ↓           ↓           ↓              ↓
progress    progress    parallel       parallel
-tracker    -tracker    -worktree      -worktree
```

| Skill | 角色 | 触发时机 |
|-------|------|---------|
| `progress-tracker` | 想法收集与任务整理 | 用户表达想法、需要整理任务 |
| `parallel-worktree` | 并行任务执行 | 多个独立任务需要并行处理 |

**工作流**：
1. 用户表达想法 → 触发 `progress-tracker` 收集
2. 整理成结构化任务清单
3. 多个独立任务 → 触发 `parallel-worktree`
4. 创建多个 WorkTree 并行执行

---

## 单独 Skill

这些 skill 不成对，独立使用：

| 时机 | Skill | 主动询问示例 |
|------|-------|--------------|
| 遇到开放性问题 | `deep-answer` | "这个问题需要深度分析吗？" |
| 成功经验可复用 | `knowledge-crystallizer` | "这个经验值得沉淀吗？" |
| 需要 CI 检查 | `ci-check` | "提交前跑一下检查？" |
| 创建/审查规则 | `write-project-rules` | "需要为这个模块创建规则吗？" |
| 做出重要决策 | `write-decisions` | "这个决策需要记录吗？" |

---

## 使用原则

1. **主动询问**：识别到相关场景时，主动询问用户是否需要使用 skill
2. **成对触发**：当一个 skill 完成后，检查是否需要触发配对的 skill
3. **不强制**：用户可以说"不用"，直接跳过
4. **简洁提示**：询问时一句话，不解释 skill 细节
