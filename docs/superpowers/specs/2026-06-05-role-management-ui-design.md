---
version: 1.0
created_at: 2026-06-05
updated_at: 2026-06-05
last_updated: 初始设计方案
abstract: 角色管理模块 UI/UX 设计规格，定义页面布局、数据聚合策略、交互流程和视觉规范
id: spec-role-management-ui
title: 角色管理模块 UI 设计规格
status: draft
module: frontend/features/roles
related_spec: docs/specs/2026-05-24-agents-role.md
code_scope:
  - frontend/src/features/roles/
  - frontend/src/shared/adapters/roleAdapter.ts
  - frontend/src/shared/adapters/teamAdapter.ts
contract_refs:
  - frontend/src/shared/types/api-schemas.ts
  - docs/DESIGN.md
---

# 角色管理模块 UI 设计规格

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 初始设计方案，定义布局、数据聚合、交互流程和视觉规范 |

---

## Overview

角色管理模块是 agents-hub 前端的独立 feature，负责展示和管理角色与团队。模块入口为左侧栏的"角色配置"按钮，点击后整个右侧区域（聊天区 + 右侧边栏）被角色管理面板替换。

模块定位：
- **负责**：角色展示（网格卡片）、团队成员管理、创建角色、添加/移除团队成员
- **不负责**：角色删除、角色编辑、Skill 管理（等技能广场功能完成后再实现）

核心设计原则：
- **数据聚合在 Adapter 层**：通过 `roleAdapter` 和 `teamAdapter` 聚合角色和技能数据
- **模块隔离**：遵循 `features/` 架构规范，不直接依赖其他 feature
- **视觉一致性**：遵循 DESIGN.md v2.0 设计系统

---

## Scope

### 范围内

- 角色管理页面布局（两个 Tab：团队管理、角色管理）
- 角色卡片网格展示（包含头像、名称、类型、描述、Skills）
- 团队列表和成员详情展示
- 创建角色弹窗（名称、平台、头像、类型、描述）
- 添加成员到团队（现有角色/新建角色）
- 从团队移除成员
- 数据聚合逻辑（Adapter 层）

### 范围外

- 角色删除功能（暂不实现）
- 角色编辑功能（暂不实现）
- Skill 添加/移除（等技能广场功能完成后再实现）
- 权限管理
- 角色搜索/筛选

---

## Architecture Design

### 目录结构

```
features/roles/
├── components/
│   ├── RoleManagementPanel.tsx       # 主面板（包含两个 tab）
│   ├── RoleCard.tsx                  # 角色卡片（网格布局）
│   ├── RoleMemberRow.tsx             # 角色成员行（团队详情）
│   ├── TeamList.tsx                  # 团队列表
│   ├── TeamMemberPanel.tsx           # 团队成员面板
│   ├── CreateRoleDialog.tsx          # 创建角色弹窗
│   ├── AddMemberDialog.tsx           # 添加成员弹窗（选择现有/新建）
│   └── AvatarSelector.tsx            # 头像选择器
├── hooks/
│   ├── useRoles.ts                   # 角色列表管理
│   ├── useTeams.ts                   # 团队列表管理
│   ├── useCreateRole.ts              # 创建角色逻辑
│   └── useTeamMembers.ts             # 团队成员管理
├── store/
│   ├── rolesStore.ts                 # 角色状态管理
│   └── teamsStore.ts                 # 团队状态管理
└── types.ts                          # 模块专属类型
```

### 数据聚合策略

采用 **Adapter 层聚合**（方案 A）：

```typescript
// shared/adapters/roleAdapter.ts
export interface RoleWithSkills {
  name: string;
  platform: AgentPlatform;
  avatar: string | null;
  type: RoleType | null;
  description: string | null;
  abilities: string[];
  skills: RoleSkillApiItem[];  // 聚合的技能列表
}

export async function fetchRoleWithSkills(roleName: string): Promise<RoleWithSkills>
export async function fetchAllRolesWithSkills(): Promise<RoleWithSkills[]>

// shared/adapters/teamAdapter.ts
export interface TeamWithMembers {
  name: string;
  members: RoleWithSkills[];  // 聚合完整的角色对象
}

export async function fetchTeamWithMembers(teamName: string): Promise<TeamWithMembers>
export async function fetchAllTeamsWithMembers(): Promise<TeamWithMembers[]>
```

