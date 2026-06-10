#!/usr/bin/env python3
"""并行运行 CI 检查：代码审查 + 文档一致性验证。

使用 claude CLI 的 print mode (-p) 调用 Claude 执行检查。
每个检查项独立运行，输出到 docs/generated/ 目录。

用法:
    python run_parallel_checks.py                    # 运行全部检查
    python run_parallel_checks.py --only code-review # 仅运行代码审查
    python run_parallel_checks.py --only architecture
    python run_parallel_checks.py --only specs
    python run_parallel_checks.py --only context
    python run_parallel_checks.py --skip code-review # 跳过代码审查
"""

import argparse
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date
from pathlib import Path

# 项目根目录（脚本位于 skills/ci-check/scripts/）
PROJECT_ROOT = Path(__file__).resolve().parents[3]
GENERATED_DIR = PROJECT_ROOT / "docs" / "generated"

TODAY = date.today().isoformat()


def get_next_run_dir() -> Path:
    """获取下一次检查的编号目录，如 001, 002, 003..."""
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    existing = [d.name for d in GENERATED_DIR.iterdir() if d.is_dir() and d.name.isdigit()]
    next_num = max((int(n) for n in existing), default=0) + 1
    run_dir = GENERATED_DIR / f"{next_num:03d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


RUN_DIR = get_next_run_dir()


CHECKS = {
    "code-review": {
        "description": "代码审查（最近提交）",
        "output": RUN_DIR / f"{TODAY}-code-review.md",
        "prompt": f"""\
你是一个代码审查专家。请审查当前分支最近的提交内容。

步骤：
1. 运行 `git log --oneline -10` 查看最近提交
2. 运行 `git diff main...HEAD` 查看分支的所有变更
3. 对变更进行代码审查，关注：
   - 代码质量和风格一致性
   - 潜在的 bug 和边界情况
   - 安全问题
   - 性能问题
   - 测试覆盖

输出格式（Markdown）：
## 代码审查报告
- 审查范围：最近提交摘要
- 审查日期：{TODAY}

### 发现的问题
按严重程度分类（Critical / Warning / Suggestion）

### 总结
整体评价和改进建议
""",
    },
    "architecture": {
        "description": "ARCHITECTURE.md 一致性检查",
        "output": RUN_DIR / f"{TODAY}-architecture-check.md",
        "prompt": """\
你是一个架构文档一致性检查专家。请对比 docs/ARCHITECTURE.md 中描述的架构与实际代码结构，找出不一致的地方。

步骤：
1. 读取 docs/ARCHITECTURE.md，理解其描述的架构（模块、层级、依赖关系）
2. 检查实际代码目录结构是否与文档描述一致
3. 检查文档中提到的模块、类、函数是否在代码中存在
4. 检查代码中是否存在文档未覆盖的重要模块
5. 检查依赖关系描述是否与实际导入一致

输出格式（Markdown）：
## ARCHITECTURE.md 一致性检查报告
- 检查日期：YYYY-MM-DD

### 一致的部分
简要列出验证通过的关键描述

### 不一致的部分
每处冲突包含：
- **位置**：文档中的章节/段落
- **文档描述**：文档说的什么
- **实际情况**：代码实际是什么
- **严重程度**：Critical / Warning / Info
- **建议修复**：如何解决

### 文档缺失覆盖
代码中存在但文档未提及的重要内容

### 总结
一致性评分和主要问题
""",
    },
    "specs": {
        "description": "docs/specs 一致性检查",
        "output": RUN_DIR / f"{TODAY}-specs-check.md",
        "prompt": """\
你是一个规格文档一致性检查专家。请对比 docs/specs/ 中的规格说明与实际代码实现，找出不一致的地方。

步骤：
1. 读取 docs/specs/index.md 了解所有 spec 文件
2. 逐个读取 spec 文件，理解每个 spec 定义的接口、行为、约束
3. 对比实际代码实现，检查：
   - spec 中定义的接口是否完整实现
   - 实现行为是否符合 spec 描述
   - spec 中的约束条件是否在代码中被遵守
   - 代码中是否有 spec 未覆盖的新增功能
   - spec 中是否有代码已删除但文档未更新的内容

输出格式（Markdown）：
## Specs 一致性检查报告
- 检查日期：YYYY-MM-DD

### 每个 Spec 的检查结果

#### spec文件名
- **状态**：✅ 一致 / ⚠️ 部分不一致 / ❌ 严重不一致
- **不一致详情**：
  - 位置、文档描述、实际情况、严重程度、建议修复

### 代码中未被 Spec 覆盖的功能
列出代码中存在但没有任何 spec 描述的功能

### 已过期的 Spec 内容
列出 spec 中描述但代码已不再实现的内容

### 总结
整体一致性评分和主要问题
""",
    },
    "context": {
        "description": "CONTEXT.md 一致性检查",
        "output": RUN_DIR / f"{TODAY}-context-check.md",
        "prompt": """\
你是一个术语一致性检查专家。请对比 CONTEXT.md 中的术语定义与代码中的实际使用，找出不一致的地方。

步骤：
1. 读取 CONTEXT.md，理解所有术语定义（实体、通信、渲染、上下文、枚举、异常等）
2. 在代码中搜索这些术语的使用，检查：
   - 术语定义是否与代码中的类名/变量名/函数名一致
   - 代码中是否使用了 CONTEXT.md 未定义的新术语
   - CONTEXT.md 中是否定义了代码中已不再使用的术语
   - 枚举值定义是否与代码一致
   - 异常类层次是否与代码一致

输出格式（Markdown）：
## CONTEXT.md 一致性检查报告
- 检查日期：YYYY-MM-DD

### 术语一致性
每个术语的检查结果：
- **术语名**
- **状态**：✅ 一致 / ⚠️ 不一致 / ❌ 已废弃
- **详情**：不一致的具体描述

### 代码中未定义的新术语
代码中使用但 CONTEXT.md 未收录的术语

### 已废弃的术语
CONTEXT.md 中定义但代码中已不再使用的术语

### 枚举/异常层次检查
枚举值和异常类的一致性检查结果

### 总结
一致性评分和主要问题
""",
    },
}


