# 前端样式与颜色层级规则

> **创建日期**: 2026-06-05  
> **触发场景**: 编写前端组件样式时，特别是涉及背景色、容器、卡片等布局元素  
> **目标**: 保证全局视觉风格统一，避免颜色层级混乱

---

## 核心原则：三层颜色关系

整个系统遵循**固定的三层颜色关系**，浅色和深色主题都保持这个层级：

```
底色层 (deepest)
  └── 容器层 (middle)
        └── 卡片/内容层 (lightest)
```

### 三层定义

| 层级 | CSS 变量 | 浅色值 | 深色值 | 用途 |
|------|---------|--------|--------|------|
| **底色层** | `var(--bg-sidebar)` | rgb(246, 246, 246) | rgb(20, 20, 20) | 左侧栏、顶栏、主容器背景 |
| **容器层** | `var(--bg-main)` | rgb(255, 255, 255) | rgb(24, 24, 24) | 主对话区、右侧栏、技能广场等主要内容区的背景 |
| **卡片/内容层** | `var(--bg-bubble)` | rgb(246, 246, 246) | rgb(20, 20, 20) | 消息气泡、右侧栏卡片、技能卡片、筛选按钮等 |

---

## 实际应用示例

### ✅ 正确：聊天界面

```
左侧栏背景: var(--bg-sidebar)  ← 底色层
主对话区背景: var(--bg-main)    ← 容器层（带左侧圆角）
  └── 消息气泡: var(--bg-bubble)  ← 卡片层
```

### ✅ 正确：右侧栏

```
右侧栏背景: var(--bg-main)      ← 容器层
  └── 成员列表卡片: var(--bg-bubble)  ← 卡片层
  └── 预览卡片: var(--bg-bubble)      ← 卡片层
  └── Diff 卡片: var(--bg-bubble)     ← 卡片层
```

### ✅ 正确：技能广场

```
主容器背景: var(--bg-sidebar)    ← 底色层
技能广场容器: var(--bg-main)     ← 容器层（带左侧圆角）
  └── 头部卡片: var(--bg-bubble)    ← 卡片层
  └── 筛选按钮: var(--bg-bubble)    ← 卡片层
  └── 技能卡片: var(--bg-bubble)    ← 卡片层
```

### ❌ 错误：跳层使用

```css
/* ❌ 错误：在底色层上直接放卡片（跳过容器层） */
.mainContainer {
  background: var(--bg-sidebar);  /* 底色层 */
}
.skillCard {
  background: var(--bg-bubble);   /* 跳过了容器层！ */
}

/* ✅ 正确：必须先有容器层 */
.mainContainer {
  background: var(--bg-sidebar);  /* 底色层 */
}
.skillSquareWrapper {
  background: var(--bg-main);     /* 容器层 */
}
.skillCard {
  background: var(--bg-bubble);   /* 卡片层 */
}
```

### ❌ 错误：硬编码颜色

```css
/* ❌ 错误：直接使用色值 */
background: rgb(246, 246, 246);

/* ✅ 正确：使用 CSS 变量 */
background: var(--bg-sidebar);
```

---

## 编码规则

### 1. 禁止跳层

**必须**按照 `底色 → 容器 → 卡片` 的顺序使用，**不能跳层**。

```css
/* ❌ 禁止 */
.parent {
  background: var(--bg-sidebar);  /* 底色层 */
}
.child {
  background: var(--bg-bubble);   /* 跳过了容器层 */
}

/* ✅ 正确 */
.parent {
  background: var(--bg-sidebar);  /* 底色层 */
}
.container {
  background: var(--bg-main);     /* 容器层 */
}
.card {
  background: var(--bg-bubble);   /* 卡片层 */
}
```

### 2. 禁止硬编码

**必须**使用 CSS 变量，**禁止**硬编码颜色值。

