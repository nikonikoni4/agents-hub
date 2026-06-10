#!/usr/bin/env python3
"""
检查项目中所有规则文档的行数
硬性指标：CLAUDE.md 和 docs/coding-rules/ 下的 md 文档不能超过 200 行
"""

import os
import sys
from pathlib import Path


def count_lines(file_path):
    """统计文件行数"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return len(f.readlines())
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return 0


def find_rule_files(project_root):
    """查找所有规则文档"""
    rule_files = []

    # 查找所有 CLAUDE.md 文件
    for claude_file in Path(project_root).rglob("CLAUDE.md"):
        rule_files.append(claude_file)

    # 查找 docs/coding-rules/ 下的所有 md 文件
    coding_rules_dir = Path(project_root) / "docs" / "coding-rules"
    if coding_rules_dir.exists():
        for md_file in coding_rules_dir.rglob("*.md"):
            rule_files.append(md_file)

    return rule_files


def check_line_counts(project_root, max_lines=200):
    """检查所有规则文档的行数"""
    rule_files = find_rule_files(project_root)

    if not rule_files:
        print("No rule files found.")
        return True

    violations = []
    results = []

    for file_path in sorted(rule_files):
        line_count = count_lines(file_path)
        relative_path = file_path.relative_to(project_root)

        status = "OK" if line_count <= max_lines else "FAIL"
        results.append((status, relative_path, line_count))

        if line_count > max_lines:
            violations.append((relative_path, line_count))

    # 输出结果
    print(f"Rule Files Line Count Report (Max: {max_lines} lines)")
    print("=" * 80)

    for status, path, count in results:
        print(f"[{status}] {path}: {count} lines")

    print("=" * 80)
    print(f"Total files: {len(results)}")
    print(f"Violations: {len(violations)}")

    if violations:
        print("\nFiles exceeding limit:")
        for path, count in violations:
            print(f"  - {path}: {count} lines (exceeds by {count - max_lines})")
        return False
    else:
        print("\nAll files within limit!")
        return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = os.getcwd()

    success = check_line_counts(project_root)
    sys.exit(0 if success else 1)
