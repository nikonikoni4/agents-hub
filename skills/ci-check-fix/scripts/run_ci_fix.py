#!/usr/bin/env python3
"""CI 修复主入口。

读取 CI 报告，按优先级修复各类问题：
1. 代码错误（静态检查）
2. Code Review 问题
3. CONTEXT.md 一致性
4. ARCHITECTURE.md 一致性
5. Spec 一致性

每项修复后更新报告中的修复状态。

用法:
    python run_ci_fix.py                          # 完整修复流程
    python run_ci_fix.py --only static            # 仅修复静态检查
    python run_ci_fix.py --only code-review       # 仅修复代码审查问题
    python run_ci_fix.py --only context           # 仅修复 CONTEXT.md
    python run_ci_fix.py --only architecture      # 仅修复 ARCHITECTURE.md
    python run_ci_fix.py --only spec              # 仅修复 spec
    python run_ci_fix.py --run-dir docs/generated/001  # 指定报告目录
"""

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
GENERATED_DIR = PROJECT_ROOT / "docs" / "generated"

# 修复阶段定义（按优先级排序）
FIX_STAGES = [
    "static",
    "code-review",
    "context",
    "architecture",
    "spec",
]


def get_latest_run_dir() -> Path:
    """获取最新的编号目录。"""
    existing = [
        d for d in GENERATED_DIR.iterdir()
        if d.is_dir() and d.name.isdigit()
    ]
    if not existing:
        raise FileNotFoundError("没有找到任何检查编号目录，请先运行 ci-check")
    return max(existing, key=lambda d: int(d.name))


def find_ci_report(run_dir: Path) -> Path:
    """在编号目录中找到 CI 汇总报告。"""
    reports = list(run_dir.glob("*-ci-report.md"))
    if not reports:
        raise FileNotFoundError(f"在 {run_dir} 中未找到 CI 报告")
    return reports[0]


def parse_report_sections(report_path: Path) -> dict[str, str]:
    """解析 CI 报告，按章节分割。"""
    content = report_path.read_text(encoding="utf-8")
    sections = {}
    current_section = "header"
    current_lines = []

    for line in content.split("\n"):
        if line.startswith("## ") and line != "## 执行摘要":
            if current_lines:
                sections[current_section] = "\n".join(current_lines)
            current_section = line[3:].strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_section] = "\n".join(current_lines)

    return sections


def add_fix_status_to_section(section_content: str, fixes: list[dict]) -> str:
    """在章节内容中追加修复状态表。"""
    status_table = "\n### 修复状态\n\n"
    status_table += "| 问题 | 严重程度 | 修复状态 | 修复说明 |\n"
    status_table += "|------|----------|----------|----------|\n"

    for fix in fixes:
        severity = fix.get("severity", "Warning")
        status = fix.get("status", "🟡 待修复")
        desc = fix.get("description", "")
        note = fix.get("note", "")
        status_table += f"| {desc} | {severity} | {status} | {note} |\n"

    return section_content + status_table


