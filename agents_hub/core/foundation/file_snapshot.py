"""文件快照工具函数

用于创建和读取文件快照（diff + content）。
"""

import re
import subprocess
from pathlib import Path

from agents_hub.core.foundation.types import FileMetadata
from agents_hub.utils.logger import get_logger

logger = get_logger(__name__)


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
        file_path: 文件路径（绝对路径或相对路径）
        cwd: 工作目录
        git_diff_range: diff 范围

    Returns:
        (diff_text, error_message) 元组
    """
    logger.debug(
        "_run_git_diff: file_path=%s, cwd=%s, git_diff_range=%s", file_path, cwd, git_diff_range
    )

    # 确定 git diff 的执行目录和相对路径
    path_obj = Path(file_path)
    if path_obj.is_absolute():
        # 绝对路径：在文件所在目录执行 git diff
        git_cwd = str(path_obj.parent)
        git_file_path = path_obj.name
    else:
        git_cwd = cwd
        git_file_path = file_path

    logger.debug("_run_git_diff: git_cwd=%s, git_file_path=%s", git_cwd, git_file_path)

    # 验证 git_diff_range 格式（防止命令注入）
    if git_diff_range:
        # 接受：commit..commit、单独的 ref（如 HEAD、HEAD~1、branch）
        range_pattern = r"^[a-zA-Z0-9\-_/.~^:]+$"
        range_pattern_with_dots = r"^[a-zA-Z0-9\-_/.~^:]+\.\.[a-zA-Z0-9\-_/.~^:]+$"
        if not re.match(range_pattern, git_diff_range) and not re.match(
            range_pattern_with_dots, git_diff_range
        ):
            logger.debug("_run_git_diff: git_diff_range 格式校验失败: %s", git_diff_range)
            return "", f"Invalid git_diff_range format: {git_diff_range}"

        # 检查文件是否是 untracked（新文件）
        is_untracked = _is_file_untracked(git_file_path, git_cwd)
        if is_untracked:
            # 对于 untracked 文件，使用 git diff --no-index 与空文件比较
            cmd = ["git", "diff", "--no-index", "/dev/null", git_file_path]
            use_no_index = True
        else:
            cmd = ["git", "diff", git_diff_range, "--", git_file_path]
            use_no_index = False
    else:
        # 检查文件是否是 untracked（新文件）
        is_untracked = _is_file_untracked(git_file_path, git_cwd)
        if is_untracked:
            # 对于 untracked 文件，使用 git diff --no-index 与空文件比较
            cmd = ["git", "diff", "--no-index", "/dev/null", git_file_path]
            use_no_index = True
        else:
            cmd = ["git", "diff", "HEAD", "--", git_file_path]
            use_no_index = False

    logger.debug("_run_git_diff: 执行命令: %s, cwd=%s", cmd, git_cwd)
    try:
        result = subprocess.run(cmd, cwd=git_cwd, capture_output=True, text=True, timeout=30)
        logger.debug(
            "_run_git_diff: returncode=%d, stdout_len=%d, stderr=%s",
            result.returncode,
            len(result.stdout),
            result.stderr,
        )

        # git diff --no-index 对于新文件会返回 exit code 1（表示有差异）
        # 只有在使用 --no-index 时才接受 exit code 1
        if result.returncode == 0 or (use_no_index and result.returncode == 1):
            return result.stdout, None
        else:
            return "", result.stderr or "git diff failed"
    except subprocess.TimeoutExpired:
        logger.debug("_run_git_diff: 命令超时")
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
        file_path: 文件路径（绝对路径或相对路径）
        cwd: 工作目录（仅用于相对路径）

    Returns:
        文件内容，如果读取失败返回空字符串
    """
    try:
        path_obj = Path(file_path)

        # 如果是绝对路径，直接使用；否则拼接 cwd
        if path_obj.is_absolute():
            full_path = path_obj.resolve()
        else:
            cwd_path = Path(cwd).resolve()
            full_path = (cwd_path / file_path).resolve()

        # TODO: 路径遍历防护暂未启用
        # 设计决策：agent 的 cwd 可能是 git 子目录，但 agent 有权限编辑 git 主仓库文件。
        # 若启用 cwd 白名单校验，将无法追踪 cwd 之外的文件变更。
        # 后续如需启用，应改为 git 仓库根目录白名单（而非 cwd）。

        logger.debug(
            "_read_file_content: file_path=%s, cwd=%s, full_path=%s, is_absolute=%s",
            file_path,
            cwd,
            full_path,
            path_obj.is_absolute(),
        )

        content = full_path.read_text(encoding="utf-8")
        logger.debug("_read_file_content: 成功读取，内容长度=%d", len(content))
        return content
    except FileNotFoundError:
        logger.debug("_read_file_content: 文件不存在: %s", full_path)
        return ""
    except (UnicodeDecodeError, PermissionError, IsADirectoryError) as e:
        logger.debug("_read_file_content: 读取失败: %s, error=%s", full_path, str(e))
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


