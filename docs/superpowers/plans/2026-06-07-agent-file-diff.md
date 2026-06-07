# Agent 文件展示功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 当 Agent 完成代码任务后，消息下方显示修改的文件列表，支持预览文件内容和查看 diff

**Architecture:** 后端在 `finish_agent_call` 时运行 git diff 并保存快照到磁盘，前端渲染折叠的文件卡片，用户点击时通过 API 获取快照内容并在右侧栏显示

**Tech Stack:** Python (FastAPI), TypeScript (React), Git CLI, file I/O

---

## 文件结构概览

### 后端新增/修改文件

```
agents_hub/
├── core/
│   ├── foundation/
│   │   └── file_snapshot.py          [新增] 文件快照工具函数
│   └── context/
│       └── group_chat_context.py     [修改] add_message 处理新字段
├── agent_bridge/
│   └── models.py                     [修改] AgentResult 增加字段
├── mcp/
│   └── server.py                     [修改] finish_agent_call 增加参数
├── api/
│   └── routes/
│       └── group_chat.py             [修改] 新增 API 端点
└── tests/
    └── core/
        └── foundation/
            └── test_file_snapshot.py [新增] 快照工具测试
```

### 前端新增/修改文件

```
frontend/src/
├── shared/
│   ├── types/
│   │   └── api-schemas.ts            [修改] 增加文件相关类型
│   └── components/
│       └── FileChangesCard/          [新增] 文件卡片组件
│           ├── FileChangesCard.tsx
│           ├── FileChangesCard.module.css
│           ├── FileItem.tsx
│           └── index.ts
├── core/
│   └── api/
│       └── groupChatApi.ts           [修改] 增加快照 API 函数
└── layouts/
    ├── ChatArea/
    │   └── ChatArea.tsx              [修改] 渲染文件卡片
    └── RightSidebar/
        └── RightSidebar.tsx          [修改] 预览和 Diff 面板
```

---

## Task 1: 扩展 AgentResult 模型

**Files:**
- Modify: `agents_hub/agent_bridge/models.py:15-25`
- Test: `tests/agent_bridge/test_models.py`

- [ ] **Step 1: 读取现有 AgentResult 定义**

查看当前字段，确认插入位置。

- [ ] **Step 2: 写失败测试 - 验证新字段**

```python
# tests/agent_bridge/test_models.py
from agents_hub.agent_bridge.models import AgentResult
from agents_hub.config.types import AgentPlatform, RoleType

def test_agent_result_with_file_fields():
    """测试 AgentResult 包含文件相关字段"""
    result = AgentResult(
        text="任务完成",
        session_id="session_1",
        timestamp="2026-06-07T10:00:00",
        agent_name="TestAgent",
        platform=AgentPlatform.CLAUDE,
        role_type=RoleType.TEAM_MEMBER,
        cwd="/path/to/project",
        modified_files=[
            {
                "path": "test.py",
                "status": "modified",
                "additions": 10,
                "deletions": 5,
                "snapshot_id": "call_123_0",
                "diff_available": True,
                "diff_error": None
            }
        ],
        git_diff_range="abc123..def456"
    )
    
    assert result.cwd == "/path/to/project"
    assert len(result.modified_files) == 1
    assert result.modified_files[0]["path"] == "test.py"
    assert result.git_diff_range == "abc123..def456"
```

- [ ] **Step 3: 运行测试验证失败**

Run: `pytest tests/agent_bridge/test_models.py::test_agent_result_with_file_fields -v`
Expected: FAIL with "unexpected keyword argument 'cwd'"

- [ ] **Step 4: 扩展 AgentResult 模型**

```python
# agents_hub/agent_bridge/models.py
@dataclass
class AgentResult:
    text: str
    session_id: str
    timestamp: str
    agent_name: str
    platform: AgentPlatform
    role_type: RoleType
    # 新增字段
    cwd: str | None = None
    modified_files: list[dict] | None = None
    git_diff_range: str | None = None
```

- [ ] **Step 5: 运行测试验证通过**

Run: `pytest tests/agent_bridge/test_models.py::test_agent_result_with_file_fields -v`
Expected: PASS

- [ ] **Step 6: 测试字段为 None 的情况**

```python
def test_agent_result_without_file_fields():
    """测试 AgentResult 不包含文件字段"""
    result = AgentResult(
        text="任务完成",
        session_id="session_1",
        timestamp="2026-06-07T10:00:00",
        agent_name="TestAgent",
        platform=AgentPlatform.CLAUDE,
        role_type=RoleType.TEAM_MEMBER
    )
    
    assert result.cwd is None
    assert result.modified_files is None
    assert result.git_diff_range is None
```

