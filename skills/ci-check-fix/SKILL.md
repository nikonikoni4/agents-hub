---
name: ci-check-fix
description: CI检查修复流程，用于修复ci-check发现的问题。按优先级修复：代码错误 → code-review → context → architecture → spec。触发词：ci-check-fix、ci修复、修复ci问题、修复检查问题、fix ci。
---

# CI Check Fix Skill

## 核心原则

**按优先级修复，逐项验证**。读取 CI 报告，按固定顺序修复各类问题，每项修复后验证通过再继续。

## 流程概览

```
输入: docs/generated/NNN/YYYY-MM-DD-ci-report.md

Stage 1: 代码错误修复
  └─ 解决 lint/type/test 静态检查失败项

Stage 2: Code Review 修复
  └─ 修复代码审查发现的 Critical/Warning 问题

Stage 3: CONTEXT.md 修复
  └─ 修复术语不一致、废弃术语、新术语缺失

Stage 4: ARCHITECTURE.md 修复
  └─ 修复架构文档与代码结构的不一致

Stage 5: Spec 修复
  └─ 修复 spec 与代码实现的不一致

输出: 更新报告中每项的修复状态
```

## 执行流程

### 准备阶段：读取 CI 报告

1. 找到最新的 CI 报告：`docs/generated/` 下最大编号目录中的 `*-ci-report.md`
2. 读取报告，提取每个检查项的发现的问题列表
3. 创建任务列表，按优先级排序

### Stage 1: 代码错误修复

处理静态检查（make check）发现的问题：

1. 读取报告中的静态检查结果
2. 对于每个失败项：
   - 分析错误信息，定位问题文件和行号
   - 修复代码错误（语法、类型、lint 规则）
3. 运行 `make check` 验证修复
4. 更新报告中对应项的修复状态

**修复策略**：
- lint 错误：按照项目 lint 规则修正代码格式
- 类型错误：添加/修正类型注解，修复类型不匹配
- 测试失败：分析测试失败原因，修复代码或测试

### Stage 2: Code Review 修复

处理代码审查发现的问题：

1. 读取报告中的代码审查部分
2. 按严重程度处理：
   - **Critical**：必须修复
   - **Warning**：评估后决定是否修复
   - **Suggestion**：记录但不强制修复
3. 对于每个待修复项：
   - 理解问题描述和建议修复方案
   - 实施修复
   - 验证修复不引入新问题
4. 更新报告中对应项的修复状态

### Stage 3: CONTEXT.md 修复

处理术语一致性问题：

1. 读取报告中的 CONTEXT.md 一致性检查结果
2. 修复策略：
   - **术语不一致**：更新 CONTEXT.md 中的定义使其与代码一致
   - **新术语缺失**：在 CONTEXT.md 中添加代码中使用的新术语
   - **废弃术语**：从 CONTEXT.md 中移除代码中已不再使用的术语
   - **枚举/异常不一致**：同步 CONTEXT.md 与代码中的定义
3. 更新报告中对应项的修复状态

### Stage 4: ARCHITECTURE.md 修复

处理架构文档一致性问题：

1. 读取报告中的 ARCHITECTURE.md 一致性检查结果
2. 修复策略：
   - **模块缺失**：在文档中添加代码中存在但未描述的模块
   - **描述过时**：更新文档使其反映实际代码结构
   - **依赖关系不一致**：修正文档中的依赖关系描述
3. 更新报告中对应项的修复状态

### Stage 5: Spec 修复

处理 spec 一致性问题：

1. 读取报告中的 specs 一致性检查结果
2. 修复策略：
   - **接口不一致**：更新 spec 使其与实际 API 一致
   - **功能缺失**：在 spec 中记录代码中已实现但未文档化的功能
   - **过期内容**：从 spec 中移除代码中已不再实现的内容
3. 修复决策原则：
   - 如果代码行为合理 → 更新 spec 对齐代码
   - 如果 spec 描述更合理 → 修改代码对齐 spec（需评估影响）
   - 如果存在歧义 → 标记为待讨论，不擅自决定
4. 更新报告中对应项的修复状态

## 修复状态标记

每项修复使用以下状态标记：

| 状态 | 标记 | 说明 |
|------|------|------|
| 待修复 | `🟡 待修复` | 已识别，尚未处理 |
| 已修复 | `🟢 已修复` | 已完成修复并验证 |
| 无需修复 | `⚪ 无需修复` | 评估后决定不修复（如 Suggestion 级别） |
| 无法修复 | `🔴 无法修复` | 需要外部依赖或超出当前能力范围 |
| 跳过 | `⏭️ 跳过` | 用户明确要求跳过 |

## 报告更新格式

修复完成后，在 CI 报告中每个检查项的章节内追加修复状态表：

```markdown
### 修复状态

| 问题 | 严重程度 | 修复状态 | 修复说明 |
|------|----------|----------|----------|
| 问题 1 描述 | Critical | 🟢 已修复 | 修复了 xxx |
| 问题 2 描述 | Warning | ⚪ 无需修复 | 评估后决定保留现状 |
| 问题 3 描述 | Suggestion | 🟡 待修复 | 计划在下个迭代处理 |
```

## 脚本使用

### 完整修复流程

```bash
python skills/ci-check-fix/scripts/run_ci_fix.py
```

### 仅修复特定阶段

```bash
python skills/ci-check-fix/scripts/run_ci_fix.py --only static
python skills/ci-check-fix/scripts/run_ci_fix.py --only code-review
python skills/ci-check-fix/scripts/run_ci_fix.py --only context
python skills/ci-check-fix/scripts/run_ci_fix.py --only architecture
python skills/ci-check-fix/scripts/run_ci_fix.py --only spec
```

### 指定 CI 报告目录

```bash
python skills/ci-check-fix/scripts/run_ci_fix.py --run-dir docs/generated/001
```

## Anti-Pattern Guards

1. **不得跳过验证** — 每项修复后必须验证通过再继续下一阶段
2. **不得擅自扩大修复范围** — 只修复报告中列出的问题，不做额外重构
3. **不得忽略修复状态更新** — 每项处理后必须更新报告中的状态
4. **不得在 spec 和代码之间单方面决策** — 遇到歧义时标记为待讨论
5. **不得破坏已有测试** — 修复过程中确保已有测试仍然通过

## Quality Checklist

- 是否读取了最新的 CI 报告？
- 是否按优先级顺序处理（static → code-review → context → architecture → spec）？
- 每项修复后是否验证通过？
- 报告中的修复状态是否已更新？
- 修复过程中是否引入了新问题？
- 是否有无法修复的项需要标记？