def get_git_head(cwd: str) -> str | None:
    """获取当前 Git HEAD 引用

    Args:
        cwd: Git 仓库工作目录

    Returns:
        HEAD 的 commit hash，如果失败返回 None
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            logger.debug("get_git_head: git rev-parse 失败: %s", result.stderr)
            return None
    except (subprocess.TimeoutExpired, Exception) as e:
        logger.debug("get_git_head: 执行失败: %s", str(e))
        return None


def get_untracked_files(cwd: str) -> set[str]:
    """获取当前所有 untracked 文件（绝对路径）

    Args:
        cwd: Git 仓库工作目录

    Returns:
        untracked 文件的绝对路径集合
    """
    try:
        cwd_path = Path(cwd).resolve()
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            untracked = set()
            for line in result.stdout.split("\n"):
                line = line.rstrip()
                if line:
                    abs_path = str(cwd_path / line)
                    untracked.add(abs_path)
                    logger.debug("get_untracked_files: 发现 untracked 文件: %s", line)
            logger.info("get_untracked_files: 共找到 %d 个 untracked 文件", len(untracked))
            return untracked
        else:
            logger.debug("get_untracked_files: git ls-files 失败: %s", result.stderr)
            return set()
    except (subprocess.TimeoutExpired, Exception) as e:
        logger.debug("get_untracked_files: 执行失败: %s", str(e))
        return set()


def get_working_tree_status(cwd: str) -> dict[str, str]:
    """获取当前工作区状态（所有文件的状态）

    Args:
        cwd: Git 仓库工作目录

    Returns:
        文件路径 -> 状态码的字典
        状态码格式：git status --porcelain 的前两个字符（如 " M", "??", "A "等）
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            cwd_path = Path(cwd).resolve()
            status_map = {}
            for line in result.stdout.split("\n"):
                line = line.rstrip()
                if line and len(line) > 3:
                    status_code = line[:2]  # XY
                    file_path = line[3:].strip()
                    # 处理重命名：R  old -> new
                    if " -> " in file_path:
                        file_path = file_path.split(" -> ")[1]
                    abs_path = str(cwd_path / file_path)
                    status_map[abs_path] = status_code
            logger.debug("get_working_tree_status: 找到 %d 个文件有变更", len(status_map))
            return status_map
        else:
            logger.debug("get_working_tree_status: git status 失败: %s", result.stderr)
            return {}
    except (subprocess.TimeoutExpired, Exception) as e:
        logger.debug("get_working_tree_status: 执行失败: %s", str(e))
        return {}


