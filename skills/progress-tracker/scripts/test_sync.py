#!/usr/bin/env python3
"""
sync_tasks.py 验证测试脚本
测试功能：
1. 解析 tasks.md 文件
2. 生成正确的 markdown 格式
3. JSON 序列化和反向序列化
4. 处理各种字段（必填字段、可选字段、列表字段）
5. 处理特殊字符和 emoji
"""

import sys
import json
import tempfile
from pathlib import Path
from dataclasses import asdict

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from sync_tasks import (
    Task, parse_markdown_tasks, tasks_to_markdown,
    tasks_to_json, json_to_tasks, md2html, html2md, validate
)

# 测试结果统计
test_results = []


def test(name, func):
    """运行单个测试"""
    try:
        result = func()
        test_results.append({"name": name, "passed": True, "error": None})
        print(f"  [PASS] {name}")
        return result
    except AssertionError as e:
        test_results.append({"name": name, "passed": False, "error": str(e)})
        print(f"  [FAIL] {name}: {e}")
        return None
    except Exception as e:
        test_results.append({"name": name, "passed": False, "error": str(e)})
        print(f"  [ERROR] {name}: {e}")
        return None


def test_parse_real_tasks_md():
    """测试解析真实的 tasks.md 文件"""
    md_path = Path(__file__).parent.parent.parent.parent / "docs" / "progress" / "tasks.md"
    if not md_path.exists():
        raise FileNotFoundError(f"tasks.md not found at {md_path}")

    md_content = md_path.read_text(encoding="utf-8")
    tasks = parse_markdown_tasks(md_content)

    print(f"\n  解析到 {len(tasks)} 个任务")
    assert len(tasks) >= 32, f"Expected at least 32 tasks, got {len(tasks)}"

    # 验证一些特定任务
    task_1 = next((t for t in tasks if t.id == 1), None)
    assert task_1 is not None, "Task #1 not found"
    assert task_1.title == "提示词优化 - 群聊工具使用", f"Task #1 title mismatch: {task_1.title}"

    task_32 = next((t for t in tasks if t.id == 32), None)
    assert task_32 is not None, "Task #32 not found"
    assert task_32.title == "Electron 打包", f"Task #32 title mismatch: {task_32.title}"

    return tasks


def test_parse_fields():
    """测试字段解析"""
    test_md = """### 100. 测试任务
- **来源**：测试来源
- **状态**：🚧 进行中
- **创建时间**：2026-06-11
- **优先级**：高
- **完成时间**：2026-06-12
- **分支**：feat-test
- **分支状态**：✅ 已创建
- **描述**：这是一个测试任务
- **背景**：测试背景
- **涉及模块**：
  - 前端模块
  - 后端模块
- **需求清单**：
  - 需求1
  - 需求2
- **子任务拆分**：
  - 子任务1
  - 子任务2
- **相关文档**：
  - docs/test.md
- **进度**：
  - ✅ 步骤1完成
  - ⏳ 步骤2进行中
- **备注**：这是备注
"""

    tasks = parse_markdown_tasks(test_md)
    assert len(tasks) == 1, f"Expected 1 task, got {len(tasks)}"

    task = tasks[0]
    assert task.id == 100
    assert task.title == "测试任务"
    assert task.source == "测试来源"
    assert task.status == "🚧 进行中"
    assert task.created_at == "2026-06-11"
    assert task.priority == "高"
    assert task.completed_at == "2026-06-12"
    assert task.branch == "feat-test"
    assert task.branch_status == "✅ 已创建"
    assert task.description == "这是一个测试任务"
    assert task.background == "测试背景"
    assert task.modules == ["前端模块", "后端模块"]
    assert task.requirements == ["需求1", "需求2"]
    assert task.subtasks == ["子任务1", "子任务2"]
    assert task.related_docs == ["docs/test.md"]
    assert task.progress == ["✅ 步骤1完成", "⏳ 步骤2进行中"]
    assert task.notes == "这是备注"


