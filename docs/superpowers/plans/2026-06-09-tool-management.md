# 角色工具管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Claude Code 角色添加工具管理功能，允许用户通过弹窗为每个角色配置可用/禁用的工具。

**Architecture:** 后端硬编码工具目录（分组 + 名称 + 描述），通过 API 返回给前端。role.json 存储 `disabled_tools` 列表。前端传 `enabled_tools`，后端做减法得出 `disabled_tools`。前端复用 SkillSelectorModal 模式实现 ToolSelectorModal 弹窗。

**Tech Stack:** Python/FastAPI (后端), React/TypeScript (前端), CSS Modules

---

## File Structure

### 后端新建
- `agents_hub/tools/__init__.py` - 包初始化
- `agents_hub/tools/catalog.py` - 工具目录定义（ALL_TOOLS 硬编码）

### 后端修改
- `agents_hub/roles/models.py` - RoleInfo 新增 disabled_tools 字段
- `agents_hub/roles/role.py` - 新增 update_disabled_tools 方法
- `agents_hub/api/schemas/roles.py` - 新增 ToolCatalogResponse，更新 RoleResponse/RoleUpdateRequest
- `agents_hub/api/services/role_service.py` - 新增 get_tool_catalog，更新 update_role
- `agents_hub/api/routes/roles.py` - 新增 GET /tools/catalog，更新 PATCH /{name}

### 前端新建
- `frontend/src/shared/components/ToolSelectorModal/ToolSelectorModal.tsx`
- `frontend/src/shared/components/ToolSelectorModal/ToolSelectorModal.module.css`
- `frontend/src/shared/components/ToolSelectorModal/index.ts`

### 前端修改
- `frontend/src/shared/types/api-schemas.ts` - 新增 ToolGroupResponse, ToolInfoResponse
- `frontend/src/shared/types/api-requests.ts` - UpdateRoleRequest 新增 enabled_tools
- `frontend/src/shared/types/index.ts` - 导出新类型
- `frontend/src/core/api/roleApi.ts` - 新增 getToolCatalog
- `frontend/src/core/api/index.ts` - 导出新函数
- `frontend/src/shared/components/index.ts` - 导出 ToolSelectorModal
- `frontend/src/features/roles/components/EditRoleDialog.tsx` - 添加工具管理区域

---

### Task 1: 后端 - 创建工具目录

**Files:**
- Create: `agents_hub/tools/__init__.py`
- Create: `agents_hub/tools/catalog.py`

- [ ] **Step 1: 创建 tools 包**

```bash
mkdir -p agents_hub/tools
```

- [ ] **Step 2: 创建 __init__.py**

```python
# agents_hub/tools/__init__.py
```

- [ ] **Step 3: 创建 catalog.py**

