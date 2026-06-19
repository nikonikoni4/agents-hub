# Git 兜底机制完整流程分析

## 场景：Agent 提交代码后，如何显示 diff

### 1. 执行前记录状态（base_agent.py:236-261）

```python
# 记录 Git 状态（用于文件变更兜底捕获）
git_head_before = None
status_before = None
if self.agent_cwd:
    git_head_before = get_git_head(self.agent_cwd)
    # 例如: "0717bb9abc..."
    
    if git_head_before:
        # 记录完整的工作区状态
        status_before = get_working_tree_status(self.agent_cwd)
        # 例如: {
        #   "/path/to/file1.py": " M",  # 已暂存
        #   "/path/to/file2.py": "??",  # untracked
        # }
```

**输出：**
- `git_head_before`: 当前 HEAD 的 commit hash
- `status_before`: 当前工作区所有文件的状态快照

---

### 2. Agent 执行任务（可能提交代码）

Agent 可能执行：
```bash
git add file1.py
git commit -m "feat: xxx"
```

此时：
- `HEAD` 从 `0717bb9` 变为 `fbffc94`（新提交）
- 工作区状态：file1.py 从 `" M"` 变为 `无状态`（已提交）

---

### 3. 执行后保存状态到 result（base_agent.py:290-293）

```python
# 保存 Git 状态到 result（供 fallback 使用）
if git_head_before:
    result.git_head_before = git_head_before  # "0717bb9..."
    result.status_before = status_before      # {"/path/to/file1.py": " M", ...}
```

---

### 4. 兜底闭环触发（base_agent.py:729-858）

```python
async def _fallback_close_task(self, msg: AgentMessage, result: AgentResult | None):
    """兜底闭环：未闭环的 TASK 补齐 mark_agent_response + 分流通知"""
    
    # 4.1 检查是否需要兜底
    if msg.message_type != MessageType.TASK:
        return
    call = await self.agent_call_manager.get_call(msg.call_id)
    if not (result and result.text and call and not call.has_agent_response):
        return
    
    # 4.2 移除 token，解析 <changes> XML
    safe_content = redact_token(result.text)
    changes = self._parse_changes_xml(safe_content)
    
    # 4.3 优先处理 XML（Agent 主动报告）
    if changes:
        if changes["files"]:
            await self._process_file_changes(
                result, msg.call_id, 
                changes["files"],      # 文件列表
                changes["diff"]        # 例如: "HEAD" 或 None
            )
    
    # 4.4 Git 兜底（Agent 没有输出 XML）
    elif result.git_head_before and self.agent_cwd:
        # 使用状态对比模式（推荐）
        status_before = getattr(result, "status_before", None)
        if status_before is not None:
            git_files = get_git_changed_files(
                self.agent_cwd,
                base_ref=result.git_head_before,  # "0717bb9..."
                status_before=status_before
            )
            
            if git_files:
                # ⚠️ 问题：这里传入 diff=None
                await self._process_file_changes(
                    result, msg.call_id, 
                    git_files,   # ["/path/to/file1.py", ...]
                    None         # ← 这里！
                )
```

---

### 5. 获取变更文件列表（file_snapshot.py:427-493）

```python
def get_git_changed_files(
    cwd: str,
    base_ref: str | None = None,           # "0717bb9..."
    status_before: dict[str, str] | None = None,  # {"/path/to/file1.py": " M", ...}
) -> list[str]:
    """获取 Git 仓库中变更的文件列表"""
    
    # 5.1 检测工作区变更（未提交的）
    status_after = get_working_tree_status(cwd)
    # 例如: {} (file1.py 已经被提交了，不在工作区了)
    
    changed_files = []
    for file_path, status_after_code in status_after.items():
        status_before_code = status_before.get(file_path)
        if status_before_code != status_after_code:
            changed_files.append(file_path)
    
    # 5.2 检测已提交的变更（HEAD 变化了）
    if base_ref:
        head_after = get_git_head(cwd)  # "fbffc94..."
        if head_after and head_after != base_ref:
            # HEAD 变化了！有新提交
            committed_files = _get_committed_files(cwd, base_ref, head_after)
            # 执行: git diff --name-only 0717bb9 fbffc94
            # 返回: ["agents_hub/core/agent/base_agent.py"]
            
            for rel_path in committed_files:
                abs_path = str(cwd_path / rel_path)
                if abs_path not in changed_files:
                    changed_files.append(abs_path)
    
    return changed_files  # ["/d/desktop/.../base_agent.py"]
```

