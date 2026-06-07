"""文件快照工具函数

用于创建和读取文件快照（diff + content）。
"""

import subprocess
from pathlib import Path

from agents_hub.agent_bridge.models import FileMetadata


def create_file_snapshot(
    snapshot_dir: Path,
    call_id: str,
    file_path: str,
    index: int,
    cwd: str,
    git_diff_range: str | None = None,
) -> FileMetadata:
    """
    为单个文件创建快照

    Args:
        snapshot_dir: 快照存储目录
        call_id: AgentCall ID
        file_path: 文件路径（相对于 cwd）
        index: 文件索引
        cwd: Agent 工作目录
        git_diff_range: Git diff 范围（可选）

    Returns:
        文件元数据字典
    """
    snapshot_id = f"{call_id}_{index}"

    # 1. 运行 git diff
    diff_text, diff_error = _run_git_diff(file_path, cwd, git_diff_range)

    # 2. 解析 diff
    if diff_text:
        additions, deletions, status = _parse_diff(diff_text)
        diff_available = True
    else:
        additions, deletions, status = 0, 0, "modified"
        diff_available = False

    # 3. 读取文件内容
    content = _read_file_content(file_path, cwd)

    # 4. 保存快照
    _save_snapshot(snapshot_dir, snapshot_id, diff_text or "", content)

    # 5. 返回元数据
    return {
        "path": file_path,
        "status": status,
        "additions": additions,
        "deletions": deletions,
        "snapshot_id": snapshot_id,
        "diff_available": diff_available,
        "diff_error": diff_error,
    }


def get_snapshot_content(snapshot_dir: Path, snapshot_id: str) -> str:
    """读取快照的文件内容

    Args:
        snapshot_dir: 快照存储目录
        snapshot_id: 快照 ID

    Returns:
        文件完整内容
    """
    content_path = snapshot_dir / f"{snapshot_id}.content"
    return content_path.read_text(encoding="utf-8")


def get_snapshot_diff(snapshot_dir: Path, snapshot_id: str) -> str:
    """读取快照的 diff

    Args:
        snapshot_dir: 快照存储目录
        snapshot_id: 快照 ID

    Returns:
        git diff 输出
    """
    diff_path = snapshot_dir / f"{snapshot_id}.diff"
    return diff_path.read_text(encoding="utf-8")


def _run_git_diff(file_path: str, cwd: str, git_diff_range: str | None) -> tuple[str, str | None]:
    """运行 git diff 命令

    Args:
        file_path: 文件路径
        cwd: 工作目录
        git_diff_range: diff 范围

    Returns:
        (diff_text, error_message) 元组
    """
    if git_diff_range:
        cmd = ["git", "diff", git_diff_range, "--", file_path]
    else:
        cmd = ["git", "diff", "HEAD", "--", file_path]

    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)

    if result.returncode == 0:
        return result.stdout, None
    else:
        return "", result.stderr or "git diff failed"


def _parse_diff(diff_text: str) -> tuple[int, int, str]:
    """解析 diff，提取 additions/deletions/status

    Args:
        diff_text: git diff 输出

    Returns:
        (additions, deletions, status) 元组
    """
    additions = 0
    deletions = 0
    status = "modified"

    for line in diff_text.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1
        elif line.startswith("new file mode"):
            status = "added"
        elif line.startswith("deleted file mode"):
            status = "deleted"

    return additions, deletions, status


def _read_file_content(file_path: str, cwd: str) -> str:
    """读取文件完整内容

    Args:
        file_path: 文件路径
        cwd: 工作目录

    Returns:
        文件内容，如果读取失败返回空字符串
    """
    try:
        full_path = Path(cwd) / file_path
        return full_path.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError):
        return ""


def _save_snapshot(snapshot_dir: Path, snapshot_id: str, diff_text: str, content: str) -> None:
    """保存快照文件

    Args:
        snapshot_dir: 快照存储目录
        snapshot_id: 快照 ID
        diff_text: diff 内容
        content: 文件内容
    """
    (snapshot_dir / f"{snapshot_id}.diff").write_text(diff_text, encoding="utf-8")
    (snapshot_dir / f"{snapshot_id}.content").write_text(content, encoding="utf-8")
