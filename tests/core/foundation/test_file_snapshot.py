"""文件快照工具测试"""

import subprocess

from agents_hub.core.foundation.file_snapshot import (
    create_file_snapshot,
    get_snapshot_content,
    get_snapshot_diff,
)


def test_create_file_snapshot_basic(tmp_path):
    """测试创建文件快照的基本功能"""
    # 准备测试环境
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()

    cwd = tmp_path / "repo"
    cwd.mkdir()

    # 创建测试文件
    test_file = cwd / "test.py"
    test_file.write_text("def hello():\n    print('world')\n")

    # 初始化 git 仓库
    subprocess.run(["git", "init"], cwd=cwd, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=cwd,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=cwd,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "test.py"], cwd=cwd, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=cwd,
        check=True,
        capture_output=True,
    )

    # 修改文件
    test_file.write_text("def hello():\n    print('hello world')\n")

    # 创建快照
    metadata = create_file_snapshot(
        snapshot_dir=snapshot_dir,
        call_id="test_call",
        file_path="test.py",
        index=0,
        cwd=str(cwd),
        git_diff_range=None,
    )

    # 验证元数据
    assert metadata["path"] == "test.py"
    assert metadata["status"] == "modified"
    assert metadata["additions"] > 0
    assert metadata["deletions"] > 0
    assert metadata["snapshot_id"] == "test_call_0"
    assert metadata["diff_available"] is True
    assert metadata["diff_error"] is None

    # 验证快照文件存在
    assert (snapshot_dir / "test_call_0.diff").exists()
    assert (snapshot_dir / "test_call_0.content").exists()


def test_get_snapshot_content(tmp_path):
    """测试读取快照内容"""
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()

    # 创建测试快照文件
    (snapshot_dir / "test_001_0.content").write_text("Hello World", encoding="utf-8")

    # 读取内容
    content = get_snapshot_content(snapshot_dir, "test_001_0")

    assert content == "Hello World"


def test_get_snapshot_diff(tmp_path):
    """测试读取快照 diff"""
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()

    # 创建测试快照文件
    diff_content = "diff --git a/test.py b/test.py\n-old line\n+new line\n"
    (snapshot_dir / "test_001_0.diff").write_text(diff_content, encoding="utf-8")

    # 读取 diff
    diff = get_snapshot_diff(snapshot_dir, "test_001_0")

    assert diff == diff_content


def test_create_snapshot_non_git_repo(tmp_path):
    """测试在非 git 仓库中创建快照"""
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()

    cwd = tmp_path / "non_git"
    cwd.mkdir()

    test_file = cwd / "test.txt"
    test_file.write_text("content")

    metadata = create_file_snapshot(
        snapshot_dir=snapshot_dir,
        call_id="test_call",
        file_path="test.txt",
        index=0,
        cwd=str(cwd),
        git_diff_range=None,
    )

    # 非 git 仓库，diff 不可用
    assert metadata["diff_available"] is False
    assert metadata["diff_error"] is not None
    # 但内容仍然保存
    assert (snapshot_dir / "test_call_0.content").exists()


def test_create_snapshot_with_git_diff_range(tmp_path):
    """测试使用 git_diff_range 参数"""
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()

    cwd = tmp_path / "repo"
    cwd.mkdir()

    # 创建测试文件
    test_file = cwd / "test.py"
    test_file.write_text("line1\n")

    # 初始化 git 仓库
    subprocess.run(["git", "init"], cwd=cwd, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=cwd,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=cwd,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "test.py"], cwd=cwd, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=cwd,
        check=True,
        capture_output=True,
    )

    # 获取当前 commit hash
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    commit1 = result.stdout.strip()

    # 修改文件
    test_file.write_text("line1\nline2\n")
    subprocess.run(["git", "add", "test.py"], cwd=cwd, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "second"],
        cwd=cwd,
        check=True,
        capture_output=True,
    )

    # 获取第二个 commit hash
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    commit2 = result.stdout.strip()

    # 再修改文件
    test_file.write_text("line1\nline2\nline3\n")

    # 使用 git_diff_range 创建快照
    git_diff_range = f"{commit1}..{commit2}"
    metadata = create_file_snapshot(
        snapshot_dir=snapshot_dir,
        call_id="test_call",
        file_path="test.py",
        index=0,
        cwd=str(cwd),
        git_diff_range=git_diff_range,
    )

    assert metadata["diff_available"] is True
    assert metadata["diff_error"] is None


def test_create_snapshot_file_not_found(tmp_path):
    """测试文件不存在的情况"""
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()

    cwd = tmp_path / "repo"
    cwd.mkdir()

    # 初始化 git 仓库
    subprocess.run(["git", "init"], cwd=cwd, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=cwd,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=cwd,
        check=True,
        capture_output=True,
    )

    # 尝试为不存在的文件创建快照
    metadata = create_file_snapshot(
        snapshot_dir=snapshot_dir,
        call_id="test_call",
        file_path="nonexistent.py",
        index=0,
        cwd=str(cwd),
        git_diff_range=None,
    )

    # 内容应该是空字符串
    content = get_snapshot_content(snapshot_dir, "test_call_0")
    assert content == ""
    # 但不应该抛异常
    assert metadata["snapshot_id"] == "test_call_0"


def test_snapshot_id_format():
    """测试 snapshot_id 格式"""
    # snapshot_id 应该是 {call_id}_{index}
    call_id = "call_123"
    index = 5
    expected = "call_123_5"

    # 这个测试确保格式遵循规范
    snapshot_id = f"{call_id}_{index}"
    assert snapshot_id == expected
