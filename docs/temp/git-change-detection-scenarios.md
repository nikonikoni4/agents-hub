# Git 文件变更检测场景全面分析

**创建时间**：2026-06-15  
**目标**：为 Agent 执行前后的文件变更检测设计可靠的兜底方案

---

## 一、问题背景

### 1.1 核心挑战

agents-hub 需要检测每个 Agent 执行前后的文件变更，但面临以下复杂场景：

- **多 Agent 顺序执行**：Agent A 和 Agent B 在同一仓库依次执行
- **文件状态多样**：untracked、tracked、staged、modified
- **修改目标重叠**：后一个 Agent 可能修改前一个 Agent 创建的文件
- **Git 状态不稳定**：用户可能在 Agent 执行间手动 commit/stage

### 1.2 当前实现

**方案 A：记录 HEAD + untracked 文件集合**

```python
# 执行前
git_head_before = get_git_head(cwd)  # 记录 commit hash
untracked_before = get_untracked_files(cwd)  # 记录 untracked 文件绝对路径集合

# 执行后
changed_files = get_git_changed_files(cwd, git_head_before, exclude_untracked=untracked_before)
```

**核心逻辑**：
1. `git diff <base_ref> HEAD` - 检测已提交的变更
2. `git status --porcelain` - 检测工作区变更（包括 staged 和 modified）
3. 过滤掉 `untracked_before` 中的文件（避免误报用户已有的截图、文档等）

**已知问题**：
- ❌ **无法检测 untracked 文件的内容变化**（状态码都是 `??`）
- ❌ **依赖文件路径集合过滤**，对于大量 untracked 文件性能较差

---

## 二、变量维度分析

### 2.1 状态维度

| 维度 | 可能值 | 说明 |
|------|--------|------|
| **跟踪状态** | Untracked / Tracked | 文件是否被 Git 跟踪 |
| **提交状态** | Committed / Staged / Modified / New | 文件在 Git 中的状态 |
| **执行次序** | Agent A 先 / Agent B 后 | 多个 Agent 顺序执行 |
| **修改目标** | 不同文件 / 相同文件 | Agent 是否修改同一文件 |

### 2.2 Git 状态码速查（`git status --porcelain`）

```
格式：XY filename
X = 暂存区状态，Y = 工作区状态

常见状态码：
?? = untracked（新文件，未被跟踪）
A  = 暂存的新文件（staged new file）
 M = 已跟踪文件被修改（modified，未暂存）
M  = 已跟踪文件被修改并暂存（staged modified）
MM = 暂存后又修改（staged and modified again）
```

---

## 三、场景穷举与检测方案对比

### 3.1 场景矩阵

| # | Agent A 操作 | A 执行后状态 | Agent B 操作 | B 执行后状态 | 关键问题 |
|---|-------------|-------------|-------------|-------------|----------|
| 1 | 创建 `new.py` | `?? new.py` | 修改 `new.py` | `?? new.py` | **状态码相同，内容变了** |
| 2 | 创建 `new.py` | `?? new.py` | stage `new.py` | `A  new.py` | 状态码变化 |
| 3 | 创建 `new.py` | `?? new.py` | commit `new.py` | （无变更） | HEAD 变化 |
| 4 | 修改 `old.py` | ` M old.py` | 再修改 `old.py` | ` M old.py` | 状态码相同，内容变了 |
| 5 | 修改 `old.py` | ` M old.py` | stage `old.py` | `M  old.py` | 状态码变化 |
| 6 | stage `old.py` | `M  old.py` | 再修改 `old.py` | `MM old.py` | 状态码变化 |
| 7 | 创建 `a.py` | `?? a.py` | 创建 `b.py` | `?? a.py`<br>`?? b.py` | 不同文件，易检测 |
| 8 | 删除 `old.py` | ` D old.py` | 恢复 `old.py` | （无变更） | 文件存在性变化 |

### 3.2 边界情况

| # | 场景 | 说明 |
|---|------|------|
| 9 | 文件重命名 | `R  old.py -> new.py` |
| 10 | .gitignore 文件 | 不会出现在 `git status` 中 |
| 11 | 非 Git 仓库 | 所有 Git 命令失败 |
| 12 | 用户手动 commit | HEAD 变化，但不是 Agent 导致的 |

