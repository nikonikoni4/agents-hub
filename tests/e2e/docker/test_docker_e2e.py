"""Docker 沙箱端到端测试

测试流程：
1. 创建 AgentBridge 实例
2. 通过 RoleManager 创建/获取 docker_test 角色
3. 获取 RoleConfig
4. 使用 AgentBridge.execute() 执行（use_docker=True）
5. 等待 15s 后打印 git 引用（验证清理回退）

运行：python -m tests.e2e.docker.test_docker_e2e
"""

import asyncio
import subprocess
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from agents_hub.agent_bridge import AgentBridge
from agents_hub.config.types import AgentPlatform
from agents_hub.roles.role_manager import RoleManager

WORKTREE_NAME = "feat_group_chat_service"
WORKTREE_PATH = PROJECT_ROOT / ".claude" / "worktrees" / WORKTREE_NAME
ROLE_NAME = "docker_test"

GIT_FILE = WORKTREE_PATH / ".git"
GITDIR_FILE = PROJECT_ROOT / ".git" / "worktrees" / WORKTREE_NAME / "gitdir"
HOST_GIT_CONTENT = f"gitdir: {(PROJECT_ROOT / '.git' / 'worktrees' / WORKTREE_NAME).as_posix()}\n"
HOST_GITDIR_CONTENT = f"{(WORKTREE_PATH / '.git').as_posix()}\n"


def cleanup_containers() -> None:
    """停止并删除所有测试相关的容器"""
    result = subprocess.run(
        ["docker", "ps", "-q"],
        capture_output=True, text=True,
    )
    if result.stdout.strip():
        subprocess.run(["docker", "stop"] + result.stdout.strip().split(), check=False)
        subprocess.run(["docker", "rm"] + result.stdout.strip().split(), check=False)
        print("[Init] 已清理所有运行中的容器")
    else:
        print("[Init] 无运行中的容器")


def restore_git_refs() -> None:
    """硬编码复原 git 引用到宿主机路径（防止上次测试异常退出留下脏数据）"""
    GIT_FILE.write_text(HOST_GIT_CONTENT, encoding="utf-8")
    GITDIR_FILE.write_text(HOST_GITDIR_CONTENT, encoding="utf-8")
    print("[Init] 已复原 git 引用到宿主机路径")


def print_git_refs(label: str) -> None:
    """打印两个 git 引用文件的内容"""
    print(f"\n{'='*50}")
    print(f"[{label}] Git 引用状态")
    print(f"{'='*50}")
    print(f"  .git    ({GIT_FILE}):")
    print(f"    {GIT_FILE.read_text(encoding='utf-8').strip()}")
    print(f"  gitdir  ({GITDIR_FILE}):")
    print(f"    {GITDIR_FILE.read_text(encoding='utf-8').strip()}")


async def main():
    # 0. 清理环境
    cleanup_containers()
    restore_git_refs()

    # 1. 创建 AgentBridge 实例
    print("[Step 1] 创建 AgentBridge 实例")
    bridge = AgentBridge()
    # 设置较短的 cleanup_timeout 用于测试
    bridge._docker_manager._cleanup_timeout = 10

    # 2. 创建/获取 docker_test 角色
    print(f"[Step 2] 创建角色: {ROLE_NAME}")
    role_manager = RoleManager()
    try:
        role = role_manager.create_role(
            name=ROLE_NAME,
            platform=AgentPlatform.CLAUDE,
            description="Docker e2e 测试角色",
        )
        print(f"  角色已创建: {role.role_dir}")
    except Exception:
        role = role_manager.get_role(ROLE_NAME)
        print(f"  角色已存在: {role.role_dir}")

    # 3. 获取 RoleConfig
    print("[Step 3] 获取 RoleConfig")
    config = role.get_role_config()
    print(f"  name={config.name}, platform={config.platform}, work_root={config.work_root}")

    # 4. 使用 AgentBridge.execute() 执行（use_docker=True）
    prompt = "执行 `git branch` 命令并展示结果，不需要做其他任何事情"
    print("\n[Step 4] 执行 AgentBridge.execute() (use_docker=True)")
    print(f"  prompt: {prompt}")
    print("-" * 50)
    result = await bridge.execute(
        prompt=prompt,
        config=config,
        cwd=str(WORKTREE_PATH),
        use_docker=True,
        group_chat_id="e2e-test",
    )
    print(f"  结果: {result.text}")
    print("-" * 50)
    print_git_refs("执行后")
    print("执行完成，容器已释放，等待清理...")

    # 5. 等待 15s（cleanup_timeout=10s，15s 后容器应已销毁，引用应已回退）
    print("\n[Step 5] 等待 15s（cleanup_timeout=10s）...")
    await asyncio.sleep(15)
    print_git_refs("清理后（应已回退到宿主机路径）")

    print("\n测试完成!")


if __name__ == "__main__":
    asyncio.run(main())
