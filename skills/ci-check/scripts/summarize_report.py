#!/usr/bin/env python3
"""汇总 CI 检查结果，生成最终报告。

读取指定编号目录下的各检查报告，合并为一份汇总报告，并更新 index.md。

用法:
    python summarize_report.py --run-dir docs/generated/001
    python summarize_report.py                  # 自动使用最新编号目录
    python summarize_report.py --date 2026-06-06
"""

import argparse
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
GENERATED_DIR = PROJECT_ROOT / "docs" / "generated"

REPORT_SECTIONS = [
    ("code-review", "代码审查"),
    ("architecture-check", "ARCHITECTURE.md 一致性"),
    ("specs-check", "docs/specs 一致性"),
    ("context-check", "CONTEXT.md 一致性"),
]

# 修复状态映射：fix 报告中的状态 → 汇总状态
FIX_STATUS_MAP = {
    "🟢 已修复": "已修复",
    "⚪ 无需修复": "无需修复",
    "🟡 待修复": "待修复",
    "🔴 无法修复": "无法修复",
    "⏭️ 跳过": "跳过",
}


def get_latest_run_dir() -> Path:
    """获取最新的编号目录。"""
    existing = [d for d in GENERATED_DIR.iterdir() if d.is_dir() and d.name.isdigit()]
    if not existing:
        raise FileNotFoundError("没有找到任何检查编号目录，请先运行 run_parallel_checks.py")
    return max(existing, key=lambda d: int(d.name))


def read_report(path: Path) -> str:
    """读取报告文件内容，截取关键摘要。"""
    if not path.exists():
        return f"> ⚠️ 报告文件不存在: `{path.name}`"

    content = path.read_text(encoding="utf-8")
    if len(content) > 5000:
        return content[:3000] + f"\n\n> ... (完整报告见 `{path.name}`，共 {len(content)} 字符)"
    return content


def parse_fix_status(run_dir: Path, report_date: str, section_key: str) -> str:
    """解析修复报告中的修复状态。

    查找匹配的 fix 报告文件（如 2026-06-06-fix-code-review.md），
    提取修复状态表中的状态信息。

    Returns:
        修复状态摘要字符串，如 "已修复 (2/3)" 或 "未修复" 或 ""
    """
    # 映射 section key 到 fix 报告名
    fix_key_map = {
        "code-review": "code-review",
        "architecture-check": "architecture",
        "specs-check": "spec",
        "context-check": "context",
    }

    fix_key = fix_key_map.get(section_key)
    if not fix_key:
        return ""

    fix_report = run_dir / f"{report_date}-fix-{fix_key}.md"
    if not fix_report.exists():
        return ""

    content = fix_report.read_text(encoding="utf-8")

    # 解析修复状态表
    fixed = 0
    total = 0
    statuses = []

    for line in content.split("\n"):
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        # 跳过表头和分隔线
        if len(cells) < 4:
            continue
        if cells[1] in ("问题", "---") or cells[1].startswith("-"):
            continue

        status_cell = cells[3] if len(cells) > 3 else ""
        for marker, label in FIX_STATUS_MAP.items():
            if marker in status_cell:
                total += 1
                statuses.append(label)
                if label == "已修复":
                    fixed += 1
                break

    if total == 0:
        return ""

    if fixed == total:
        return f"🟢 全部修复 ({fixed}/{total})"
    elif fixed > 0:
        return f"🟡 部分修复 ({fixed}/{total})"
    else:
        return f"🔴 未修复 (0/{total})"


def parse_fix_status_from_summary(run_dir: Path, report_date: str) -> dict[str, str]:
    """从 CI 报告的修复摘要中解析各阶段修复状态。

    Returns:
        {section_key: fix_status} 映射
    """
    report_path = run_dir / f"{report_date}-ci-report.md"
    if not report_path.exists():
        return {}

    content = report_path.read_text(encoding="utf-8")
    statuses = {}

    in_summary = False
    for line in content.split("\n"):
        if "## 修复摘要" in line:
            in_summary = True
            continue
        if in_summary and line.startswith("## "):
            break
        if in_summary and "|" in line:
            cells = [c.strip() for c in line.split("|")]
            if len(cells) >= 3 and cells[1] not in ("阶段", "---"):
                label = cells[1]
                status = cells[2]
                # 反向映射
                for key, section_label in [
                    ("static", "静态检查"),
                    ("code-review", "代码审查"),
                    ("context", "CONTEXT.md"),
                    ("architecture", "ARCHITECTURE.md"),
                    ("spec", "Spec"),
                ]:
                    if section_label in label:
                        statuses[key] = status
                        break

    return statuses


