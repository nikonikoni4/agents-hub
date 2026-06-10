---
title: Agent 完成任务后的文件展示功能设计
date: 2026-06-07
status: draft
author: Claude & nico
---

# Agent 完成任务后的文件展示功能设计

## 1. 概述

### 1.1 功能目标

当 Agent 完成代码任务后，消息下方显示修改的文件列表，用户可以：
- 查看修改了哪些文件
- 查看每个文件的代码变更统计（新增/删除行数）
- 点击预览文件完整内容
- 点击查看文件的 diff

### 1.2 使用场景

- Agent 完成代码开发任务，修改了多个文件
- 用户需要快速了解 Agent 做了哪些修改
- 用户需要审查代码变更
- 用户需要查看文件的完整内容或 diff 细节

### 1.3 支持的文件类型

- 代码文件：`.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.css`, `.html` 等
- 文档文件：`.md`, `.txt`, `.json`, `.yaml`, `.yml`, `.toml` 等
- 不支持二进制文件（`.pptx`, `.xlsx`, `.pdf`, `.jpg` 等）

## 2. 数据结构设计

### 2.1 GroupChatSession 消息格式

扩展现有消息格式，增加文件相关字段：

```python
{
  "agent_name": "小李",
  "content": "任务完成，已修改 3 个文件",
  "timestamp": "2026-06-07T09:31:22.123456",
  "platform": "claude",
  "cwd": "/path/to/project",              # 新增：Agent 工作目录
  
  # 新增：文件修改列表
  "modified_files": [
    {
      "path": "src/components/FileCard.tsx",     # 文件路径（相对于 cwd）
      "status": "modified",                       # 文件状态：added/modified/deleted
      "additions": 45,                            # 新增行数
      "deletions": 12,                            # 删除行数
      "snapshot_id": "call_abc_0",                # 快照 ID
      "diff_available": true,                     # diff 是否可用
      "diff_error": null                          # 错误信息（如果有）
    },
    {
      "path": "docs/ARCHITECTURE.md",
      "status": "added",
      "additions": 93,
      "deletions": 0,
      "snapshot_id": "call_abc_1",
      "diff_available": true,
      "diff_error": null
    }
  ],
  
  # 新增：Git diff 范围（可选）
  "git_diff_range": "abc123..def456"
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `cwd` | string | 是 | Agent 当前工作目录，用于定位文件真实路径 |
| `modified_files` | array | 否 | 修改的文件列表，如果没有修改文件则为空或不传 |
| `modified_files[].path` | string | 是 | 文件路径（相对于 cwd） |
| `modified_files[].status` | string | 是 | 文件状态：`added`（新增）、`modified`（修改）、`deleted`（删除） |
| `modified_files[].additions` | number | 是 | 新增行数（绿色 +45） |
| `modified_files[].deletions` | number | 是 | 删除行数（红色 -12） |
| `modified_files[].snapshot_id` | string | 是 | 快照 ID，格式：`{call_id}_{index}` |
| `modified_files[].diff_available` | boolean | 是 | diff 是否可用（后端生成） |
| `modified_files[].diff_error` | string\|null | 是 | 错误信息（如果 diff 生成失败） |
| `git_diff_range` | string | 否 | Git commit 范围，如 `abc123..def456` |

**字段职责划分**：

- **Agent 传入**：`modified_files`（只传文件路径列表）、`git_diff_range`（可选）
- **后端生成**：`status`、`additions`、`deletions`、`snapshot_id`、`diff_available`、`diff_error`

**git_diff_range 默认行为**：
- 如果 Agent 传入了 `git_diff_range`，使用该范围：`git diff <range> -- <file>`
- 如果 Agent 未传入，默认对比工作区与 HEAD：`git diff HEAD -- <file>`
- 这样可以捕获 Agent 在工作区的所有修改

### 2.2 文件快照存储

**存储位置**：
```
local_data/teams/<project_path>/<group_chat_id>/
└── file_snapshots/
    ├── call_abc_0.diff      # FileCard.tsx 的 diff
    ├── call_abc_0.content   # FileCard.tsx 的完整内容
    ├── call_abc_1.diff      # ARCHITECTURE.md 的 diff
    └── call_abc_1.content   # ARCHITECTURE.md 的完整内容
