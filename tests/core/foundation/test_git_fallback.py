"""测试 Git 兜底文件变更捕获功能"""

import subprocess
from pathlib import Path

import pytest

from agents_hub.core.foundation.file_snapshot import get_git_changed_files, get_git_head


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


def test_get_git_head(temp_git_repo):
    """测试获取 Git HEAD"""
    head = get_git_head(str(temp_git_repo))

    assert head is not None
    assert len(head) == 40  # Git commit hash 长度
    assert all(c in "0123456789abcdef" for c in head)


def test_get_git_head_non_git_repo(tmp_path):
    """测试非 Git 仓库返回 None"""
    non_git_dir = tmp_path / "not_a_repo"
    non_git_dir.mkdir()

    head = get_git_head(str(non_git_dir))
    assert head is None


def test_get_git_changed_files_with_base_ref(temp_git_repo):
    """测试基于 base_ref 获取变更文件"""
    # 获取初始 HEAD
    base_head = get_git_head(str(temp_git_repo))
    assert base_head is not None

    # 修改文件
    (temp_git_repo / "file1.py").write_text("print('hello')", encoding="utf-8")
    (temp_git_repo / "file2.py").write_text("print('world')", encoding="utf-8")

    # 获取变更文件（相对于 base_head）
    changed_files, diff_range = get_git_changed_files(str(temp_git_repo), base_head)

    assert len(changed_files) == 2
    # 现在返回绝对路径
    assert str(temp_git_repo / "file1.py") in changed_files
    assert str(temp_git_repo / "file2.py") in changed_files
    assert diff_range is None  # 没有新提交（工作区变更）


def test_get_git_changed_files_without_base_ref(temp_git_repo):
    """测试不指定 base_ref（使用 git status）"""
    # 修改已跟踪文件
    (temp_git_repo / "README.md").write_text("# Modified", encoding="utf-8")

    # 创建新文件（untracked）
    (temp_git_repo / "new_file.py").write_text("print('new')", encoding="utf-8")

    # 获取变更文件
    changed_files, diff_range = get_git_changed_files(str(temp_git_repo), None)

    assert len(changed_files) == 2
    # 现在返回绝对路径
    assert str(temp_git_repo / "README.md") in changed_files
    assert str(temp_git_repo / "new_file.py") in changed_files
    assert diff_range is None  # 没有 base_ref


def test_get_git_changed_files_with_renamed_file(temp_git_repo):
    """测试文件重命名"""
    # 创建并提交文件
    (temp_git_repo / "old_name.py").write_text("print('test')", encoding="utf-8")
    subprocess.run(["git", "add", "old_name.py"], cwd=temp_git_repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add file"], cwd=temp_git_repo, check=True)

    # 重命名文件
    subprocess.run(["git", "mv", "old_name.py", "new_name.py"], cwd=temp_git_repo, check=True)

    # 获取变更文件（应该只显示新文件名）
    changed_files, diff_range = get_git_changed_files(str(temp_git_repo), None)

    assert len(changed_files) == 1
    # 现在返回绝对路径
    assert str(temp_git_repo / "new_name.py") in changed_files
    assert str(temp_git_repo / "old_name.py") not in changed_files
    assert diff_range is None  # 没有新提交（staged 变更）


def test_get_git_changed_files_empty_repo(temp_git_repo):
    """测试没有变更时返回空列表"""
    base_head = get_git_head(str(temp_git_repo))

    changed_files, diff_range = get_git_changed_files(str(temp_git_repo), base_head)

    assert changed_files == []
    assert diff_range is None


def test_get_git_changed_files_non_git_repo(tmp_path):
    """测试非 Git 仓库返回空列表"""
    non_git_dir = tmp_path / "not_a_repo"
    non_git_dir.mkdir()

    changed_files, diff_range = get_git_changed_files(str(non_git_dir), None)
    assert changed_files == []
    assert diff_range is None


def test_git_fallback_workflow(temp_git_repo):
    """测试完整的 Git 兜底工作流"""
    # 1. 记录执行前的 Git HEAD
    head_before = get_git_head(str(temp_git_repo))
    assert head_before is not None

    # 2. 模拟 agent 执行：创建多个文件
    (temp_git_repo / "feature1.py").write_text("def feature1(): pass", encoding="utf-8")
    (temp_git_repo / "feature2.py").write_text("def feature2(): pass", encoding="utf-8")
    (temp_git_repo / "test.py").write_text("def test(): pass", encoding="utf-8")

    # 3. 执行后获取变更文件
    changed_files, diff_range = get_git_changed_files(str(temp_git_repo), head_before)

    # 4. 验证捕获到所有变更（现在是绝对路径）
    assert len(changed_files) == 3
    assert str(temp_git_repo / "feature1.py") in changed_files
    assert str(temp_git_repo / "feature2.py") in changed_files
    assert str(temp_git_repo / "test.py") in changed_files
    assert diff_range is None  # 没有新提交（工作区变更）