**优势**：
- 符合现有架构规范（Adapters 层负责数据聚合）
- 组件无需关心数据来源，直接消费聚合后的数据
- 两个面板可以复用相同的聚合逻辑

---

## UI Layout Design

### 整体布局

点击左侧栏的"角色配置"后，整个右侧区域（聊天区 + 右侧边栏）被角色管理面板替换：

```
┌─────────────────────────────────────────────────────────┐
│ RoleManagementPanel                                      │
├─────────────────────────────────────────────────────────┤
│ Header: 角色管理 | [团队管理 / 角色管理] Tab | 主题切换  │
├─────────────────────────────────────────────────────────┤
│ Content (flex: 1, overflow: auto/hidden):                │
│   - 团队管理 Tab: TeamManagementView                     │
│   - 角色管理 Tab: RoleGridView                          │
└─────────────────────────────────────────────────────────┘
```

### 团队管理 Tab

左侧团队列表（260px）+ 右侧成员详情（flex: 1）：

```
┌──────────────┬──────────────────────────────────────────┐
│ 团队列表      │ 团队成员详情                              │
│              │                                          │
│ ┌──────────┐ │ [团队头部：图标 + 名称 + 描述 + 人数]     │
│ │ Frontend │ │                                          │
│ │ Team ✓   │ │ [添加成员] 按钮                          │
│ └──────────┘ │                                          │
│ ┌──────────┐ │ [成员列表]                               │
│ │ Backend  │ │ 👤 Designer       [team_member] [x]     │
│ │ Team     │ │    前端设计师...                         │
│ └──────────┘ │ 👤 Developer      [team_member] [x]     │
│ ┌──────────┐ │    开发工程师...                         │
│ │ Product  │ │                                          │
│ │ Team     │ │                                          │
│ └──────────┘ │                                          │
└──────────────┴──────────────────────────────────────────┘
```

### 角色管理 Tab

网格布局展示所有角色：

```
┌─────────────────────────────────────────────────────────┐
│ [添加角色] 按钮（右上角）                                │
├─────────────────────────────────────────────────────────┤
│ Grid Layout (auto-fill, minmax(280px, 1fr), gap: 16px)  │
│                                                          │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│ │ 👤 Designer │  │ 👤 Developer│  │ 👤 Tester   │      │
│ │ [claude]    │  │ [codex]     │  │ [claude]    │      │
│ │ team_member │  │ team_member │  │ team_member │      │
│ │             │  │             │  │             │      │
│ │ 前端设计师...│  │ 开发工程师...│  │ 测试工程师...│      │
│ │             │  │             │  │             │      │
│ │ Skills:     │  │ Skills:     │  │ Skills:     │      │
│ │ [待开发]    │  │ [待开发]    │  │ [待开发]    │      │
│ └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────────────────────────────────────────┘
```

---

## Interaction Flow

### 创建角色流程

```
用户点击"添加角色"
  ↓
打开 CreateRoleDialog
  ↓
填写表单：
  - 角色名称（必填，Input）
  - 平台选择（必填，Select: Claude / Codex）
  - 头像选择（可选，AvatarSelector 网格）
  - 角色类型（固定显示 team_member，不可编辑）
  - 角色描述（可选，Textarea）
  - 技能列表（占位：显示"技能配置功能开发中..."）
  ↓
提交表单 → 调用 createRole API
  ↓
刷新角色列表 → 关闭弹窗
```

### 添加团队成员流程

```
用户点击团队详情的"添加成员"
  ↓
打开 AddMemberDialog
  ↓
选择模式：
  A. 添加现有角色
     ↓
     显示角色列表（多选）
     ↓
     提交 → 调用 updateTeam API（追加到 members）
  
  B. 创建新角色
     ↓
     打开 CreateRoleDialog（嵌套）
     ↓
     创建完成后自动添加到团队
     ↓
     调用 updateTeam API
  ↓
刷新团队成员列表 → 关闭弹窗
```

