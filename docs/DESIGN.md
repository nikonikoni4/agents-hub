# Agents Hub 设计系统文档

> **创建日期**：2026-06-03  
> **版本**：v2.0  
> **参考风格**：Cursor / Windsurf 风格  
> **目标**：建立简洁、现代、双主题的设计系统

---

## 一、设计哲学

### 核心原则

1. **极简主义**：去除一切不必要的线条和装饰
2. **双主题优先**：浅色和深色主题同等重要
3. **圆角层级**：通过左侧圆角建立主内容区的视觉层级
4. **无边界感**：减少分隔线，通过背景色区分区域

### 设计目标

- **现代感**：符合 2026 年主流开发工具审美
- **高效性**：减少视觉噪音，聚焦内容
- **舒适性**：长时间使用不疲劳

---

## 二、色彩系统 ⭐⭐⭐⭐⭐

### 双主题色板

#### 浅色主题（Light Theme）

| 变量名 | 色值 | RGB | 用途 |
|--------|------|-----|------|
| `bg-sidebar` | `rgb(246, 246, 246)` | 246, 246, 246 | 顶栏、左侧栏背景 |
| `bg-shadow` | `rgb(234, 234, 234)` | 234, 234, 234 | 悬停态背景 |
| `bg-main` | `rgb(255, 255, 255)` | 255, 255, 255 | 主对话区背景 |
| `bg-bubble` | `rgb(246, 246, 246)` | 246, 246, 246 | 消息气泡背景 |
| `bg-right-base` | `rgb(255, 255, 255)` | 255, 255, 255 | 右侧栏背景 |
| `bg-right-module` | `rgb(246, 246, 246)` | 246, 246, 246 | 右侧栏模块背景 |
| `bg-right-shadow` | `rgb(233, 234, 234)` | 233, 234, 234 | 右侧栏模块阴影 |
| `bg-input` | `rgb(255, 255, 255)` | 255, 255, 255 | 输入框背景 |

| 变量名 | 色值 | RGB | 用途 |
|--------|------|-----|------|
| `text-primary` | `rgb(30, 30, 30)` | 30, 30, 30 | 主要文字 |
| `text-secondary` | `rgb(100, 100, 100)` | 100, 100, 100 | 次要文字 |
| `text-tertiary` | `rgb(150, 150, 150)` | 150, 150, 150 | 辅助文字 |
| `border-color` | `rgb(220, 220, 220)` | 220, 220, 220 | 边框颜色 |
| `accent-color` | `rgb(74, 158, 255)` | 74, 158, 255 | 强调色 |

#### 深色主题（Dark Theme）

| 变量名 | 浅色值 | 深色值 | RGB (深色) |
|--------|--------|--------|-----------|
| `bg-sidebar` | 246, 246, 246 | **20, 20, 20** | rgb(20, 20, 20) |
| `bg-shadow` | 234, 234, 234 | **38, 38, 38** | rgb(38, 38, 38) |
| `bg-main` | 255, 255, 255 | **24, 24, 24** | rgb(24, 24, 24) |
| `bg-bubble` | 246, 246, 246 | **20, 20, 20** | rgb(20, 20, 20) |
| `bg-right-base` | 255, 255, 255 | **24, 24, 24** | rgb(24, 24, 24) |
| `bg-right-module` | 246, 246, 246 | **20, 20, 20** | rgb(20, 20, 20) |
| `bg-right-shadow` | 233, 234, 234 | **36, 36, 36** | rgb(36, 36, 36) |
| `bg-input` | 255, 255, 255 | **45, 45, 45** | rgb(45, 45, 45) |

| 变量名 | 浅色值 | 深色值 | RGB (深色) |
|--------|--------|--------|-----------|
| `text-primary` | 30, 30, 30 | **230, 230, 230** | rgb(230, 230, 230) |
| `text-secondary` | 100, 100, 100 | **180, 180, 180** | rgb(180, 180, 180) |
| `text-tertiary` | 150, 150, 150 | **120, 120, 120** | rgb(120, 120, 120) |
| `border-color` | 220, 220, 220 | **60, 60, 60** | rgb(60, 60, 60) |
| `accent-color` | 74, 158, 255 | **74, 158, 255** | rgb(74, 158, 255) |