```python
"""工具目录 - 硬编码所有可用工具的分组、名称和描述"""

from dataclasses import dataclass


@dataclass
class ToolInfo:
    name: str
    description: str


@dataclass
class ToolGroup:
    name: str
    icon: str
    tools: list[ToolInfo]


ALL_TOOLS: list[ToolGroup] = [
    ToolGroup(
        name="文件操作",
        icon="📁",
        tools=[
            ToolInfo("Read", "读取文件内容"),
            ToolInfo("Write", "创建或覆盖文件"),
            ToolInfo("Edit", "精确替换文件内容"),
            ToolInfo("Glob", "按模式查找文件"),
            ToolInfo("NotebookEdit", "编辑 Jupyter Notebook"),
        ],
    ),
    ToolGroup(
        name="执行",
        icon="⚡",
        tools=[
            ToolInfo("Bash", "执行 shell 命令"),
            ToolInfo("Agent", "启动子代理执行任务"),
        ],
    ),
    ToolGroup(
        name="搜索",
        icon="🔍",
        tools=[
            ToolInfo("Grep", "搜索文件内容"),
            ToolInfo("WebSearch", "网页搜索"),
            ToolInfo("WebFetch", "获取网页内容"),
        ],
    ),
    ToolGroup(
        name="任务管理",
        icon="📋",
        tools=[
            ToolInfo("TaskCreate", "创建任务"),
            ToolInfo("TaskUpdate", "更新任务状态"),
            ToolInfo("TaskOutput", "获取任务输出"),
            ToolInfo("TaskStop", "停止任务"),
        ],
    ),
    ToolGroup(
        name="系统",
        icon="⚙️",
        tools=[
            ToolInfo("CronCreate", "创建定时任务"),
            ToolInfo("CronDelete", "删除定时任务"),
            ToolInfo("CronList", "列出定时任务"),
            ToolInfo("ScheduleWakeup", "调度唤醒"),
            ToolInfo("EnterPlanMode", "进入计划模式"),
            ToolInfo("ExitPlanMode", "退出计划模式"),
            ToolInfo("EnterWorktree", "进入工作树"),
            ToolInfo("ExitWorktree", "退出工作树"),
            ToolInfo("AskUserQuestion", "向用户提问"),
            ToolInfo("ListMcpResourcesTool", "列出 MCP 资源"),
            ToolInfo("ReadMcpResourceTool", "读取 MCP 资源"),
        ],
    ),
    ToolGroup(
        name="MCP (agents-hub)",
        icon="🔌",
        tools=[
            ToolInfo("call_agent", "派活给团队成员"),
            ToolInfo("health_check", "健康检查端点"),
            ToolInfo("create_group_chat", "创建新群聊"),
            ToolInfo("report_progress", "向群聊发送进展信息"),
            ToolInfo("complete_task", "结束 AgentCall"),
            ToolInfo("check_agent_call", "查询 AgentCall 状态"),
            ToolInfo("assign_tasks_to_team", "覆盖式更新任务列表"),
            ToolInfo("archive_task_list", "归档当前 ACTIVE 列表"),
            ToolInfo("create_agent", "创建新的成员角色"),
            ToolInfo("request_permission", "请求权限"),
        ],
    ),
]


def get_all_tool_names() -> list[str]:
    """获取所有工具名称的扁平列表"""
    return [tool.name for group in ALL_TOOLS for tool in group.tools]
```

- [ ] **Step 4: 验证模块可导入**

Run: `python -c "from agents_hub.tools.catalog import ALL_TOOLS, get_all_tool_names; print(f'{len(ALL_TOOLS)} groups, {len(get_all_tool_names())} tools')"`
Expected: `6 groups, 35 tools`

- [ ] **Step 5: Commit**

```bash
git add agents_hub/tools/
git commit -m "feat: add tool catalog with grouped tool definitions"
```

---

### Task 2: 后端 - RoleInfo 新增 disabled_tools

**Files:**
- Modify: `agents_hub/roles/models.py:28-51`
- Modify: `agents_hub/roles/role.py:73-93`
- Modify: `agents_hub/roles/role_manager.py:131-151`

- [ ] **Step 1: 修改 RoleInfo dataclass**

在 `agents_hub/roles/models.py` 的 `RoleInfo` 类中新增 `disabled_tools` 字段：

```python
@dataclass
class RoleInfo:
    name: str
    platform: AgentPlatform
    avatar: str | None
    abilities: list[str]
    type: RoleType | None = RoleType.TEAM_MEMBER
    description: str | None = None
    scope: list[str] | None = None
    disabled_tools: list[str] | None = None  # 新增
```

- [ ] **Step 2: 修改 Role.get_info()**

在 `agents_hub/roles/role.py` 的 `get_info` 方法中读取 `disabled_tools`：

```python
def get_info(self) -> RoleInfo:
    data = self._read_role_json()
    return RoleInfo(
        name=data.get("name", ""),
        platform=AgentPlatform(data.get("platform", "claude")),
        avatar=data.get("avatar"),
        abilities=data.get("abilities", []),
        type=RoleType(data["type"]) if data.get("type") else None,
        description=data.get("description"),
        scope=data.get("scope"),
        disabled_tools=data.get("disabled_tools"),  # 新增
    )
```

- [ ] **Step 3: 新增 Role.update_disabled_tools()**

在 `agents_hub/roles/role.py` 中新增方法：

```python
def update_disabled_tools(self, disabled_tools: list[str]) -> None:
    data = self._read_role_json()
    data["disabled_tools"] = disabled_tools
    self._write_role_json(data)
```