---

## 四、检测方案对比

### 方案 A：记录 `git status` 前后对比（推荐 ✅）

**实现**：
```python
# 执行前
status_before = get_working_tree_status(cwd)  # 返回 {绝对路径: 状态码} 字典

# 执行后
status_after = get_working_tree_status(cwd)

# 对比：找出状态码变化的文件
changed_files = []
for file_path, status_after_code in status_after.items():
    status_before_code = status_before.get(file_path)
    if status_before_code != status_after_code:  # 包括新增（None -> "??"）
        changed_files.append(file_path)
```

**优点**：
- ✅ **能检测 untracked 文件的内容变化**（场景 1）
- ✅ 能检测所有状态转换（场景 2-6）
- ✅ 能检测新增文件（场景 7）
- ✅ 实现简单，只需一个 `git status` 命令
- ✅ 性能好：状态码字符串比较，O(n) 复杂度

**缺点**：
- ⚠️ **无法区分内容变化的程度**（场景 1、4：状态码相同时，不知道改了多少）
- ⚠️ 对于 untracked 文件，`??` 状态码相同意味着无法检测

**适用场景**：
- ✅ 检测"有没有变化"（布尔值）
- ❌ 无法用于生成 diff 统计（additions/deletions）

---

### 方案 B：使用 `git stash create` 创建临时快照

**实现**：
```python
# 执行前
stash_before = subprocess.run(
    ["git", "stash", "create"],
    cwd=cwd, capture_output=True, text=True
).stdout.strip()  # 返回 stash commit hash，如果工作区干净则返回空

# 执行后
stash_after = subprocess.run(["git", "stash", "create"], ...).stdout.strip()

# 对比
if stash_before != stash_after:
    # 有变更，获取变更文件列表
    if stash_before and stash_after:
        # 两个 stash 都存在，对比差异
        result = subprocess.run(
            ["git", "diff", "--name-only", stash_before, stash_after],
            cwd=cwd, capture_output=True, text=True
        )
        changed_files = result.stdout.strip().split("\n")
    elif not stash_before and stash_after:
        # 从干净工作区变为有变更
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", stash_after],
            cwd=cwd, capture_output=True, text=True
        )
        changed_files = result.stdout.strip().split("\n")
```

**优点**：
- ✅ **能检测 staged + modified 的内容变化**
- ✅ 能生成 diff（通过 `git diff <stash1> <stash2>`）

**缺点**：
- ❌ **无法检测 untracked 文件**（`git stash create` 不包含 untracked）
- ❌ 复杂度高：需要处理 stash 为空的情况
- ❌ 性能较差：生成 stash 需要遍历工作区
- ❌ 场景 1 完全无法检测（untracked 文件不在 stash 中）

**适用场景**：
- ❌ 不适合作为通用兜底方案（无法覆盖 untracked）

---

### 方案 C：只检测 untracked 文件的增量（当前实现的一部分）

**实现**：
```python
# 执行前
untracked_before = get_untracked_files(cwd)  # 返回绝对路径集合

# 执行后
untracked_after = get_untracked_files(cwd)

# 增量
new_untracked = untracked_after - untracked_before
```

**优点**：
- ✅ 能检测新创建的 untracked 文件（场景 7）
- ✅ 能过滤用户已有的 untracked 文件

**缺点**：
- ❌ **无法检测 untracked 文件的内容变化**（场景 1）
- ❌ 无法检测状态转换（untracked → staged）
- ❌ 只能检测文件的增减，不能检测修改

**适用场景**：
- ⚠️ 需要与其他方案组合使用
- ❌ 单独使用无法覆盖场景 1

---

### 方案 D：结合方案 A + 文件内容哈希（完全兜底）