def test_parse_optional_fields_empty():
    """测试空可选字段"""
    test_md = """### 101. 简单任务
- **来源**：测试
- **状态**：⏳ 待开始
- **创建时间**：2026-06-11
- **描述**：简单描述
"""

    tasks = parse_markdown_tasks(test_md)
    assert len(tasks) == 1

    task = tasks[0]
    assert task.priority is None
    assert task.completed_at is None
    assert task.cancel_reason is None
    assert task.branch is None
    assert task.modules is None
    assert task.requirements is None


def test_parse_star():
    """测试星标任务解析"""
    test_md = """### 102. 星标任务 ⭐
- **来源**：测试
- **状态**：⏳ 待开始
- **创建时间**：2026-06-11
- **描述**：带星标的任务
"""

    tasks = parse_markdown_tasks(test_md)
    assert len(tasks) == 1
    assert tasks[0].has_star == True

    test_md_no_star = """### 103. 普通任务
- **来源**：测试
- **状态**：⏳ 待开始
- **创建时间**：2026-06-11
- **描述**：不带星标
"""

    tasks_no_star = parse_markdown_tasks(test_md_no_star)
    assert tasks_no_star[0].has_star == False


def test_parse_cancelled_task():
    """测试已取消任务"""
    test_md = """### 104. 已取消任务
- **来源**：测试
- **状态**：❌ 已取消
- **创建时间**：2026-06-11
- **取消原因**：不再需要
- **描述**：这个任务被取消了
"""

    tasks = parse_markdown_tasks(test_md)
    assert tasks[0].status == "❌ 已取消"
    assert tasks[0].cancel_reason == "不再需要"


def test_markdown_generation():
    """测试 markdown 生成"""
    tasks = [
        Task(
            id=200,
            title="生成测试任务",
            source="测试来源",
            status="⏳ 待开始",
            created_at="2026-06-11",
            description="测试描述",
            priority="高",
            has_star=True
        ),
        Task(
            id=201,
            title="进行中任务",
            source="测试",
            status="🚧 进行中",
            created_at="2026-06-11",
            description="进行中的任务"
        ),
        Task(
            id=202,
            title="已完成任务",
            source="测试",
            status="✅ 已完成",
            created_at="2026-06-11",
            description="已完成的任务",
            completed_at="2026-06-12"
        )
    ]

    md_content = tasks_to_markdown(tasks)

    # 验证基本结构
    assert "# 任务列表" in md_content
    assert "## 待开始" in md_content
    assert "## 进行中" in md_content
    assert "## 已完成" in md_content

    # 验证任务内容
    assert "### 200. 生成测试任务 ⭐" in md_content
    assert "### 201. 进行中任务" in md_content
    assert "### 202. 已完成任务" in md_content
    assert "- **优先级**：高" in md_content
    assert "- **完成时间**：2026-06-12" in md_content


def test_json_serialization():
    """测试 JSON 序列化和反序列化"""
    original_tasks = [
        Task(
            id=300,
            title="JSON 测试任务",
            source="测试",
            status="⏳ 待开始",
            created_at="2026-06-11",
            description="测试 JSON 序列化",
            priority="中",
            modules=["模块A", "模块B"],
            requirements=["需求1", "需求2"],
            has_star=False
        ),
        Task(
            id=301,
            title="特殊字符任务 🎉",
            source="测试 with special chars: <>&\"'",
            status="🚧 进行中",
            created_at="2026-06-11",
            description="包含 emoji 🚀 和特殊字符 <script>alert('xss')</script>"
        )
    ]

    # 序列化
    json_str = tasks_to_json(original_tasks)
    json_data = json.loads(json_str)

    assert len(json_data) == 2
    assert json_data[0]["id"] == 300
    assert json_data[0]["modules"] == ["模块A", "模块B"]

    # 验证特殊字符
    assert "🎉" in json_data[1]["title"]
    assert "<script>" in json_data[1]["description"]

    # 反序列化
    restored_tasks = json_to_tasks(json_str)
    assert len(restored_tasks) == 2
    assert restored_tasks[0].id == 300
    assert restored_tasks[0].modules == ["模块A", "模块B"]
    assert restored_tasks[1].title == "特殊字符任务 🎉"


