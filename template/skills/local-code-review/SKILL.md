---
name: local-code-review
description: 本地代码审查工具，用于审查指定范围的代码变更。支持多种输入方式：(1) git range（如 HEAD~3..HEAD）(2) 暂存区（--staged）(3) 指定文件/目录路径 (4) 模糊功能描述（如"认证模块"、"用户登录"）。必须指定审查范围，否则直接返回错误。输出审查报告到 docs/generated/。触发词：local-review、本地审查、代码审查、review。
---

# Local Code Review

本地代码审查技能，严格限制在指定范围内进行审查。

## 输入验证（必须首先执行）

**关键规则**：如果用户没有指定任何审查内容，直接返回错误并退出。

```
❌ 错误示例：/local-review（无参数）
✅ 正确示例：
  /local-review HEAD~3..HEAD
  /local-review --staged
  /local-review src/auth/
  /local-review 认证模块
```

### 输入类型识别

| 输入模式 | 识别方式 | 处理方法 |
|---------|---------|---------|
| `--staged` | 暂存区变更 | `git diff --cached` |
| `HEAD~n..HEAD` 或 `commit1..commit2` | Git range | `git diff <range>` |
| 文件/目录路径 | 存在于文件系统 | `git diff` 对比该路径 |
| 功能描述文本 | 非路径、非 git 语法 | 搜索相关文件后审查 |

## 审查流程

### Step 1: 验证输入并获取变更

1. 检查是否提供了审查范围参数
2. 如果没有参数，输出错误信息并退出：
   ```
   ❌ 必须指定审查内容。支持的输入方式：
   - Git range: /local-review HEAD~3..HEAD
   - 暂存区: /local-review --staged
   - 文件路径: /local-review src/auth/
   - 功能描述: /local-review 认证模块
   ```
3. 根据输入类型获取变更文件列表

### Step 2: 收集上下文（CLAUDE.md + ADR + Spec）

启动 Haiku Agent 收集审查上下文：

**2a. 收集 CLAUDE.md 文件**
1. 读取项目根目录的 CLAUDE.md
2. 扫描变更文件所在目录及其父目录的 CLAUDE.md
3. 返回所有相关 CLAUDE.md 文件路径列表

**2b. 搜索相关 ADR（架构决策记录）**
1. 搜索 `docs/ADR/` 目录下的 ADR 文件
2. 使用变更模块/功能名作为关键词搜索 ADR 内容
3. 检查 git 历史中的决策相关提交：
   ```bash
   git log --grep="decision\|chose\|instead of\|trade-off" -10 -- <changed_files>
   ```
4. 返回相关 ADR 列表及其状态（proposed/accepted/deprecated）

**2c. 搜索相关 Spec（产品规格）**
1. 读取 `docs/specs/index.md` 获取 spec 索引
2. 搜索与变更文件/功能相关的 spec
3. 检查 `docs/ADR/` 目录下的决策文档
4. 返回相关 spec 列表及关键约束

**输出：ADR + Spec 上下文块**
```markdown
## 架构上下文

### 相关 ADR
- ADR-0003: 使用 Zustand 做状态管理 (accepted)
- ADR-0007: 原子文件写入 (accepted)

### 相关 Spec
- docs/specs/auth-module.md: 认证模块规格
- docs/ADR/user-design-summary.md: 用户决策习惯

### 决策覆盖
- 3/5 变更文件有 ADR 关联
- 2 个文件无文档化决策上下文
```

### Step 3: 生成变更摘要

1. 使用 SubAgent分析变更内容
2. 返回：变更文件列表、变更行数、变更类型（新增/修改/删除）

### Step 4: 并行审查（8 个 Sonnet Agent）

同时启动 8 个 Agent 进行独立审查：

**Agent #1: Security（安全）**
- 检查漏洞、注入风险、认证问题、密钥泄露
- 关注：SQL 注入、XSS、硬编码密钥、缺失认证、不安全加密

**Agent #2: Performance（性能）**
- 检查 N+1 查询、内存泄漏、低效算法
- 关注：缺失索引、大载荷、无分页、未关闭连接

