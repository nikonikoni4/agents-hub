"""测试spec-verifier skill的功能。

用法:
    python skills/spec-verifier/scripts/test_spec_verifier.py

输出:
    测试结果
"""

import json
import tempfile
from pathlib import Path


def create_test_session(session_dir: Path, session_id: str, user_messages: list, ai_documents: list):
    """创建测试会话文件。"""
    session_data = {
        'session_id': session_id,
        'messages': []
    }

    # 添加用户消息
    for msg in user_messages:
        session_data['messages'].append({
            'role': 'user',
            'content': msg,
            'timestamp': '2026-06-06T10:00:00'
        })

    # 添加AI文档
    for doc in ai_documents:
        session_data['messages'].append({
            'role': 'assistant',
            'content': doc,
            'timestamp': '2026-06-06T10:01:00'
        })

    # 写入会话文件
    session_file = session_dir / f"{session_id}.json"
    with open(session_file, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)

    return session_file


def test_session_reader():
    """测试session_reader.py的功能。"""
    print("测试 session_reader.py...")

    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        session_dir = Path(temp_dir) / "sessions"
        session_dir.mkdir()

        # 创建测试会话
        user_messages = ["我需要一个用户登录功能"]
        ai_documents = ["## User Login Spec\n\n### 功能需求\n- 用户名密码登录\n- 记住登录状态\n- 忘记密码功能"]

        session_file = create_test_session(session_dir, "test123", user_messages, ai_documents)

        # 导入并测试session_reader
        import sys
        sys.path.append('skills/spec-verifier/scripts')
        from session_reader import read_session_content, extract_key_info

        # 读取会话内容
        session_data = read_session_content(session_file)

        # 提取关键信息
        key_info = extract_key_info(session_data)

        # 验证结果
        assert key_info['session_id'] == 'test123', "会话ID不匹配"
        assert len(key_info['user_messages']) == 1, "用户消息数量不正确"
        assert len(key_info['ai_documents']) == 1, "AI文档数量不正确"

        print("✅ session_reader.py 测试通过")


def test_verify_spec():
    """测试verify_spec.py的功能。"""
    print("测试 verify_spec.py...")

    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        session_dir = Path(temp_dir) / "sessions"
        session_dir.mkdir()

        # 创建测试会话
        user_messages = ["我需要一个用户登录功能"]
        ai_documents = ["## User Login Spec\n\n### 功能需求\n- 用户名密码登录\n- 记住登录状态\n- 忘记密码功能"]

        session_file = create_test_session(session_dir, "test123", user_messages, ai_documents)

        # 导入并测试verify_spec
        import sys
        sys.path.append('skills/spec-verifier/scripts')
        from verify_spec import read_session_data, extract_user_requirements, extract_ai_documents, compare_requirements_with_documents, generate_report

        # 读取会话数据
        session_data = read_session_data("test123", Path(temp_dir))

        # 提取用户需求
        user_requirements = extract_user_requirements(session_data)

        # 提取AI文档
        ai_documents = extract_ai_documents(session_data)

        # 对比需求和文档
        comparison_results = compare_requirements_with_documents(user_requirements, ai_documents)

        # 生成报告
        report = generate_report(comparison_results, session_data)

        # 验证结果
        assert len(user_requirements) == 1, "用户需求数量不正确"
        assert len(ai_documents) == 1, "AI文档数量不正确"
        assert len(comparison_results['covered']) == 1, "已覆盖需求数量不正确"
        assert len(comparison_results['missing']) == 0, "未覆盖需求数量不正确"

        print("✅ verify_spec.py 测试通过")


def main():
    """运行所有测试。"""
    print("开始测试 spec-verifier skill...")
    print()

    try:
        test_session_reader()
        print()
        test_verify_spec()
        print()
        print("🎉 所有测试通过！")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    import sys
    main()