- [ ] **Step 4: 修改 RoleManager.list_roles()**

在 `agents_hub/roles/role_manager.py` 的 `list_roles` 方法中读取 `disabled_tools`：

找到构建 `RoleInfo` 的地方（约 line 131-151），在其中添加 `disabled_tools` 字段的读取：

```python
disabled_tools=data.get("disabled_tools"),
```

- [ ] **Step 5: 运行现有测试确认无破坏**

Run: `python -m pytest tests/ -x -q --tb=short 2>&1 | tail -20`
Expected: 所有现有测试通过

- [ ] **Step 6: Commit**

```bash
git add agents_hub/roles/models.py agents_hub/roles/role.py agents_hub/roles/role_manager.py
git commit -m "feat: add disabled_tools field to RoleInfo and Role"
```

---

### Task 3: 后端 - API Schema 更新

**Files:**
- Modify: `agents_hub/api/schemas/roles.py`

- [ ] **Step 1: 新增工具目录 Schema**

在 `agents_hub/api/schemas/roles.py` 末尾新增：

```python
class ToolInfoResponse(BaseModel):
    name: str
    description: str


class ToolGroupResponse(BaseModel):
    name: str
    icon: str
    tools: list[ToolInfoResponse]


class ToolCatalogResponse(BaseModel):
    groups: list[ToolGroupResponse]
```

- [ ] **Step 2: 更新 RoleResponse**

在 `RoleResponse` 类中新增 `disabled_tools` 字段：

```python
class RoleResponse(BaseModel):
    name: str
    platform: Literal["claude", "codex"]
    avatar: str | None = None
    abilities: list[str] = []
    type: Literal["leader", "team_member", "system"] | None = None
    scope: list[str] | None = None
    description: str | None = None
    skills: list["RoleSkillResponse"] = []
    disabled_tools: list[str] = []  # 新增

    @classmethod
    def from_domain(cls, role_info: RoleInfo, skills: list[SkillInfo]) -> "RoleResponse":
        return cls(
            name=role_info.name,
            platform=role_info.platform.value,
            avatar=role_info.avatar,
            abilities=role_info.abilities,
            type=role_info.type.value if role_info.type else None,
            scope=role_info.scope,
            description=role_info.description,
            skills=[RoleSkillResponse.from_domain(s) for s in skills],
            disabled_tools=role_info.disabled_tools or [],  # 新增
        )
```

- [ ] **Step 3: 更新 RoleUpdateRequest**

在 `RoleUpdateRequest` 类中新增 `enabled_tools` 字段：

```python
class RoleUpdateRequest(BaseModel):
    avatar: str | None = None
    abilities: list[str] | None = None
    description: str | None = None
    enabled_tools: list[str] | None = None  # 新增
```

- [ ] **Step 4: 验证 Schema 可导入**

Run: `python -c "from agents_hub.api.schemas.roles import ToolCatalogResponse, RoleResponse, RoleUpdateRequest; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add agents_hub/api/schemas/roles.py
git commit -m "feat: add tool catalog and enabled_tools to role schemas"
```

---

### Task 4: 后端 - Service 和 Route 层

**Files:**
- Modify: `agents_hub/api/services/role_service.py`
- Modify: `agents_hub/api/routes/roles.py`

- [ ] **Step 1: 新增 RoleService.get_tool_catalog()**

在 `agents_hub/api/services/role_service.py` 中新增：

```python
from agents_hub.tools.catalog import ALL_TOOLS, get_all_tool_names

class RoleService:
    # ... 现有方法 ...

    def get_tool_catalog(self) -> list:
        """返回工具目录"""
        return ALL_TOOLS
```

- [ ] **Step 2: 修改 RoleService.update_role()**

在 `update_role` 方法中处理 `enabled_tools`：

```python
def update_role(self, name: str, request: RoleUpdateRequest) -> tuple[RoleInfo, list[SkillInfo]]:
    role = self.role_manager.get_role(name)

    if request.avatar is not None:
        role.update_avatar(request.avatar)
    if request.abilities is not None:
        role.update_abilities(request.abilities)
    if request.description is not None:
        role.update_description(request.description)
    if request.enabled_tools is not None:
        all_names = get_all_tool_names()
        disabled = [n for n in all_names if n not in request.enabled_tools]
        role.update_disabled_tools(disabled)

    info = role.get_info()
    skills = role.list_skills()
    return info, skills
```