def run_check(name: str, config: dict) -> tuple[str, bool, str]:
    """运行单个检查项。返回 (名称, 是否成功, 输出路径)。"""
    output_path: Path = config["output"]
    prompt: str = config["prompt"]

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "text",
        "--max-turns",
        "30",
        "--allowedTools",
        "Bash(git *) Bash(make:*) Bash(ls:*) Bash(cat:*) Bash(head:*) Bash(wc:*) Bash(find:*) Read Glob Grep WebSearch WebFetch",
        "--append-system-prompt",
        "You are a read-only CI checker. Never modify any files. Only read, search, and report.",
    ]

    print(f"[{name}] 开始执行: {config['description']}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=600,  # 10 分钟超时
        )

        if result.returncode != 0:
            error_msg = f"命令执行失败 (exit code {result.returncode}):\n{result.stderr}"
            print(f"[{name}] ❌ 失败")
            # 即使失败也写入输出文件，记录错误
            output_path.write_text(
                f"# {config['description']} — 执行失败\n\n```\n{error_msg}\n```\n",
                encoding="utf-8",
            )
            return name, False, str(output_path)

        # 写入结果
        output_path.write_text(result.stdout, encoding="utf-8")
        print(f"[{name}] ✅ 完成 → {output_path.relative_to(PROJECT_ROOT)}")
        return name, True, str(output_path)

    except subprocess.TimeoutExpired:
        print(f"[{name}] ❌ 超时 (600s)")
        output_path.write_text(
            f"# {config['description']} — 执行超时\n\n检查执行超过 10 分钟限制。\n",
            encoding="utf-8",
        )
        return name, False, str(output_path)
    except FileNotFoundError:
        print(f"[{name}] ❌ 未找到 claude CLI，请确保已安装 Claude Code")
        return name, False, ""


def main():
    parser = argparse.ArgumentParser(description="并行运行 CI 检查")
    parser.add_argument(
        "--only",
        choices=list(CHECKS.keys()),
        help="仅运行指定检查项",
    )
    parser.add_argument(
        "--skip",
        choices=list(CHECKS.keys()),
        action="append",
        default=[],
        help="跳过指定检查项（可多次使用）",
    )
    args = parser.parse_args()

    # 确定要执行的检查项
    if args.only:
        checks_to_run = {args.only: CHECKS[args.only]}
    else:
        checks_to_run = {k: v for k, v in CHECKS.items() if k not in args.skip}

    if not checks_to_run:
        print("没有要执行的检查项")
        sys.exit(0)

    print(f"=== CI 并行检查 ===")
    print(f"检查项: {', '.join(checks_to_run.keys())}")
    print(f"输出目录: {RUN_DIR.relative_to(PROJECT_ROOT)}")
    print()

    results = {}

    # 并行执行所有检查
    with ProcessPoolExecutor(max_workers=len(checks_to_run)) as executor:
        futures = {
            executor.submit(run_check, name, config): name for name, config in checks_to_run.items()
        }

        for future in as_completed(futures):
            name = futures[future]
            try:
                check_name, success, output_path = future.result()
                results[check_name] = (success, output_path)
            except Exception as e:
                print(f"[{name}] ❌ 异常: {e}")
                results[name] = (False, "")

    # 输出汇总
    print()
    print("=== 检查结果汇总 ===")
    all_success = True
    for name, (success, output_path) in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        desc = CHECKS[name]["description"]
        print(f"  {status} {desc}")
        if not success:
            all_success = False

    print()
    if all_success:
        print("所有检查项通过 ✅")
    else:
        print("部分检查项失败 ❌")

    # 返回非零退出码表示有失败项
    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
