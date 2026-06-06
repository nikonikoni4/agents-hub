"""验证spec或计划文档是否符合用户意图。

用法:
    python skills/spec-verifier/scripts/verify_spec.py <session_id> <claude_config_dir> [--document <document_path>]

参数:
    session_id: 会话ID
    claude_config_dir: Claude配置目录路径
    --document: 可选，指定要审查的文档路径

输出:
    验证报告
"""

import json
import sys
import argparse
from pathlib import Path


def read_session_data(session_id: str, config_dir: Path) -> dict:
    """读取会话数据。"""
    sessions_dir = config_dir / "sessions"

    if not sessions_dir.exists():
        raise FileNotFoundError(f"会话目录不存在: {sessions_dir}")

    # 查找匹配的会话文件
    for session_file in sessions_dir.glob("*.json"):
        if session_id in session_file.stem:
            with open(session_file, 'r', encoding='utf-8') as f:
                return json.load(f)

    raise FileNotFoundError(f"未找到会话: {session_id}")


def extract_user_requirements(session_data: dict) -> list:
    """提取用户需求。"""
    messages = session_data.get('messages', [])
    user_requirements = []

    for msg in messages:
        if msg.get('role') == 'user':
            content = msg.get('content', '')
            # 提取包含需求的关键词
            if any(keyword in content.lower() for keyword in ['需要', '希望', '要求', '必须', '应该']):
                user_requirements.append({
                    'content': content,
                    'timestamp': msg.get('timestamp', '')
                })

    return user_requirements


def extract_ai_documents(session_data: dict) -> list:
    """提取AI生成的文档。"""
    messages = session_data.get('messages', [])
    ai_documents = []

    for msg in messages:
        if msg.get('role') == 'assistant':
            content = msg.get('content', '')
            # 检查是否包含文档内容（更宽松的匹配）
            # 包括标题、列表、代码块等Markdown元素
            if any(keyword in content.lower() for keyword in ['spec', 'plan', 'specification', 'document', '##', '- ', '```']):
                ai_documents.append({
                    'content': content,
                    'timestamp': msg.get('timestamp', '')
                })

    return ai_documents


def compare_requirements_with_documents(requirements: list, documents: list) -> dict:
    """对比需求和文档。"""
    results = {
        'covered': [],
        'missing': [],
        'extra': []
    }

    # 改进的关键词匹配逻辑
    for req in requirements:
        req_content = req['content'].lower()
        covered = False

        # 提取需求中的关键名词和动词
        req_keywords = set()
        # 简单的关键词提取（实际应用中可能需要更复杂的NLP分析）
        # 对于中文，我们提取2-4个字的词组
        for i in range(len(req_content)):
            for j in range(i+2, min(i+5, len(req_content)+1)):
                word = req_content[i:j]
                if len(word) > 1:  # 过滤单个字符
                    req_keywords.add(word)

        for doc in documents:
            doc_content = doc['content'].lower()
            # 检查需求关键词是否在文档中
            matched_keywords = set()
            for keyword in req_keywords:
                if keyword in doc_content:
                    matched_keywords.add(keyword)

            # 如果超过10%的关键词匹配，则认为需求被覆盖
            if len(req_keywords) > 0 and len(matched_keywords) / len(req_keywords) > 0.1:
                covered = True
                break

        if covered:
            results['covered'].append(req)
        else:
            results['missing'].append(req)

    return results


def generate_report(comparison_results: dict, session_data: dict) -> str:
    """生成验证报告。"""
    report = []
    report.append("# 文档验证报告")
    report.append("")
    report.append("## 审查概览")
    report.append(f"- 会话ID: {session_data.get('session_id', 'N/A')}")
    report.append(f"- 用户需求数量: {len(comparison_results['covered']) + len(comparison_results['missing'])}")
    report.append(f"- 已覆盖需求数量: {len(comparison_results['covered'])}")
    report.append(f"- 未覆盖需求数量: {len(comparison_results['missing'])}")
    report.append("")

    report.append("## 已覆盖的用户需求")
    if comparison_results['covered']:
        for req in comparison_results['covered']:
            report.append(f"- ✅ {req['content'][:100]}...")
    else:
        report.append("- 无")
    report.append("")

    report.append("## 未覆盖的用户需求")
    if comparison_results['missing']:
        for req in comparison_results['missing']:
            report.append(f"- ❌ {req['content'][:100]}...")
    else:
        report.append("- 无")
    report.append("")

    # 计算覆盖率
    total = len(comparison_results['covered']) + len(comparison_results['missing'])
    coverage = (len(comparison_results['covered']) / total * 100) if total > 0 else 0

    report.append("## 整体评估")
    report.append(f"- 需求覆盖率: {coverage:.1f}%")

    if coverage >= 80:
        report.append("- 评价: 良好")
    elif coverage >= 60:
        report.append("- 评价: 一般")
    else:
        report.append("- 评价: 需要改进")

    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="验证spec或计划文档是否符合用户意图")
    parser.add_argument("session_id", help="会话ID")
    parser.add_argument("claude_config_dir", help="Claude配置目录路径")
    parser.add_argument("--document", help="指定要审查的文档路径")

    args = parser.parse_args()

    try:
        # 读取会话数据
        session_data = read_session_data(args.session_id, Path(args.claude_config_dir))

        # 提取用户需求
        user_requirements = extract_user_requirements(session_data)

        # 提取AI文档
        ai_documents = extract_ai_documents(session_data)

        # 对比需求和文档
        comparison_results = compare_requirements_with_documents(user_requirements, ai_documents)

        # 生成报告
        report = generate_report(comparison_results, session_data)

        # 输出报告
        print(report)

    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