```

**文件命名规则**：
- `snapshot_id` = `{call_id}_{file_index}`
- 例如：`call_abc_0` 表示 call_id 为 `call_abc` 的第 0 个文件
- `call_id` 由 `AgentCallManager` 在 `call_agent` 时生成，全局唯一
- Agent 调用 `complete_task` 时传入相同的 `call_id`
- 避免时间戳冲突（多个 Agent 同时完成任务）

**文件内容**：
- `.diff` 文件：`git diff` 的原始输出
- `.content` 文件：文件的完整内容（用于预览）

### 2.3 AgentResult 模型扩展

扩展 `agents_hub/agent_bridge/models.py` 中的 `AgentResult`：

```python
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

## 3. 数据流设计

### 3.1 完整数据流

```
┌─────────────────┐
│ Agent 调用 MCP  │
│ complete_task│
│ (传入文件列表)   │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ MCP Server      │
│ 1. 验证 token   │
│ 2. 获取 cwd     │
│ 3. 运行 git diff│
│ 4. 解析统计     │
│ 5. 保存快照     │
│ 6. 构造元数据   │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ GroupChatContext│
│ add_message()   │
│ 写入 .jsonl     │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ WebSocket 推送  │
│ 刷新通知        │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ 前端接收        │
│ 渲染文件卡片    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ 用户点击预览/Diff│
│ API 请求快照    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ 右侧栏显示      │
│ 内容或 diff     │
└─────────────────┘
```

### 3.2 详细步骤说明

**步骤 1：Agent 调用 MCP tool**

```python
complete_task(
    agent_token="agent_token_xxx",
    call_id="call_abc",
    content="任务完成，已修改 3 个文件",
    modified_files=["src/components/FileCard.tsx", "docs/ARCHITECTURE.md"],
    git_diff_range="abc123..def456"  # 可选
)
```

**步骤 2：MCP Server 处理**（`agents_hub/mcp/server.py`）

```python
# 伪代码
from agents_hub.core.foundation.file_snapshot import create_file_snapshot

# 1. 获取 Agent 信息
agent = _find_agent(group_chat, agent_name)
cwd = agent.cwd

# 2. 准备快照目录
snapshot_dir = Path(f"local_data/teams/{project_path}/{group_chat_id}/file_snapshots")
snapshot_dir.mkdir(parents=True, exist_ok=True)

# 3. 为每个文件创建快照
file_metadata_list = []
for index, file_path in enumerate(modified_files):
    metadata = create_file_snapshot(
        snapshot_dir=snapshot_dir,
        call_id=call_id,
        file_path=file_path,
        index=index,
        cwd=cwd,
        git_diff_range=git_diff_range
    )
    file_metadata_list.append(metadata)

# 4. 构造 AgentResult
result = AgentResult(
    text=content,
    session_id=agent.session_id,
    timestamp=datetime.now().isoformat(),
    agent_name=agent_name,
    platform=agent.platform,
    role_type=agent.role_type,
    cwd=cwd,
    modified_files=file_metadata_list,
    git_diff_range=git_diff_range
)

# 5. 保存到上下文
await group_chat.group_chat_context.add_message(result)

# 6. 广播刷新
await broadcast_group_chat_refresh(group_chat_id)
```

**步骤 3：文件快照创建**（`agents_hub/core/foundation/file_snapshot.py`）

