---
name: ci-check
description: CI检查流程，用于提交前的全面质量检查。包含：后端+前端静态检查（lint/type/test）、代码审查（最近提交）、文档一致性验证（ARCHITECTURE.md/specs/CONTEXT.md vs 代码）。触发词：ci-check、ci检查、提交前检查、pre-commit检查、质量检查、跑一下检查。
---

# CI Check Skill

## 核心原则

**只读检查，不做修改**。Makefile 的自动格式化（ruff format、prettier）属于自动修复，允许执行。

## 流程概览

```
Stage 1: 静态检查 (串行)
  ├─ make check (后端)
  └─ cd frontend && make check (前端)

Stage 2 & 3: 并行执行
  ├─ [Agent A] 代码审查 — 使用 claude code-review 技能审查最近提交
  ├─ [Agent B] ARCHITECTURE.md 一致性检查
  ├─ [Agent C] docs/specs 一致性检查
  └─ [Agent D] CONTEXT.md 一致性检查

Stage 4: 汇总报告 → docs/generated/NNN/YYYY-MM-DD-ci-report.md

可选: 运行 ci-check-fix 修复发现的问题
  └─ python skills/ci-check-fix/scripts/run_ci_fix.py
```

## 执行流程

### Stage 1: 静态检查

运行项目 Makefile 的 check 目标：

```bash
# 后端检查
make check

# 前端检查
cd frontend && make check
```

- 先后端再前端，串行执行
- 如果任一阶段失败，记录错误但继续后续阶段（不中断）
- 失败的检查项会在最终报告中标注

### Stage 2 & 3: 并行 Agent 检查

使用 `scripts/run_parallel_checks.py` 并行执行 4 项检查。该脚本通过 `claude` CLI 的 `-p`（print mode）调用 Claude：

- **Agent A — 代码审查**：使用 `code-review` 技能审查最近的提交内容
- **Agent B — ARCHITECTURE.md 一致性**：对比架构文档描述与实际代码结构
- **Agent C — specs 一致性**：对比 `docs/specs/` 中的规格说明与实际代码实现
- **Agent D — CONTEXT.md 一致性**：对比术语表中的概念定义与代码中的实际使用

每项检查输出独立的 Markdown 文件到 `docs/generated/NNN/` 编号目录（如 `001/`, `002/`），文件命名格式为 `YYYY-MM-DD-{检查项}.md`。

所有 Agent 均通过 `--allowedTools` 限制为只读工具：`Bash(git *) Bash(ls:*) Read Glob Grep WebSearch WebFetch`，并附加 `--append-system-prompt` 强制只读指令。禁止使用 `Edit`, `Write`, `NotebookEdit`, `Agent` 等写入工具。

### Stage 4: 汇总报告

运行 `scripts/summarize_report.py`，将检查结果汇总到同一编号目录下 `YYYY-MM-DD-ci-report.md`，并更新 `docs/generated/index.md` 索引。包含：

1. **执行摘要** — 整体通过/失败状态，含修复状态列
2. **静态检查结果** — 后端/前端各检查项状态
3. **代码审查摘要** — 关键发现和建议
4. **文档一致性摘要** — 各文档的冲突点列表
5. **待修复事项** — 按优先级排列的行动项

#### 修复状态跟踪

汇总报告的执行摘要表包含「修复状态」列，用于跟踪 ci-check-fix 修复后的状态：

| 检查项 | 检查状态 | 修复状态 |
|--------|----------|----------|
| 代码审查 | ✅ 完成 | 🟢 全部修复 (3/3) |
| ARCHITECTURE.md 一致性 | ✅ 完成 | 🟡 部分修复 (1/4) |
| docs/specs 一致性 | ✅ 完成 | 🔴 未修复 (0/2) |
| CONTEXT.md 一致性 | ✅ 完成 | — |

修复状态取值：
- `🟢 全部修复 (N/N)` — 所有问题已修复
- `🟡 部分修复 (N/M)` — 部分问题已修复
- `🔴 未修复 (0/N)` — 未运行修复或修复失败
- `⚪ 无需修复` — 检查通过，无需修复
- `—` — 未运行 ci-check-fix

每个检查项章节内也会显示修复状态，并附带详细的修复状态表（由 ci-check-fix 生成）。

## 脚本使用

### 完整执行

```bash
python skills/ci-check/scripts/run_ci_check.py
```

### 仅运行并行检查（跳过静态检查）

```bash
python skills/ci-check/scripts/run_ci_check.py --skip-static
```

### 仅运行特定 Agent 检查

```bash
python skills/ci-check/scripts/run_parallel_checks.py --only code-review
python skills/ci-check/scripts/run_parallel_checks.py --only architecture
python skills/ci-check/scripts/run_parallel_checks.py --only specs
python skills/ci-check/scripts/run_parallel_checks.py --only context
```

## Anti-Pattern Guards

1. **不得在检查阶段修改代码** — 除了 Makefile 自动格式化外，所有操作必须只读。通过 `--allowedTools` 限制 Bash 命令范围 + `--append-system-prompt` 强制限制
2. **不得跳过失败项** — 即使某个阶段失败，也要记录并继续执行后续阶段
3. **不得忽略文档冲突** — 发现的每处不一致都必须记录在报告中
4. **不得在报告中省略错误详情** — 失败项需要包含完整的错误输出

## Quality Checklist

- 后端 `make check` 是否执行并记录结果？
- 前端 `make check` 是否执行并记录结果？
- 代码审查是否覆盖了最近的提交？
- 三个文档一致性检查是否并行执行？
- 最终报告是否包含所有检查阶段的结果？
- 报告是否输出到 `docs/generated/NNN/` 编号目录？
- 报告中的时间戳是否正确？
- 执行摘要表是否包含「修复状态」列？