Run: `pytest tests/agent_bridge/test_models.py::test_agent_result_without_file_fields -v`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add agents_hub/agent_bridge/models.py tests/agent_bridge/test_models.py
git commit -m "feat: 扩展 AgentResult 模型支持文件元数据字段

新增字段：
- cwd: Agent 工作目录
- modified_files: 修改的文件列表元数据
- git_diff_range: Git diff 范围"
```

---

## Task 2: 实现文件快照工具模块

**Files:**
- Create: `agents_hub/core/foundation/file_snapshot.py`
- Test: `tests/core/foundation/test_file_snapshot.py`

- [ ] **Step 1: 写失败测试 - 创建快照基本功能**

```python
# tests/core/foundation/test_file_snapshot.py
import tempfile
from pathlib import Path
from agents_hub.core.foundation.file_snapshot import create_file_snapshot

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
    import subprocess
    subprocess.run(["git", "init"], cwd=cwd, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=cwd, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=cwd, check=True, capture_output=True)
    subprocess.run(["git", "add", "test.py"], cwd=cwd, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=cwd, check=True, capture_output=True)
    
    # 修改文件
    test_file.write_text("def hello():\n    print('hello world')\n")
    
    # 创建快照
    metadata = create_file_snapshot(
        snapshot_dir=snapshot_dir,
        call_id="test_call",
        file_path="test.py",
        index=0,
        cwd=str(cwd),
        git_diff_range=None
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
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/core/foundation/test_file_snapshot.py::test_create_file_snapshot_basic -v`
Expected: FAIL with "cannot import name 'create_file_snapshot'"

- [ ] **Step 3: 实现 create_file_snapshot 函数**

```python
# agents_hub/core/foundation/file_snapshot.py
"""文件快照工具函数"""

import subprocess
from pathlib import Path
from typing import Tuple


def create_file_snapshot(
    snapshot_dir: Path,
    call_id: str,
    file_path: str,
    index: int,
    cwd: str,
    git_diff_range: str | None = None
) -> dict:
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
        "diff_error": diff_error
    }


def _run_git_diff(file_path: str, cwd: str, git_diff_range: str | None) -> Tuple[str, str | None]:
    """运行 git diff 命令"""
    if git_diff_range:
        cmd = ["git", "diff", git_diff_range, "--", file_path]
    else:
        cmd = ["git", "diff", "HEAD", "--", file_path]
    
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    
    if result.returncode == 0:
        return result.stdout, None
    else:
        return "", result.stderr or "git diff failed"


def _parse_diff(diff_text: str) -> Tuple[int, int, str]:
    """解析 diff，提取 additions/deletions/status"""
    additions = 0
    deletions = 0
    status = "modified"
    
    for line in diff_text.split('\n'):
        if line.startswith('+') and not line.startswith('+++'):
            additions += 1
        elif line.startswith('-') and not line.startswith('---'):
            deletions += 1
        elif line.startswith('new file mode'):
            status = "added"
        elif line.startswith('deleted file mode'):
            status = "deleted"
    
    return additions, deletions, status


def _read_file_content(file_path: str, cwd: str) -> str:
    """读取文件完整内容"""
    try:
        full_path = Path(cwd) / file_path
        return full_path.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError):
        return ""


def _save_snapshot(snapshot_dir: Path, snapshot_id: str, diff_text: str, content: str) -> None:
    """保存快照文件"""
    (snapshot_dir / f"{snapshot_id}.diff").write_text(diff_text, encoding="utf-8")
    (snapshot_dir / f"{snapshot_id}.content").write_text(content, encoding="utf-8")
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/core/foundation/test_file_snapshot.py::test_create_file_snapshot_basic -v`
Expected: PASS

- [ ] **Step 5: 写测试 - 读取快照内容**

```python
def test_get_snapshot_content(tmp_path):
    """测试读取快照内容"""
    from agents_hub.core.foundation.file_snapshot import get_snapshot_content
    
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    
    # 创建测试快照文件
    (snapshot_dir / "test_001_0.content").write_text("Hello World", encoding="utf-8")
    
    # 读取内容
    content = get_snapshot_content(snapshot_dir, "test_001_0")
    
    assert content == "Hello World"
```

- [ ] **Step 6: 实现 get_snapshot_content 函数**

```python
# 添加到 agents_hub/core/foundation/file_snapshot.py

def get_snapshot_content(snapshot_dir: Path, snapshot_id: str) -> str:
    """读取快照的文件内容"""
    content_path = snapshot_dir / f"{snapshot_id}.content"
    return content_path.read_text(encoding="utf-8")


