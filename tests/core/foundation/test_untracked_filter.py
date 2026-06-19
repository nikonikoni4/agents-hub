"""测试 untracked 文件过滤功能"""

import subprocess
from pathlib import Path

import pytest

from agents_hub.core.foundation.file_snapshot import get_git_changed_files, get_untracked_files


@pytest.fixture
def temp_git_repo_with_untracked(tmp_path):
    """创建包含已存在 untracked 文件的临时 Git 仓库"""
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

    # 创建一些已存在的 untracked 文件（模拟用户文档、截图等）
    (repo_dir / "old_screenshot.png").write_text("fake image", encoding="utf-8")
    (repo_dir / "temp_notes.txt").write_text("some notes", encoding="utf-8")

    return repo_dir


def test_get_untracked_files(temp_git_repo_with_untracked):
    """测试获取 untracked 文件列表"""
    repo = temp_git_repo_with_untracked

    untracked = get_untracked_files(str(repo))

    assert len(untracked) == 2
    assert str(repo / "old_screenshot.png") in untracked
    assert str(repo / "temp_notes.txt") in untracked



def test_no_exclude_untracked(temp_git_repo_with_untracked):
    """测试不使用 exclude_untracked 时的行为（向后兼容）"""
    repo = temp_git_repo_with_untracked

    # 不传 exclude_untracked 参数
    changed_files, diff_range = get_git_changed_files(str(repo), None)

    # 应该捕获所有 untracked 文件
    assert len(changed_files) == 2
    assert str(repo / "old_screenshot.png") in changed_files
    assert str(repo / "temp_notes.txt") in changed_files
    assert diff_range is None  # 没有新提交