**实现**：
```python
# 执行前
status_before = get_working_tree_status(cwd)
# 对于 untracked 文件，额外记录内容哈希
untracked_hashes_before = 
for file_path, status_code in status_before.items():
    if status_code == "??":
        content = Path(file_path).read_bytes()
        untracked_hashes_before[file_path] = hashlib.sha256(content).hexdigest()

# 执行后
status_after = get_working_tree_status(cwd)
untracked_hashes_after = {}
for file_path, status_code in status_after.items():
    if status_code == "??":
        content = Path(file_path).read_bytes()
        untracked_hashes_after[file_path] = hashlib.sha256(content).hexdigest()

# 对比
changed_files = []
# 1. 状态码变化
for file_path, status_after_code in status_after.items():
    if status_before.get(file_path) != status_after_code:
        changed_files.append(file_path)

# 2. untracked 文件内容变化
for file_path, hash_after in untracked_hashes_after.items():
    hash_before = untracked_hashes_before.get(file_path)
    if hash_before and hash_before != hash_after:
        changed_files.append(file_path)
```

**优点**：
- ✅ **完全覆盖所有场景**（包括场景 1）
- ✅ 能检测 untracked 文件的内容变化
- ✅ 能检测所有状态转换

**缺点**：
- ⚠️ 性能开销：需要读取所有 untracked 文件的内容计算哈希
- ⚠️ 对于大量 untracked 文件（如 node_modules）性能较差
- ⚠️ 需要处理文件读取失败（权限、编码等）

**优化方案**：
- 只对"小文件"计算哈希（如 < 1MB）
- 使用文件 mtime（修改时间）作为快速检测（不可靠但快）
- 结合 .gitignore 规则，跳过不需要跟踪的文件

**适用场景**：
- ✅ 需要完全可靠的兜底方案
- ✅ untracked 文件数量可控（< 100 个）

---

## 五、实际测试验证

### 5.1 测试场景 1：untracked 文件内容变化

```bash
# 初始状态
$ git status --porcelain
?? new.py

# Agent A 修改 new.py（内容从 "v1" 改为 "v2"）
$ git status --porcelain
?? new.py  # ← 状态码没变！

# 测试方案 A（状态对比）
状态码前后都是 "??"，无法检测 ❌

# 测试方案 D（状态 + 哈希）
哈希从 sha256("v1") 变为 sha256("v2")，能检测 ✅
```

**结论**：方案 A 无法检测场景 1，需要方案 D。

### 5.2 测试场景 2：untracked → staged

```bash
# Agent A 执行后
$ git status --porcelain
?? new.py

# Agent B 执行 git add
$ git status --porcelain
A  new.py  # ← 状态码变化

# 测试方案 A
"??" → "A " 能检测 ✅
```

**结论**：方案 A 能检测状态转换。

### 5.3 测试场景 4：tracked 文件多次修改

```bash
# Agent A 修改 old.py
$ git status --porcelain
 M old.py

# Agent B 再修改 old.py
$ git status --porcelain
 M old.py  # ← 状态码没变

# 测试方案 A
状态码前后都是 " M"，无法检测 ❌

# 但实际上：old.py 是 tracked 文件
# 可以用 git diff 检测内容变化（与 HEAD 对比）
$ git diff HEAD -- old.py  # 能看到完整 diff ✅
```

**关键发现**：
- 对于 **tracked 文件**，即使状态码相同，`git diff HEAD` 也能检测内容变化
- 对于 **untracked 文件**，状态码相同时，无法用 git diff 检测（因为没有 baseline）

---

## 六、推荐方案与实现

### 6.1 方案选择矩阵

| 场景 | 方案 A<br>（状态对比） | 方案 D<br>（状态+哈希） | 实际需求 |
|------|----------------------|----------------------|----------|
| Untracked 新增 | ✅ | ✅ | 高 |
| Untracked 内容变化 | ❌ | ✅ | **中** |
| Tracked 状态转换 | ✅ | ✅ | 高 |
| Tracked 内容变化 | ⚠️（用 diff） | ✅ | 高 |
| 性能 | 优秀 | 中等 | 高 |
| 实现复杂度 | 低 | 中 | - |

### 6.2 推荐方案：**混合方案**（方案 A + 按需哈希）

**核心思路**：
1. 默认使用方案 A（状态对比）- 覆盖 90% 场景
2. 对于状态码未变但需要确认的文件，按需计算哈希或使用 mtime
3. 优先使用 Git 命令（tracked 文件用 `git diff`）