def build_summary(run_dir: Path, report_date: str) -> str:
    """构建汇总报告。"""
    lines = [
        f"# CI 检查报告",
        f"",
        f"- **日期**: {report_date}",
        f"- **编号**: {run_dir.name}",
        f"",
    ]

    statuses = []
    for key, label in REPORT_SECTIONS:
        report_path = run_dir / f"{report_date}-{key}.md"
        exists = report_path.exists()
        has_failure = False
        if exists:
            content = report_path.read_text(encoding="utf-8")
            has_failure = "执行失败" in content or "执行超时" in content

        # 获取修复状态
        fix_status = parse_fix_status(run_dir, report_date, key)

        if not exists:
            statuses.append((label, "未执行", fix_status))
        elif has_failure:
            statuses.append((label, "执行失败", fix_status))
        else:
            statuses.append((label, "完成", fix_status))

    lines.append("## 执行摘要")
    lines.append("")
    lines.append("| 检查项 | 检查状态 | 修复状态 |")
    lines.append("|--------|----------|----------|")
    for label, status, fix_status in statuses:
        icon = {"完成": "✅", "执行失败": "❌", "未执行": "⏭️"}.get(status, "❓")
        fix_display = fix_status if fix_status else "—"
        lines.append(f"| {label} | {icon} {status} | {fix_display} |")
    lines.append("")

    for key, label in REPORT_SECTIONS:
        report_path = run_dir / f"{report_date}-{key}.md"
        fix_status = parse_fix_status(run_dir, report_date, key)

        lines.append("---")
        lines.append("")
        lines.append(f"## {label}")
        if fix_status:
            lines.append("")
            lines.append(f"> 修复状态: {fix_status}")
        lines.append("")
        lines.append(read_report(report_path))
        lines.append("")

    return "\n".join(lines)


def update_index(run_dir: Path, report_date: str):
    """更新 docs/generated/index.md，追加本次检查记录。"""
    index_path = GENERATED_DIR / "index.md"

    # 读取现有内容
    existing = ""
    if index_path.exists():
        existing = index_path.read_text(encoding="utf-8")

    # 如果有写入指南模板，先删除
    if "<index-write-guide>" in existing:
        existing = existing.split("</index-write-guide>")[-1].strip()

    # 检查是否有修复报告
    fix_reports = list(run_dir.glob(f"{report_date}-fix-*.md"))
    fix_status = ""
    if fix_reports:
        fix_statuses = parse_fix_status_from_summary(run_dir, report_date)
        if fix_statuses:
            status_icons = {
                "🟢 全部修复": "✅",
                "🟡 部分修复": "⚠️",
                "🔴 未修复": "❌",
                "⚪ 无需修复": "✅",
            }
            fixed_count = sum(
                1 for s in fix_statuses.values() if "全部修复" in s or "无需修复" in s
            )
            total_count = len(fix_statuses)
            if fixed_count == total_count:
                fix_status = f"\n - 修复状态：✅ 全部已修复 ({fixed_count}/{total_count})"
            elif fixed_count > 0:
                fix_status = f"\n - 修复状态：⚠️ 部分修复 ({fixed_count}/{total_count})"
            else:
                fix_status = f"\n - 修复状态：❌ 存在未修复项"

    # 构建新条目
    entry = f"""## CI 检查 {run_dir.name}
 - updated_at : {report_date}
 - path: generated/{run_dir.name}/
 - 触发规则：ci-check 技能触发的提交前检查
 - 内容摘要：代码审查 + 文档一致性检查（ARCHITECTURE.md / specs / CONTEXT.md）{fix_status}"""

    # 追加到 index
    if existing:
        new_content = existing + "\n\n" + entry
    else:
        new_content = entry

    index_path.write_text(new_content, encoding="utf-8")
    print(f"已更新: {index_path.relative_to(PROJECT_ROOT)}")


def main():
    parser = argparse.ArgumentParser(description="汇总 CI 检查报告")
    parser.add_argument(
        "--run-dir",
        help="检查编号目录路径 (如 docs/generated/001)",
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="报告日期 (默认今天)",
    )
    args = parser.parse_args()

    if args.run_dir:
        run_dir = Path(args.run_dir)
        if not run_dir.is_absolute():
            run_dir = PROJECT_ROOT / run_dir
    else:
        run_dir = get_latest_run_dir()

    summary = build_summary(run_dir, args.date)

    output_path = run_dir / f"{args.date}-ci-report.md"
    output_path.write_text(summary, encoding="utf-8")
    print(f"汇总报告已生成: {output_path.relative_to(PROJECT_ROOT)}")

    update_index(run_dir, args.date)


if __name__ == "__main__":
    main()
