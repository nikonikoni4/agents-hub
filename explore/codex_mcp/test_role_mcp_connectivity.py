"""测试通过 RoleManager 创建 Codex 角色后 MCP 连通性"""

import os
import shutil
import subprocess
from pathlib import Path

from agents_hub.config import AgentPlatform
from agents_hub.roles import RoleManager

ROLE_NAME = "mcp_connectivity_test"


def main():
    role_manager = RoleManager()

    # 1. 清理旧的测试角色
    test_dir = role_manager.agents_dir / ROLE_NAME
    if test_dir.exists():
        print(f"[清理] 删除旧测试角色: {test_dir}")
        shutil.rmtree(test_dir)

    # 2. 创建角色（自动注册 MCP）
    print(f"\n[创建] Codex 角色: {ROLE_NAME}")
    role = role_manager.create_role(name=ROLE_NAME, platform=AgentPlatform.CODEX)
    work_root = role.role_dir / "work_root"
    print(f"[创建] work_root: {work_root}")

    # 3. 检查 MCP 配置
    config_toml = work_root / "config.toml"
    if config_toml.exists():
        content = config_toml.read_text(encoding="utf-8")
        if "mcp_servers" in content:
            print("[检查] MCP 配置已写入 config.toml")
            for line in content.splitlines():
                if "mcp" in line.lower():
                    print(f"  {line}")
        else:
            print("[检查] config.toml 中没有 mcp_servers 配置!")
    else:
        print("[检查] config.toml 不存在!")

    # 4. 测试 Codex 连接（CODEX_HOME = work_root）
    print(f"\n[测试] CODEX_HOME={work_root}")
    env = {**os.environ, "CODEX_HOME": str(work_root)}
    cmd = 'codex exec "Call the health_check MCP tool and report the result" --dangerously-bypass-approvals-and-sandbox --json --ephemeral -m o4-mini'
    result = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        shell=True,
    )
    print(f"[测试] exit code: {result.returncode}")
    if result.stdout:
        # 只打印关键的 mcp_tool_call 行
        for line in result.stdout.strip().splitlines():
            if "mcp_tool_call" in line or "agent_message" in line or "error" in line.lower():
                print(f"  {line}")
    if result.stderr:
        print(f"[测试] stderr:\n{result.stderr[-500:]}")

    # 5. 清理
    print(f"\n[清理] 删除测试角色")
    shutil.rmtree(test_dir)
    print("[完成]")


if __name__ == "__main__":
    main()
