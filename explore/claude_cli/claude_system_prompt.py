"""
测试 Claude CLI 的 system prompt 和 settings 覆盖功能

测试1：测试不同的 system prompt 是否能分配不同角色
测试2：测试不同的 settings 配置是否能控制权限
"""

import subprocess
import json
from pathlib import Path

# 获取当前脚本所在目录
SCRIPT_DIR = Path(__file__).parent
SETTINGS1_PATH = SCRIPT_DIR / "settings1.json"
SETTINGS2_PATH = SCRIPT_DIR / "settings2.json"


def test_system_prompt():
    """测试1：测试 system prompt 是否生效"""
    print("=" * 80)
    print("Test 1: System Prompt Role Assignment")
    print("=" * 80)

    # 角色1：Python专家
    print("\n[Role 1: Python Expert]")
    result1 = subprocess.run(
        [
            "claude",
            "--print",
            "--bare",
            "--append-system-prompt", "You are a Python expert. When asked about your specialty, always mention Python programming.",
            "What is your specialty? Answer in one sentence."
        ],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    print(f"Output: {result1.stdout}")
    if result1.stderr:
        print(f"Error: {result1.stderr}")

    # 角色2：JavaScript专家
    print("\n[Role 2: JavaScript Expert]")
    result2 = subprocess.run(
        [
            "claude",
            "--print",
            "--bare",
            "--append-system-prompt", "You are a JavaScript expert. When asked about your specialty, always mention JavaScript programming.",
            "What is your specialty? Answer in one sentence."
        ],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    print(f"Output: {result2.stdout}")
    if result2.stderr:
        print(f"Error: {result2.stderr}")


def test_settings_override():
    """测试2：测试 settings 配置覆盖"""
    print("\n" + "=" * 80)
    print("Test 2: Settings Override (Permission Control)")
    print("=" * 80)

    # 配置1：允许 git log
    print("\n[Config 1: Using settings1.json (Allow all operations)]")
    result1 = subprocess.run(
        [
            "claude",
            "--print",
            "--settings", str(SETTINGS1_PATH),
            "--append-system-prompt", "You are an assistant. When user asks you to run git log, you MUST try to execute it. If you cannot execute it, reply 'CANNOT_EXECUTE_GIT_LOG'.",
            "Run 'git log --oneline -5' command. If you cannot execute it, just say CANNOT_EXECUTE_GIT_LOG."
        ],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    print(f"Output: {result1.stdout}")
    if result1.stderr:
        print(f"Error: {result1.stderr}")

    # 配置2：禁止 git log
    print("\n[Config 2: Using settings2.json (Deny git log)]")
    result2 = subprocess.run(
        [
            "claude",
            "--print",
            "--settings", str(SETTINGS2_PATH),
            "--append-system-prompt", "You are an assistant. When user asks you to run git log, you MUST try to execute it. If you cannot execute it, reply 'CANNOT_EXECUTE_GIT_LOG'.",
            "Run 'git log --oneline -5' command. If you cannot execute it, just say CANNOT_EXECUTE_GIT_LOG."
        ],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    print(f"Output: {result2.stdout}")
    if result2.stderr:
        print(f"Error: {result2.stderr}")


def main():
    print("Claude CLI Configuration Override Test")
    print("=" * 80)

    # 测试1：system prompt
    # test_system_prompt()

    # 测试2：settings 覆盖
    test_settings_override()

    print("\n" + "=" * 80)
    print("Test Completed")
    print("=" * 80)


if __name__ == "__main__":
    main()