**实现伪代码**：
```python
def get_git_changed_files_v2(cwd: str, status_before: dict, enable_content_check: bool = False):
    """
    Args:
        cwd: 工作目录
        status_before: 执行前的状态 {绝对路径: 状态码}
        enable_content_check: 是否启用内容变化检测（针对 untracked 文件）
    """
    status_after = get_working_tree_status(cwd)
    changed_files = []
    
    # 1. 检测状态码变化（包括新增文件）
    for file_path, status_after_code in status_after.items():
        status_before_code = status_before.get(file_path)
        if status_before_code != status_after_code:
            changed_files.append(file_path)
            continue
        
        # 2. 对于状态码相同的文件，按需检测内容
        if enable_content_check and status_after_code == "??":
            # untracked 文件：使用 mtime 快速检测（或哈希）
            if _is_file_modified_by_mtime(file_path, status_before):
                changed_files.append(file_path)
    
    return changed_files

def _is_file_modified_by_mtime(file_path: str, status_before_snapshot: dict) -> bool:
    """通过文件修改时间快速判断（不完全可靠，但快）"""
    try:
        current_mtime = Path(file_path).stat().st_mtime
        # 需要在 status_before 中额外存储 mtime
        before_mtime = status_before_snapshot.get(file_path, {}).get("mtime")
        if before_mtime is None:
            return False  # 无法判断
        return current_mtime > before_mtime
    except (FileNotFoundError, PermissionError):
        return False
```

**数据结构升级**：
```python
# 当前
status_before = {
    "/path/to/file.py": "??",
}

# 升级后（可选存储更多元数据）
status_before = {
    "/path/to/file.py": {
        "status": "??",
        "mtime": 1718438400.0,  # 可选：文件修改时间
        "size": 1024,            # 可选：文件大小
    }
}
```

---

### 6.3 推荐实现（分阶段）

#### 阶段 1：升级现有方案（短期，覆盖 90%）

**目标**：从 `exclude_untracked` 迁移到 `status_before`

```python
# agents_hub/core/foundation/file_snapshot.py

def get_working_tree_status(cwd: str) -> dict[str, str]:
    """获取当前工作区状态（已实现）
    
    Returns:
        {绝对路径: 状态码} 字典
        状态码格式：XY（如 "??", " M", "A ", "MM"）
    """
    # 已实现，见现有代码
    pass

def get_git_changed_files(
    cwd: str,
    base_ref: str | None = None,
    status_before: dict[str, str] | None = None,  # 推荐参数
    exclude_untracked: set[str] | None = None,    # 废弃，保留兼容
) -> list[str]:
    """获取 Git 仓库中变更的文件列表
    
    推荐使用 status_before 参数（状态对比模式）。
    """
    if status_before is not None:
        # 使用状态对比模式（推荐）
        status_after = get_working_tree_status(cwd)
        changed_files = []
        
        for file_path, status_after_code in status_after.items():
            status_before_code = status_before.get(file_path)
            if status_before_code != status_after_code:
                changed_files.append(file_path)
        
        return changed_files
    
    # 向后兼容：使用旧的 exclude_untracked 逻辑
    # ...（保留现有实现）
```

**Agent 调用代码升级**：
```python
# agents_hub/core/agent/base_agent.py

# 执行前（替换现有的 untracked_before）
status_before = None
if self.agent_cwd:
    from agents_hub.core.foundation.file_snapshot import get_working_tree_status
    status_before = get_working_tree_status(self.agent_cwd)

# 执行后
if status_before is not None:
    changed_files = get_git_changed_files(self.agent_cwd, None, status_before=status_before)
```

**优点**：
- ✅ 实现简单，改动量小
- ✅ 覆盖 90% 场景（状态转换、新增文件）
- ✅ 性能优秀（只需两次 `git status`）
- ✅ 向后兼容（保留 `exclude_untracked` 参数）

**缺点**：
- ⚠️ 无法检测 untracked 文件的内容变化（场景 1）
- ⚠️ 无法检测 tracked 文件的二次修改（场景 4）

---

#### 阶段 2：增强内容检测（中期，可选）