```python
def create_file_snapshot(
    snapshot_dir: Path,
    call_id: str,
    file_path: str,
    index: int,
    cwd: str,
    git_diff_range: str | None = None
) -> dict:
    snapshot_id = f"{call_id}_{index}"
    
    # 1. 运行 git diff
    if git_diff_range:
        cmd = f"git diff {git_diff_range} -- {file_path}"
    else:
        cmd = f"git diff HEAD -- {file_path}"
    
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    diff_text = result.stdout if result.returncode == 0 else None
    diff_error = result.stderr if result.returncode != 0 else None
    
    # 2. 解析 diff
    if diff_text:
        additions, deletions, status = _parse_diff(diff_text)
        diff_available = True
    else:
        additions, deletions, status = 0, 0, "modified"
        diff_available = False
    
    # 3. 读取文件内容
    full_path = Path(cwd) / file_path
    content = full_path.read_text(encoding="utf-8") if full_path.exists() else ""
    
    # 4. 保存快照
    (snapshot_dir / f"{snapshot_id}.diff").write_text(diff_text or "", encoding="utf-8")
    (snapshot_dir / f"{snapshot_id}.content").write_text(content, encoding="utf-8")
    
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
```

**步骤 4：前端接收和展示**

```typescript
// 1. WebSocket 收到刷新通知
// 2. 调用 API 获取最新消息
const messages = await getGroupChatMessages(groupChatId);

// 3. 渲染消息，包含文件卡片
{message.modified_files && message.modified_files.length > 0 && (
  <FileChangesCard
    modifiedFiles={message.modified_files}
    groupChatId={groupChatId}
    onPreview={(snapshotId, filePath) => openPreview(snapshotId, filePath)}
    onDiff={(snapshotId, filePath) => openDiff(snapshotId, filePath)}
  />
)}
```

**步骤 5：用户交互和 API 调用**

```typescript
// 用户点击「预览」按钮
async function openPreview(snapshotId: string, filePath: string) {
  const content = await getFileSnapshotContent(groupChatId, snapshotId);
  // 在右侧栏显示代码（使用语法高亮）
  showInRightSidebar({ type: 'preview', content, filePath });
}

// 用户点击「Diff」按钮
async function openDiff(snapshotId: string, filePath: string) {
  const diff = await getFileSnapshotDiff(groupChatId, snapshotId);
  // 在右侧栏显示 diff（使用 diff 渲染库）
  showInRightSidebar({ type: 'diff', diff, filePath });
}
```

## 4. 后端实现设计

### 4.1 MCP Tool 扩展

**文件**：`agents_hub/mcp/server.py`

**修改**：扩展 `complete_task` 函数签名

```python
async def complete_task(
    agent_token: str,
    call_id: str,
    content: str,
    success: bool = True,
    modified_files: list[str] | None = None,      # 新增：文件路径列表
    git_diff_range: str | None = None,            # 新增：Git diff 范围
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
    # 实现略（参考 3.2 步骤 2）
```

### 4.2 文件快照工具模块

**文件**：`agents_hub/core/foundation/file_snapshot.py`（新增）

**职责**：
- 为单个文件创建快照（运行 git diff、解析、保存）
- 读取快照内容
- 读取快照 diff

**核心函数**：

```python
def create_file_snapshot(
    snapshot_dir: Path,
    call_id: str,
    file_path: str,
    index: int,
    cwd: str,
    git_diff_range: str | None = None
) -> dict:
    """创建文件快照，返回元数据"""
    pass

def get_snapshot_content(snapshot_dir: Path, snapshot_id: str) -> str:
    """读取快照的文件内容"""
    pass

def get_snapshot_diff(snapshot_dir: Path, snapshot_id: str) -> str:
    """读取快照的 diff"""
    pass

# 私有辅助函数
def _run_git_diff(file_path: str, cwd: str, git_diff_range: str | None) -> tuple[str, str | None]:
    """运行 git diff 命令"""
    pass

def _parse_diff(diff_text: str) -> tuple[int, int, str]:
    """解析 diff，提取 additions/deletions/status"""
    pass

def _read_file_content(file_path: str, cwd: str) -> str:
    """读取文件完整内容"""
    pass

def _save_snapshot(snapshot_dir: Path, snapshot_id: str, diff_text: str, content: str) -> None:
    """保存快照文件"""
    pass
```

