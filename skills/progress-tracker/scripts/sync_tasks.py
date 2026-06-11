#!/usr/bin/env python3
"""
Progress Tracker - Tasks 同步脚本
支持 tasks.md 和 tasks.html 双向同步

用法：
  python sync_tasks.py md2html    # markdown -> html
  python sync_tasks.py html2md    # html -> markdown
  python sync_tasks.py validate   # 验证数据一致性
"""

import re
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime


@dataclass
class Task:
    """任务数据结构"""
    id: int
    title: str
    source: str
    status: str  # ⏳ 待开始 / 🚧 进行中 / ✅ 已完成 / ❌ 已取消
    created_at: str
    description: str
    priority: Optional[str] = None
    completed_at: Optional[str] = None
    cancel_reason: Optional[str] = None
    branch: Optional[str] = None
    branch_status: Optional[str] = None  # ✅ 已创建 / ⏳ 未创建
    modules: Optional[List[str]] = None
    requirements: Optional[List[str]] = None
    background: Optional[str] = None
    subtasks: Optional[List[str]] = None
    related_docs: Optional[List[str]] = None
    progress: Optional[List[str]] = None
    notes: Optional[str] = None
    has_star: bool = False  # ⭐ 标记

    def to_dict(self) -> Dict:
        """转换为字典，过滤 None 值"""
        result = {}
        for k, v in asdict(self).items():
            if v is not None and v != [] and v != False:
                result[k] = v
        return result


def parse_markdown_tasks(md_content: str) -> List[Task]:
    """解析 markdown 格式的任务列表"""
    tasks = []
    current_section = None

    # 分割成行
    lines = md_content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # 检测 section
        if line == '## 待开始':
            current_section = 'pending'
        elif line == '## 进行中':
            current_section = 'in_progress'
        elif line == '## 已完成':
            current_section = 'completed'

        # 检测任务标题 (### N. Title 或 ### N. Title ⭐)
        task_match = re.match(r'^### (\d+)\.\s+(.+?)(\s*⭐)?$', line)
        if task_match:
            task_id = int(task_match.group(1))
            title = task_match.group(2).strip()
            has_star = task_match.group(3) is not None

            # 收集该任务的所有字段
            fields = {}
            i += 1
            while i < len(lines):
                line = lines[i].strip()

                # 遇到下一个任务或 section 时停止
                if line.startswith('### ') or line.startswith('## ') or line == '---':
                    break

                # 解析字段 (- **key**：value 或 - **key**：)
                field_match = re.match(r'^-\s+\*\*(.+?)\*\*[：:]\s*(.*)$', line)
                if field_match:
                    key = field_match.group(1).strip()
                    value = field_match.group(2).strip()
                    fields[key] = value

                # 解析列表项 (  - value)，但排除字段行
                elif line.startswith('- ') and not line.startswith('- **') and fields:
                    # 获取最后一个字段的 key
                    last_key = list(fields.keys())[-1]
                    last_value = fields[last_key]
                    if isinstance(last_value, list):
                        last_value.append(line[2:].strip())
                    elif last_value == '':
                        # 空值后跟列表项，开始新列表
                        fields[last_key] = [line[2:].strip()]
                    else:
                        fields[last_key] = [last_value, line[2:].strip()]

                # 解析缩进的列表项 (  - **key**：value)
                elif line.startswith('  - ') and fields:
                    last_key = list(fields.keys())[-1]
                    last_value = fields[last_key]
                    if isinstance(last_value, list):
                        last_value.append(line[4:].strip())
                    elif last_value == '':
                        # 空值后跟列表项，开始新列表
                        fields[last_key] = [line[4:].strip()]
                    else:
                        fields[last_key] = [last_value, line[4:].strip()]

                i += 1

            # 构建 Task 对象
            task = Task(
                id=task_id,
                title=title,
                source=fields.get('来源', ''),
                status=fields.get('状态', '⏳ 待开始'),
                created_at=fields.get('创建时间', ''),
                description=fields.get('描述', ''),
                priority=fields.get('优先级'),
                completed_at=fields.get('完成时间'),
                cancel_reason=fields.get('取消原因'),
                branch=fields.get('分支'),
                branch_status=fields.get('分支状态'),
                modules=fields.get('涉及模块') if isinstance(fields.get('涉及模块'), list) else None,
                requirements=fields.get('需求清单') if isinstance(fields.get('需求清单'), list) else None,
                background=fields.get('背景'),
                subtasks=fields.get('子任务拆分') if isinstance(fields.get('子任务拆分'), list) else None,
                related_docs=fields.get('相关文档') if isinstance(fields.get('相关文档'), list) else None,
                progress=fields.get('进度') if isinstance(fields.get('进度'), list) else None,
                notes=fields.get('备注'),
                has_star=has_star
            )
            tasks.append(task)
            continue

        i += 1

    return tasks


