#!/usr/bin/env python3
"""Pre-commit hook：检查 flow 文档是否需要更新

安装方法：
    # 创建软链接（推荐，方便更新）
    ln -s ../../scripts/docs_update/pre-commit-check-flow.py .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit

    # 或者复制文件
    cp scripts/docs_update/pre-commit-check-flow.py .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit

功能：
    在 git commit 前检查暂存区的函数变化是否影响 flow 文档
    如果有影响，给出警告提示，但不阻塞提交
"""

import subprocess
import sys
from pathlib import Path

# 检查脚本路径
CHECK_SCRIPT = Path(__file__).parent.parent / "scripts" / "docs_update" / "check_flow_outdated.py"

# 如果是软链接，需要找到仓库根目录
if not CHECK_SCRIPT.exists():
    # 从 .git/hooks/ 目录向上找
    repo_root = Path(__file__).parent.parent.parent
    CHECK_SCRIPT = repo_root / "scripts" / "docs_update" / "check_flow_outdated.py"

if not CHECK_SCRIPT.exists():
    print(f"错误：找不到检查脚本 {CHECK_SCRIPT}")
    sys.exit(0)  # 不阻塞提交

# 运行检查
print("\n🔍 检查 flow 文档是否需要更新...\n")
result = subprocess.run(
    [sys.executable, str(CHECK_SCRIPT), "--staged"],
    cwd=CHECK_SCRIPT.parent.parent.parent
)

# 始终允许提交（返回 0）
print("\n💡 提示：如果有 flow 文档需要更新，请在提交后尽快更新\n")
sys.exit(0)
