"""测试 Claude CLI 的 CLAUDE_CONFIG_DIR profile 隔离功能

验证：
1. 设置 CLAUDE_CONFIG_DIR 指向不同角色目录
2. 每个角色目录有独立的 CLAUDE.md（定义角色身份）和 settings.json（配置）
3. 执行 CLI 后，不同角色应表现出不同的身份

测试目录结构：
  claude-test/
    nico/
      CLAUDE.md    -> "你是nico，你的任务是后端开发"
      settings.json
    xiaoli/
      CLAUDE.md    -> "你是xiaoli，你的任务是前端设计"
      settings.json
"""

import os
import subprocess
from pathlib import Path

CLAUDE_TEST_DIR = Path(r"D:\desktop\软件开发\claude-test")
ROLE_NICO = CLAUDE_TEST_DIR / "nico"
ROLE_XIAOLI = CLAUDE_TEST_DIR / "xiaoli"


def run_claude(config_dir: str, prompt: str) -> tuple[str, str]:
    """使用指定的 CLAUDE_CONFIG_DIR 执行 claude -p"""
    env = os.environ.copy()
    env["CLAUDE_CONFIG_DIR"] = config_dir

    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=os.getcwd(),
        timeout=60,
        check=False,
    )
    return (result.stdout or "").strip(), (result.stderr or "").strip()


def test_profile_isolation():
    """测试两个角色的 profile 隔离"""
    prompt = "你好，请告诉我你的名字是什么，你的任务是什么？你加载了什么skill？一句话说明。你能否使用git log?如果可以回复结果，如果不可以回复，不能使用git log"

    print("=" * 60)
    print("Test: CLAUDE_CONFIG_DIR Profile Isolation")
    print("=" * 60)

    # 角色 1: nico
    print(f"\n[Role: nico]")
    print(f"  CLAUDE_CONFIG_DIR = {ROLE_NICO}")
    stdout, stderr = run_claude(str(ROLE_NICO), prompt)
    print(f"  Response: {stdout}")
    if stderr:
        print(f"  Stderr: {stderr}")

    # 角色 2: xiaoli
    print(f"\n[Role: xiaoli]")
    print(f"  CLAUDE_CONFIG_DIR = {ROLE_XIAOLI}")
    stdout, stderr = run_claude(str(ROLE_XIAOLI), prompt)
    print(f"  Response: {stdout}")
    if stderr:
        print(f"  Stderr: {stderr}")

    print("\n" + "=" * 60)
    print("Test Completed")
    print("=" * 60)


def test_settings_applied():
    """测试 settings.json 是否被正确加载"""
    print("\n" + "=" * 60)
    print("Test: Settings Applied (model check)")
    print("=" * 60)

    for role_name, role_dir in [("nico", ROLE_NICO), ("xiaoli", ROLE_XIAOLI)]:
        print(f"\n[Role: {role_name}]")
        stdout, stderr = run_claude(
            str(role_dir),
            "请用一句话回答：你现在使用的模型是什么？"
        )
        print(f"  Response: {stdout}")
        if stderr:
            print(f"  Stderr: {stderr}")


def main():
    # 检查测试目录是否存在
    if not ROLE_NICO.exists():
        print(f"ERROR: {ROLE_NICO} does not exist")
        return
    if not ROLE_XIAOLI.exists():
        print(f"ERROR: {ROLE_XIAOLI} does not exist")
        return

    test_profile_isolation()
    # test_settings_applied()  # 取消注释以测试 settings 是否生效


if __name__ == "__main__":
    main()