def test_task_to_dict():
    """测试 Task.to_dict() 过滤 None 值"""
    task = Task(
        id=400,
        title="字典测试",
        source="测试",
        status="⏳ 待开始",
        created_at="2026-06-11",
        description="测试",
        priority=None,
        completed_at=None,
        modules=None,
        has_star=False
    )

    d = task.to_dict()
    assert "priority" not in d
    assert "completed_at" not in d
    assert "modules" not in d
    assert "has_star" not in d  # False should be filtered
    assert d["id"] == 400


def test_special_characters():
    """测试特殊字符处理"""
    test_md = """### 500. 包含特殊字符的任务 <>&"'
- **来源**：用户 "直接" 输入
- **状态**：⏳ 待开始
- **创建时间**：2026-06-11
- **描述**：这个描述包含 <html> 标签 & 特殊字符 "引号" 和 '单引号'
- **备注**：emoji 测试 🎉🚀✨
"""

    tasks = parse_markdown_tasks(test_md)
    assert len(tasks) == 1
    assert "<>&\"'" in tasks[0].title
    assert "<html>" in tasks[0].description
    assert "🎉" in tasks[0].notes


def test_multiline_description():
    """测试多行描述（列表形式）"""
    test_md = """### 600. 多行描述任务
- **来源**：测试
- **状态**：⏳ 待开始
- **创建时间**：2026-06-11
- **描述**：第一行描述
- **涉及模块**：
  - 前端
  - 后端
  - MCP
- **备注**：这个任务有多个模块
"""

    tasks = parse_markdown_tasks(test_md)
    assert tasks[0].modules == ["前端", "后端", "MCP"]


def test_roundtrip_consistency():
    """测试 md -> parse -> generate -> parse 一致性"""
    original_md = """### 700. 往返测试任务 ⭐
- **来源**：测试来源
- **状态**：🚧 进行中
- **创建时间**：2026-06-11
- **优先级**：高
- **描述**：测试往返一致性
- **涉及模块**：
  - 模块A
  - 模块B
- **备注**：备注内容
"""

    # 第一次解析
    tasks1 = parse_markdown_tasks(original_md)

    # 生成 markdown
    generated_md = tasks_to_markdown(tasks1)

    # 第二次解析
    tasks2 = parse_markdown_tasks(generated_md)

    assert len(tasks1) == len(tasks2)
    assert tasks1[0].id == tasks2[0].id
    assert tasks1[0].title == tasks2[0].title
    assert tasks1[0].status == tasks2[0].status
    assert tasks1[0].modules == tasks2[0].modules
    assert tasks1[0].notes == tasks2[0].notes


def test_md2html_command():
    """测试 md2html 命令"""
    # 找到实际的文件路径
    base_dir = Path(__file__).parent.parent.parent.parent
    md_path = base_dir / "docs" / "progress" / "tasks.md"
    html_path = Path(__file__).parent.parent / "assets" / "tasks.html"

    if not md_path.exists():
        raise FileNotFoundError(f"tasks.md not found: {md_path}")
    if not html_path.exists():
        raise FileNotFoundError(f"tasks.html not found: {html_path}")

    # 备份原始 HTML
    original_html = html_path.read_text(encoding="utf-8")

    try:
        # 运行 md2html
        md2html(str(md_path), str(html_path))

        # 验证 HTML 被更新
        updated_html = html_path.read_text(encoding="utf-8")
        assert "const TASKS_DATA" in updated_html, "TASKS_DATA not found in HTML"

        # 验证 JSON 数据有效
        import re
        match = re.search(r"const TASKS_DATA = (\[.*?\]);", updated_html, re.DOTALL)
        assert match, "Could not extract TASKS_DATA from HTML"

        json_data = json.loads(match.group(1))
        assert len(json_data) >= 32, f"Expected at least 32 tasks in HTML, got {len(json_data)}"

        print(f"  -> HTML 中包含 {len(json_data)} 个任务")

    finally:
        # 恢复原始 HTML
        html_path.write_text(original_html, encoding="utf-8")