```css
/* ❌ 禁止 */
background: #f6f6f6;
background: rgb(246, 246, 246);
background: white;

/* ✅ 正确 */
background: var(--bg-sidebar);
background: var(--bg-main);
background: var(--bg-bubble);
```

### 3. 容器层的圆角规则

当容器层（`var(--bg-main)`）作为主内容区时，**必须**添加左侧圆角以形成"浮起"的视觉效果。

```css
/* ✅ 主对话区 */
.chatArea {
  background: var(--bg-main);
  border-radius: var(--radius-xl) 0 0 var(--radius-xl);  /* 左侧圆角 */
}

/* ✅ 技能广场 */
.skillSquare {
  background: var(--bg-main);
  border-radius: var(--radius-xl) 0 0 var(--radius-xl);  /* 左侧圆角 */
}

/* ✅ 右侧栏不需要圆角 */
.rightSidebar {
  background: var(--bg-main);
  /* 无圆角 */
}
```

### 4. 卡片层的一致性

所有卡片（消息、技能卡片、右侧栏模块）**必须**使用相同的背景色 `var(--bg-bubble)`。

```css
/* ✅ 所有卡片使用相同背景 */
.messageBubble {
  background: var(--bg-bubble);
}
.skillCard {
  background: var(--bg-bubble);
}
.memberListCard {
  background: var(--bg-bubble);
}
```

---

## 其他 CSS 变量

除了三层颜色，以下变量也**必须**使用：

### 文字颜色

```css
--text-primary: rgb(30, 30, 30) / rgb(230, 230, 230)   /* 主要文字 */
--text-secondary: rgb(100, 100, 100) / rgb(180, 180, 180) /* 次要文字 */
--text-tertiary: rgb(150, 150, 150) / rgb(120, 120, 120)  /* 辅助文字 */
```

### 边框和强调色

```css
--border-color: rgb(220, 220, 220) / rgb(60, 60, 60)  /* 边框 */
--accent-color: rgb(74, 158, 255) / rgb(74, 158, 255) /* 强调色（按钮、链接） */
```

### 圆角系统

```css
--radius-sm: 4px    /* 小按钮 */
--radius-md: 6px    /* 普通按钮、输入框 */
--radius-lg: 8px    /* 卡片 */
--radius-xl: 12px   /* 主对话区左侧圆角 */
--radius-2xl: 16px  /* 大圆角（特殊场景） */
```

### 间距系统（4px 倍数）

```css
--spacing-1: 4px
--spacing-2: 8px
--spacing-3: 12px
--spacing-4: 16px
--spacing-6: 24px
```

---

## 检查清单

在编写样式时，检查以下几点：

- [ ] 是否使用了 `var(--bg-xxx)` 而非硬编码颜色？
- [ ] 颜色层级是否正确（底色 → 容器 → 卡片）？
- [ ] 是否跳过了中间层级？
- [ ] 容器层是否添加了左侧圆角（如果是主内容区）？
- [ ] 是否使用了 `var(--radius-xxx)` 而非硬编码圆角？
- [ ] 间距是否为 4 的倍数？

---

## 违规检测

如果发现以下情况，**必须修正**：

```css
/* 🚨 违规 1：硬编码颜色 */
background: #ffffff;

/* 🚨 违规 2：跳层使用 */
.parent { background: var(--bg-sidebar); }
.child { background: var(--bg-bubble); }  /* 缺少容器层 */

/* 🚨 违规 3：硬编码圆角 */
border-radius: 12px;

/* 🚨 违规 4：非4倍数间距 */
padding: 15px;  /* 应该是 16px */
```

---

## 参考

- 设计系统完整文档：`docs/DESIGN.md`
- CSS 变量定义：`frontend/src/styles/theme.css`
- 实际案例：
  - 聊天界面：`frontend/src/layouts/ChatArea/`
  - 右侧栏：`frontend/src/layouts/RightSidebar/`
  - 技能广场：`frontend/src/features/skills/`