def _get_committed_files(cwd: str, base_ref: str, head_ref: str) -> list[str]:
    """获取已提交的文件列表（base_ref 到 head_ref 之间的提交）

    Args:
        cwd: Git 仓库工作目录
        base_ref: 基准 commit hash
        head_ref: 当前 HEAD commit hash

    Returns:
        相对路径列表（相对于 cwd）
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref, head_ref],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            files = [line.strip() for line in result.stdout.split("\n") if line.strip()]
            logger.debug("_get_committed_files: 找到 %d 个已提交文件", len(files))
            return files
        else:
            logger.debug("_get_committed_files: git diff 失败: %s", result.stderr)
            return []
    except (subprocess.TimeoutExpired, Exception) as e:
        logger.debug("_get_committed_files: 执行失败: %s", str(e))
        return []


def get_git_changed_files(
    cwd: str,
    base_ref: str | None = None,
    exclude_untracked: set[str] | None = None,
    status_before: dict[str, str] | None = None,
) -> list[str]:
    """获取 Git 仓库中变更的文件列表

    Args:
        cwd: Git 仓库工作目录
        base_ref: 基准引用（如 HEAD、commit hash），用于检测提交
        exclude_untracked: 要排除的 untracked 文件绝对路径集合（已废弃，使用 status_before）
        status_before: 执行前的工作区状态（推荐使用）

    Returns:
        变更文件的绝对路径列表（失败时返回空列表，不抛出异常）
    """
    try:
        logger.debug(
            "get_git_changed_files: cwd=%s, base_ref=%s, has_status_before=%s",
            cwd,
            base_ref[:8] if base_ref else None,
            status_before is not None,
        )

        # 优先使用状态对比模式（推荐）
        if status_before is not None:
            logger.debug("get_git_changed_files: 使用状态对比模式")

            # 1. 检测工作区变更（未提交的）
            status_after = get_working_tree_status(cwd)
            changed_files = []

            for file_path, status_after_code in status_after.items():
                status_before_code = status_before.get(file_path)
                if status_before_code != status_after_code:
                    logger.debug(
                        "get_git_changed_files: 捕获工作区变更: %s (状态: %s -> %s)",
                        Path(file_path).name,
                        status_before_code or "无",
                        status_after_code,
                    )
                    changed_files.append(file_path)

            # 2. 检测已提交的变更（如果 HEAD 变化了）
            if base_ref:
                head_after = get_git_head(cwd)
                if head_after and head_after != base_ref:
                    logger.debug("get_git_changed_files: HEAD 变化，检测已提交文件")
                    committed_files = _get_committed_files(cwd, base_ref, head_after)
                    if committed_files:
                        cwd_path = Path(cwd).resolve()
                        for rel_path in committed_files:
                            abs_path = str(cwd_path / rel_path)
                            if abs_path not in changed_files:
                                logger.debug("get_git_changed_files: 捕获已提交文件: %s", rel_path)
                                changed_files.append(abs_path)

            logger.info(
                "get_git_changed_files: 找到 %d 个变更文件（状态对比模式）", len(changed_files)
            )
            return changed_files

    except Exception as e:
        logger.error("get_git_changed_files: 执行失败，返回空列表: %s", str(e), exc_info=True)
        return []

    # 向后兼容：旧的 base_ref + exclude_untracked 模式（已废弃）
    try:
        logger.debug("get_git_changed_files: 使用旧的兼容模式（已废弃）")
        cwd_path = Path(cwd).resolve()
        exclude_set = exclude_untracked or set()

        if base_ref:
            # 使用 git diff --name-only 获取相对于 base_ref 的变更
            # 包括工作区和暂存区的所有变更
            logger.debug("get_git_changed_files: 使用 base_ref 模式")
            result = subprocess.run(
                ["git", "diff", "--name-only", base_ref, "HEAD"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # 如果 HEAD 没变，再检查工作区未提交的变更
            if result.returncode == 0:
                committed_files_legacy = (
                    set(result.stdout.strip().split("\n")) if result.stdout.strip() else set()
                )  # type: set[str]
                logger.debug(
                    "get_git_changed_files: committed_files=%d", len(committed_files_legacy)
                )

                # 获取工作区变更（包括未暂存和已暂存）
                status_result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if status_result.returncode == 0:
                    working_files: set[str] = set()
                    for line in status_result.stdout.split("\n"):
                        line = line.rstrip()  # 只移除行尾空白，保留开头空格
                        if line and len(line) > 3:
                            file_path = line[3:].strip()
                            # 处理重命名：R  old -> new
                            if " -> " in file_path:
                                file_path = file_path.split(" -> ")[1]
                            working_files.add(file_path)

                    # 合并已提交和未提交的变更，转换为绝对路径并过滤
                    all_files = committed_files_legacy | working_files
                    result_list = []
                    filtered_count = 0
                    for f in all_files:
                        if f:
                            abs_path = str(cwd_path / f)
                            if abs_path in exclude_set:
                                logger.debug(
                                    "get_git_changed_files: 过滤已存在的 untracked: %s",
                                    Path(abs_path).name,
                                )
                                filtered_count += 1
                            else:
                                result_list.append(abs_path)
                                logger.debug(
                                    "get_git_changed_files: 捕获变更文件: %s", Path(abs_path).name
                                )
                    logger.info(
                        "get_git_changed_files: 找到 %d 个变更文件，过滤 %d 个",
                        len(result_list),
                        filtered_count,
                    )
                    return result_list
        else:
            # 使用 git status --porcelain 获取当前所有变更（包括 untracked）
            logger.debug("get_git_changed_files: 使用 git status 模式")
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30,
            )

        if result.returncode != 0:
            logger.debug("get_git_changed_files: git 命令失败: %s", result.stderr)
            return []

        # 解析输出，转换为绝对路径并过滤
        files = []
        filtered_count = 0
        for line in result.stdout.split("\n"):
            line = line.rstrip()  # 只移除行尾空白，保留开头空格
            if not line or len(line) < 3:
                continue

            # git status --porcelain 输出：XY filename
            # 格式：前两个字符是状态码，第三个字符是空格，后面是文件路径
            file_path = line[3:].strip()
            # 处理重命名：R  old -> new
            if " -> " in file_path:
                file_path = file_path.split(" -> ")[1]
            # 转换为绝对路径并过滤
            abs_path = str(cwd_path / file_path)
            if abs_path in exclude_set:
                logger.debug(
                    "get_git_changed_files: 过滤已存在的 untracked: %s", Path(abs_path).name
                )
                filtered_count += 1
            else:
                files.append(abs_path)
                logger.debug("get_git_changed_files: 捕获变更文件: %s", Path(abs_path).name)

        logger.info(
            "get_git_changed_files: 找到 %d 个变更文件，过滤 %d 个", len(files), filtered_count
        )
        return files

    except (subprocess.TimeoutExpired, Exception) as e:
        logger.error(
            "get_git_changed_files: 旧兼容模式执行失败，返回空列表: %s", str(e), exc_info=True
        )
        return []