- [ ] **Step 3: 新增路由 GET /tools/catalog**

在 `agents_hub/api/routes/roles.py` 中新增（放在 `/{name}` 路由之前）：

```python
from agents_hub.api.schemas.roles import ToolCatalogResponse, ToolGroupResponse, ToolInfoResponse

@router.get("/tools/catalog", response_model=ToolCatalogResponse)
def get_tool_catalog(
    service: RoleService = Depends(get_role_service),
) -> ToolCatalogResponse:
    catalog = service.get_tool_catalog()
    return ToolCatalogResponse(
        groups=[
            ToolGroupResponse(
                name=g.name,
                icon=g.icon,
                tools=[ToolInfoResponse(name=t.name, description=t.description) for t in g.tools],
            )
            for g in catalog
        ]
    )
```

- [ ] **Step 4: 运行后端测试**

Run: `python -m pytest tests/ -x -q --tb=short 2>&1 | tail -20`
Expected: 所有测试通过

- [ ] **Step 5: 启动后端验证 API**

Run: `python -m uvicorn agents_hub.api.app:app --port 8099 &`
Then: `curl http://localhost:8099/api/v1/roles/tools/catalog | python -m json.tool | head -30`
Expected: 返回工具目录 JSON

Then: `curl http://localhost:8099/api/v1/roles/manager | python -m json.tool | grep disabled_tools`
Expected: `"disabled_tools": []`

- [ ] **Step 6: Commit**

```bash
git add agents_hub/api/services/role_service.py agents_hub/api/routes/roles.py
git commit -m "feat: add tool catalog API endpoint and enabled_tools update logic"
```

---

### Task 5: 前端 - 类型定义

**Files:**
- Modify: `frontend/src/shared/types/api-schemas.ts`
- Modify: `frontend/src/shared/types/api-requests.ts`
- Modify: `frontend/src/shared/types/index.ts`

- [ ] **Step 1: 新增工具目录类型**

在 `frontend/src/shared/types/api-schemas.ts` 末尾新增：

```typescript
export interface ToolInfoResponse {
  name: string;
  description: string;
}

export interface ToolGroupResponse {
  name: string;
  icon: string;
  tools: ToolInfoResponse[];
}

export interface ToolCatalogResponse {
  groups: ToolGroupResponse[];
}
```

- [ ] **Step 2: 更新 RoleApiResponse**

在 `RoleApiResponse` 接口中新增 `disabled_tools`：

```typescript
export interface RoleApiResponse {
  name: string;
  platform: AgentPlatform;
  avatar: string | null;
  abilities: string[];
  type: RoleType | null;
  scope: string[] | null;
  description: string | null;
  skills: RoleSkillApiItem[];
  disabled_tools: string[];  // 新增
}
```

- [ ] **Step 3: 更新 UpdateRoleRequest**

在 `frontend/src/shared/types/api-requests.ts` 的 `UpdateRoleRequest` 中新增：

```typescript
export interface UpdateRoleRequest {
  avatar?: string | null;
  abilities?: string[] | null;
  description?: string | null;
  enabled_tools?: string[] | null;  // 新增
}
```

- [ ] **Step 4: 导出新类型**

在 `frontend/src/shared/types/index.ts` 中添加导出（如果需要）。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/shared/types/
git commit -m "feat: add tool catalog and enabled_tools frontend types"
```

---

### Task 6: 前端 - API 函数

**Files:**
- Modify: `frontend/src/core/api/roleApi.ts`
- Modify: `frontend/src/core/api/index.ts`

- [ ] **Step 1: 新增 getToolCatalog**

在 `frontend/src/core/api/roleApi.ts` 中新增：

```typescript
import type { ToolCatalogResponse } from '@/shared/types/api-schemas';