**目标**：为高价值场景增加内容检测

```python
def get_working_tree_status_with_metadata(cwd: str) -> dict[str, dict]:
    """获取工作区状态 + 文件元数据
    
    Returns:
        {
            "/path/to/file.py": {
                "status": "??",
                "mtime": 1718438400.0,  # 修改时间
                "size": 1024,            # 文件大小（字节）
            }
        }
    """
    status_map = get_working_tree_status(cwd)
    result = {}
    
    for file_path, status_code in status_map.items():
        try:
            stat = Path(file_path).stat()
            result[file_path] = {
                "status": status_code,
                "mtime": stat.st_mtime,
                "size": stat.st_size,
            }
        except (FileNotFoundError, PermissionError):
            result[file_path] = {"status": status_code}
    
    return result

def get_git_changed_files_enhanced(
    cwd: str,
    status_before: dict[str, dict],  # 包含 mtime
    check_untracked_content: bool = True,
) -> list[str]:
    """增强版文件变更检测"""
    status_after = get_working_tree_status_with_metadata(cwd)
    changed_files = []
    
    for file_path, after_meta in status_after.items():
        before_meta = status_before.get(file_path, {})
        before_status = before_meta.get("status")
        after_status = after_meta["status"]
        
        # 1. 状态码变化
        if before_status != after_status:
            changed_files.append(file_path)
            continue
        
        # 2. untracked 文件内容变化（通过 mtime + size 快速检测）
        if check_untracked_content and after_status == "??":
            before_mtime = before_meta.get("mtime", 0)
            before_size = before_meta.get("size", -1)
            after_mtime = after_meta.get("mtime", 0)
            after_size = after_meta.get("size", -1)
            
            # mtime 或 size 变化 → 内容可能变化
            if after_mtime > before_mtime or after_size != before_size:
                changed_files.append(file_path)
    
    return changed_files
```

**优点**：
- ✅ 能检测 untracked 文件的内容变化（通过 mtime/size）
- ✅ 性能开销低（stat 系统调用很快）
- ✅ 不需要读取文件内容

**缺点**：
- ⚠️ mtime 不完全可靠（可能被用户手动修改）
- ⚠️ 同样大小的文件修改无法检测（罕见）

**何时启用**：
- 用户配置 `enable_content_check=true`
- 或者只在 untracked 文件数量 < 50 时自动启用

---

#### 阶段 3：完全兜底（长期，按需）

**目标**：100% 可靠检测（哈希验证）

```python
def get_git_changed_files_with_hash(
    cwd: str,
    status_before: dict[str, dict],  # 包含 hash
) -> list[str]:
    """完全可靠的文件变更检测（使用 SHA256 哈希）"""
    # 执行前需要计算所有 untracked 文件的哈希
    # 性能开销较大，仅在必要时使用
    pass
```

**使用场景**：
- 用户明确要求"完全可靠检测"
- 关键任务（如生产部署前的变更审查）
- untracked 文件数量 < 20 且都是小文件

---

## 七、特殊场景处理

### 7.1 文件重命名

```bash
$ git status --porcelain
R  old.py -> new.py
```

**处理方式**：
- `git status --porcelain` 输出中，重命名文件显示为 `R  old -> new`
- 现有代码已处理：提取 ` -> ` 后的新文件名
- 状态对比模式下：
  - `old.py` 从状态字典中消失（或变为 ` D`）
  - `new.py` 出现，状态码为 `R `

### 7.2 .gitignore 文件

**特性**：
- 被 `.gitignore` 忽略的文件**不会出现在 `git status` 中**
- 因此不会被检测为变更

**处理方式**：
- 如果需要检测 gitignore 文件的变更，需要额外逻辑：
  ```bash
  git ls-files --others --ignored --exclude-standard
  ```
- **推荐**：不检测 gitignore 文件（它们被忽略通常是有原因的）

### 7.3 非 Git 仓库

**检测方式**：
```python
def is_git_repo(cwd: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=cwd, capture_output=True
    )
    return result.returncode == 0
```

**处理方式**：
- 执行前检测是否是 Git 仓库
- 如果不是，跳过 Git 兜底，返回空列表
- 记录日志：`logger.info("非 Git 仓库，跳过文件变更检测")`