### 4.3 API 路由扩展

**文件**：`agents_hub/api/routes/group_chat.py`

**新增端点**：

```python
@router.get("/{group_chat_id}/files/{snapshot_id}/content")
async def get_file_snapshot_content(
    group_chat_id: str,
    snapshot_id: str
) -> dict:
    """
    获取文件快照的完整内容
    
    Returns:
        {
            "content": "文件完整内容...",
            "file_path": "src/a.py"
        }
    """
    # 1. 查找 group_chat
    group_chat = await group_chat_manager.load_group_chat(group_chat_id)
    
    # 2. 构造快照目录
    snapshot_dir = Path(f"local_data/teams/{group_chat.project_path}/{group_chat_id}/file_snapshots")
    
    # 3. 读取内容
    from agents_hub.core.foundation.file_snapshot import get_snapshot_content
    content = get_snapshot_content(snapshot_dir, snapshot_id)
    
    return {"content": content}


@router.get("/{group_chat_id}/files/{snapshot_id}/diff")
async def get_file_snapshot_diff(
    group_chat_id: str,
    snapshot_id: str
) -> dict:
    """
    获取文件快照的 diff
    
    Returns:
        {
            "diff": "git diff 输出...",
            "file_path": "src/a.py"
        }
    """
    # 实现类似 get_file_snapshot_content
    pass
```

### 4.4 AgentResult 模型扩展

**文件**：`agents_hub/agent_bridge/models.py`

**修改**：增加新字段

```python
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

### 4.5 GroupChatContext 扩展

**文件**：`agents_hub/core/context/group_chat_context.py`

**修改**：`add_message()` 方法需要处理新增字段

确保 `AgentResult` 的 `cwd`、`modified_files`、`git_diff_range` 字段被正确写入 `.jsonl` 文件。

## 5. 前端实现设计

### 5.1 类型定义扩展

**文件**：`frontend/src/shared/types/api-schemas.ts`

```typescript
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

### 5.2 文件卡片组件

**文件**：`frontend/src/shared/components/FileChangesCard/FileChangesCard.tsx`（新增）

**组件结构**：

```typescript
interface FileChangesCardProps {
  modifiedFiles: ModifiedFileInfo[];
  groupChatId: string;
  onPreview: (snapshotId: string, filePath: string) => void;
  onDiff: (snapshotId: string, filePath: string) => void;
}

export function FileChangesCard({ 
  modifiedFiles, 
  groupChatId, 
  onPreview, 
  onDiff 
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
          <FileEditIcon />
          <span>已编辑 {modifiedFiles.length} 个文件</span>
          <span className={styles.stats}>
            <span className={styles.additions}>+{totalAdditions}</span>
            <span className={styles.deletions}>-{totalDeletions}</span>
          </span>
        </div>
        <button className={styles.toggleBtn}>
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

**子组件：FileItem**

```typescript
interface FileItemProps {
  file: ModifiedFileInfo;
  onPreview: () => void;
  onDiff: () => void;
}

