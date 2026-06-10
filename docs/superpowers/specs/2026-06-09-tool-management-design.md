# 角色工具管理设计

## 概述

为 Claude Code 角色添加工具管理功能，允许用户为每个角色配置可用/禁用的工具。前端通过弹窗展示分组工具列表，用户点击切换启用/禁用状态。

## 数据结构

### 后端工具目录（硬编码）

```python
# agents_hub/tools/catalog.py

@dataclass
class ToolInfo:
    name: str           # "Read"
    description: str    # "读取文件内容"

@dataclass
class ToolGroup:
    name: str           # "文件操作"
    icon: str           # "📁"
    tools: list[ToolInfo]

ALL_TOOLS: list[ToolGroup] = [...]
```

工具分组：
- CronCreate
  - CronDelete
  - CronList
  - Edit
  - EnterPlanMode
  - EnterWorktree
  - ExitPlanMode
  - ExitWorktree
  - Glob
  - Grep
  - ListMcpResourcesTool
  - NotebookEdit
  - PowerShell
  - Read
  - ReadMcpResourceTool
  - ScheduleWakeup
  - Skill
  - TaskOutput
  - TaskStop
  - TodoWrite
  - WebFetch
  - WebSearch
  - Write
  
  **MCP 服务工具：**
  - mcp__agents-hub__archive_task_list
  - mcp__agents-hub__assign_tasks_to_team
  - mcp__agents-hub__call_agent
  - mcp__agents-hub__check_agent_call
  - mcp__agents-hub__create_agent
  - mcp__agents-hub__create_group_chat
  - mcp__agents-hub__complete_task
  - mcp__agents-hub__health_check
  - mcp__agents-hub__report_progress
  - mcp__mimo-image__understand_image
| 分组 | 图标 | 工具 |
|------|------|------|
| 文件操作 | 📁 | Read, Write, Edit, Glob, NotebookEdit |
| 执行 | ⚡ | Bash, Agent |
| 搜索 | 🔍 | Grep, WebSearch, WebFetch |
| 任务管理 | 📋 | TaskCreate, TaskUpdate, TaskOutput, TaskStop |
| 系统 | ⚙️ | CronCreate, CronDelete, CronList, ScheduleWakeup, EnterPlanMode, ExitPlanMode, EnterWorktree, ExitWorktree, AskUserQuestion, ListMcpResourcesTool, ReadMcpResourceTool |
| MCP (agents-hub) | 🔌 | call_agent, health_check, create_group_chat, report_progress, complete_task, check_agent_call, assign_tasks_to_team, archive_task_list, create_agent, request_permission |

### role.json 存储

```json
{
  "name": "manager",
  "platform": "claude",
  "description": "...",
  "disabled_tools": ["Agent", "Write"]
}
```

- `disabled_tools`: 禁用的工具名列表
- 默认 `[]` 表示全部启用
- 仅 Claude 平台角色适用

### API Schema

```python
# 工具目录
class ToolInfoResponse(BaseModel):
    name: str
    description: str

class ToolGroupResponse(BaseModel):
    name: str
    icon: str
    tools: list[ToolInfoResponse]

class ToolCatalogResponse(BaseModel):
    groups: list[ToolGroupResponse]

# 角色响应 - 新增 disabled_tools
class RoleResponse(BaseModel):
    # ... 现有字段
    disabled_tools: list[str] = []

# 角色更新请求 - 新增 enabled_tools
class RoleUpdateRequest(BaseModel):
    # ... 现有字段
    enabled_tools: list[str] | None = None
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/tools/catalog` | 返回完整工具目录 |
| GET | `/api/v1/roles/{name}` | 返回角色信息（含 disabled_tools） |
| PUT | `/api/v1/roles/{name}` | 更新角色（前端传 enabled_tools，后端算 disabled） |

### GET /api/v1/tools/catalog

响应：
```json
{
  "groups": [
    {
      "name": "文件操作",
      "icon": "📁",
      "tools": [
        {"name": "Read", "description": "读取文件内容"},
        {"name": "Write", "description": "创建或覆盖文件"}
      ]
    }
  ]
}
```

### PUT /api/v1/roles/{name}

请求体新增 `enabled_tools` 字段：
```json
{
  "enabled_tools": ["Read", "Bash", "Glob", "Grep"]
}
```

后端处理逻辑：
```python
# 从 ALL_TOOLS 获取全部工具名
all_tool_names = [t.name for g in ALL_TOOLS for t in g.tools]
# 计算禁用列表
disabled = [name for name in all_tool_names if name not in enabled_tools]
# 存入 role.json
```

## 前端组件

### ToolSelectorModal

位置：`frontend/src/shared/components/ToolSelectorModal/`

复用 SkillSelectorModal 模式：
- 搜索框：按名称和描述过滤
- 分组显示：每组有标题（图标 + 组名）
- 卡片网格：每个工具一张卡片，显示名称 + 描述
- 状态标记：已启用显示"已启用"标记，已禁用显示"已禁用"
- 点击切换：点击卡片切换启用/禁用状态
- 回调返回：关闭时通过回调返回新的 enabled_tools 列表

Props：
```typescript
interface ToolSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (enabledTools: string[]) => void;
  catalog: ToolGroupResponse[];      // 工具目录
  disabledTools: string[];           // 当前禁用的工具
}
```

### EditRoleDialog 修改

- 工具列表区域：在技能列表下方，显示已启用工具的 badge
- `+ 管理工具` 按钮：打开 ToolSelectorModal
- 保存时：将 enabled_tools 随其他字段一起提交

## 数据流

```
1. 用户打开 EditRoleDialog
   → GET /api/v1/roles/{name} → 获取 disabled_tools
   → GET /api/v1/tools/catalog → 获取工具目录
   → 计算：catalog - disabled_tools = 已启用工具
   → 显示已启用工具 badge

2. 用户点击 "+ 管理工具"
   → 打开 ToolSelectorModal
   → 传入 catalog 和 disabled_tools
   → 用户点击切换工具状态
   → 关闭时回调返回新的 enabled_tools

3. 用户点击 "保存"
   → PUT /api/v1/roles/{name}
   → 请求体：{ enabled_tools: [...], description: ..., ... }
   → 后端计算 disabled = total - enabled
   → 存入 role.json
```

## 实现范围

### 后端
- 新建 `agents_hub/tools/catalog.py` - 工具目录定义
- 修改 `agents_hub/roles/models.py` - RoleInfo 新增 disabled_tools
- 修改 `agents_hub/roles/role_manager.py` - 读写 disabled_tools
- 修改 `agents_hub/api/schemas/roles.py` - 新增 Schema 字段
- 修改 `agents_hub/api/routes/roles.py` - 新增 catalog 端点，修改 update 逻辑

### 前端
- 新建 `shared/components/ToolSelectorModal/` - 工具选择弹窗
- 修改 `features/roles/components/EditRoleDialog.tsx` - 添加工具管理区域
- 修改 `shared/types/api-schemas.ts` - 新增类型
- 修改 `shared/types/api-requests.ts` - 新增请求类型
- 修改 `core/api/roleApi.ts` - 新增 catalog API
- 修改 `features/roles/components/RoleCard.tsx` - 显示工具 badge（可选）