### 移除团队成员流程

```
用户点击成员行的 [x] 按钮
  ↓
确认提示（可选："确定将 XXX 从团队中移除？"）
  ↓
调用 updateTeam API（从 members 列表中移除该角色名称）
  ↓
刷新团队成员列表
```

---

## Visual Design

### 色彩应用

遵循 DESIGN.md v2.0 色彩系统：

| 元素 | 浅色主题 | 深色主题 |
|------|---------|---------|
| 主面板背景 | `var(--bg-main)` | `var(--bg-main)` |
| Header 背景 | 透明或渐变 | 透明或渐变 |
| 团队列表背景 | `var(--bg-sidebar)` | `var(--bg-sidebar)` |
| 角色卡片背景 | `var(--bg-main)` + border | `var(--bg-main)` + border |
| 卡片悬停阴影 | `var(--shadow-card-hover)` | `var(--shadow-card-hover)` |
| 强调色 | `var(--accent-color)` | `var(--accent-color)` |

### 圆角规范

| 元素 | 圆角值 |
|------|--------|
| 角色卡片 | 10px |
| 成员行悬停 | 6px |
| 团队列表项 | 6px |
| 弹窗 | 12px |
| 按钮 | 6px |
| 头像 | 10px（方形图标）或 50%（圆形） |

### 间距规范

| 元素 | 间距值 |
|------|--------|
| Grid gap | 16px |
| 卡片 padding | 20px |
| 列表项 padding | 10px |
| Header 高度 | 56px |
| 团队列表宽度 | 260px |

---

## Component Specifications

### RoleCard（角色卡片）

**Props**:
```typescript
interface RoleCardProps {
  role: RoleWithSkills;
  onClick?: () => void;
}
```

**视觉特点**：
- 悬停时有阴影（`var(--shadow-card-hover)`）和轻微上移（`translateY(-2px)`）
- 头像：圆角方块 + SVG 图标或首字母
- 平台 Badge：显示 Claude / Codex
- 类型 Badge：显示 leader / team_member
- Skills 列表：以 Badge 形式展示（MVP 阶段显示占位文本）

**布局**：
```
┌─────────────────────┐
│ [头像]  [名称]      │
│        [平台] [类型]│
│                     │
│ [描述文本...]       │
│                     │
│ Skills:             │
│ [待开发]            │
└─────────────────────┘
```

### CreateRoleDialog（创建角色弹窗）

**表单字段**：
1. 角色名称：`<Input required />`
2. 平台选择：`<Select options={['claude', 'codex']} required />`
3. 头像选择：`<AvatarSelector avatars={avatarList} />`
4. 角色类型：`<Badge>team_member</Badge>`（固定显示，不可编辑）
5. 角色描述：`<Textarea optional />`
6. 技能列表：占位文本"技能配置功能开发中..."

**按钮**：
- 取消（次要按钮，左侧）
- 创建（主要按钮，强调色，右侧）

**尺寸**：宽度 600px，高度根据内容自适应

### AvatarSelector（头像选择器）

**Props**:
```typescript
interface AvatarSelectorProps {
  selectedAvatar: string | null;
  onSelect: (avatar: string) => void;
  avatars: string[];
}
```

**布局**：
- 网格布局：`grid-template-columns: repeat(5, 1fr)`
- 每个头像：64x64px，圆角 8px
- 选中状态：蓝色边框（`var(--accent-color)`，2px）
- 悬停状态：背景色变化

---

## Data Flow

### rolesStore（Zustand）

```typescript
interface RolesState {
  roles: RoleWithSkills[];
  loading: boolean;
  error: string | null;
  
  // Actions
  fetchRoles: () => Promise<void>;
  createRole: (data: CreateRoleRequest) => Promise<void>;
  refreshRoles: () => Promise<void>;
}
```

### teamsStore（Zustand）