**输出：** 包含已提交文件的绝对路径列表

---

### 6. 处理文件变更（base_agent.py:681-728）

```python
async def _process_file_changes(
    self,
    result: AgentResult,
    call_id: str,
    files: list[str],      # ["/d/.../base_agent.py"]
    diff: str | None,      # None ← 问题！
):
    """处理文件变更：创建快照并更新 result"""
    
    file_metadata_list = []
    for index, file_path in enumerate(files):
        metadata = create_file_snapshot(
            snapshot_dir=snapshot_dir,
            call_id=call_id,
            file_path=file_path,
            index=index,
            cwd=self.agent_cwd,
            git_diff_range=diff,  # None ← 传递下去了！
        )
        file_metadata_list.append(metadata)
    
    result.modified_files = file_metadata_list
    result.git_diff_range = diff
```

---

### 7. 创建文件快照（file_snapshot.py:16-66）

```python
def create_file_snapshot(
    snapshot_dir: Path,
    call_id: str,
    file_path: str,        # "/d/.../base_agent.py"
    index: int,
    cwd: str,
    git_diff_range: str | None = None,  # None
) -> FileMetadata:
    """为单个文件创建快照"""
    
    snapshot_id = f"{call_id}_{index}"
    
    # 7.1 运行 git diff
    diff_text, diff_error = _run_git_diff(
        file_path, 
        cwd, 
        git_diff_range  # None
    )
    
    # 7.2 解析 diff
    if diff_text:
        additions, deletions, status = _parse_diff(diff_text)
        diff_available = True
    else:
        # ⚠️ 如果没有 diff，标记为不可用
        additions, deletions, status = 0, 0, "modified"
        diff_available = False
    
    # 7.3 读取文件内容
    content = _read_file_content(file_path, cwd)
    
    # 7.4 保存快照
    _save_snapshot(snapshot_dir, snapshot_id, diff_text or "", content)
    
    # 7.5 返回元数据
    return {
        "path": file_path,
        "status": status,
        "additions": additions,
        "deletions": deletions,
        "snapshot_id": snapshot_id,
        "diff_available": diff_available,  # False！
        "diff_error": diff_error,
    }
```

---

### 8. 运行 git diff（file_snapshot.py:103-180）

```python
def _run_git_diff(
    file_path: str,              # "/d/.../base_agent.py"
    cwd: str,
    git_diff_range: str | None   # None
) -> tuple[str, str | None]:
    """运行 git diff 命令"""
    
    # 8.1 确定执行目录
    path_obj = Path(file_path)
    if path_obj.is_absolute():
        git_cwd = str(path_obj.parent)
        git_file_path = path_obj.name
    else:
        git_cwd = cwd
        git_file_path = file_path
    
    # 8.2 构建命令
    if git_diff_range:
        # 有 range，使用指定的 range
        cmd = ["git", "diff", git_diff_range, "--", git_file_path]
    else:
        # ⚠️ 没有 range，默认使用 HEAD
        is_untracked = _is_file_untracked(git_file_path, git_cwd)
        if is_untracked:
            cmd = ["git", "diff", "--no-index", "/dev/null", git_file_path]
        else:
            cmd = ["git", "diff", "HEAD", "--", git_file_path]
            # ← 问题所在！对于已提交的文件，这个命令返回空！
    
    # 8.3 执行命令
    result = subprocess.run(cmd, cwd=git_cwd, capture_output=True, text=True, timeout=30)
    
    if result.returncode == 0:
        return result.stdout, None  # 空字符串！
    else:
        return "", result.stderr or "git diff failed"
```

---

## 问题分析

### 已提交文件的 diff 为空的原因

对于已经提交的文件 `base_agent.py`：

