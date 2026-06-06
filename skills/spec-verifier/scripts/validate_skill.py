"""验证spec-verifier skill的完整性。

用法:
    python skills/spec-verifier/scripts/validate_skill.py

输出:
    验证结果
"""

import sys
from pathlib import Path


def check_file_exists(file_path: Path, description: str) -> bool:
    """检查文件是否存在。"""
    if file_path.exists():
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} 不存在")
        return False


def check_directory_structure(skill_dir: Path) -> bool:
    """检查目录结构。"""
    print("检查目录结构...")

    required_files = [
        ("SKILL.md", "Skill主文件"),
        ("README.md", "使用说明"),
        ("scripts/session_reader.py", "会话读取脚本"),
        ("scripts/verify_spec.py", "文档验证脚本"),
        ("scripts/test_spec_verifier.py", "测试脚本"),
        ("references/subagent_prompt.md", "Subagent提示词模板"),
        ("examples/usage_example.md", "使用示例文档")
    ]

    all_exist = True
    for file_name, description in required_files:
        file_path = skill_dir / file_name
        if not check_file_exists(file_path, description):
            all_exist = False

    return all_exist


def check_python_syntax(file_path: Path) -> bool:
    """检查Python文件的语法。"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            compile(f.read(), file_path, 'exec')
        print(f"✅ 语法检查通过: {file_path}")
        return True
    except SyntaxError as e:
        print(f"❌ 语法错误: {file_path} - {e}")
        return False


def check_markdown_format(file_path: Path) -> bool:
    """检查Markdown文件的基本格式。"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否包含基本的Markdown元素
        if '# ' in content or '## ' in content:
            print(f"✅ Markdown格式正确: {file_path}")
            return True
        else:
            print(f"⚠️  Markdown格式可能不完整: {file_path}")
            return True  # 不是严重错误
    except Exception as e:
        print(f"❌ 读取错误: {file_path} - {e}")
        return False


def validate_skill(skill_dir: Path) -> bool:
    """验证skill的完整性。"""
    print(f"验证skill: {skill_dir}")
    print()

    # 检查目录结构
    if not check_directory_structure(skill_dir):
        return False

    print()

    # 检查Python文件的语法
    print("检查Python文件语法...")
    python_files = [
        skill_dir / "scripts" / "session_reader.py",
        skill_dir / "scripts" / "verify_spec.py",
        skill_dir / "scripts" / "test_spec_verifier.py"
    ]

    all_syntax_ok = True
    for python_file in python_files:
        if python_file.exists():
            if not check_python_syntax(python_file):
                all_syntax_ok = False

    print()

    # 检查Markdown文件格式
    print("检查Markdown文件格式...")
    markdown_files = [
        skill_dir / "SKILL.md",
        skill_dir / "README.md",
        skill_dir / "references" / "subagent_prompt.md",
        skill_dir / "examples" / "usage_example.md"
    ]

    all_markdown_ok = True
    for markdown_file in markdown_files:
        if markdown_file.exists():
            if not check_markdown_format(markdown_file):
                all_markdown_ok = False

    print()

    # 汇总结果
    if all_syntax_ok and all_markdown_ok:
        print("🎉 Skill验证通过！")
        return True
    else:
        print("❌ Skill验证失败，请检查上述错误")
        return False


def main():
    """主函数。"""
    # 获取skill目录
    skill_dir = Path(__file__).parent.parent

    # 验证skill
    if validate_skill(skill_dir):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
