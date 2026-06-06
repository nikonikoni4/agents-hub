#!/usr/bin/env python3
"""CI 检查主入口。

执行完整 CI 检查流程：
1. 静态检查 (make check)
2. 并行 Agent 检查 (代码审查 + 文档一致性)
3. 汇总报告

用法:
    python run_ci_check.py                  # 完整流程
    python run_ci_check.py --skip-static    # 跳过静态检查
    python run_ci_check.py --skip-parallel  # 跳过并行检查
"""

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parents[2]


def run_static_checks() -> bool:
    """运行后端和前端的 make check。"""
    print("=" * 60)
    print("Stage 1: 静态检查")
    print("=" * 60)

    all_pass = True

    # 后端检查
    print("\n--- 后端 make check ---")
    result = subprocess.run(
        ["make", "check"],
        cwd=str(PROJECT_ROOT),
        timeout=300,
    )
    if result.returncode != 0:
        print("❌ 后端检查失败")
        all_pass = False
    else:
        print("✅ 后端检查通过")

    # 前端检查
    print("\n--- 前端 make check ---")
    frontend_dir = PROJECT_ROOT / "frontend"
    result = subprocess.run(
        ["make", "check"],
        cwd=str(frontend_dir),
        timeout=300,
    )
    if result.returncode != 0:
        print("❌ 前端检查失败")
        all_pass = False
    else:
        print("✅ 前端检查通过")

    return all_pass


def run_parallel_checks() -> bool:
    """运行并行 Agent 检查。"""
    print("\n" + "=" * 60)
    print("Stage 2 & 3: 并行 Agent 检查")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "run_parallel_checks.py")],
        cwd=str(PROJECT_ROOT),
        timeout=900,
    )
    return result.returncode == 0


def run_summary():
    """生成汇总报告。"""
    print("\n" + "=" * 60)
    print("Stage 4: 生成汇总报告")
    print("=" * 60)

    subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "summarize_report.py")],
        cwd=str(PROJECT_ROOT),
    )


def main():
    parser = argparse.ArgumentParser(description="CI 检查主入口")
    parser.add_argument(
        "--skip-static",
        action="store_true",
        help="跳过静态检查 (make check)",
    )
    parser.add_argument(
        "--skip-parallel",
        action="store_true",
        help="跳过并行 Agent 检查",
    )
    args = parser.parse_args()

    print(f"CI 检查开始 — {date.today().isoformat()}")
    print(f"项目根目录: {PROJECT_ROOT}")
    print()

    static_ok = True
    parallel_ok = True

    if not args.skip_static:
        static_ok = run_static_checks()
    else:
        print("⏭️ 跳过静态检查")

    if not args.skip_parallel:
        parallel_ok = run_parallel_checks()
    else:
        print("⏭️ 跳过并行检查")

    run_summary()

    # 最终状态
    print("\n" + "=" * 60)
    print("CI 检查完成")
    print("=" * 60)

    if static_ok and parallel_ok:
        print("✅ 全部通过")
        sys.exit(0)
    else:
        if not static_ok:
            print("❌ 静态检查有失败项")
        if not parallel_ok:
            print("❌ 并行检查有失败项")
        sys.exit(1)


if __name__ == "__main__":
    main()
