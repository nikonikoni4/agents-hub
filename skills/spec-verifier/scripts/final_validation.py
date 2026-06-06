"""最终验证spec-verifier skill的完整性。

用法:
    python skills/spec-verifier/scripts/final_validation.py

输出:
    最终验证结果
"""

import sys
from pathlib import Path


def check_all_files(skill_dir: Path) -> bool:
    """检查所有必需的文件。"""
    print("检查所有文件...")

    required_files = [
        ("SKILL.md", "Skill主文件"),
        ("README.md", "详细使用说明"),
        ("QUICK_START.md", "快速入门指南"),
        ("scripts/session_reader.py", "会话读取脚本"),
        ("scripts/verify_spec.py", "文档验证脚本"),
        ("scripts/test_spec_verifier.py", "单元测试脚本"),
        ("scripts/e2e_test.py", "端到端测试脚本"),
        ("scripts/validate_skill.py", "Skill验证脚本"),
        ("scripts/final_validation.py", "最终验证脚本"),
        ("references/subagent_prompt.md", "Subagent提示词模板"),
        ("examples/usage_example.md", "使用示例文档")
    ]

    all_exist = True
    for file_name, description in required_files:
        file_path = skill_dir / file_name
        if file_path.exists():
            print(f"✅ {description}: {file_path.name}")
        else:
            print(f"❌ {description}: {file_path.name} 不存在")
            all_exist = False

    return all_exist


def check_file_sizes(skill_dir: Path) -> bool:
    """检查文件大小。"""
    print("\n检查文件大小...")

    files_to_check = [
        "SKILL.md",
        "README.md",
        "scripts/session_reader.py",
        "scripts/verify_spec.py"
    ]

    all_ok = True
    for file_name in files_to_check:
        file_path = skill_dir / file_name
        if file_path.exists():
            size = file_path.stat().st_size
            if size > 0:
                print(f"✅ {file_name}: {size} 字节")
            else:
                print(f"❌ {file_name}: 文件为空")
                all_ok = False
        else:
            print(f"❌ {file_name}: 文件不存在")
            all_ok = False

    return all_ok


def check_python_imports() -> bool:
    """检查Python导入。"""
    print("\n检查Python导入...")

    try:
        import sys
        sys.path.append('skills/spec-verifier/scripts')

        # 测试导入session_reader
        from session_reader import read_session_content, extract_key_info
        print("✅ session_reader 导入成功")

        # 测试导入verify_spec
        from verify_spec import read_session_data, extract_user_requirements, extract_ai_documents
        print("✅ verify_spec 导入成功")

        return True
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False


def main():
    """主函数。"""
    print("开始最终验证...")
    print("=" * 50)

    # 获取skill目录
    skill_dir = Path(__file__).parent.parent

    # 检查所有文件
    if not check_all_files(skill_dir):
        print("\n❌ 文件检查失败")
        sys.exit(1)

    # 检查文件大小
    if not check_file_sizes(skill_dir):
        print("\n❌ 文件大小检查失败")
        sys.exit(1)

    # 检查Python导入
    if not check_python_imports():
        print("\n❌ Python导入检查失败")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("🎉 最终验证通过！Spec Verifier skill 已准备就绪。")
    print("\n使用方法：")
    print("1. 在Claude Code中触发skill：'验证一下刚才写的spec'")
    print("2. 查看README.md了解详细使用说明")
    print("3. 运行测试：python skills/spec-verifier/scripts/test_spec_verifier.py")


if __name__ == "__main__":
    main()