def tasks_to_markdown(tasks: List[Task]) -> str:
    """将任务列表转换为 markdown 格式"""
    # 按状态分组
    in_progress = [t for t in tasks if t.status == '🚧 进行中']
    pending = [t for t in tasks if t.status == '⏳ 待开始']
    completed = [t for t in tasks if t.status == '✅ 已完成']
    cancelled = [t for t in tasks if t.status == '❌ 已取消']

    lines = [
        '# 任务列表',
        '',
        '> 此文件由 progress-tracker 自动维护，请勿手动编辑',
        '',
        '---',
        ''
    ]

    # 待开始
    if pending or cancelled:
        lines.append('## 待开始')
        lines.append('')
        for task in sorted(pending, key=lambda t: t.id):
            lines.extend(task_to_markdown(task))
            lines.append('')

    # 进行中
    if in_progress:
        lines.append('## 进行中')
        lines.append('')
        for task in sorted(in_progress, key=lambda t: t.id):
            lines.extend(task_to_markdown(task))
            lines.append('')

    # 已完成
    if completed:
        lines.append('## 已完成')
        lines.append('')
        for task in sorted(completed, key=lambda t: t.id, reverse=True):
            lines.extend(task_to_markdown(task))
            lines.append('')

    return '\n'.join(lines)


def task_to_markdown(task: Task) -> List[str]:
    """将单个任务转换为 markdown 行"""
    star = ' ⭐' if task.has_star else ''
    lines = [f'### {task.id}. {task.title}{star}']

    # 必填字段
    lines.append(f'- **来源**：{task.source}')
    lines.append(f'- **状态**：{task.status}')
    lines.append(f'- **创建时间**：{task.created_at}')

    # 可选字段
    if task.priority:
        lines.append(f'- **优先级**：{task.priority}')

    if task.completed_at:
        lines.append(f'- **完成时间**：{task.completed_at}')

    if task.cancel_reason:
        lines.append(f'- **取消原因**：{task.cancel_reason}')

    if task.branch:
        lines.append(f'- **分支**：{task.branch}')

    if task.branch_status:
        lines.append(f'- **分支状态**：{task.branch_status}')

    lines.append(f'- **描述**：{task.description}')

    if task.background:
        lines.append(f'- **背景**：{task.background}')

    if task.modules:
        lines.append('- **涉及模块**：')
        for mod in task.modules:
            lines.append(f'  - {mod}')

    if task.requirements:
        lines.append('- **需求清单**：')
        for req in task.requirements:
            lines.append(f'  - {req}')

    if task.subtasks:
        lines.append('- **子任务拆分**：')
        for sub in task.subtasks:
            lines.append(f'  - {sub}')

    if task.related_docs:
        lines.append('- **相关文档**：')
        for doc in task.related_docs:
            lines.append(f'  - {doc}')

    if task.progress:
        lines.append('- **进度**：')
        for prog in task.progress:
            lines.append(f'  - {prog}')

    if task.notes:
        lines.append(f'- **备注**：{task.notes}')

    return lines


def tasks_to_json(tasks: List[Task]) -> str:
    """将任务列表转换为 JSON 格式（供 HTML 使用）"""
    data = [task.to_dict() for task in tasks]
    return json.dumps(data, ensure_ascii=False, indent=2)


def json_to_tasks(json_content: str) -> List[Task]:
    """从 JSON 解析任务列表"""
    data = json.loads(json_content)
    tasks = []
    for item in data:
        task = Task(
            id=item['id'],
            title=item['title'],
            source=item['source'],
            status=item['status'],
            created_at=item['created_at'],
            description=item['description'],
            priority=item.get('priority'),
            completed_at=item.get('completed_at'),
            cancel_reason=item.get('cancel_reason'),
            branch=item.get('branch'),
            branch_status=item.get('branch_status'),
            modules=item.get('modules'),
            requirements=item.get('requirements'),
            background=item.get('background'),
            subtasks=item.get('subtasks'),
            related_docs=item.get('related_docs'),
            progress=item.get('progress'),
            notes=item.get('notes'),
            has_star=item.get('has_star', False)
        )
        tasks.append(task)
    return tasks


