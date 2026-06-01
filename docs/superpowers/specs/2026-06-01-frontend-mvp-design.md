---
version: 1.0
created_at: 2026-06-01
updated_at: 2026-06-01
abstract: Agents Hub 前端 MVP 界面设计规格，定义核心组件、布局结构和交互流程
id: spec-frontend-mvp-design
title: Frontend MVP 设计规格
status: draft
related_docs:
  - docs/DESIGN.md
  - docs/PRD.md
  - docs/ARCHITECTURE.md
---

# Frontend MVP 设计规格

## 版本历史

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0  | 初始版本，定义 MVP 核心界面和组件 |

## Overview

本文档定义 agents-hub 前端 MVP 版本的界面设计，包括：
- 整体布局结构
- 核心组件清单
- 交互流程
- 数据流

**MVP 核心场景**：群聊场景（Orchestrator 自动分派任务）

**技术栈**：React + Electron + WebSocket

## Scope

### 范围内

- 两栏布局（会话列表 + 聊天窗口）
- 顶部工具栏（设置、搜索、导航等）
- 群聊信息面板（只读展示成员信息）
- 消息流（支持完整 Markdown 渲染）
- 输入框（发送文本消息）

### 范围外（后续迭代）

- 文件上传/下载
- Diff 视图
- 预览功能
- 成员编辑/添加/移除
- 消息搜索
- 多团队管理
- 单聊模式

## 整体布局

### 布局结构

```
┌────────────────────────────────────────────────────────────┐
│ [≡] [⊐] [🔍]  [←] [→]                          [-] [□] [×] │ ← TopBar (顶部工具栏)
├──────────────────┬─────────────────────────────────────────┤
│                  │  agents-hub / Frontend design prep [⋮]  │ ← ChatHeader (聊天标题栏)
│  会话列表        ├─────────────────────────────────────────┤
│                  │                                          │
│  [+ 新建会话]    │  ┌─────────────────────────────────────┐│
│                  │  │                                     ││
│  ┌────────────┐  │  │  消息流区域                         ││ ← MessageList (消息流)
│  │ 群聊 1     │  │  │                                     ││
│  │ Team A     │  │  │  [Manager]: 我来分配任务...         ││
│  │ 2分钟前    │  │  │  [Worker1]: 我负责前端...           ││
│  └────────────┘  │  │                                     ││
│                  │  └─────────────────────────────────────┘│
│  ┌────────────┐  │                                          │
│  │ 群聊 2     │  │  ┌─────────────────────────────────────┐│
│  │ Team B     │  │  │  输入框                             ││ ← InputArea (输入区域)
│  │ 1小时前    │  │  │  [输入消息...]            [发送]    ││
│  └────────────┘  │  └─────────────────────────────────────┘│
│                  │                                          │
│  (280px)         │                                          │
└──────────────────┴─────────────────────────────────────────┘
```

### 尺寸规范

| 区域 | 宽度 | 说明 |
|------|------|------|
| 左侧会话列表 | 280px | 固定宽度，可收起 |
| 右侧聊天窗口 | flex: 1 | 自适应剩余空间 |
| 顶部工具栏 | 100% | 高度 48px |
| 聊天标题栏 | 100% | 高度 56px |
| 输入框区域 | 100% | 最小高度 80px，自适应内容 |

## 核心组件

### 1. TopBar（顶部工具栏）

**组件职责**：提供全局操作入口

**子组件**：

| 组件 | 图标 | 功能 | MVP 状态 |
|------|------|------|---------|
| SettingsMenuButton | ≡ | 设置菜单 | 占位 |
| SidebarToggleButton | ⊐/⊏ | 收起/展开侧边栏 | 实现 |
| SearchBar | 🔍 | 搜索群聊记录 | 占位 |
| PrevSessionButton | ← | 上一条会话 | 实现 |
| NextSessionButton | → | 下一条会话 | 实现 |