def run_fix_static(run_dir: Path, report_path: Path) -> list[dict]:
    """Stage 1: 修复静态检查错误。"""
    print("\n" + "=" * 60)
    print("Stage 1: 修复代码错误（静态检查）")
    print("=" * 60)

    fixes = []

    # 读取静态检查相关的报告内容
    sections = parse_report_sections(report_path)

    # 检查后端
    print("\n--- 后端 make check ---")
    try:
        result = subprocess.run(
            ["make", "check"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            print("后端检查仍有失败项，尝试修复...")
            # 尝试运行自动格式化
            subprocess.run(
                ["make", "format"],
                cwd=str(PROJECT_ROOT),
                timeout=120,
            )
            # 再次检查
            result = subprocess.run(
                ["make", "check"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                fixes.append({
                    "description": "后端静态检查",
                    "severity": "Critical",
                    "status": "🟢 已修复",
                    "note": "通过 make format 自动修复格式问题",
                })
            else:
                fixes.append({
                    "description": "后端静态检查",
                    "severity": "Critical",
                    "status": "🔴 无法修复",
                    "note": f"自动修复后仍失败: {result.stderr[:200]}",
                })
        else:
            fixes.append({
                "description": "后端静态检查",
                "severity": "Critical",
                "status": "⚪ 无需修复",
                "note": "检查已通过",
            })
    except Exception as e:
        fixes.append({
            "description": "后端静态检查",
            "severity": "Critical",
            "status": "🔴 无法修复",
            "note": str(e)[:200],
        })

    # 检查前端
    print("\n--- 前端 make check ---")
    frontend_dir = PROJECT_ROOT / "frontend"
    try:
        result = subprocess.run(
            ["make", "check"],
            cwd=str(frontend_dir),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            print("前端检查仍有失败项，尝试修复...")
            subprocess.run(
                ["make", "format"],
                cwd=str(frontend_dir),
                timeout=120,
            )
            result = subprocess.run(
                ["make", "check"],
                cwd=str(frontend_dir),
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                fixes.append({
                    "description": "前端静态检查",
                    "severity": "Critical",
                    "status": "🟢 已修复",
                    "note": "通过 make format 自动修复格式问题",
                })
            else:
                fixes.append({
                    "description": "前端静态检查",
                    "severity": "Critical",
                    "status": "🔴 无法修复",
                    "note": f"自动修复后仍失败: {result.stderr[:200]}",
                })
        else:
            fixes.append({
                "description": "前端静态检查",
                "severity": "Critical",
                "status": "⚪ 无需修复",
                "note": "检查已通过",
            })
    except Exception as e:
        fixes.append({
            "description": "前端静态检查",
            "severity": "Critical",
            "status": "🔴 无法修复",
            "note": str(e)[:200],
        })

    return fixes


def run_fix_agent_stage(stage_name: str, section_label: str, run_dir: Path, report_path: Path) -> list[dict]:
    """运行单个 Agent 修复阶段。"""
    print(f"\n--- {section_label} 修复 ---")

    # 读取对应章节内容
    sections = parse_report_sections(report_path)
    section_content = None
    for key, value in sections.items():
        if section_label in key or stage_name.replace("-", "") in key.replace(" ", "").replace("-", ""):
            section_content = value
            break

    if not section_content:
        print(f"未找到 {section_label} 章节，跳过")
        return [{
            "description": section_label,
            "severity": "Warning",
            "status": "⏭️ 跳过",
            "note": "报告中未找到对应章节",
        }]

    # 构建修复 prompt
    prompt = f"""你是一个代码修复专家。请根据以下 CI 检查报告中的 {section_label} 部分，修复发现的问题。

报告内容：
{section_content}

修复要求：
1. 只修复报告中明确列出的问题
2. 每项修复后验证不引入新问题
3. 对于无法确定如何修复的问题，标记为"无法修复"
4. 对于 spec 和代码之间的歧义，标记为"待讨论"

请直接开始修复，修复完成后输出修复结果摘要。
"""

    output_path = run_dir / f"{date.today().isoformat()}-fix-{stage_name}.md"

    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "text",
        "--max-turns",
        "50",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=900,  # 15 分钟超时
        )

        if result.returncode == 0:
            output_path.write_text(result.stdout, encoding="utf-8")
            print(f"✅ {section_label} 修复完成 → {output_path.relative_to(PROJECT_ROOT)}")
            return [{
                "description": section_label,
                "severity": "Warning",
                "status": "🟢 已修复",
                "note": f"详见 {output_path.name}",
            }]
        else:
            print(f"❌ {section_label} 修复失败")
            return [{
                "description": section_label,
                "severity": "Warning",
                "status": "🔴 无法修复",
                "note": f"Agent 执行失败 (exit code {result.returncode})",
            }]

    except subprocess.TimeoutExpired:
        print(f"❌ {section_label} 修复超时")
        return [{
            "description": section_label,
            "severity": "Warning",
            "status": "🔴 无法修复",
            "note": "执行超时 (900s)",
        }]
    except FileNotFoundError:
        print("❌ 未找到 claude CLI")
        return [{
            "description": section_label,
            "severity": "Warning",
            "status": "🔴 无法修复",
            "note": "未找到 claude CLI",
        }]


def update_report_with_fix_status(report_path: Path, all_fixes: dict[str, list[dict]]):
    """更新 CI 报告，添加修复状态。"""
    content = report_path.read_text(encoding="utf-8")

    # 在报告开头添加修复摘要
    summary_lines = [
        "",
        "## 修复摘要",
        "",
        "| 阶段 | 修复状态 |",
        "|------|----------|",
    ]

    stage_labels = {
        "static": "静态检查",
        "code-review": "代码审查",
        "context": "CONTEXT.md",
        "architecture": "ARCHITECTURE.md",
        "spec": "Spec",
    }

    for stage, fixes in all_fixes.items():
        label = stage_labels.get(stage, stage)
        if not fixes:
            icon = "⏭️ 跳过"
        elif all(f["status"] == "🟢 已修复" for f in fixes):
            icon = "🟢 全部修复"
        elif any(f["status"] == "🟢 已修复" for f in fixes):
            icon = "🟡 部分修复"
        elif all(f["status"] == "⚪ 无需修复" for f in fixes):
            icon = "⚪ 无需修复"
        else:
            icon = "🔴 存在未修复项"
        summary_lines.append(f"| {label} | {icon} |")

    summary_text = "\n".join(summary_lines)

    # 在执行摘要之后插入修复摘要
    if "## 执行摘要" in content:
        # 找到执行摘要的结束位置（下一个 --- 或 ##）
        insert_pos = content.find("---", content.find("## 执行摘要"))
        if insert_pos == -1:
            insert_pos = content.find("\n## ", content.find("## 执行摘要") + 1)
        if insert_pos != -1:
            content = content[:insert_pos] + summary_text + "\n\n" + content[insert_pos:]
    else:
        content = content + "\n" + summary_text

    report_path.write_text(content, encoding="utf-8")
    print(f"\n已更新报告: {report_path.relative_to(PROJECT_ROOT)}")


def main():
    parser = argparse.ArgumentParser(description="CI 修复主入口")
    parser.add_argument(
        "--only",
        choices=FIX_STAGES,
        help="仅修复指定阶段",
    )
    parser.add_argument(
        "--run-dir",
        help="CI 报告编号目录路径 (如 docs/generated/001)",
    )
    args = parser.parse_args()

    # 确定报告目录
    if args.run_dir:
        run_dir = Path(args.run_dir)
        if not run_dir.is_absolute():
            run_dir = PROJECT_ROOT / run_dir
    else:
        run_dir = get_latest_run_dir()

    report_path = find_ci_report(run_dir)

    print(f"CI 修复开始 — {date.today().isoformat()}")
    print(f"报告目录: {run_dir.relative_to(PROJECT_ROOT)}")
    print(f"报告文件: {report_path.name}")

    all_fixes = {}

    # 确定要执行的阶段
    if args.only:
        stages = [args.only]
    else:
        stages = FIX_STAGES

    for stage in stages:
        if stage == "static":
            all_fixes["static"] = run_fix_static(run_dir, report_path)
        elif stage == "code-review":
            all_fixes["code-review"] = run_fix_agent_stage(
                "code-review", "代码审查", run_dir, report_path
            )
        elif stage == "context":
            all_fixes["context"] = run_fix_agent_stage(
                "context", "CONTEXT.md 一致性", run_dir, report_path
            )
        elif stage == "architecture":
            all_fixes["architecture"] = run_fix_agent_stage(
                "architecture", "ARCHITECTURE.md 一致性", run_dir, report_path
            )
        elif stage == "spec":
            all_fixes["spec"] = run_fix_agent_stage(
                "spec", "docs/specs 一致性", run_dir, report_path
            )

    # 更新报告
    update_report_with_fix_status(report_path, all_fixes)

    # 最终状态
    print("\n" + "=" * 60)
    print("CI 修复完成")
    print("=" * 60)

    has_failures = any(
        f["status"] in ("🔴 无法修复", "🟡 待修复")
        for fixes in all_fixes.values()
        for f in fixes
    )

    if has_failures:
        print("⚠️ 部分问题未能自动修复，请查看报告详情")
        sys.exit(1)
    else:
        print("✅ 所有问题已处理")
        sys.exit(0)


if __name__ == "__main__":
    main()
