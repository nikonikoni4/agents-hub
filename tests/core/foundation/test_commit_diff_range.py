"""测试提交后的 diff_range 返回（修复验证）

验证 get_git_changed_files() 在检测到新提交时，返回正确的 commit range。
"""

import subprocess
from pathlib import Path

import pytest

from agents_hub.core.foundation.file_snapshot import (
    create_file_snapshot,
    get_git_changed_files,
    get_git_head,
    get_working_tree_status,
)


@pytest.fixture
def temp_git_repo(tmp_path):
    """创建临时 Git 仓库"""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # 初始化 Git 仓库
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)

    # 创建初始提交
    (repo_dir / "README.md").write_text("# Test Repo", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True)

    return repo_dir


def test_commit_returns_correct_diff_range(temp_git_repo):
    """测试：提交文件后返回正确的 diff_range"""
    repo = temp_git_repo

    # 执行前
    head_before = get_git_head(str(repo))
    status_before = get_working_tree_status(str(repo))

    # Agent 执行：创建并提交文件
    (repo / "feature.py").write_text("def feature(): pass", encoding="utf-8")
    subprocess.run(["git", "add", "feature.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add feature"], cwd=repo, check=True)

    # 执行后
    changed_files, diff_range = get_git_changed_files(str(repo), head_before, status_before=status_before)

    # 验证
    assert len(changed_files) == 1
    assert str(repo / "feature.py") in changed_files

    # 核心验证：返回正确的 diff_range
    assert diff_range is not None, "应该返回 diff_range（检测到新提交）"
    assert ".." in diff_range, f"diff_range 格式错误: {diff_range}"

    # 验证 diff_range 可以用于 git diff
    head_after = get_git_head(str(repo))
    assert head_after != head_before, "HEAD 应该变化"
    assert diff_range == f"{head_before}..{head_after}", f"diff_range 应该是 base_ref..head_after"


def test_create_snapshot_with_commit_diff_range(temp_git_repo):
    """测试：create_file_snapshot() 使用提交的 diff_range 能生成 diff"""
    repo = temp_git_repo

    # 执行前
    head_before = get_git_head(str(repo))
    status_before = get_working_tree_status(str(repo))

    # Agent 执行：创建并提交文件
    (repo / "feature.py").write_text("def feature():\n    return 'hello'\n", encoding="utf-8")
    subprocess.run(["git", "add", "feature.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add feature"], cwd=repo, check=True)

    # 获取变更和 diff_range
    changed_files, diff_range = get_git_changed_files(str(repo), head_before, status_before=status_before)

    assert diff_range is not None, "应该返回 diff_range"

    # 创建快照（使用 diff_range）
    snapshot_dir = repo / ".snapshots"
    metadata = create_file_snapshot(
        snapshot_dir=snapshot_dir,
        call_id="test_call",
        file_path=str(repo / "feature.py"),
        index=0,
        cwd=str(repo),
        git_diff_range=diff_range,
    )

    # 验证：diff 可用
    assert metadata["diff_available"], "diff 应该可用（不应该为空）"
    assert metadata["additions"] > 0, "应该有新增行"
    assert metadata["status"] == "added", "状态应该是 added"

    # 读取 diff 文件，验证内容
    diff_file = snapshot_dir / f"{metadata['snapshot_id']}.diff"
    diff_content = diff_file.read_text(encoding="utf-8")
    assert "def feature():" in diff_content, "diff 应该包含函数定义"
    assert "+def feature():" in diff_content, "diff 应该显示为新增"


def test_unstaged_changes_return_none_diff_range(temp_git_repo):
    """测试：未提交的变更返回 None diff_range（对比场景）"""
    repo = temp_git_repo

    # 执行前
    head_before = get_git_head(str(repo))
    status_before = get_working_tree_status(str(repo))

    # Agent 执行：创建文件但不提交
    (repo / "draft.py").write_text("def draft(): pass", encoding="utf-8")

    # 执行后
    changed_files, diff_range = get_git_changed_files(str(repo), head_before, status_before=status_before)

    # 验证
    assert len(changed_files) == 1
    assert str(repo / "draft.py") in changed_files
    assert diff_range is None, "未提交的变更应该返回 None（工作区变更）"


def test_mixed_changes_with_commit(temp_git_repo):
    """测试：混合场景（既有提交又有工作区变更）"""
    repo = temp_git_repo

    # 执行前
    head_before = get_git_head(str(repo))
    status_before = get_working_tree_status(str(repo))

    # Agent 执行 1：创建并提交文件
    (repo / "committed.py").write_text("def committed(): pass", encoding="utf-8")
    subprocess.run(["git", "add", "committed.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add committed"], cwd=repo, check=True)

    # Agent 执行 2：创建未提交的文件
    (repo / "draft.py").write_text("def draft(): pass", encoding="utf-8")

    # 执行后
    changed_files, diff_range = get_git_changed_files(str(repo), head_before, status_before=status_before)

    # 验证：捕获两个文件
    assert len(changed_files) == 2
    assert str(repo / "committed.py") in changed_files
    assert str(repo / "draft.py") in changed_files

    # 验证：有提交就返回 diff_range
    assert diff_range is not None, "有新提交应该返回 diff_range"
    assert ".." in diff_range


def test_multiple_commits_diff_range(temp_git_repo):
    """测试：多次提交返回的 diff_range 跨越所有提交"""
    repo = temp_git_repo

    # 执行前
    head_before = get_git_head(str(repo))
    status_before = get_working_tree_status(str(repo))

    # Agent 执行：多次提交
    (repo / "file1.py").write_text("# file 1", encoding="utf-8")
    subprocess.run(["git", "add", "file1.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add file1"], cwd=repo, check=True)

    (repo / "file2.py").write_text("# file 2", encoding="utf-8")
    subprocess.run(["git", "add", "file2.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add file2"], cwd=repo, check=True)

    # 执行后
    changed_files, diff_range = get_git_changed_files(str(repo), head_before, status_before=status_before)

    # 验证：捕获两个文件
    assert len(changed_files) == 2
    assert str(repo / "file1.py") in changed_files
    assert str(repo / "file2.py") in changed_files

    # 验证：diff_range 跨越所有提交
    assert diff_range is not None
    head_after = get_git_head(str(repo))
    assert diff_range == f"{head_before}..{head_after}"
    assert head_before != head_after