export async function getToolCatalog(): Promise<ToolCatalogResponse> {
  return mockableRequest(
    () => apiClient.get<ToolCatalogResponse>('/roles/tools/catalog'),
    { groups: [] }
  );
}
```

- [ ] **Step 2: 导出**

在 `frontend/src/core/api/index.ts` 中添加 `getToolCatalog` 的导出。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/core/api/
git commit -m "feat: add getToolCatalog API function"
```

---

### Task 7: 前端 - ToolSelectorModal 组件

**Files:**
- Create: `frontend/src/shared/components/ToolSelectorModal/ToolSelectorModal.tsx`
- Create: `frontend/src/shared/components/ToolSelectorModal/ToolSelectorModal.module.css`
- Create: `frontend/src/shared/components/ToolSelectorModal/index.ts`
- Modify: `frontend/src/shared/components/index.ts`

- [ ] **Step 1: 创建 index.ts**

```typescript
export { ToolSelectorModal } from './ToolSelectorModal';
export type { ToolSelectorModalProps } from './ToolSelectorModal';
```

- [ ] **Step 2: 创建 ToolSelectorModal.tsx**

```tsx
import { useState, useMemo } from 'react';
import { SearchIcon } from '@/shared/components';
import type { ToolGroupResponse } from '@/shared/types/api-schemas';
import styles from './ToolSelectorModal.module.css';

export interface ToolSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (enabledTools: string[]) => void;
  catalog: ToolGroupResponse[];
  disabledTools: string[];
}

export function ToolSelectorModal({
  isOpen,
  onClose,
  onSave,
  catalog,
  disabledTools,
}: ToolSelectorModalProps) {
  const [searchQuery, setSearchQuery] = useState('');
  // 本地维护一份 disabled 集合，关闭时提交
  const [localDisabled, setLocalDisabled] = useState<Set<string>>(
    () => new Set(disabledTools)
  );

  // 每次打开时重置
  const [prevIsOpen, setPrevIsOpen] = useState(false);
  if (isOpen && !prevIsOpen) {
    setPrevIsOpen(true);
    setLocalDisabled(new Set(disabledTools));
  }
  if (!isOpen && prevIsOpen) {
    setPrevIsOpen(false);
  }

  const toggleTool = (name: string) => {
    setLocalDisabled((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  const filteredGroups = useMemo(() => {
    if (!searchQuery) return catalog;
    const q = searchQuery.toLowerCase();
    return catalog
      .map((group) => ({
        ...group,
        tools: group.tools.filter(
          (t) =>
            t.name.toLowerCase().includes(q) ||
            t.description.toLowerCase().includes(q)
        ),
      }))
      .filter((group) => group.tools.length > 0);
  }, [catalog, searchQuery]);

  const handleSave = () => {
    const allNames = catalog.flatMap((g) => g.tools.map((t) => t.name));
    const enabled = allNames.filter((n) => !localDisabled.has(n));
    onSave(enabled);
    onClose();
  };

  const handleClose = () => {
    setSearchQuery('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={handleClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>工具管理</h2>
          <button type="button" className={styles.closeBtn} onClick={handleClose}>
            ×
          </button>
        </div>

        <div className={styles.searchBox}>
          <SearchIcon />
          <input
            type="text"
            className={styles.searchInput}
            placeholder="搜索工具..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className={styles.content}>
          {filteredGroups.map((group) => (
            <div key={group.name} className={styles.group}>
              <div className={styles.groupTitle}>
                <span>{group.icon}</span>
                <span>{group.name}</span>
              </div>
              <div className={styles.toolsGrid}>
                {group.tools.map((tool) => {
                  const isDisabled = localDisabled.has(tool.name);
                  return (
                    <button
                      key={tool.name}
                      type="button"
                      className={`${styles.toolCard} ${isDisabled ? styles.disabled : styles.enabled}`}
                      onClick={() => toggleTool(tool.name)}
                    >
                      <div className={styles.toolName}>{tool.name}</div>
                      <div className={styles.toolDesc}>{tool.description}</div>
                      <span className={isDisabled ? styles.badgeDisabled : styles.badgeEnabled}>
                        {isDisabled ? '已禁用' : '已启用'}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        <div className={styles.footer}>
          <button type="button" className={styles.cancelBtn} onClick={handleClose}>
            取消
          </button>
          <button type="button" className={styles.saveBtn} onClick={handleSave}>
            确定
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 创建 ToolSelectorModal.module.css**

```css
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1100;
}