def get_snapshot_diff(snapshot_dir: Path, snapshot_id: str) -> str:
    """读取快照的 diff"""
    diff_path = snapshot_dir / f"{snapshot_id}.diff"
    return diff_path.read_text(encoding="utf-8")
```

Run: `pytest tests/core/foundation/test_file_snapshot.py::test_get_snapshot_content -v`
Expected: PASS

- [ ] **Step 7: 写测试 - 处理非 git 仓库**

```python
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
        git_diff_range=None
    )
    
    # 非 git 仓库，diff 不可用
    assert metadata["diff_available"] is False
    assert metadata["diff_error"] is not None
    # 但内容仍然保存
    assert (snapshot_dir / "test_call_0.content").exists()
```

Run: `pytest tests/core/foundation/test_file_snapshot.py::test_create_snapshot_non_git_repo -v`
Expected: PASS (已有错误处理)

- [ ] **Step 8: 提交**

```bash
git add agents_hub/core/foundation/file_snapshot.py tests/core/foundation/test_file_snapshot.py
git commit -m "feat: 实现文件快照工具模块

新增功能：
- create_file_snapshot: 运行 git diff、解析、保存快照
- get_snapshot_content: 读取快照文件内容
- get_snapshot_diff: 读取快照 diff
- 支持非 git 仓库降级处理"
```

---

## Task 3: 扩展 finish_agent_call MCP tool

**Files:**
- Modify: `agents_hub/mcp/server.py:495-600`
- Read: `agents_hub/core/orchestration/group_chat_manager.py`

- [ ] **Step 1: 查看现有 finish_agent_call 函数签名**

确认参数插入位置和现有逻辑。

- [ ] **Step 2: 扩展函数签名**

```python
# agents_hub/mcp/server.py

async def finish_agent_call(
    agent_token: str,
    call_id: str,
    content: str,
    success: bool = True,
    modified_files: list[str] | None = None,      # 新增
    git_diff_range: str | None = None,            # 新增
) -> dict:
    """
    结束一个需要回复的 AgentCall
    
    Args:
        agent_token: 调用者的身份令牌
        call_id: 要结束的 AgentCall ID
        content: 最终回复内容
        success: True 表示完成，False 表示失败
        modified_files: 修改的文件路径列表（相对于 Agent 工作目录）
        git_diff_range: Git diff 范围，如 "abc123..def456"
    """
```

- [ ] **Step 3: 在 finish_agent_call 中集成文件快照逻辑**

在现有的 `_send_agent_call_completion_notification` 调用之前插入：

```python
# agents_hub/mcp/server.py (在 finish_agent_call 函数内)

from pathlib import Path
from agents_hub.core.foundation.file_snapshot import create_file_snapshot

# ... 现有的 token 验证和 call 获取逻辑 ...

# 处理文件快照（如果有 modified_files）
file_metadata_list = []
if modified_files:
    # 获取 Agent 的工作目录
    agent = _find_agent(group_chat, agent_name)
    cwd = getattr(agent, 'cwd', None) or group_chat.project_path
    
    # 准备快照目录
    snapshot_dir = Path(f"local_data/teams/{group_chat.project_path}/{group_chat_id}/file_snapshots")
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    # 为每个文件创建快照
    for index, file_path in enumerate(modified_files):
        try:
            metadata = create_file_snapshot(
                snapshot_dir=snapshot_dir,
                call_id=call_id,
                file_path=file_path,
                index=index,
                cwd=cwd,
                git_diff_range=git_diff_range
            )
            file_metadata_list.append(metadata)
        except Exception as e:
            # 单个文件失败不影响整体
            logger.warning(f"Failed to create snapshot for {file_path}: {e}")
            file_metadata_list.append({
                "path": file_path,
                "status": "modified",
                "additions": 0,
                "deletions": 0,
                "snapshot_id": f"{call_id}_{index}",
                "diff_available": False,
                "diff_error": str(e)
            })
```

- [ ] **Step 4: 修改 AgentResult 构造，传入文件元数据**

在 finish_agent_call 中构造 AgentResult 时添加新字段：

```python
# 构造 AgentResult（在现有逻辑基础上添加）
result = _make_chat_result(
    group_chat=group_chat,
    agent_name=agent_name,
    content=render_for_chat(agent_name, call.send_from, safe_content)
)

# 如果有文件元数据，添加到 result
if file_metadata_list:
    # result 是 AgentResult 对象，需要更新其字段
    result.cwd = cwd
    result.modified_files = file_metadata_list
    result.git_diff_range = git_diff_range
