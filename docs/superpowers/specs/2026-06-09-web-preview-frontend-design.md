---
title: 网页预览卡片前端设计
date: 2026-06-09
status: draft
author: Claude & nico
---

# 网页预览卡片前端设计

## 1. 概述

### 1.1 功能目标

Agent 返回任务结果时可以附带网页预览信息，消息气泡中显示可点击的链接卡片，点击后在右侧栏专用 tab 中通过 iframe 展示网页内容。

### 1.2 使用场景

- Agent 生成了网页报告（如测试报告、可视化页面），用户需要预览
- Agent 完成前端开发任务，用户需要查看渲染效果
- Agent 生成了在线文档或图表，用户需要快速浏览

### 1.3 数据来源

后端已完成：`finish_agent_call` MCP tool 接收 `web_preview_url` + `web_preview_title`，经 `AgentResult` → `GroupChatSession.add_message()` → 消息 dict → `MessageInfo` Pydantic schema 传递到前端 API。

前端 API 响应中 `MessageApiItem.web_preview` 结构：
```typescript
{
  url: string;      // 预览页面 URL（必填）
  title?: string;   // 页面标题（可选）
}
```

## 2. 组件设计

### 2.1 WebPreviewCard（消息内卡片）

**位置**：`frontend/src/shared/components/WebPreviewCard/`

**职责**：在消息气泡中展示网页预览入口，点击后在右侧栏打开预览。

**Props**：
```typescript
interface WebPreviewCardProps {
  url: string;
  title?: string;
  /** 当前是否已在右侧栏打开 */
  isActive: boolean;
  onClick: () => void;
}
```

**视觉设计**：
- 左侧：网页图标（Globe 类型 SVG）
- 中间：title（如有）+ URL 域名（如 `localhost:3000`）
- 右侧：箭头图标
- 激活态：左边框 accent 色 + 浅色背景高亮，表示已在右侧栏打开
- 悬停态：背景微变

**展示位置**：`MessageBubble` 内部，紧跟 `FileChangesCard` 之后（如有），在 `messageActions` 之前。

### 2.2 RightSidebar "网页" tab

**位置**：现有 `frontend/src/layouts/RightSidebar/RightSidebar.tsx` 中新增 tab。

**Tab 定义**：`SidebarTab` 类型新增 `'web'`，标签文案 `"网页"`。

**渲染逻辑**：
- 有内容时：iframe 全宽填充 + 标题栏（标题 + "在浏览器中打开"按钮）
- 无内容时：空态提示 "点击消息中的预览卡片查看网页"

**iframe 配置**：
- `sandbox="allow-scripts allow-same-origin allow-forms"` — 限制权限
- `loading="lazy"` — 延迟加载
- CSS：宽度 100%，高度填满可用空间

### 2.3 RightSidebarContent 类型扩展

**文件**：`frontend/src/shared/types/layout.ts`

现有类型：
```typescript
interface RightSidebarContent {
  type: 'preview' | 'diff';
  content: string;
  filePath: string;
}
```

扩展为联合类型：
```typescript
type RightSidebarContent =
  | { type: 'preview'; content: string; filePath: string }
  | { type: 'diff'; content: string; filePath: string }
  | { type: 'web'; url: string; title?: string };
```

### 2.4 MessageApiItem 类型扩展

**文件**：`frontend/src/shared/types/api-schemas.ts`

新增：
```typescript
interface WebPreviewInfo {
  url: string;
  title?: string;
}

// MessageApiItem 中新增：
web_preview?: WebPreviewInfo;
```

## 3. 数据流

```
用户点击 WebPreviewCard
  → ChatArea.handleWebPreview(url, title)
  → setRightSidebarContent({ type: 'web', url, title })
  → MainLayout 传递 content prop 到 RightSidebar
  → RightSidebar 自动切换到 'web' tab
  → iframe 加载 url
```

**激活状态同步**：
- `WebPreviewCard` 的 `isActive` 通过比较 `rightSidebarContent` 判断
- `rightSidebarContent?.type === 'web' && rightSidebarContent.url === cardUrl`

**会话切换**：
- 切换 activeSessionId 时，清空 `rightSidebarContent`（现有行为，无需额外处理）

## 4. 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `shared/types/api-schemas.ts` | 修改 | `MessageApiItem` 加 `web_preview` 字段 |
| `shared/types/layout.ts` | 修改 | `RightSidebarContent` 加 `web` 分支 |
| `shared/components/WebPreviewCard/WebPreviewCard.tsx` | 新建 | 卡片组件 |
| `shared/components/WebPreviewCard/WebPreviewCard.module.css` | 新建 | 卡片样式 |
| `shared/components/index.ts` | 修改 | 导出 WebPreviewCard |
| `layouts/RightSidebar/RightSidebar.tsx` | 修改 | 新增 "网页" tab + iframe 渲染 |
| `layouts/ChatArea/ChatArea.tsx` | 修改 | MessageBubble 加 WebPreviewCard |

## 5. 设计决策

### 5.1 为什么用独立 tab 而非复用 preview tab？

现有 `preview` tab 用于文本文件预览（MarkdownRenderer 渲染）。网页预览（iframe）是完全不同的渲染方式，且后续可能扩展更多功能（如多页面切换、刷新、全屏等），独立 tab 更灵活。

### 5.2 为什么卡片放在 shared/components 而非 features/chat？

WebPreviewCard 是纯展示组件，不依赖任何 feature 的 store 或 hooks，符合 shared/components 的定义。消息渲染逻辑仍在 ChatArea（layout 层），卡片只是被引用的子组件。

### 5.3 iframe sandbox 策略

使用 `allow-scripts allow-same-origin allow-forms`，允许页面正常运行但禁止弹窗、top-level navigation 等。这是 Agent 生成的本地预览页面，安全性要求中等。