.dialog {
  width: 600px;
  max-width: 90vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  background: var(--bg-main);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--border-main);
}

.header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.closeBtn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  font-size: 20px;
  cursor: pointer;
  color: var(--text-secondary);
  border-radius: 4px;
}

.closeBtn:hover {
  background: var(--bg-hover);
}

.searchBox {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 16px;
  padding: 8px 12px;
  background: var(--bg-input);
  border-radius: 8px;
}

.searchBox:focus-within {
  outline: 2px solid var(--accent);
}

.searchInput {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 13px;
  color: var(--text-primary);
  outline: none;
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 0 16px 16px;
}

.group {
  margin-bottom: 16px;
}

.groupTitle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--border-main);
}

.toolsGrid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.toolCard {
  flex: 1 1 calc(50% - 4px);
  min-width: 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--bg-bubble);
  border: 1px solid transparent;
  cursor: pointer;
  text-align: left;
  position: relative;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.toolCard:hover {
  border-color: var(--accent);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.toolCard.enabled {
  border-left: 3px solid var(--accent);
}

.toolCard.disabled {
  opacity: 0.6;
}

.toolName {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toolDesc {
  font-size: 11px;
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.badgeEnabled,
.badgeDisabled {
  position: absolute;
  top: 6px;
  right: 6px;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
}

.badgeEnabled {
  background: var(--accent);
  color: white;
}

.badgeDisabled {
  background: var(--bg-shadow);
  color: var(--text-secondary);
}

.footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--border-main);
}

.cancelBtn,
.saveBtn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  border: none;
}

.cancelBtn {
  background: var(--bg-input);
  color: var(--text-primary);
}

.saveBtn {
  background: var(--accent);
  color: white;
}

.saveBtn:hover {
  opacity: 0.9;
}
```

- [ ] **Step 4: 导出到 shared/components/index.ts**

在 `frontend/src/shared/components/index.ts` 中添加：

```typescript
export { ToolSelectorModal } from './ToolSelectorModal';
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/shared/components/ToolSelectorModal/
git add frontend/src/shared/components/index.ts
git commit -m "feat: add ToolSelectorModal component with grouped tool display"
```

---

### Task 8: 前端 - EditRoleDialog 集成

**Files:**
- Modify: `frontend/src/features/roles/components/EditRoleDialog.tsx`

- [ ] **Step 1: 添加 imports 和 state**

在 `EditRoleDialog.tsx` 中新增：

```typescript
import { ToolSelectorModal } from '@/shared/components';
import { getToolCatalog } from '@/core/api';
import type { ToolGroupResponse } from '@/shared/types/api-schemas';
```

新增 state：

```typescript
const [showToolSelector, setShowToolSelector] = useState(false);
const [toolCatalog, setToolCatalog] = useState<ToolGroupResponse[]>([]);
const [enabledTools, setEnabledTools] = useState<string[]>([]);
```

- [ ] **Step 2: 加载工具目录和角色禁用列表**

在 `useEffect` 中加载（当 role 变化时）：

```typescript
useEffect(() => {
  if (!role) return;
  // 加载工具目录
  getToolCatalog().then((data) => setToolCatalog(data.groups));
  // 从 role 计算已启用工具
  const allNames = toolCatalog.flatMap((g) => g.tools.map((t) => t.name));
  const disabled = role.disabled_tools ?? [];
  setEnabledTools(allNames.filter((n) => !disabled.includes(n)));
}, [role]);
```

注意：`toolCatalog` 依赖会导致首次渲染时 allNames 为空。改用另一个 useEffect：

```typescript
// 加载目录
useEffect(() => {
  if (!role) return;
  getToolCatalog().then((data) => setToolCatalog(data.groups));
}, [role]);