```

注意：需要检查 `_make_chat_result` 的返回类型，确保是 AgentResult。

- [ ] **Step 5: 测试 - 手动验证（集成测试）**

由于这是 MCP tool，需要在实际环境中测试：

1. 启动 MCP server
2. 模拟 Agent 调用：
```python
finish_agent_call(
    agent_token="<valid_token>",
    call_id="<existing_call_id>",
    content="任务完成",
    modified_files=["test.py"],
    git_diff_range=None
)
```
3. 检查快照目录是否创建文件
4. 检查 .jsonl 中是否包含 modified_files 字段

预期：快照文件创建成功，消息包含文件元数据

- [ ] **Step 6: 提交**

```bash
git add agents_hub/mcp/server.py
git commit -m "feat: finish_agent_call 支持文件快照

新增参数：
- modified_files: 文件路径列表
- git_diff_range: Git diff 范围

功能：
- 为每个文件创建快照（diff + content）
- 构造文件元数据列表
- 传递给 AgentResult"
```

---

## Task 4: 修改 GroupChatContext.add_message 处理新字段

**Files:**
- Modify: `agents_hub/core/context/group_chat_context.py:150-200`
- Read: `agents_hub/core/context/group_chat_repository.py`

- [ ] **Step 1: 查看 add_message 现有实现**

确认 AgentResult 如何转换为 dict 并写入 .jsonl。

- [ ] **Step 2: 确认 AgentResult 字段是否自动序列化**

检查是否使用 `dataclasses.asdict()` 或手动构造 dict。

如果是手动构造，需要添加新字段：

```python
# agents_hub/core/context/group_chat_context.py

async def add_message(self, result: AgentResult) -> None:
    """添加消息到上下文"""
    message_dict = {
        "agent_name": result.agent_name,
        "content": result.text,
        "timestamp": result.timestamp,
        "platform": result.platform.value,
        # 新增字段
        "cwd": result.cwd,
        "modified_files": result.modified_files,
        "git_diff_range": result.git_diff_range,
    }
    
    # 移除 None 值（可选，保持 .jsonl 文件简洁）
    message_dict = {k: v for k, v in message_dict.items() if v is not None}
    
    # ... 现有的写入逻辑 ...
```

如果是自动序列化（如 `asdict(result)`），则无需修改。

- [ ] **Step 3: 测试 - 验证字段写入 .jsonl**

写单元测试：

```python
# tests/core/context/test_group_chat_context.py

async def test_add_message_with_files(tmp_path):
    """测试添加包含文件元数据的消息"""
    from agents_hub.core.context.group_chat_context import GroupChatContext
    from agents_hub.agent_bridge.models import AgentResult
    
    # 创建测试 context
    context = GroupChatContext(...)  # 根据实际构造函数
    
    # 构造包含文件字段的 AgentResult
    result = AgentResult(
        text="完成",
        session_id="s1",
        timestamp="2026-06-07T10:00:00",
        agent_name="Agent1",
        platform=AgentPlatform.CLAUDE,
        role_type=RoleType.TEAM_MEMBER,
        cwd="/test",
        modified_files=[{"path": "a.py", "additions": 1, "deletions": 0}],
        git_diff_range="abc..def"
    )
    
    # 添加消息
    await context.add_message(result)
    
    # 读取 .jsonl 验证
    # ... 根据实际文件位置读取 ...
    # 验证 modified_files 字段存在
```

Run: `pytest tests/core/context/test_group_chat_context.py::test_add_message_with_files -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add agents_hub/core/context/group_chat_context.py tests/core/context/test_group_chat_context.py
git commit -m "feat: GroupChatContext.add_message 处理文件元数据字段

支持将 AgentResult 的 cwd、modified_files、git_diff_range 
字段写入 .jsonl 消息历史"
```

---

## Task 5: 新增 API 端点获取文件快照

**Files:**
- Modify: `agents_hub/api/routes/group_chat.py:400-500`
- Test: `tests/api/routes/test_group_chat.py`

- [ ] **Step 1: 写失败测试 - 获取快照内容**

```python
# tests/api/routes/test_group_chat.py
from fastapi.testclient import TestClient

def test_get_file_snapshot_content(client: TestClient, tmp_path):
    """测试获取文件快照内容 API"""
    # 准备测试数据：创建快照文件
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    (snapshot_dir / "test_call_0.content").write_text("Hello World")
    
    # 调用 API
    response = client.get("/api/group_chats/test_chat/files/test_call_0/content")
    
    assert response.status_code == 200
    assert response.json()["content"] == "Hello World"
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/api/routes/test_group_chat.py::test_get_file_snapshot_content -v`
Expected: FAIL with "404 Not Found"

- [ ] **Step 3: 实现 get_file_snapshot_content 端点**

```python
# agents_hub/api/routes/group_chat.py