**布局**：
```jsx
<TopBar>
  <LeftGroup>
    <SettingsMenuButton />
    <SidebarToggleButton />
    <SearchBar />
  </LeftGroup>
  <CenterGroup>
    <PrevSessionButton />
    <NextSessionButton />
  </CenterGroup>
  <RightGroup>
    {/* 窗口控制按钮（Electron） */}
  </RightGroup>
</TopBar>
```

---

### 2. SessionList（会话列表）

**组件职责**：显示所有群聊会话，支持切换

**子组件**：
- `NewSessionButton`：新建会话按钮
- `SessionItem`：单个会话项

**SessionItem 结构**：
```
┌────────────────────┐
│ 群聊名称           │
│ Team A             │
│ 2分钟前            │
└────────────────────┘
```

**数据结构**：
```typescript
interface Session {
  id: string;
  name: string;
  teamName: string;
  lastMessageTime: string;
  unreadCount?: number;
}
```

---

### 3. ChatWindow（聊天窗口）

**组件职责**：显示当前群聊的消息流和输入框

**子组件**：
- `ChatHeader`：聊天标题栏
- `MessageList`：消息流
- `InputArea`：输入区域
- `ChatInfoPanel`：群聊信息面板（可选显示）

---

#### 3.1 ChatHeader（聊天标题栏）

**组件职责**：显示群聊名称和操作菜单

**布局**：
```
┌─────────────────────────────────────────────────────────┐
│ agents-hub / Frontend design preparation  [⋮]          │
└─────────────────────────────────────────────────────────┘
```

**子组件**：
- `ChatTitle`：群聊名称
- `ChatMenuButton`：菜单按钮（⋮）
  - 点击展开下拉菜单

**下拉菜单选项**：
```
┌─────────────────────────────┐
│ ▷ 群聊信息                  │ ← 实现
│ ▷ Diff (占位)               │ ← 占位
│ ▷ 预览 (占位)               │ ← 占位
└─────────────────────────────┘
```

---

#### 3.2 MessageList（消息流）

**组件职责**：显示所有消息，支持滚动加载

**子组件**：
- `MessageItem`：单条消息

**MessageItem 结构**：
```
┌─────────────────────────────────────┐
│ [头像] Manager                      │
│        我来分配任务：                │
│        - Worker1 负责前端           │
│        - Worker2 负责后端           │
│                          10:30 AM   │
└─────────────────────────────────────┘
```

**数据结构**：
```typescript
interface Message {
  id: string;
  sendFrom: string;        // Agent 名称
  content: string;         // Markdown 格式文本
  timestamp: string;
  platform: 'claude' | 'codex';
}
```

**Markdown 渲染**：
- 使用 `react-markdown` 库
- 支持代码块语法高亮（使用 `react-syntax-highlighter`）
- 支持标题、列表、链接、加粗、斜体等

---

#### 3.3 InputArea（输入区域）

**组件职责**：用户输入和发送消息

**布局**：
```
┌─────────────────────────────────────┐
│  [输入消息...]            [发送]    │
└─────────────────────────────────────┘
```

**子组件**：
- `MessageInput`：多行文本输入框
  - 支持 Enter 发送，Shift+Enter 换行
  - 自动调整高度（最小 1 行，最大 10 行）
- `SendButton`：发送按钮

---

#### 3.4 ChatInfoPanel（群聊信息面板）

**组件职责**：显示群聊基本信息和成员列表

**触发方式**：点击 ChatHeader 的菜单按钮 → 选择"群聊信息"

**展示方式**：右侧滑出面板

**布局**：
```
┌─────────────────────┐
│  群聊信息      [×]  │
├─────────────────────┤
│  群聊名称：         │
│  Frontend design... │
│                     │
│  团队：Team A       │
│                     │
│  成员 (3)           │
│  ┌───────────────┐ │
│  │ [头像] Manager│ │
│  │ 团队管理者    │ │
│  │ Claude Code   │ │
│  └───────────────┘ │
│  ┌───────────────┐ │
│  │ [头像] Worker1│ │
│  │ 工作者        │ │
│  │ Codex         │ │
│  └───────────────┘ │
│  ┌───────────────┐ │
│  │ [头像] Worker2│ │
│  │ 工作者        │ │
│  │ Claude Code   │ │
│  └───────────────┘ │
└─────────────────────┘
```

