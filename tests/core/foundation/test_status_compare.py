"""测试状态对比模式（方案 A）"""

import subprocess
from pathlib import Path

import pytest

from agents_hub.core.foundation.file_snapshot import (
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


def test_status_compare_new_untracked_file(temp_git_repo):
    """测试：检测新创建的 untracked 文件"""
    repo = temp_git_repo

    # 执行前
    head_before = get_git_head(str(repo))
    status_before = get_working_tree_status(str(repo))

    # Agent 执行：创建新文件
    (repo / "new_file.py").write_text("def hello(): pass", encoding="utf-8")

    # 执行后
    changed_files = get_git_changed_files(str(repo), head_before, status_before=status_before)

    # 验证
    assert len(changed_files) == 1
    assert str(repo / "new_file.py") in changed_files


def test_status_compare_modify_tracked_file(temp_git_repo):
    """测试：检测修改已跟踪的文件"""
    repo = temp_git_repo

    # 执行前
    head_before = get_git_head(str(repo))
    status_before = get_working_tree_status(str(repo))

    # Agent 执行：修改已跟踪文件
    (repo / "README.md").write_text("# Modified", encoding="utf-8")

    # 执行后
    changed_files = get_git_changed_files(str(repo), head_before, status_before=status_before)

    # 验证
    assert len(changed_files) == 1
    assert str(repo / "README.md") in changed_files


def test_status_compare_stage_file(temp_git_repo):
    """测试：检测 stage 文件（状态转换）"""
    repo = temp_git_repo

    # 先创建 untracked 文件
    (repo / "new.py").write_text("code", encoding="utf-8")

    # 执行前
    head_before = get_git_head(str(repo))
    status_before = get_working_tree_status(str(repo))
    assert status_before[str(repo / "new.py")] == "??"

    # Agent 执行：stage 文件
    subprocess.run(["git", "add", "new.py"], cwd=repo, check=True)

    # 执行后
    changed_files = get_git_changed_files(str(repo), head_before, status_before=status_before)

    # 验证：状态从 ?? → A
    assert len(changed_files) == 1
    assert str(repo / "new.py") in changed_files


def test_status_compare_commit_file(temp_git_repo):
    """测试：检测已提交的文件（HEAD 变化）"""
    repo = temp_git_repo

    # 执行前
    head_before = get_git_head(str(repo))
    status_before = get_working_tree_status(str(repo))

    # Agent 执行：创建并提交文件
    (repo / "committed.py").write_text("code", encoding="utf-8")
    subprocess.run(["git", "add", "committed.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add file"], cwd=repo, check=True)

    # 执行后
    changed_files = get_git_changed_files(str(repo), head_before, status_before=status_before)

    # 验证：捕获已提交的文件
    assert len(changed_files) == 1
    assert str(repo / "committed.py") in changed_files


def test_status_compare_ignore_existing_untracked(temp_git_repo):
    """测试：不误报执行前已存在的 untracked 文件"""
    repo = temp_git_repo

    # 执行前已有 untracked 文件
    (repo / "old_screenshot.png").write_text("old", encoding="utf-8")

    # 执行前
    head_before = get_git_head(str(repo))
    status_before = get_working_tree_status(str(repo))

    # Agent 执行：创建新文件
    (repo / "new_feature.py").write_text("code", encoding="utf-8")

    # 执行后
    changed_files = get_git_changed_files(str(repo), head_before, status_before=status_before)

    # 验证：只捕获新文件，不误报旧 untracked
    assert len(changed_files) == 1
    assert str(repo / "new_feature.py") in changed_files
    assert str(repo / "old_screenshot.png") not in changed_files


def test_status_compare_multiple_agents(temp_git_repo):
    """测试：多个 Agent 顺序执行不累积（核心场景）"""
    repo = temp_git_repo

    # === Agent A 执行 ===
    head_a_before = get_git_head(str(repo))
    status_a_before = get_working_tree_status(str(repo))

    (repo / "file_a.py").write_text("code A", encoding="utf-8")

    changed_a = get_git_changed_files(str(repo), head_a_before, status_before=status_a_before)
    assert len(changed_a) == 1
    assert str(repo / "file_a.py") in changed_a

    # === Agent B 执行 ===
    head_b_before = get_git_head(str(repo))
    status_b_before = get_working_tree_status(str(repo))  # 此时 file_a.py 是 ??

    (repo / "file_b.py").write_text("code B", encoding="utf-8")

    changed_b = get_git_changed_files(str(repo), head_b_before, status_before=status_b_before)

    # 验证：只捕获 Agent B 的变更，不包含 Agent A 的
    assert len(changed_b) == 1
    assert str(repo / "file_b.py") in changed_b
    assert str(repo / "file_a.py") not in changed_b  # 关键：不会误报 Agent A 的文件


def test_status_compare_error_handling(temp_git_repo):
    """测试：Git 命令失败不抛出异常"""
    repo = temp_git_repo

    # 使用无效的 cwd（非 Git 仓库）
    invalid_cwd = str(repo.parent / "non_existent")

    # 应该返回空列表，不抛出异常
    result = get_git_changed_files(invalid_cwd, "abc123", status_before={})
    assert result == []