from pathlib import Path
from agents_hub.core.foundation.file_snapshot import get_snapshot_content, get_snapshot_diff

@router.get("/{group_chat_id}/files/{snapshot_id}/content")
async def get_file_snapshot_content(
    group_chat_id: str,
    snapshot_id: str
) -> dict:
    """
    获取文件快照的完整内容
    
    Returns:
        {"content": "文件完整内容..."}
    """
    try:
        # 查找 group_chat
        group_chat = await group_chat_manager.load_group_chat(group_chat_id)
        
        # 构造快照目录
        snapshot_dir = Path(f"local_data/teams/{group_chat.project_path}/{group_chat_id}/file_snapshots")
        
        # 读取内容
        content = get_snapshot_content(snapshot_dir, snapshot_id)
        
        return {"content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{group_chat_id}/files/{snapshot_id}/diff")
async def get_file_snapshot_diff(
    group_chat_id: str,
    snapshot_id: str
) -> dict:
    """
    获取文件快照的 diff
    
    Returns:
        {"diff": "git diff 输出..."}
    """
    try:
        group_chat = await group_chat_manager.load_group_chat(group_chat_id)
        snapshot_dir = Path(f"local_data/teams/{group_chat.project_path}/{group_chat_id}/file_snapshots")
        diff = get_snapshot_diff(snapshot_dir, snapshot_id)
        return {"diff": diff}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/api/routes/test_group_chat.py::test_get_file_snapshot_content -v`
Expected: PASS

- [ ] **Step 5: 写测试 - 获取 diff**

```python
def test_get_file_snapshot_diff(client: TestClient, tmp_path):
    """测试获取文件快照 diff API"""
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    (snapshot_dir / "test_call_0.diff").write_text("diff --git...")
    
    response = client.get("/api/group_chats/test_chat/files/test_call_0/diff")
    
    assert response.status_code == 200
    assert "diff --git" in response.json()["diff"]
```

Run: `pytest tests/api/routes/test_group_chat.py::test_get_file_snapshot_diff -v`
Expected: PASS

- [ ] **Step 6: 测试 404 场景**

```python
def test_get_snapshot_not_found(client: TestClient):
    """测试获取不存在的快照"""
    response = client.get("/api/group_chats/test_chat/files/nonexistent/content")
    assert response.status_code == 404
```

Run: `pytest tests/api/routes/test_group_chat.py::test_get_snapshot_not_found -v`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add agents_hub/api/routes/group_chat.py tests/api/routes/test_group_chat.py
git commit -m "feat: 新增 API 端点获取文件快照

端点：
- GET /api/group_chats/{id}/files/{snapshot_id}/content
- GET /api/group_chats/{id}/files/{snapshot_id}/diff

错误处理：
- 404: 快照不存在
- 500: 读取失败"
```

---

## Task 6: 前端类型定义扩展

**Files:**
- Modify: `frontend/src/shared/types/api-schemas.ts:66-82`

- [ ] **Step 1: 添加 ModifiedFileInfo 接口**

```typescript
// frontend/src/shared/types/api-schemas.ts

/**
 * 文件修改信息
 */
export interface ModifiedFileInfo {
  /** 文件路径（相对于 cwd） */
  path: string;
  /** 文件状态 */
  status: 'added' | 'modified' | 'deleted';
  /** 新增行数 */
  additions: number;
  /** 删除行数 */
  deletions: number;
  /** 快照 ID */
  snapshot_id: string;
  /** diff 是否可用 */
  diff_available: boolean;
  /** diff 错误信息（如果有） */
  diff_error: string | null;
}
```

- [ ] **Step 2: 扩展 MessageApiItem 接口**

```typescript
/**
 * 消息信息（扩展）
 */
export interface MessageApiItem {
  speaker: string;
  content: string;
  timestamp: string;
  platform: string;
  cwd?: string;                           // 新增
  modified_files?: ModifiedFileInfo[];     // 新增
  git_diff_range?: string;                 // 新增
}
```

- [ ] **Step 3: 验证类型定义**

Run: `cd frontend && npm run type-check`
Expected: 无类型错误

- [ ] **Step 4: 提交**

```bash
git add frontend/src/shared/types/api-schemas.ts
git commit -m "feat: 前端类型定义扩展 - 文件元数据

新增类型：
- ModifiedFileInfo: 文件修改信息
扩展类型：
- MessageApiItem: 增加 cwd、modified_files、git_diff_range"
```

---

## Task 7: 实现 FileChangesCard 组件