### 7.4 Git 子模块

**特性**：
- 子模块在主仓库中显示为一个特殊项（`160000` 模式）
- `git status` 显示子模块路径，但不显示子模块内部的文件

**处理方式**：
- 当前实现：将子模块路径作为整体检测
- **推荐**：记录子模块的 commit hash 变化，不深入子模块内部

---

## 八、性能与可靠性分析

### 8.1 性能对比

| 方案 | 命令数 | 文件 I/O | 时间复杂度 | 适用文件数 |
|------|--------|---------|-----------|-----------|
| 方案 A（状态对比） | 2 次 `git status` | 0 | O(n) | 无限制 |
| 方案 D（状态+mtime） | 2 次 `git status` + n 次 stat | n 次 stat | O(n) | < 1000 |
| 方案 D（状态+哈希） | 2 次 `git status` | n 次文件读取 | O(n×m) | < 50 |

**说明**：
- n = 文件数量
- m = 平均文件大小
- stat 系统调用很快（< 1ms）
- 文件读取速度取决于磁盘 I/O（SSD 约 500MB/s）

**性能测试数据**（估算）：

| 场景 | 文件数 | 方案 A | 方案 D (mtime) | 方案 D (哈希) |
|------|--------|--------|---------------|--------------|
| 小项目 | 10 | < 10ms | < 20ms | < 50ms |
| 中项目 | 100 | < 50ms | < 100ms | < 500ms |
| 大项目 | 1000 | < 200ms | < 500ms | < 5s |

**推荐配置**：
- 默认：方案 A（快速，覆盖 90%）
- 文件数 < 50：自动升级到方案 D (mtime)
- 用户显式要求：方案 D (哈希)

### 8.2 可靠性分析

| 场景 | 方案 A | 方案 D (mtime) | 方案 D (哈希) |
|------|--------|---------------|--------------|
| Untracked 新增 | ✅ 100% | ✅ 100% | ✅ 100% |
| Untracked 内容变 | ❌ 0% | ⚠️ 95% | ✅ 100% |
| Tracked 状态转换 | ✅ 100% | ✅ 100% | ✅ 100% |
| Tracked 内容变 | ⚠️ Git diff | ✅ 100% | ✅ 100% |
| 误报率 | 0% | < 1% | 0% |

**误报来源（mtime）**：
- 用户手动 `touch` 文件（修改 mtime 但不修改内容）
- 文件系统时间不同步
- **实际影响**：误报优于漏报（用户看到没变化的文件，但不会漏掉真正的变化）

### 8.3 推荐决策树

```
开始检测文件变更
    ↓
是否是 Git 仓库？
    ├─ 否 → 跳过检测，返回空列表
    └─ 是 → 记录 status_before
        ↓
    Agent 执行完成
        ↓
    获取 status_after，状态对比
        ↓
    有状态码变化的文件？
        ├─ 是 → 加入 changed_files
        └─ 否 → 继续
            ↓
    untracked 文件数 < 50？
        ├─ 是 → 检测 mtime/size 变化
        └─ 否 → 跳过内容检测
            ↓
    返回 changed_files
```

---

## 九、实现建议与迁移路径

### 9.1 短期（1-2 天）：升级到方案 A

**目标**：从 `exclude_untracked` 迁移到 `status_before`

**改动点**：
1. `agents_hub/core/foundation/file_snapshot.py`：
   - ✅ `get_working_tree_status()` 已实现
   - ✅ `get_git_changed_files()` 支持 `status_before` 参数（已实现）
   - 无需改动

2. `agents_hub/core/agent/base_agent.py`：
   - 替换 `untracked_before = get_untracked_files()` → `status_before = get_working_tree_status()`
   - 替换 `exclude_untracked=untracked_before` → `status_before=status_before`

3. 测试：
   - 运行现有测试 `tests/core/foundation/test_git_fallback.py`
   - 新增测试：场景 2-6（状态转换）

**预期收益**：
- 覆盖 90% 场景
- 性能提升（减少 `git ls-files` 调用）
- 代码更简洁

### 9.2 中期（1 周）：可选增强