```bash
# 当前状态
HEAD = fbffc94 (新提交)
base_agent.py 已经在这个提交中

# Git 兜底执行的命令
git diff HEAD -- base_agent.py
# 返回: (空) ← 因为 HEAD 本身就包含这个修改！

# 应该执行的命令
git diff 0717bb9 fbffc94 -- base_agent.py
# 或者
git diff 0717bb9 HEAD -- base_agent.py
# 返回: (有 diff) ← 显示从旧提交到新提交的变化
```

---

## 解决方案设计

### 方案 1：在 _fallback_close_task 中检测 HEAD 变化并构造 diff_range

```python
# base_agent.py:768-807
elif result.git_head_before and self.agent_cwd:
    try:
        status_before = getattr(result, "status_before", None)
        if status_before is not None:
            git_files = get_git_changed_files(
                self.agent_cwd,
                base_ref=result.git_head_before,
                status_before=status_before,
            )
            
            if git_files:
                # ✅ 检测 HEAD 是否变化
                from agents_hub.core.foundation.file_snapshot import get_git_head
                
                head_after = get_git_head(self.agent_cwd)
                if head_after and head_after != result.git_head_before:
                    # HEAD 变化了，使用 commit range
                    git_diff_range = f"{result.git_head_before}..{head_after}"
                    logger.info(
                        "[Git 兜底] 检测到新提交: %s -> %s",
                        result.git_head_before[:8],
                        head_after[:8]
                    )
                else:
                    # 没有新提交，对比工作区与 HEAD
                    git_diff_range = None
                
                await self._process_file_changes(
                    result, msg.call_id, git_files, git_diff_range
                )
```

### 方案 2：在 get_git_changed_files 中返回 diff_range

```python
# file_snapshot.py
def get_git_changed_files(...) -> tuple[list[str], str | None]:
    """返回 (变更文件列表, diff_range)"""
    
    changed_files = []
    diff_range = None
    
    # ...
    
    if base_ref:
        head_after = get_git_head(cwd)
        if head_after and head_after != base_ref:
            # HEAD 变化了
            diff_range = f"{base_ref}..{head_after}"
            committed_files = _get_committed_files(cwd, base_ref, head_after)
            # ...
    
    return changed_files, diff_range
```

### 方案 3：让 _run_git_diff 自动检测

```python
# file_snapshot.py:_run_git_diff
def _run_git_diff(file_path: str, cwd: str, git_diff_range: str | None) -> tuple[str, str | None]:
    # ...
    
    if git_diff_range:
        cmd = ["git", "diff", git_diff_range, "--", git_file_path]
    else:
        is_untracked = _is_file_untracked(git_file_path, git_cwd)
        if is_untracked:
            cmd = ["git", "diff", "--no-index", "/dev/null", git_file_path]
        else:
            # ✅ 智能检测：如果文件在 HEAD 中没有未提交的修改，尝试对比最近的提交
            staged_diff = subprocess.run(
                ["git", "diff", "HEAD", "--", git_file_path],
                cwd=git_cwd, capture_output=True, text=True, timeout=10
            )
            if not staged_diff.stdout.strip():
                # 没有未提交的修改，尝试显示最近一次提交的修改
                cmd = ["git", "diff", "HEAD~1", "HEAD", "--", git_file_path]
            else:
                cmd = ["git", "diff", "HEAD", "--", git_file_path]
```

---

## 推荐方案

**方案 1**：在 `_fallback_close_task` 中检测并构造 `diff_range`

**理由**：
1. 逻辑清晰：在调用方明确表达意图
2. 不改变底层函数签名（向后兼容）
3. 和 `get_git_changed_files` 中的 HEAD 检测逻辑一致
4. 数据来源准确：已经在 `get_git_changed_files` 中获取了 `head_after`，可以复用

**缺点**：
- 重复计算 `head_after`（在 `get_git_changed_files` 和 `_fallback_close_task` 中各调用一次）

---

## 改进建议

让 `get_git_changed_files` 返回元组 `(files, diff_range)`：

```python
def get_git_changed_files(...) -> tuple[list[str], str | None]:
    """返回 (变更文件列表, 推荐的 diff_range)"""
    # ...
    return changed_files, diff_range
```

这样可以：
1. 避免重复计算 `head_after`
2. 让 `get_git_changed_files` 的职责更完整（不仅返回文件列表，还告诉你如何 diff）
3. 调用方更简单