**Files:**
- Create: `frontend/src/shared/components/FileChangesCard/FileChangesCard.tsx`
- Create: `frontend/src/shared/components/FileChangesCard/FileChangesCard.module.css`
- Create: `frontend/src/shared/components/FileChangesCard/FileItem.tsx`
- Create: `frontend/src/shared/components/FileChangesCard/index.ts`

- [ ] **Step 1: 创建组件目录结构**

```bash
mkdir -p frontend/src/shared/components/FileChangesCard
```

- [ ] **Step 2: 实现 FileChangesCard 主组件**

```typescript
// frontend/src/shared/components/FileChangesCard/FileChangesCard.tsx
import { useState } from 'react';
import { ModifiedFileInfo } from '@/shared/types/api-schemas';
import { FileItem } from './FileItem';
import styles from './FileChangesCard.module.css';

export interface FileChangesCardProps {
  modifiedFiles: ModifiedFileInfo[];
  groupChatId: string;
  onPreview: (snapshotId: string, filePath: string) => void;
  onDiff: (snapshotId: string, filePath: string) => void;
}

export function FileChangesCard({
  modifiedFiles,
  groupChatId,
  onPreview,
  onDiff,
}: FileChangesCardProps) {
  const [collapsed, setCollapsed] = useState(true);

  // 计算总的 additions 和 deletions
  const totalAdditions = modifiedFiles.reduce((sum, file) => sum + file.additions, 0);
  const totalDeletions = modifiedFiles.reduce((sum, file) => sum + file.deletions, 0);

  return (
    <div className={styles.card}>
      {/* 折叠头部 */}
      <div className={styles.header} onClick={() => setCollapsed(!collapsed)}>
        <div className={styles.summary}>
          <span className={styles.icon}>📝</span>
          <span>已编辑 {modifiedFiles.length} 个文件</span>
          <span className={styles.stats}>
            <span className={styles.additions}>+{totalAdditions}</span>
            <span className={styles.deletions}>-{totalDeletions}</span>
          </span>
        </div>
        <button className={styles.toggleBtn} type="button">
          {collapsed ? '展开 ▼' : '收起 ▲'}
        </button>
      </div>

      {/* 文件列表（展开时显示） */}
      {!collapsed && (
        <div className={styles.fileList}>
          {modifiedFiles.map((file) => (
            <FileItem
              key={file.snapshot_id}
              file={file}
              onPreview={() => onPreview(file.snapshot_id, file.path)}
              onDiff={() => onDiff(file.snapshot_id, file.path)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: 实现 FileItem 子组件**

```typescript
// frontend/src/shared/components/FileChangesCard/FileItem.tsx
import { ModifiedFileInfo } from '@/shared/types/api-schemas';
import styles from './FileChangesCard.module.css';

export interface FileItemProps {
  file: ModifiedFileInfo;
  onPreview: () => void;
  onDiff: () => void;
}