### 色彩映射规则

**从浅色到深色的映射逻辑**：
- 浅灰 (246) → 深黑 (20)
- 浅灰阴影 (234) → 深灰 (38)
- 纯白 (255) → 深灰主体 (24)
- 浅灰模块阴影 (233) → 深灰阴影 (36)
- **特殊**：输入框从纯白 (255) → 深灰偏亮 (45)

### 色彩使用规则

#### 层级关系

```
主背景 (sidebar bg) 
  └── 主对话区 (main bg) - 通过左侧圆角突出
      └── 消息气泡 (bubble bg)
      └── 输入框 (input bg)
```

#### ✅ 正确使用

- 顶栏和左侧栏：使用 `bg-sidebar`
- 主对话区：使用 `bg-main` + 左侧圆角
- 右侧栏：底色 `bg-right-base`，模块 `bg-right-module`

#### ❌ 避免

- 不要在同一层级混用不同背景色
- 不要使用未定义的中间色值
- 不要破坏颜色映射关系

---

## 三、字体系统 ⭐⭐⭐

### 字体族

```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
```

### 字号阶梯

| 级别 | 字号 | 行高 | 字重 | 用途 |
|------|------|------|------|------|
| `text-base` | 14px | 1.6 | 400 | 正文、消息 |
| `text-sm` | 13px | 1.5 | 400/500 | 侧边栏列表、按钮 |
| `text-xs` | 11px | 1.4 | 600 | 标签、小标注 |

### 字重规则

| 字重 | 数值 | 用途 |
|------|------|------|
| Regular | 400 | 正文、列表项 |
| Medium | 500 | 按钮、强调 |
| Semibold | 600 | 标题、标签 |

---

## 四、间距系统 ⭐⭐⭐⭐

### 基础单位：4px

### 间距阶梯

| 变量名 | 数值 | 用途 |
|--------|------|------|
| `spacing-1` | 4px | 极小间距 |
| `spacing-2` | 8px | 小间距、列表项间距 |
| `spacing-3` | 12px | 按钮内边距、小模块 |
| `spacing-4` | 16px | 模块内边距、区块间距 |
| `spacing-6` | 24px | 大区块间距 |

### 关键间距

- 顶栏高度：`40px`
- 左侧栏宽度：`280px`
- 右侧栏宽度：`320px`
- 聊天头部高度：`56px`
- 主内容区左右 padding：`24px`

---

## 五、圆角系统 ⭐⭐⭐⭐⭐

### 圆角阶梯

| 变量名 | 数值 | 用途 |
|--------|------|------|
| `radius-sm` | 4px | 小按钮 |
| `radius-md` | 6px | 普通按钮、列表项 |
| `radius-lg` | 8px | 模块卡片 |
| `radius-xl` | 12px | **主对话区左侧圆角**、大圆角 |
| `radius-2xl` | 16px | **消息气泡、输入框** |

### 关键圆角设计

#### 主对话区圆角（核心设计）

```css
.chat-area {
  border-radius: 12px 0 0 12px; /* 左上、右上、右下、左下 */
}
```

**设计理念**：
- 左侧圆角让主对话区像"卡片"一样浮在背景上
- 主背景使用 `bg-sidebar` 色，主对话区使用 `bg-main` 色
- 圆角清晰可见，建立视觉层级

#### 消息气泡和输入框

```css
.message-bubble,
.chat-input-wrapper {
  border-radius: 16px;
}
```

---

## 六、布局系统 ⭐⭐⭐⭐⭐

### 整体结构

```
app-container (flex column, 100vh)
├── top-bar (40px, bg-sidebar)
│   └── 左侧按钮组 + 搜索
└── main-container (flex row, flex: 1, bg-sidebar, padding: 8px 0)
    ├── left-sidebar (280px, bg-sidebar)
    │   ├── sidebar-buttons (按钮区)
    │   ├── sidebar-projects (flex: 1, 项目区)
    │   ├── sidebar-chats (对话区)
    │   └── sidebar-footer (设置)
    ├── chat-area (flex: 1, bg-main, border-radius: 12px 0 0 12px)
    │   ├── chat-header (56px)
    │   ├── chat-messages (flex: 1)
    │   └── chat-input-container
    └── right-sidebar (320px, bg-right-base)
        ├── right-header (收起按钮)
        └── right-module × N (模块)
```