```typescript
interface TeamsState {
  teams: TeamWithMembers[];
  selectedTeam: string | null;
  loading: boolean;
  error: string | null;
  
  // Actions
  fetchTeams: () => Promise<void>;
  selectTeam: (name: string) => void;
  addMemberToTeam: (teamName: string, roleNames: string[]) => Promise<void>;
  removeMemberFromTeam: (teamName: string, roleName: string) => Promise<void>;
  refreshTeam: (teamName: string) => Promise<void>;
}
```

---

## Mock Data Updates

### teamApi Mock 数据对齐

将 Mock 团队的成员名称与 roleApi 中的角色对齐：

```typescript
const MOCK_TEAMS: TeamApiResponse[] = [
  {
    name: 'Frontend Team',
    members: ['Designer', 'Developer'],  // 对应 roleApi 中的角色名称
  },
  {
    name: 'Backend Team',
    members: ['Developer', 'Tester'],
  },
  {
    name: 'Product Team',
    members: ['Designer'],
  },
];
```

### Mock 头像数据

```typescript
// roleApi.ts
const MOCK_AVATARS: string[] = [
  'avatar-circle.svg',
  'avatar-square.svg',
  'avatar-hexagon.svg',
  'avatar-triangle.svg',
  'avatar-star.svg',
];
```

前端渲染时根据文件名生成不同形状的简单 SVG 占位符。

---

## Implementation Priority

### Phase 1：基础展示（MVP）
1. ✅ RoleManagementPanel 主面板
2. ✅ Tab 切换逻辑
3. ✅ 角色管理 Tab：网格卡片展示
4. ✅ 团队管理 Tab：左侧列表 + 右侧详情
5. ✅ Adapter 层聚合函数
6. ✅ rolesStore / teamsStore

### Phase 2：创建和管理功能
1. ✅ CreateRoleDialog 弹窗
2. ✅ AvatarSelector 组件
3. ✅ 添加角色到角色管理
4. ✅ AddMemberDialog（添加现有/新建）
5. ✅ 从团队移除成员

### Phase 3：增强功能（技能广场完成后）
1. ⏸ Skill 列表展示
2. ⏸ Skill 添加/移除

---

## Technical Constraints

### 架构约束
- 遵循 `features/` 模块隔离原则
- 数据聚合在 Adapter 层完成
- 组件通过 hooks 消费数据，不直接调用 API
- 禁止 feature 之间直接依赖

### 样式约束
- 使用 CSS Modules 或 Tailwind CSS
- 所有颜色使用 CSS 变量（支持主题切换）
- 遵循 DESIGN.md v2.0 的圆角、间距规范
- 支持双主题（浅色/深色）

### 测试约束
- 测试文件与源文件共置（`.test.tsx`）
- Mock 数据不可变（使用 `const`）
- Adapter 函数需要单元测试
- 组件需要基础渲染测试

---

## Acceptance Criteria

1. ✅ 点击左侧栏"角色配置"后，右侧区域被角色管理面板替换
2. ✅ 角色管理 Tab 以网格卡片形式展示所有角色
3. ✅ 团队管理 Tab 左侧列表展示所有团队，右侧展示选中团队的成员
4. ✅ 角色卡片展示：头像、名称、平台、类型、描述、Skills（占位）
5. ✅ 创建角色弹窗包含所有必填字段，技能列表显示占位文本
6. ✅ 头像选择器以网格形式展示预设头像，支持点击选择
7. ✅ 可以从团队中移除成员，调用 API 后刷新列表
8. ✅ 可以添加现有角色到团队
9. ✅ 可以创建新角色并自动添加到团队
10. ✅ 所有视觉元素遵循 DESIGN.md v2.0 规范
11. ✅ 支持双主题（浅色/深色）切换

---

## Out of Spec

- 角色删除功能
- 角色编辑功能（更新名称、描述等）
- Skill 的实际添加/移除（等技能广场功能完成）
- 角色搜索/筛选功能
- 权限管理
- 批量操作（批量删除、批量移动）
- 角色导入/导出