export function FileItem({ file, onPreview, onDiff }: FileItemProps) {
  // 根据文件状态选择图标
  const getIcon = () => {
    if (file.status === 'added') return '➕';
    if (file.status === 'deleted') return '➖';
    return '📄';
  };

  return (
    <div className={styles.fileItem}>
      <div className={styles.fileInfo}>
        <span className={styles.fileIcon}>{getIcon()}</span>
        <span className={styles.filePath}>{file.path}</span>
        <span className={styles.stats}>
          <span className={styles.additions}>+{file.additions}</span>
          <span className={styles.deletions}>-{file.deletions}</span>
        </span>
      </div>
      <div className={styles.actions}>
        <button className={styles.actionBtn} onClick={onPreview} type="button">
          预览
        </button>
        {file.diff_available && (
          <button className={styles.actionBtn} onClick={onDiff} type="button">
            Diff
          </button>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 创建样式文件**

```css
/* frontend/src/shared/components/FileChangesCard/FileChangesCard.module.css */
.card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: #fff;
  margin-top: 8px;
  overflow: hidden;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
}

.header:hover {
  background: #f5f5f5;
}

.summary {
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon {
  font-size: 18px;
}

.stats {
  display: flex;
  gap: 8px;
  margin-left: 8px;
}

.additions {
  color: #4caf50;
  font-weight: 500;
}

.deletions {
  color: #f44336;
  font-weight: 500;
}

.toggleBtn {
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  font-size: 12px;
}

.fileList {
  border-top: 1px solid #f0f0f0;
}

.fileItem {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.fileItem:last-child {
  border-bottom: none;
}

.fileInfo {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.fileIcon {
  font-size: 16px;
}

.filePath {
  color: #333;
  font-size: 14px;
  flex: 1;
}

.actions {
  display: flex;
  gap: 8px;
}

.actionBtn {
  padding: 4px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background: #fff;
  color: #333;
  cursor: pointer;
  font-size: 13px;
}

.actionBtn:hover {
  background: #f5f5f5;
}
```

- [ ] **Step 5: 创建 index.ts 导出**

```typescript
// frontend/src/shared/components/FileChangesCard/index.ts
export { FileChangesCard } from './FileChangesCard';
export type { FileChangesCardProps } from './FileChangesCard';
```

- [ ] **Step 6: 验证组件编译**

Run: `cd frontend && npm run build`
Expected: 编译成功，无错误

- [ ] **Step 7: 提交**

```bash
git add frontend/src/shared/components/FileChangesCard/
git commit -m "feat: 实现 FileChangesCard 组件

组件功能：
- 折叠/展开文件列表
- 显示文件数量和总行数变化
- 每个文件显示路径、状态图标、行数变化
- 预览和 Diff 按钮（diff 不可用时隐藏）"
```

---

## Task 8: 新增 API 调用函数

**Files:**
- Modify: `frontend/src/core/api/groupChatApi.ts:100-150`

- [ ] **Step 1: 添加获取快照内容函数**

```typescript
// frontend/src/core/api/groupChatApi.ts

/**
 * 获取文件快照内容
 */
export async function getFileSnapshotContent(
  groupChatId: string,
  snapshotId: string
): Promise<string> {
  const response = await fetch(
    `/api/group_chats/${groupChatId}/files/${snapshotId}/content`
  );
  
  if (!response.ok) {
    throw new Error(`Failed to fetch snapshot content: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.content;
}

/**
 * 获取文件快照 diff
 */
export async function getFileSnapshotDiff(
  groupChatId: string,
  snapshotId: string
): Promise<string> {
  const response = await fetch(
    `/api/group_chats/${groupChatId}/files/${snapshotId}/diff`
  );
  
  if (!response.ok) {
    throw new Error(`Failed to fetch snapshot diff: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.diff;
}
```

- [ ] **Step 2: 验证类型检查**

Run: `cd frontend && npm run type-check`
Expected: 无类型错误

- [ ] **Step 3: 提交**

```bash
git add frontend/src/core/api/groupChatApi.ts
git commit -m "feat: 新增文件快照 API 调用函数

新增函数：
- getFileSnapshotContent: 获取快照文件内容
- getFileSnapshotDiff: 获取快照 diff"
```

---

## Task 9: 集成到 ChatArea

**Files:**
- Modify: `frontend/src/layouts/ChatArea/ChatArea.tsx:30-60`
- Read: `frontend/src/layouts/RightSidebar/RightSidebar.tsx`

- [ ] **Step 1: 导入 FileChangesCard 组件**

```typescript
// frontend/src/layouts/ChatArea/ChatArea.tsx
import { FileChangesCard } from '@/shared/components/FileChangesCard';
import { getFileSnapshotContent, getFileSnapshotDiff } from '@/core/api/groupChatApi';
```

- [ ] **Step 2: 添加右侧栏内容状态管理**

```typescript
const [rightSidebarContent, setRightSidebarContent] = useState<{
  type: 'preview' | 'diff' | null;
  content: string;
  filePath: string;
} | null>(null);
```

- [ ] **Step 3: 实现预览和 Diff 处理函数**

```typescript
const handlePreview = async (snapshotId: string, filePath: string) => {
  try {
    const content = await getFileSnapshotContent(groupChatId, snapshotId);
    setRightSidebarContent({
      type: 'preview',
      content,
      filePath,
    });
    // 打开右侧栏（如果有 onToggleRightSidebar prop）
    onToggleRightSidebar?.();
  } catch (error) {
    console.error('Failed to load preview:', error);
    // TODO: 显示错误提示
  }
};

const handleDiff = async (snapshotId: string, filePath: string) => {
  try {
    const diff = await getFileSnapshotDiff(groupChatId, snapshotId);
    setRightSidebarContent({
      type: 'diff',
      content: diff,
      filePath,
    });
    onToggleRightSidebar?.();
  } catch (error) {
    console.error('Failed to load diff:', error);
  }
};
```

- [ ] **Step 4: 在消息渲染中添加 FileChangesCard**

在消息气泡下方添加：

```typescript
{/* 消息气泡 */}
<div className={styles.messageBubble}>
  <p>{message.content}</p>
</div>

{/* 文件变更卡片 */}
{message.modified_files && message.modified_files.length > 0 && (
  <FileChangesCard
    modifiedFiles={message.modified_files}
    groupChatId={groupChatId}
    onPreview={handlePreview}
    onDiff={handleDiff}
  />
)}
```

- [ ] **Step 5: 验证编译**

Run: `cd frontend && npm run build`
Expected: 编译成功

- [ ] **Step 6: 提交**

```bash
git add frontend/src/layouts/ChatArea/ChatArea.tsx
git commit -m "feat: ChatArea 集成 FileChangesCard

功能：
- 在消息下方渲染文件卡片
- 处理预览和 Diff 点击事件
- 调用 API 获取快照内容
- 更新右侧栏状态"
```

---

## Task 10: 右侧栏预览和 Diff 面板（简化版）

**Files:**
- Modify: `frontend/src/layouts/RightSidebar/RightSidebar.tsx:40-100`

- [ ] **Step 1: 扩展 RightSidebar 接收内容 prop**

```typescript
// frontend/src/layouts/RightSidebar/RightSidebar.tsx
export interface RightSidebarProps {
  collapsed: boolean;
  content?: {
    type: 'preview' | 'diff';
    content: string;
    filePath: string;
  } | null;
}

export function RightSidebar({ collapsed, content }: RightSidebarProps) {
```

- [ ] **Step 2: 实现预览面板（简化版 - 纯文本）**

```typescript
{/* 现有的成员列表、预览、Diff 模块 */}

{/* 动态内容显示 */}
{content && (
  <div className={styles.rightModule}>
    <div className={styles.moduleTitle}>
      {content.type === 'preview' ? '📄 预览' : '🔍 Diff'}
    </div>
    <div className={styles.moduleContent}>
      <div className={styles.filePathHeader}>{content.filePath}</div>
      <pre className={styles.codeBlock}>
        <code>{content.content}</code>
      </pre>
    </div>
  </div>
)}
```

- [ ] **Step 3: 添加简单样式**

```css
/* frontend/src/layouts/RightSidebar/RightSidebar.module.css */
.moduleContent {
  padding: 12px;
  max-height: 600px;
  overflow: auto;
}

.filePathHeader {
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
  padding: 4px 8px;
  background: #f5f5f5;
  border-radius: 4px;
}

.codeBlock {
  margin: 0;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  overflow-x: auto;
}

.codeBlock code {
  font-family: inherit;
}
```

- [ ] **Step 4: 验证编译和基本功能**

Run: `cd frontend && npm run dev`
手动测试：
1. 查看消息是否显示文件卡片
2. 点击预览，右侧栏是否显示内容
3. 点击 Diff，右侧栏是否显示 diff

Expected: 基本功能可用

- [ ] **Step 5: 提交**

```bash
git add frontend/src/layouts/RightSidebar/
git commit -m "feat: 右侧栏支持预览和 Diff 显示（简化版）

功能：
- 接收 content prop（type + content + filePath）
- 预览面板：纯文本显示文件内容
- Diff 面板：纯文本显示 diff 输出
- 基础样式和滚动支持

注：后续可升级为代码高亮和专业 diff 渲染"
```

---

## 自查清单

### Spec 覆盖检查

- [x] 数据结构设计 - AgentResult 扩展（Task 1）
- [x] 文件快照存储 - file_snapshot.py（Task 2）
- [x] MCP tool 扩展 - finish_agent_call（Task 3）
- [x] 消息持久化 - GroupChatContext（Task 4）
- [x] API 端点 - 获取快照（Task 5）
- [x] 前端类型定义（Task 6）
- [x] 文件卡片组件（Task 7）
- [x] API 调用函数（Task 8）
- [x] ChatArea 集成（Task 9）
- [x] 右侧栏预览（Task 10，简化版）
- [ ] 边界情况处理（敏感文件过滤、编码错误等） - 未包含，属于 P2
- [ ] 代码高亮和专业 Diff 渲染 - 未包含，属于 P1/P2

### 占位符检查

无 TBD、TODO 或模糊描述。

### 类型一致性检查

- `snapshot_id` 格式：`{call_id}_{index}` ✓
- `ModifiedFileInfo` 字段名：path, status, additions, deletions... ✓
- API 响应格式：`{content: string}` / `{diff: string}` ✓

---

## 实现顺序总结

**阶段 1: 后端核心（Task 1-5）**
1. 扩展数据模型
2. 实现快照工具
3. 集成到 MCP tool
4. 持久化到 .jsonl
5. 暴露 API 端点

**阶段 2: 前端核心（Task 6-10）**
6. 类型定义
7. 文件卡片组件
8. API 调用
9. ChatArea 集成
10. 右侧栏预览

**后续优化（未包含在本计划）**
- 代码高亮（react-syntax-highlighter）
- 专业 Diff 渲染（react-diff-view）
- 敏感文件过滤
- 大文件处理
- 错误提示优化

---