def md2html(md_path: str, html_path: str):
    """将 markdown 同步到 HTML"""
    md_content = Path(md_path).read_text(encoding='utf-8')
    tasks = parse_markdown_tasks(md_content)

    # 读取 HTML 模板
    html_template = Path(html_path).read_text(encoding='utf-8')

    # 将任务数据注入到 HTML 中
    json_data = tasks_to_json(tasks)

    # 替换 HTML 中的数据占位符
    pattern = r'const TASKS_DATA = \[.*?\];'
    replacement = f'const TASKS_DATA = {json_data};'

    if re.search(pattern, html_template, re.DOTALL):
        html_content = re.sub(pattern, replacement, html_template, flags=re.DOTALL)
    else:
        # 如果没有找到占位符，在 </script> 前插入
        insert_point = html_content.rfind('</script>')
        html_content = html_template[:insert_point] + f'\nconst TASKS_DATA = {json_data};\n' + html_template[insert_point:]

    Path(html_path).write_text(html_content, encoding='utf-8')
    print(f'✅ 已同步 {len(tasks)} 个任务到 {html_path}')


def html2md(html_path: str, md_path: str):
    """将 HTML 同步到 markdown"""
    html_content = Path(html_path).read_text(encoding='utf-8')

    # 从 HTML 中提取 JSON 数据
    match = re.search(r'const TASKS_DATA = (\[.*?\]);', html_content, re.DOTALL)
    if not match:
        print('❌ 无法从 HTML 中提取任务数据')
        return

    json_data = match.group(1)
    tasks = json_to_tasks(json_data)

    # 生成 markdown
    md_content = tasks_to_markdown(tasks)

    Path(md_path).write_text(md_content, encoding='utf-8')
    print(f'✅ 已同步 {len(tasks)} 个任务到 {md_path}')


def validate(md_path: str, html_path: str):
    """验证 markdown 和 HTML 数据一致性"""
    md_content = Path(md_path).read_text(encoding='utf-8')
    html_content = Path(html_path).read_text(encoding='utf-8')

    # 解析 markdown
    md_tasks = parse_markdown_tasks(md_content)
    md_dict = {t.id: t for t in md_tasks}

    # 解析 HTML
    match = re.search(r'const TASKS_DATA = (\[.*?\]);', html_content, re.DOTALL)
    if not match:
        print('❌ 无法从 HTML 中提取任务数据')
        return False

    html_tasks = json_to_tasks(match.group(1))
    html_dict = {t.id: t for t in html_tasks}

    # 比较
    errors = []

    # 检查数量
    if len(md_tasks) != len(html_tasks):
        errors.append(f'任务数量不一致: md={len(md_tasks)}, html={len(html_tasks)}')

    # 检查每个任务
    all_ids = set(md_dict.keys()) | set(html_dict.keys())
    for task_id in sorted(all_ids):
        if task_id not in md_dict:
            errors.append(f'任务 #{task_id} 在 md 中不存在')
        elif task_id not in html_dict:
            errors.append(f'任务 #{task_id} 在 html 中不存在')
        else:
            md_task = md_dict[task_id]
            html_task = html_dict[task_id]

            # 比较关键字段
            for field in ['title', 'status', 'priority', 'branch']:
                md_val = getattr(md_task, field)
                html_val = getattr(html_task, field)
                if md_val != html_val:
                    errors.append(f'任务 #{task_id} 的 {field} 不一致: md="{md_val}", html="{html_val}"')

    if errors:
        print('❌ 验证失败:')
        for error in errors:
            print(f'  - {error}')
        return False
    else:
        print(f'✅ 验证通过: {len(md_tasks)} 个任务完全一致')
        return True


def main():
    if len(sys.argv) < 2:
        print('用法:')
        print('  python sync_tasks.py md2html    # markdown -> html')
        print('  python sync_tasks.py html2md    # html -> markdown')
        print('  python sync_tasks.py validate   # 验证数据一致性')
        sys.exit(1)

    command = sys.argv[1]

    # 默认路径
    base_dir = Path(__file__).parent.parent.parent.parent
    md_path = base_dir / 'docs' / 'progress' / 'tasks.md'
    html_path = Path(__file__).parent.parent / 'assets' / 'tasks.html'

    # 检查文件是否存在
    if not md_path.exists():
        print(f'❌ 找不到 markdown 文件: {md_path}')
        sys.exit(1)

    if command == 'md2html':
        if not html_path.exists():
            print(f'❌ 找不到 HTML 文件: {html_path}')
            sys.exit(1)
        md2html(str(md_path), str(html_path))

    elif command == 'html2md':
        if not html_path.exists():
            print(f'❌ 找不到 HTML 文件: {html_path}')
            sys.exit(1)
        html2md(str(html_path), str(md_path))

    elif command == 'validate':
        if not html_path.exists():
            print(f'❌ 找不到 HTML 文件: {html_path}')
            sys.exit(1)
        validate(str(md_path), str(html_path))

    else:
        print(f'❌ 未知命令: {command}')
        sys.exit(1)


if __name__ == '__main__':
    main()