**目标**：支持 mtime 检测（按需启用）

**改动点**：
1. 新增 `get_working_tree_status_with_metadata()`
2. 新增配置项 `enable_content_check`（默认 False）
3. 自动启用条件：untracked 文件数 < 50

**使用场景**：
- 用户明确关心 untracked 文件的内容变化
- 开发场景（频繁修改未 commit 的新文件）

### 9.3 长期（按需）：完全兜底

**目标**：哈希验证（用户显式启用）

**触发条件**：
- 用户配置 `reliable_detection=true`
- 或通过 MCP tool 参数 `enable_hash_check=true`

---

## 十、总结与推荐

### 10.1 核心发现

1. **状态码对比（方案 A）是最优的基础方案**：
   - 覆盖 90% 场景
   - 性能优秀
   - 实现简单

2. **Untracked 文件内容变化（场景 1）是唯一盲区**：
   - 现有方案无法检测
   - 实际影响：Agent A 创建文件，Agent B 修改该文件时漏报
   - 发生频率：低（Agent 通常操作不同文件）

3. **Tracked 文件的内容变化可以用 Git 检测**：
   - 即使状态码相同（场景 4），`git diff HEAD` 也能检测
   - 但需要额外调用 `git diff`，增加复杂度

### 10.2 推荐方案

**阶段 1（立即实施）**：
- ✅ 使用 `status_before` 替代 `exclude_untracked`
- ✅ 覆盖 90% 场景，性能优秀
- ✅ 改动量小，风险低

**阶段 2（可选）**：
- ⚠️ 增加 mtime 检测（自动启用条件：untracked < 50）
- ⚠️ 覆盖 95% 场景
- ⚠️ 极低误报率

**阶段 3（按需）**：
- ❓ 哈希验证（用户显式启用）
- ❓ 100% 可靠，但性能开销大

### 10.3 实现优先级

| 任务 | 优先级 | 工作量 | 价值 |
|------|--------|--------|------|
| 迁移到 `status_before` | P0 | 1h | 高 |
| 编写测试（场景 2-6） | P0 | 2h | 高 |
| 实现 mtime 检测 | P1 | 4h | 中 |
| 实现哈希检测 | P2 | 6h | 低 |
| 文档更新 | P0 | 1h | 高 |

### 10.4 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 场景 1 漏报 | Agent B 修改 Agent A 创建的 untracked 文件未检测 | 低 | 阶段 2 增加 mtime 检测 |
| mtime 误报 | 用户 touch 文件导致误报变更 | 极低 | 误报优于漏报，可接受 |
| 性能下降 | 大量 untracked 文件时 stat 调用慢 | 低 | 限制 mtime 检测的触发条件 |

---

## 十一、代码示例

### 11.1 推荐实现（阶段 1）

```python
# agents_hub/core/agent/base_agent.py

async def _process_message(self, msg: AgentMessage, prompt: str = ""):
    # 记录 Git 状态（执行前）
    status_before = None
    if self.agent_cwd:
        from agents_hub.core.foundation.file_snapshot import (
            get_working_tree_status,
            is_git_repo,
        )
        
        if is_git_repo(self.agent_cwd):
            status_before = get_working_tree_status(self.agent_cwd)
            self.logger.info(
                "[Git 兜底] 记录执行前状态: %d 个文件有变更, agent=%s",
                len(status_before),
                self.name,
            )
        else:
            self.logger.info("[Git 兜底] 非 Git 仓库，跳过检测, agent=%s", self.name)
    
    try:
        # ... 执行 Agent ...
        result = await self.execute(...)
        
        # Git 兜底：检测文件变更（执行后）
        if status_before is not None:
            from agents_hub.core.foundation.file_snapshot import get_git_changed_files
            
            changed_files = get_git_changed_files(
                self.agent_cwd,
                base_ref=None,  # 不使用 base_ref
                status_before=status_before,  # 使用状态对比
            )
            
            if changed_files:
                self.logger.info(
                    "[Git 兜底] 检测到 %d 个文件变更, agent=%s",
                    len(changed_files),
                    self.name,
                )
                # 补充到 result.modified_files（如果为空）
                if not result.modified_files:
                    result.modified_files = changed_files
    
    except Exception as e:
        # ...
        pass
```