// 目录加载后，计算 enabledTools
useEffect(() => {
  if (!role || toolCatalog.length === 0) return;
  const allNames = toolCatalog.flatMap((g) => g.tools.map((t) => t.name));
  const disabled = role.disabled_tools ?? [];
  setEnabledTools(allNames.filter((n) => !disabled.includes(n)));
}, [role, toolCatalog]);
```

- [ ] **Step 3: 修改 handleSubmit**

在 `handleSubmit` 中将 `enabled_tools` 一起提交：

```typescript
const handleSubmit = async () => {
  if (!role) return;
  await updateRole(
    role.name,
    { description, avatar, enabled_tools: enabledTools },
    onSuccess
  );
};
```

- [ ] **Step 4: 新增工具管理 UI 区域**

在技能列表区域下方，`+ 添加技能` 按钮之后，新增：

```tsx
{/* 工具管理 */}
<div className={styles.skillSection}>
  <label className={styles.skillLabel}>工具</label>
  <div className={styles.skillList}>
    {enabledTools.length > 0 ? (
      enabledTools.slice(0, 8).map((name) => (
        <span key={name} className={styles.skillItem}>
          {name}
        </span>
      ))
    ) : (
      <span className={styles.noSkills}>全部禁用</span>
    )}
    {enabledTools.length > 8 && (
      <span className={styles.skillItem}>+{enabledTools.length - 8}</span>
    )}
  </div>
  <button
    type="button"
    className={styles.addSkillBtn}
    onClick={() => setShowToolSelector(true)}
  >
    + 管理工具
  </button>
</div>
```

- [ ] **Step 5: 新增 ToolSelectorModal 实例**

在 SkillSelectorModal 之后新增：

```tsx
<ToolSelectorModal
  isOpen={showToolSelector}
  onClose={() => setShowToolSelector(false)}
  onSave={(enabled) => setEnabledTools(enabled)}
  catalog={toolCatalog}
  disabledTools={
    toolCatalog
      .flatMap((g) => g.tools.map((t) => t.name))
      .filter((n) => !enabledTools.includes(n))
  }
/>
```

- [ ] **Step 6: 验证前端编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: 无类型错误

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/roles/components/EditRoleDialog.tsx
git commit -m "feat: integrate tool management into EditRoleDialog"
```

---

### Task 9: 端到端验证

- [ ] **Step 1: 启动后端**

Run: `python -m uvicorn agents_hub.api.app:app --port 8099`

- [ ] **Step 2: 验证工具目录 API**

Run: `curl http://localhost:8099/api/v1/roles/tools/catalog`
Expected: 返回包含 6 个分组的 JSON

- [ ] **Step 3: 验证角色 API 返回 disabled_tools**

Run: `curl http://localhost:8099/api/v1/roles/manager`
Expected: 响应包含 `"disabled_tools": []`

- [ ] **Step 4: 验证更新 enabled_tools**

Run:
```bash
curl -X PATCH http://localhost:8099/api/v1/roles/manager \
  -H "Content-Type: application/json" \
  -d '{"enabled_tools": ["Read", "Bash", "Grep"]}'
```
Expected: 响应中 `disabled_tools` 包含除 Read/Bash/Grep 之外的所有工具

- [ ] **Step 5: 验证 role.json 已持久化**

Run: `cat local_data/agents/manager/role.json | python -m json.tool | grep disabled_tools`
Expected: `disabled_tools` 列表包含 Agent、Write 等

- [ ] **Step 6: 恢复测试数据**

Run:
```bash
curl -X PATCH http://localhost:8099/api/v1/roles/manager \
  -H "Content-Type: application/json" \
  -d '{"enabled_tools": []}'
```
注意：传空列表会使所有工具被禁用。要恢复全部启用，传入所有工具名列表，或者修改后端逻辑：`enabled_tools` 为 `null` 时不更新，为 `[]` 时视为全部禁用。需要确认这个行为是否符合预期。

- [ ] **Step 7: 启动前端验证 UI**

Run: `cd frontend && npm run dev`
打开浏览器，进入角色管理，点击编辑角色，验证：
- 工具列表区域显示已启用工具 badge
- 点击 "+ 管理工具" 打开弹窗
- 弹窗按分组显示工具，可点击切换启用/禁用
- 保存后角色信息更新

- [ ] **Step 8: Final Commit**

```bash
git add -A
git commit -m "feat: complete tool management feature for role configuration"
```