### 层级关系说明

1. **主背景层**：`main-container` 使用 `bg-sidebar` (246/20)
2. **内容卡片层**：`chat-area` 使用 `bg-main` (255/24) + 左侧圆角
3. **嵌套内容层**：消息气泡、输入框使用对应背景色

**关键**：主对话区必须有左侧圆角，才能在主背景上形成"浮起"的视觉效果

---

## 七、核心组件规范

### 1. 顶部栏（Top Bar）

```css
height: 40px;
background: var(--bg-sidebar);
padding: 0 12px;
gap: 16px;
```

**内容**：
- 左侧：切换按钮、前进后退、搜索
- 无：文件、编辑等菜单（已移除）

### 2. 左侧栏（Left Sidebar）

```css
width: 280px;
background: var(--bg-sidebar);
border-right: 1px solid var(--border-color);
```

**分区**：
1. **按钮区** (sidebar-buttons)
   - 新对话
   - 角色管理
   - 技能广场

2. **项目区** (sidebar-projects, flex: 1)
   - 项目文件夹列表
   - 对话列表（嵌套在项目下）

3. **对话区** (sidebar-chats)
   - 历史对话列表

4. **设置** (sidebar-footer)
   - 设置按钮

### 3. 主对话区（Chat Area）

```css
flex: 1;
background: var(--bg-main);
border-radius: 12px 0 0 12px; /* 关键 */
display: flex;
flex-direction: column;
```

**分区**：
1. **头部** (chat-header, 56px)
   - 对话标题
   - 操作按钮

2. **消息区** (chat-messages, flex: 1)
   - 消息列表，可滚动

3. **输入区** (chat-input-container)
   - 输入框 (border-radius: 16px)

### 4. 右侧栏（Right Sidebar）

```css
width: 320px;
background: var(--bg-right-base);
border-left: 1px solid var(--border-color);
```

**内容**：
- 收起按钮（顶部）
- 成员列表模块
- 预览模块
- Diff 模块

**模块样式**：
```css
.right-module {
  margin: 12px;
  padding: 16px;
  background: var(--bg-right-module);
  border-radius: 8px;
  box-shadow: 0 1px 3px var(--bg-right-shadow);
}
```

### 5. 按钮（Button）

#### 顶栏按钮

```css
.top-bar-btn {
  width: 32px;
  height: 28px;
  border-radius: 4px;
  color: var(--text-secondary);
  transition: background 0.15s;
}

.top-bar-btn:hover {
  background: var(--bg-shadow);
}
```

#### 侧边栏按钮

```css
.sidebar-btn {
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  gap: 10px;
  transition: background 0.15s;
}

.sidebar-btn:hover {
  background: var(--bg-shadow);
}
```

### 6. 列表项（List Item）

#### 项目列表项

```css
.project-item {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  transition: background 0.15s;
}

.project-item:hover {
  background: var(--bg-shadow);
}
```

#### 对话列表项

```css
.chat-item {
  padding: 6px 12px 6px 24px; /* 左侧缩进 */
  font-size: 13px;
  color: var(--text-secondary);
  border-radius: 6px;
  transition: background 0.15s;
}
```

### 7. 消息气泡（Message Bubble）

```css
.message-bubble {
  background: var(--bg-bubble);
  padding: 16px;
  border-radius: 16px; /* 大圆角 */
  font-size: 14px;
  line-height: 1.6;
  max-width: 80%;
}
```

### 8. 输入框（Input）

```css
.chat-input-wrapper {
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 16px; /* 大圆角 */
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.chat-input {
  flex: 1;
  background: transparent;
  border: none;
  font-size: 14px;
  color: var(--text-primary);
}
```

---

## 八、主题切换

### 实现方式

```javascript
// HTML 根元素添加 data-theme 属性
document.documentElement.setAttribute('data-theme', 'dark');
```

### CSS 变量定义