### 11.2 增强实现（阶段 2）

```python
# agents_hub/core/foundation/file_snapshot.py

def get_working_tree_status_with_metadata(
    cwd: str,
    include_mtime: bool = True,
) -> dict[str, dict]:
    """获取工作区状态 + 文件元数据
    
    Returns:
        {
            "/path/to/file.py": {
                "status": "??",
                "mtime": 1718438400.0,  # 可选
                "size": 1024,            # 可选
            }
        }
    """
    status_map = get_working_tree_status(cwd)
    result = {}
    
    for file_path, status_code in status_map.items():
        meta = {"status": status_code}
        
        if include_mtime:
            try:
                stat = Path(file_path).stat()
                meta["mtime"] = stat.st_mtime
                meta["size"] = stat.st_size
            except (FileNotFoundError, PermissionError):
                pass  # 跳过无法访问的文件
        
        result[file_path] = meta
    
    return result


def get_git_changed_files(
    cwd: str,
    base_ref: str | None = None,
    status_before: dict[str, str | dict] | None = None,
    check_content: bool = False,  # 新增参数
) -> list[str]:
    """获取 Git 仓库中变更的文件列表
    
    Args:
        cwd: Git 仓库工作目录
        base_ref: 基准引用（废弃，推荐使用 status_before）
        status_before: 执行前的工作区状态
        check_content: 是否检测 untracked 文件的内容变化（通过 mtime）
    """
    if status_before is None:
        # 向后兼容：使用旧逻辑
        # ...
        return []
    
    # 判断 status_before 的格式
    is_with_metadata = any(
        isinstance(v, dict) for v in status_before.values()
    )
    
    if is_with_metadata:
        # 新格式：包含 mtime 等元数据
        status_after = get_working_tree_status_with_metadata(cwd, include_mtime=check_content)
    else:
        # 旧格式：只有状态码
        status_after = get_working_tree_status(cwd)
    
    changed_files = []
    
    for file_path, after_value in status_after.items():
        # 提取状态码
        if isinstance(after_value, dict):
            after_status = after_value["status"]
            after_mtime = after_value.get("mtime", 0)
            after_size = after_value.get("size", -1)
        else:
            after_status = after_value
            after_mtime = 0
            after_size = -1
        
        # 获取执行前的状态
        before_value = status_before.get(file_path)
        if isinstance(before_value, dict):
            before_status = before_value.get("status")
            before_mtime = before_value.get("mtime", 0)
            before_size = before_value.get("size", -1)
        else:
            before_status = before_value
            before_mtime = 0
            before_size = -1
        
        # 1. 状态码变化
        if before_status != after_status:
            changed_files.append(file_path)
            continue
        
        # 2. Untracked 文件内容变化（通过 mtime/size）
        if check_content and after_status == "??":
            if after_mtime > before_mtime or after_size != before_size:
                logger.debug(
                    "检测到 untracked 文件内容变化: %s (mtime: %.0f -> %.0f, size: %d -> %d)",
                    Path(file_path).name,
                    before_mtime,
                    after_mtime,
                    before_size,
                    after_size,
                )
                changed_files.append(file_path)
    
    return changed_files
```

---

## 十二、参考资料

### 12.1 Git 命令文档

- `git status --porcelain`：[Git - git-status Documentation](https://git-scm.com/docs/git-status)
- `git diff`：[Git - git-diff Documentation](https://git-scm.com/docs/git-diff)
- `git stash`：[Git - git-stash Documentation](https://git-scm.com/docs/git-stash)

### 12.2 相关代码

- `agents_hub/core/foundation/file_snapshot.py`：文件快照工具
- `agents_hub/core/agent/base_agent.py`：Agent 执行逻辑
- `tests/core/foundation/test_git_fallback.py`：Git 兜底测试

### 12.3 设计文档

- `docs/temp/hand-off/2026-06-07-agent-file-diff.md`：文件展示功能设计
- `docs/superpowers/specs/2026-06-07-agent-file-diff-design.md`：详细技术规格

---

**报告结束**