def test_validate_command():
    """测试 validate 命令"""
    base_dir = Path(__file__).parent.parent.parent.parent
    md_path = base_dir / "docs" / "progress" / "tasks.md"
    html_path = Path(__file__).parent.parent / "assets" / "tasks.html"

    if not md_path.exists() or not html_path.exists():
        raise FileNotFoundError("Required files not found")

    # 先同步一下
    md2html(str(md_path), str(html_path))

    # 运行验证 - 应该通过
    result = validate(str(md_path), str(html_path))
    assert result == True, "Validation should pass after sync"


def test_json_roundtrip_full():
    """测试完整的 JSON 往返（使用真实数据）"""
    md_path = Path(__file__).parent.parent.parent.parent / "docs" / "progress" / "tasks.md"
    md_content = md_path.read_text(encoding="utf-8")

    # 解析
    original_tasks = parse_markdown_tasks(md_content)

    # 转 JSON
    json_str = tasks_to_json(original_tasks)

    # 从 JSON 恢复
    restored_tasks = json_to_tasks(json_str)

    # 验证数量
    assert len(original_tasks) == len(restored_tasks), \
        f"Task count mismatch: {len(original_tasks)} vs {len(restored_tasks)}"

    # 验证每个任务的关键字段
    for orig, restored in zip(original_tasks, restored_tasks):
        assert orig.id == restored.id, f"ID mismatch for task {orig.id}"
        assert orig.title == restored.title, f"Title mismatch for task {orig.id}"
        assert orig.status == restored.status, f"Status mismatch for task {orig.id}"
        assert orig.modules == restored.modules, f"Modules mismatch for task {orig.id}"

    print(f"  -> {len(original_tasks)} 个任务 JSON 往返测试通过")


def main():
    print("=" * 60)
    print("sync_tasks.py 验证测试")
    print("=" * 60)

    print("\n[1] 解析真实 tasks.md")
    test("解析 tasks.md 文件 (32+ 任务)", test_parse_real_tasks_md)

    print("\n[2] 字段解析测试")
    test("必填字段解析", test_parse_fields)
    test("可选字段为空", test_parse_optional_fields_empty)
    test("星标任务解析", test_parse_star)
    test("已取消任务解析", test_parse_cancelled_task)

    print("\n[3] Markdown 生成测试")
    test("Markdown 格式生成", test_markdown_generation)

    print("\n[4] JSON 序列化测试")
    test("JSON 序列化/反序列化", test_json_serialization)
    test("Task.to_dict() 过滤", test_task_to_dict)

    print("\n[5] 特殊字符测试")
    test("特殊字符和 emoji", test_special_characters)
    test("多行描述和列表", test_multiline_description)

    print("\n[6] 一致性测试")
    test("往返一致性 (md->parse->generate->parse)", test_roundtrip_consistency)
    test("完整 JSON 往返", test_json_roundtrip_full)

    print("\n[7] 命令测试")
    test("md2html 命令", test_md2html_command)
    test("validate 命令", test_validate_command)

    # 统计结果
    print("\n" + "=" * 60)
    total = len(test_results)
    passed = sum(1 for r in test_results if r["passed"])
    failed = total - passed

    print(f"测试结果: {passed}/{total} 通过, {failed} 失败")

    if failed > 0:
        print("\n失败的测试:")
        for r in test_results:
            if not r["passed"]:
                print(f"  - {r['name']}: {r['error']}")

    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