```css
:root {
  /* 浅色主题变量 */
  --bg-sidebar: rgb(246, 246, 246);
  /* ... */
}

html[data-theme="dark"] {
  /* 深色主题变量 */
  --bg-sidebar: rgb(20, 20, 20);
  /* ... */
}
```

### 主题切换按钮

```css
.theme-toggle {
  position: fixed;
  bottom: 20px;
  left: 20px;
  width: 40px;
  height: 40px;
  background: var(--accent-color);
  border-radius: 8px;
  z-index: 1000;
}
```

---

## 九、侧边栏收起

### 左侧栏收起

```css
.left-sidebar.collapsed {
  width: 0;
  margin-left: -280px;
}
```

### 右侧栏收起

```css
.right-sidebar.collapsed {
  width: 0;
  margin-right: -320px;
}
```

### 过渡动画

```css
transition: width 0.3s, margin-left 0.3s;
/* 或 */
transition: width 0.3s, margin-right 0.3s;
```

---

## 十、图标系统

### 图标样式

所有图标使用 SVG，统一样式：

```css
svg {
  width: 18px; /* 或 24px */
  height: 18px;
  stroke: currentColor;
  fill: none;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
```

### 常用图标

| 功能 | SVG Path |
|------|----------|
| 新对话 | `<path d="M12 5v14m7-7H5"/>` (加号) |
| 角色管理 | `<circle cx="12" cy="7" r="4"/><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>` (人形) |
| 技能广场 | `<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>` (闪电) |
| 搜索 | `<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>` (放大镜) |
| 侧边栏切换 | `<rect x="3" y="3" width="7" height="18" rx="1"/><rect x="14" y="3" width="7" height="18" rx="1"/>` (双竖条) |
| 后退 | `<path d="M15 18l-6-6 6-6"/>` (左箭头) |
| 前进 | `<path d="M9 18l6-6-6-6"/>` (右箭头) |

---

## 十一、滚动条样式

```css
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--text-tertiary);
}
```

---

## 十二、设计决策

### 为什么选择这套设计？

1. **简洁性**：移除不必要的线条和装饰，聚焦内容
2. **现代感**：符合 2026 年主流开发工具审美（Cursor、Windsurf）
3. **双主题**：浅色和深色主题同等重要，色值精确映射
4. **层级清晰**：通过圆角和背景色建立视觉层级
5. **高效性**：减少视觉噪音，提高工作效率

### 与 v1.0 的主要变化

| 维度 | v1.0 (Claude Code 风格) | v2.0 (Cursor 风格) |
|------|------------------------|-------------------|
| **色彩** | 深色单主题 | 双主题（浅色/深色） |
| **线条** | 较多分隔线 | 极少分隔线 |
| **圆角** | 主要在组件 | 主对话区左侧圆角 |
| **顶栏** | 有菜单栏 | 只有按钮 |
| **左侧栏** | 4个按钮 | 3个按钮（精简） |
| **布局** | 平面式 | 卡片式（圆角浮起） |

---

## 十三、AI 使用指南

### 何时使用这套设计系统

- ✅ 修改前端 UI/UX 时
- ✅ 新增页面或组件时
- ✅ 调整色彩、间距、圆角时

### 关键检查点

1. **是否使用了 CSS 变量**（不要硬编码颜色）
2. **是否支持双主题**（浅色和深色）
3. **主对话区是否有左侧圆角**（12px）
4. **消息气泡和输入框圆角是否为 16px**
5. **间距是否为 4 的倍数**

### 快速参考

**核心 CSS 变量**：
```css
var(--bg-sidebar)      /* 顶栏、左侧栏 */
var(--bg-main)         /* 主对话区 */
var(--bg-bubble)       /* 消息气泡 */
var(--bg-input)        /* 输入框 */
var(--text-primary)    /* 主要文字 */
var(--text-secondary)  /* 次要文字 */
var(--border-color)    /* 边框 */
var(--accent-color)    /* 强调色 */
```

---

## 十四、参考原型

- **最新原型**：`_temp/agents-hub-new-style.html` ⭐⭐⭐
- 完整实现了 v2.0 设计系统
- 支持双主题切换
- 支持侧边栏收起

---

**准备好后，开始使用这套设计系统构建 agents-hub 的前端界面！**
