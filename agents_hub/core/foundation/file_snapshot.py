"""文件快照工具函数

用于创建和读取文件快照（diff + content）。
"""

import re
import subprocess
from pathlib import Path

from agents_hub.core.foundation.types import FileMetadata


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
    try:
        content_path = snapshot_dir / f"{snapshot_id}.content"
        return content_path.read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
        raise ValueError(f"Failed to read snapshot content: {e}") from e


def get_snapshot_diff(snapshot_dir: Path, snapshot_id: str) -> str:
    """读取快照的 diff

    Args:
        snapshot_dir: 快照存储目录
        snapshot_id: 快照 ID

    Returns:
        git diff 输出
    """
    try:
        diff_path = snapshot_dir / f"{snapshot_id}.diff"
        return diff_path.read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
        raise ValueError(f"Failed to read snapshot diff: {e}") from e


def _run_git_diff(file_path: str, cwd: str, git_diff_range: str | None) -> tuple[str, str | None]:
    """运行 git diff 命令

    Args:
        file_path: 文件路径
        cwd: 工作目录
        git_diff_range: diff 范围

    Returns:
        (diff_text, error_message) 元组
    """
    # 验证 git_diff_range 格式（防止命令注入）
    if git_diff_range:
        # 接受 commit..commit（SHA）或 git ref..ref（如 HEAD~5..HEAD、branch..branch）
        pattern = r"^[a-zA-Z0-9\-_/.~^:]+\.\.[a-zA-Z0-9\-_/.~^:]+$"
        if not re.match(pattern, git_diff_range):
            return "", f"Invalid git_diff_range format: {git_diff_range}"
        cmd = ["git", "diff", git_diff_range, "--", file_path]
        use_no_index = False
    else:
        # 检查文件是否是 untracked（新文件）
        is_untracked = _is_file_untracked(file_path, cwd)
        if is_untracked:
            # 对于 untracked 文件，使用 git diff --no-index 与空文件比较
            cmd = ["git", "diff", "--no-index", "/dev/null", file_path]
            use_no_index = True
        else:
            cmd = ["git", "diff", "HEAD", "--", file_path]
            use_no_index = False

    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=30)

        # git diff --no-index 对于新文件会返回 exit code 1（表示有差异）
        # 只有在使用 --no-index 时才接受 exit code 1
        if result.returncode == 0 or (use_no_index and result.returncode == 1):
            return result.stdout, None
        else:
            return "", result.stderr or "git diff failed"
    except subprocess.TimeoutExpired:
        return "", "git diff timeout (30s)"


def _is_file_untracked(file_path: str, cwd: str) -> bool:
    """检查文件是否是 git untracked（新文件）

    Args:
        file_path: 文件路径
        cwd: 工作目录

    Returns:
        True 如果文件是 untracked
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", file_path],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        # untracked 文件在 git status --porcelain 中以 "?? " 开头
        return result.stdout.startswith("?? ")
    except (subprocess.TimeoutExpired, Exception):
        return False


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
        cwd_path = Path(cwd).resolve()
        full_path = (cwd_path / file_path).resolve()

        # 路径遍历防护：确保解析后的路径在 cwd 内
        if not str(full_path).startswith(str(cwd_path)):
            return ""

        return full_path.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError, PermissionError, IsADirectoryError):
        return ""


def _save_snapshot(snapshot_dir: Path, snapshot_id: str, diff_text: str, content: str) -> None:
    """保存快照文件

    Args:
        snapshot_dir: 快照存储目录
        snapshot_id: 快照 ID
        diff_text: diff 内容
        content: 文件内容
    """
    # 确保目录存在
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    (snapshot_dir / f"{snapshot_id}.diff").write_text(diff_text, encoding="utf-8")
    (snapshot_dir / f"{snapshot_id}.content").write_text(content, encoding="utf-8")