**子组件**：
- `PanelHeader`：标题 + 关闭按钮
- `ChatBasicInfo`：群聊名称、团队名称
- `MemberList`：成员列表
  - `MemberCard`：单个成员卡片

**MemberCard 数据结构**：
```typescript
interface Member {
  name: string;
  role: 'manager' | 'worker';
  platform: 'claude' | 'codex';
  avatar?: string;
}
```

**MVP 限制**：
- 所有信息只读，不支持编辑
- 不支持添加/移除成员

## 组件树结构

```
App
├── TopBar
│   ├── SettingsMenuButton (占位)
│   ├── SidebarToggleButton
│   ├── SearchBar (占位)
│   ├── PrevSessionButton
│   └── NextSessionButton
│
├── SessionList (可收起)
│   ├── NewSessionButton
│   └── SessionItem (多个)
│
└── ChatWindow
    ├── ChatHeader
    │   ├── ChatTitle
    │   └── ChatMenuButton
    │       └── ChatMenuDropdown
    │           ├── "群聊信息" → 打开 ChatInfoPanel
    │           ├── "Diff" (占位)
    │           └── "预览" (占位)
    │
    ├── ChatInfoPanel (右侧滑出，可选显示)
    │   ├── PanelHeader
    │   ├── ChatBasicInfo
    │   └── MemberList
    │       └── MemberCard (多个)
    │
    ├── MessageList
    │   └── MessageItem (多个)
    │       ├── Avatar
    │       ├── SenderName
    │       ├── MessageContent (Markdown 渲染)
    │       └── Timestamp
    │
    └── InputArea
        ├── MessageInput
        └── SendButton
```

## 交互流程

### 1. 用户发送消息

```
用户在 InputArea 输入消息
  ↓
点击发送按钮 / 按 Enter
  ↓
前端通过 WebSocket 发送消息
  ↓
后端 API Server 接收
  ↓
Core 层路由给 Manager
  ↓
Manager 分派任务给 Workers
  ↓
Workers 执行并回复
  ↓
WebSocket 推送消息给前端
  ↓
MessageList 显示新消息
  ↓
自动滚动到最新消息
```

### 2. 查看群聊信息

```
用户点击 ChatHeader 的菜单按钮 (⋮)
  ↓
展开下拉菜单
  ↓
点击"群聊信息"
  ↓
右侧滑出 ChatInfoPanel
  ↓
显示群聊名称、团队、成员列表
  ↓
用户点击关闭按钮 [×]
  ↓
面板收起
```

### 3. 切换会话

```
用户点击 SessionList 中的某个 SessionItem
  ↓
更新当前选中的会话 ID
  ↓
ChatWindow 加载该会话的消息历史
  ↓
MessageList 显示历史消息
```

### 4. 收起/展开侧边栏

```
用户点击 TopBar 的 SidebarToggleButton
  ↓
SessionList 收起/展开
  ↓
ChatWindow 宽度自适应调整
```

## 数据流

### WebSocket 消息格式

**前端 → 后端（发送消息）**：
```json
{
  "type": "send_message",
  "group_chat_id": "gc_123",
  "content": "请帮我实现一个登录页面"
}
```

**后端 → 前端（接收消息）**：
```json
{
  "type": "new_message",
  "message": {
    "id": "msg_456",
    "send_from": "Manager",
    "content": "收到！我来分配任务...",
    "timestamp": "2026-06-01T10:30:00Z",
    "platform": "claude"
  }
}
```

### REST API