function FileItem({ file, onPreview, onDiff }: FileItemProps) {
  const icon = getFileIcon(file.path, file.status);
  
  return (
    <div className={styles.fileItem}>
      <div className={styles.fileInfo}>
        {icon}
        <span className={styles.filePath}>{file.path}</span>
        <span className={styles.stats}>
          <span className={styles.additions}>+{file.additions}</span>
          <span className={styles.deletions}>-{file.deletions}</span>
        </span>
      </div>
      <div className={styles.actions}>
        <button className={styles.actionBtn} onClick={onPreview}>
          预览
        </button>
        {file.diff_available && (
          <button className={styles.actionBtn} onClick={onDiff}>
            Diff
          </button>
        )}
      </div>
    </div>
  );
}
```

**组件样式**（参考）：
- 默认折叠状态
- 头部显示汇总信息：文件数量、总行数变化
- 展开后显示文件列表
- 每个文件一行，显示路径、行数变化、操作按钮
- 绿色表示新增（+45），红色表示删除（-12）

### 5.3 API 调用函数

**文件**：`frontend/src/core/api/groupChatApi.ts`

```typescript
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
  const data = await response.json();
  return data.diff;
}
```

### 5.4 右侧栏扩展

**文件**：`frontend/src/layouts/RightSidebar/RightSidebar.tsx`

**修改**：增加文件预览和 Diff 视图

**预览面板**：
- 使用代码高亮组件（如 `react-syntax-highlighter` 或轻量级方案）
- 显示文件路径
- 显示文件内容（只读）

**Diff 面板**：
- 使用 diff 渲染库（需要选型，如 `react-diff-view`、`diff2html` 或自实现）
- 支持 unified 或 side-by-side 模式
- 高亮新增/删除行

### 5.5 集成到 ChatArea

**文件**：`frontend/src/layouts/ChatArea/ChatArea.tsx`

**修改**：在消息气泡**下方**渲染文件卡片（与消息内容分离，便于折叠）

```typescript
{message.modified_files && message.modified_files.length > 0 && (
  <FileChangesCard
    modifiedFiles={message.modified_files}
    groupChatId={groupChatId}
    onPreview={(snapshotId, filePath) => {
      // 打开右侧栏，显示预览
      setRightSidebarContent({
        type: 'preview',
        snapshotId,
        filePath
      });
    }}
    onDiff={(snapshotId, filePath) => {
      // 打开右侧栏，显示 diff
      setRightSidebarContent({
        type: 'diff',
        snapshotId,
        filePath
      });
    }}
  />
)}
```

## 6. 边界情况处理

### 6.1 新文件（untracked）

**场景**：Agent 创建了新文件，文件未被 git 跟踪

**处理**：
- `git diff` 可能返回空或失败
- 后端检测到文件是新增的（通过 `git status`）
- `status` 设置为 `added`
- `diff_available` 设置为 `false`（或生成 "全新" 的 diff）
- 保存文件内容，用户可以预览

### 6.2 删除的文件

**场景**：Agent 删除了文件

**处理**：
- `git diff` 显示删除操作
- `status` 设置为 `deleted`
- `additions` = 0，`deletions` = 原文件行数
- 保存删除前的文件内容（从 git 历史中读取）
- 用户可以查看删除前的内容和 diff

### 6.3 非 Git 仓库

**场景**：Agent 工作目录不是 git 仓库

**处理**：
- `git diff` 命令失败
- `diff_available` 设置为 `false`
- `diff_error` 设置为 `"not_a_git_repo"`
- 仍然保存文件内容，用户可以预览
- 前端只显示「预览」按钮，隐藏「Diff」按钮

### 6.4 Git worktree 路径处理

**场景**：Agent 在 git worktree 中工作

**处理**：
- 检测是否在 worktree 中（`git rev-parse --git-dir`）
- 将文件路径转换为相对于 git root 的路径
- 在 git root 目录执行 `git diff` 命令
- 确保路径一致性

### 6.5 大文件处理

**场景**：文件或 diff 非常大（如 bundle.js、SQL dump）

**处理**：
- 设置大小上限：
  - 单个文件内容：1MB
  - 单个 diff：5000 行
- 超过上限时：
  - 截断内容，保存前 N 行
  - 在元数据中标记 `truncated: true`
  - 前端显示提示："文件过大，已截断显示"

### 6.6 并发冲突

**场景**：多个 Agent 同时完成任务，`snapshot_id` 可能冲突

**处理**：
- `snapshot_id` 包含 `call_id`，保证唯一性
- `call_id` 由系统生成，全局唯一
- 不会发生冲突

### 6.7 敏感文件过滤

**场景**：Agent 修改了敏感文件（`.env`、`credentials.json` 等）

**处理**：
- 后端检测敏感文件模式：
  - `.env`, `*.key`, `*.pem`, `credentials.*`, `secrets.*`
- 敏感文件：
  - 不保存快照内容
  - 在元数据中标记 `is_sensitive: true`
  - 前端显示提示："敏感文件，已隐藏内容"

### 6.8 文件编码处理

**场景**：文件使用非 UTF-8 编码（如 GBK、Latin-1）

**处理**：
- 只支持 UTF-8 编码
- 遇到编码错误时：
  - 跳过该文件的内容保存
  - `diff_available` 设置为 `false`
  - `diff_error` 设置为 `"encoding_error"`
  - 前端显示提示："文件编码不支持，无法显示"
- 不引入自动编码检测（避免额外依赖和复杂度）

## 7. 技术风险和缓解措施

### 7.1 性能风险

**风险**：大量文件或大文件可能导致性能问题

**缓解措施**：
- 文件数量限制：单次最多 50 个文件
- 文件大小限制：单个文件最大 1MB
- 前端懒加载：只有用户点击时才请求内容
- 后端缓存：快照持久化到磁盘，避免重复计算

### 7.2 存储风险

**风险**：快照文件占用大量磁盘空间

**缓解措施**：
- 定期清理：保留最近 30 天的快照
- 压缩存储：对大文件使用 gzip 压缩
- 用户配置：允许用户设置保留策略

### 7.3 可靠性风险

**风险**：`git diff` 命令可能失败

**缓解措施**：
- 完整的错误处理：捕获所有异常
- 降级策略：失败时仍保存文件内容
- 错误记录：将错误信息存储在元数据中
- 前端容错：diff 不可用时显示预览

### 7.4 安全风险

**风险**：快照可能包含敏感信息

**缓解措施**：
- 敏感文件过滤（见 6.7）
- 访问控制：只有群聊成员可以访问快照
- 路径验证：防止路径穿越攻击
- 内容审查：记录敏感内容访问日志

## 8. 实现计划

### 8.1 阶段 1：后端基础设施（优先级：P0）

- [ ] 扩展 `AgentResult` 模型
- [ ] 实现 `file_snapshot.py` 工具模块
- [ ] 扩展 `complete_task` MCP tool
- [ ] 修改 `GroupChatContext.add_message()` 处理新字段
- [ ] 新增 API 端点：`/files/{snapshot_id}/content` 和 `/diff`
- [ ] 单元测试：文件快照创建、读取

### 8.2 阶段 2：前端基础组件（优先级：P0）

- [ ] 扩展类型定义：`ModifiedFileInfo`、`MessageApiItem`
- [ ] 实现 `FileChangesCard` 组件（折叠/展开）
- [ ] 实现 `FileItem` 子组件
- [ ] 新增 API 调用函数：`getFileSnapshotContent`、`getFileSnapshotDiff`
- [ ] 集成到 `ChatArea`：渲染文件卡片

### 8.3 阶段 3：右侧栏预览和 Diff（优先级：P1）

- [ ] 选型和集成 diff 渲染库
- [ ] 实现预览面板（代码高亮）
- [ ] 实现 Diff 面板（unified/side-by-side）
- [ ] 右侧栏状态管理（切换内容）
- [ ] 样式优化

### 8.4 阶段 4：边界情况和优化（优先级：P2）

- [ ] 处理新文件、删除文件、非 git 仓库
- [ ] 大文件截断和提示
- [ ] 敏感文件过滤
- [ ] 性能优化：懒加载、缓存
- [ ] 错误提示和用户反馈

### 8.5 阶段 5：测试和文档（优先级：P2）

- [ ] 集成测试：完整流程测试
- [ ] 边界情况测试
- [ ] 性能测试
- [ ] 用户文档：如何使用文件预览功能

## 9. 技术选型

### 9.1 前端 Diff 渲染库

**候选方案**：

| 库名 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| `react-diff-view` | 功能完整，支持 unified/side-by-side，样式可定制 | 体积稍大（~50KB） | ⭐⭐⭐⭐⭐ |
| `diff2html` | 成熟稳定，样式美观 | 非 React 原生，需要适配 | ⭐⭐⭐⭐ |
| 自实现 | 轻量，完全可控 | 开发成本高，功能有限 | ⭐⭐⭐ |

**推荐**：`react-diff-view`（如果未安装需要先安装）

### 9.2 代码高亮库

**候选方案**：

| 库名 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| `react-syntax-highlighter` | 功能完整，支持多种语言和主题 | 体积较大 | ⭐⭐⭐⭐⭐ |
| `prism-react-renderer` | 轻量，基于 Prism | 主题选择少 | ⭐⭐⭐⭐ |
| `highlight.js` | 成熟稳定 | 非 React 原生 | ⭐⭐⭐ |

**推荐**：根据项目现有依赖选择

## 10. 未来扩展

### 10.1 行内编辑

- 用户可以在预览面板中直接编辑文件
- 编辑后发送给 Agent 或直接保存

### 10.2 文件对比

- 对比同一文件在不同消息中的版本
- 查看文件的演变历史

### 10.3 批量操作

- 批量下载所有修改的文件
- 批量应用/还原修改

### 10.4 代码审查

- 在 diff 上添加评论
- 标记需要修改的地方
- 与 Agent 协作修改

## 11. 附录

### 11.1 相关文件清单

**后端**：
- `agents_hub/mcp/server.py` - MCP tool 扩展
- `agents_hub/core/foundation/file_snapshot.py` - 文件快照工具（新增）
- `agents_hub/core/context/group_chat_context.py` - add_message 扩展
- `agents_hub/agent_bridge/models.py` - AgentResult 扩展
- `agents_hub/api/routes/group_chat.py` - API 端点扩展
- `agents_hub/api/schemas/group_chats.py` - Schema 扩展（可选）

**前端**：
- `frontend/src/shared/types/api-schemas.ts` - 类型定义扩展
- `frontend/src/shared/components/FileChangesCard/` - 文件卡片组件（新增）
- `frontend/src/core/api/groupChatApi.ts` - API 函数扩展
- `frontend/src/layouts/ChatArea/ChatArea.tsx` - 集成文件卡片
- `frontend/src/layouts/RightSidebar/RightSidebar.tsx` - 预览和 Diff 面板

### 11.2 数据流图

```
Agent → complete_task(modified_files) 
  → MCP Server (运行 git diff, 解析, 保存快照)
  → GroupChatContext.add_message(AgentResult)
  → .jsonl 文件 (持久化)
  → WebSocket 广播
  → 前端接收 (渲染 FileChangesCard)
  → 用户点击预览/Diff
  → API 请求快照
  → 右侧栏显示内容
```

### 11.3 快照文件示例

**文件结构**：
```
local_data/teams/my-project/chat_123/
├── chat_123.jsonl
├── agent_member.json
└── file_snapshots/
    ├── call_abc_0.diff
    ├── call_abc_0.content
    ├── call_abc_1.diff
    └── call_abc_1.content
```

**`.diff` 文件示例**：
```diff
diff --git a/src/a.py b/src/a.py
index 1234567..abcdefg 100644
--- a/src/a.py
+++ b/src/a.py
@@ -10,7 +10,7 @@ def hello():
-    print("old")
+    print("new")
```

**`.content` 文件示例**：
```python
def hello():
    print("new")
```

---

## 变更日志

- 2026-06-07：初始版本