**Agent #3: Architecture（架构）**
- 检查设计模式、SOLID 原则、耦合度
- 关注：职责不清、过度耦合、违反设计原则
- **额外检查**：变更是否符合已接受的 ADR，是否引入未记录的架构决策

**Agent #4: Code Quality（代码质量）**
- 检查可读性、复杂度、重复代码
- 关注：长函数、深层嵌套、魔法数字、重复代码、缺失类型
- **项目规则检查**：
  - 读取 `docs/coding-rules/index.md` 获取规则索引
  - 按需加载与变更相关的编码规则
  - 检查是否符合所涉及到的 CLAUDE.md 中的规范

**Agent #5: Best Practices（最佳实践）**
- 检查语言惯用写法、框架约定
- 关注：不符合语言习惯、违反框架规范

**Agent #6: Testing（测试）**
- 检查覆盖率缺口、测试质量、边界情况
- 关注：缺失测试、测试不覆盖边界、测试质量差

**Agent #7: Documentation（文档）**
- 检查缺失文档、过时注释
- 关注：新增功能无文档、注释与代码不符

**Agent #8: 代码注释合规**
- 读取变更文件中的代码注释
- 确保变更符合注释中的指导

每个 Agent 返回：问题列表及原因（安全/性能/架构/质量/最佳实践/测试/文档/注释合规）

### Step 5: 置信度评分

对每个发现的问题，启动 Haiku Agent 进行评分（0-100）：

| 分数 | 含义 |
|-----|------|
| 0 | 误报，经不起推敲，或预先存在的问题 |
| 25 | 可能是问题，也可能是误报。未验证确认 |
| 50 | 确认是问题，但可能是吹毛求疵或不常触发 |
| 75 | 高度可信，很可能触发，现有方案不足 |
| 100 | 绝对确定，频繁触发，证据确凿 |

**评分要求**：
- 对于因 CLAUDE.md 标记的问题，必须确认 CLAUDE.md 明确提到该问题
- 忽略 linter/编译器会捕获的问题
- 忽略预先存在的问题
- 忽略用户未修改的行上的问题

### Step 6: 过滤并输出

1. 过滤掉分数 < 80 的问题
2. 如果没有问题满足条件，输出"No issues found"
3. 生成审查报告并保存到 `docs/generated/NNN/code-review-<timestamp>.md`（NNN 为递增序号，如 001、002、003）

## 输出格式

### 报告模板

```markdown
# Code Review Report

**审查范围**: [用户指定的范围]
**审查时间**: [时间戳]
**变更文件**: [文件列表]

## 架构上下文

### 相关 ADR
- [ADR 列表及状态]

### 相关 Spec
- [Spec 列表及关键约束]

### 决策覆盖
- [覆盖情况统计]

## 审查结果

Found N issues:

### Issue 1: [简要描述]
- **类型**: [Security / Performance / Architecture / Code Quality / Best Practices / Testing / Documentation / 代码注释合规]
- **置信度**: [分数]
- **位置**: [文件路径:行号]
- **详情**: [具体问题描述]
- **依据**: [引用 CLAUDE.md / ADR / Spec 或其他来源]

### Issue 2: ...

## 变更摘要

[变更的简要概述]
```

### 无问题时的输出

```markdown
# Code Review Report

**审查范围**: [用户指定的范围]
**审查时间**: [时间戳]

## 架构上下文

### 相关 ADR
- [ADR 列表及状态]

### 相关 Spec
- [Spec 列表及关键约束]

## 审查结果

No issues found. Checked for bugs, security, performance, and architecture compliance.

## 变更摘要

[变更的简要概述]
```

## 关键约束

1. **严格范围限制**：只审查用户指定范围内的代码
2. **必须指定输入**：无参数时直接报错退出
3. **避免误报**：
   - 忽略预先存在的问题
   - 忽略 linter/编译器会捕获的问题
   - 忽略风格问题（除非 CLAUDE.md 明确要求）
   - 忽略用户未修改的行
4. **输出位置**：`docs/generated/NNN/code-review-<timestamp>.md`（NNN 为递增序号）
5. **引用规范**：必须引用具体的 CLAUDE.md 或代码位置