**获取会话列表**：
```
GET /api/sessions
Response:
{
  "sessions": [
    {
      "id": "gc_123",
      "name": "Frontend design preparation",
      "team_name": "Team A",
      "last_message_time": "2026-06-01T10:30:00Z"
    }
  ]
}
```

**获取群聊信息**：
```
GET /api/group_chats/{group_chat_id}
Response:
{
  "id": "gc_123",
  "name": "Frontend design preparation",
  "team_name": "Team A",
  "members": [
    {
      "name": "Manager",
      "role": "manager",
      "platform": "claude"
    },
    {
      "name": "Worker1",
      "role": "worker",
      "platform": "codex"
    }
  ]
}
```

**获取消息历史**：
```
GET /api/group_chats/{group_chat_id}/messages?limit=50&offset=0
Response:
{
  "messages": [
    {
      "id": "msg_456",
      "send_from": "Manager",
      "content": "收到！我来分配任务...",
      "timestamp": "2026-06-01T10:30:00Z",
      "platform": "claude"
    }
  ]
}
```

## 设计系统应用

所有组件必须遵循 `docs/DESIGN.md` 中定义的设计系统：

### 色彩

- 背景：`bg-base` (#1f1f1e)
- 侧边栏：`bg-elevated` (#262626)
- 消息气泡：`bg-surface` (#2a2a2a)
- 主色调：`accent-primary` (#4a9eff)
- 文字：`text-secondary` (#e0e0e0)

### 字体

- 正文：15px, Regular (400)
- 标题：18px, Semibold (600)
- 辅助文字：14px, Regular (400)

### 间距

- 组件内边距：16-20px
- 组件间距：20-24px
- 消息间距：20px

### 圆角

- 消息气泡：12px
- 输入框：12px
- 按钮：7-8px

### 阴影

- 消息气泡：`shadow-sm` (0 1px 3px rgba(0,0,0,0.08))
- 输入框：`shadow-lg` (0 4px 16px rgba(0,0,0,0.25))

## 技术约束

### 前端技术栈

- **框架**：React 18+
- **状态管理**：React Context + Hooks（MVP 阶段不引入 Redux）
- **WebSocket**：原生 WebSocket API
- **Markdown 渲染**：react-markdown + react-syntax-highlighter
- **样式**：CSS Modules 或 Tailwind CSS
- **打包**：Electron + Vite

### 性能要求

- 消息列表虚拟滚动（当消息数 > 100 时）
- WebSocket 自动重连
- 消息发送失败重试机制

### 可访问性

- 所有交互元素支持键盘操作
- 聚焦态有明显视觉反馈
- 对比度符合 WCAG AA 标准（≥ 4.5:1）

## Out of Spec

以下内容不在 MVP 范围内：

- 文件上传/下载功能
- Diff 视图实现
- 预览功能实现
- 消息搜索功能
- 成员编辑/添加/移除
- 多团队管理
- 单聊模式
- 消息引用/回复
- 消息重新生成
- 表情反应
- 通知系统
- 离线消息同步

## Acceptance Criteria

MVP 完成的验收标准：

1. ✅ 用户可以看到会话列表
2. ✅ 用户可以切换不同的群聊
3. ✅ 用户可以发送文本消息
4. ✅ 用户可以看到 Agent 的回复（Markdown 渲染正确）
5. ✅ 用户可以查看群聊信息（成员列表）
6. ✅ 用户可以收起/展开侧边栏
7. ✅ 用户可以通过箭头按钮切换会话
8. ✅ 消息流自动滚动到最新消息
9. ✅ WebSocket 连接断开后自动重连
10. ✅ 所有占位功能显示"功能开发中"提示

## Next Steps

MVP 完成后的迭代方向：

1. **Phase 2**：实现 Diff 视图和预览功能
2. **Phase 3**：支持文件上传/下载
3. **Phase 4**：成员管理功能（编辑/添加/移除）
4. **Phase 5**：消息搜索和筛选
5. **Phase 6**：单聊模式
6. **Phase 7**：多团队管理
