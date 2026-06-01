# Agents Hub 设计系统文档

> **创建日期**：2026-06-01  
> **版本**：v1.0  
> **参考风格**：Claude Code Desktop  
> **目标**：为 agents-hub 项目建立统一、可扩展、AI 可理解的视觉设计系统

---

## 一、设计哲学

### 核心原则

1. **专业克制**：开发者工具的专业感，避免过度装饰
2. **层级清晰**：通过阴影、边框、背景色建立视觉层级
3. **状态明确**：每个交互元素都有清晰的状态反馈
4. **一致性优先**：所有元素遵循统一的设计语言

### 设计目标

- **统一性**：所有界面元素遵循相同的设计语言
- **可扩展性**：新增元素时能自动匹配现有风格
- **AI 可理解性**：规则清晰、语义化、有明确的使用场景说明

---

## 二、色彩系统 ⭐⭐⭐⭐⭐

### 基础色板

#### 背景层级色（从深到浅）

| 变量名 | 色值 | RGB | 用途 | 何时使用 |
|--------|------|-----|------|---------|
| `bg-base` | `#1f1f1e` | rgb(31, 31, 30) | 主背景 | 页面主体背景、内容区域 |
| `bg-elevated` | `#262626` | rgb(38, 38, 38) | 提升背景 | 侧边栏、导航栏、固定区域 |
| `bg-surface` | `#2a2a2a` | rgb(42, 42, 42) | 表面背景 | 卡片、消息气泡、输入框 |
| `bg-surface-hover` | `#2d2d2d` | rgb(45, 45, 45) | 表面悬停 | 卡片/输入框悬停态 |
| `bg-overlay` | `#1a1a1a` | rgb(26, 26, 26) | 遮罩背景 | 底部输入区、模态框背景 |

#### 边框色

| 变量名 | 色值 | RGB | 用途 |
|--------|------|-----|------|
| `border-subtle` | `#2a2a2a` | rgb(42, 42, 42) | 微妙分隔 |
| `border-default` | `#353535` | rgb(53, 53, 53) | 默认边框 |
| `border-strong` | `#3a3a3a` | rgb(58, 58, 58) | 强调边框 |
| `border-hover` | `#404040` | rgb(64, 64, 64) | 悬停边框 |

#### 文字色

| 变量名 | 色值 | RGB | 对比度 | 用途 |
|--------|------|-----|--------|------|
| `text-primary` | `#ffffff` | rgb(255, 255, 255) | 最高 | 标题、重要文字 |
| `text-secondary` | `#e0e0e0` | rgb(224, 224, 224) | 高 | 正文、主要内容 |
| `text-tertiary` | `#b0b0b0` | rgb(176, 176, 176) | 中 | 次要信息、辅助文字 |
| `text-quaternary` | `#888888` | rgb(136, 136, 136) | 低 | 占位符、禁用文字 |
| `text-disabled` | `#666666` | rgb(102, 102, 102) | 最低 | 禁用状态 |

#### 主色调（Accent）

| 变量名 | 色值 | RGB | 用途 | 何时使用 |
|--------|------|-----|------|---------|
| `accent-primary` | `#4a9eff` | rgb(74, 158, 255) | 主操作 | 主要按钮、链接、选中状态 |
| `accent-primary-hover` | `#357abd` | rgb(53, 122, 189) | 主操作悬停 | 按钮悬停态 |
| `accent-secondary` | `#ff6b6b` | rgb(255, 107, 107) | 次要强调 | 图标、装饰元素 |

#### 语义色

| 变量名 | 色值 | 用途 | 何时使用 |
|--------|------|------|---------|
| `semantic-success` | `#4ade80` | 成功状态 | 操作成功提示、完成状态 |
| `semantic-warning` | `#fbbf24` | 警告状态 | 需要注意的信息 |
| `semantic-error` | `#f87171` | 错误状态 | 错误提示、失败状态 |
| `semantic-info` | `#60a5fa` | 信息状态 | 一般信息提示 |

### 色彩使用规则

#### ✅ 允许的组合

- `bg-base` + `text-secondary`（主内容区）
- `bg-elevated` + `text-secondary`（侧边栏）
- `bg-surface` + `text-secondary`（卡片内容）
- `accent-primary` + `#ffffff`（按钮文字）
- `bg-surface` + `border-default`（卡片边框）

#### ❌ 禁止的组合

- `bg-base` + `text-quaternary`（对比度不足 < 4.5:1）
- `accent-primary` + `accent-secondary`（色彩冲突）
- 任何中灰背景 + 浅灰文字（可读性差）

#### 对比度要求

- **正文文字**：对比度 ≥ 4.5:1（WCAG AA 标准）
- **大号文字**（≥18px）：对比度 ≥ 3:1
- **装饰元素**：对比度 ≥ 3:1

---

## 三、字体系统 ⭐⭐⭐⭐

### 字体族

```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
```

**选择理由**：
- 使用系统字体栈，保持原生感
- 跨平台一致性好
- 性能优秀（无需加载外部字体）

### 字号阶梯

| 级别 | 字号 | 行高 | 字重 | 用途 | 何时使用 |
|------|------|------|------|------|---------|
| `text-2xl` | 22px | 1.3 | 700 | 页面标题 | 主内容区标题（更重的字重） |
| `text-xl` | 18px | 1.4 | 600 | 区块标题 | 卡片标题、章节标题 |
| `text-lg` | 16px | 1.5 | 500 | 强调文字 | 重要信息、子标题 |
| `text-base` | 15px | 1.6 | 400 | 正文 | 消息内容、输入框文字 |
| `text-sm` | 14px | 1.5 | 400 | 辅助文字 | 侧边栏列表项 |
| `text-xs` | 11px | 1.4 | 600 | 标签文字 | 分类标签、状态标签 |

### 字重规则

| 字重 | 数值 | 用途 |
|------|------|------|
| Regular | 400 | 正文、列表项（默认） |
| Medium | 500 | 按钮、强调文字、激活的列表项 |
| Semibold | 600 | 区块标题、标签 |
| Bold | 700 | 页面主标题 |

### 字体使用规则

#### ✅ 正确使用

- 标题使用 Bold（700）+ 较大字号（22px）
- 正文使用 Regular（400）+ 15px
- 侧边栏列表项使用 Regular（400）+ 14px，激活时 Medium（500）
- 标签使用 Semibold（600）+ 11px + 大写 + 字间距

#### ❌ 避免

- 正文字号 < 14px（可读性差）
- 标题使用 Regular（层级不明显）
- 过多字重变化（视觉混乱）

---

## 四、间距系统 ⭐⭐⭐⭐

### 基础单位

**8px 基础单位**（4px 作为半单位）

### 间距阶梯

| 变量名 | 数值 | 用途 | 何时使用 |
|--------|------|------|---------|
| `spacing-1` | 4px | 极小间距 | 图标与文字、紧密元素 |
| `spacing-2` | 8px | 小间距 | 组件内边距、相关元素 |
| `spacing-3` | 12px | 中小间距 | 输入框内边距、按钮内边距 |
| `spacing-4` | 16px | 中等间距 | 组件间距、卡片内边距 |
| `spacing-5` | 20px | 中大间距 | 侧边栏内边距、区块内边距 |
| `spacing-6` | 24px | 大间距 | 区块间距、页面内边距 |
| `spacing-8` | 32px | 超大间距 | 页面边距、大区块间距 |
| `spacing-12` | 48px | 巨大间距 | 页面顶部/底部留白 |

### 间距使用规则

#### 格式塔原理

- **相关元素间距 < 无关元素间距**
- 同一组内的元素：8-12px
- 不同组之间：16-24px
- 不同区块之间：32-48px

#### ✅ 正确使用

- 消息气泡内边距：18-20px（上下更方正）
- 消息之间间距：20-24px
- 侧边栏内边距：20px（更宽松的呼吸空间）
- 侧边栏顶部 logo 区域：margin-bottom 24px
- 页面主内容边距：24-32px
- 输入框内边距：14-18px（更松弛）
- 主内容区顶部间距：32px（更多空气感）

#### ❌ 避免

- 使用 5px、7px、13px 等不规则数值
- 相关元素间距过大（破坏视觉分组）
- 间距不一致（同类元素使用不同间距）

---

## 五、圆角系统 ⭐⭐⭐

### 圆角阶梯

| 变量名 | 数值 | 用途 | 何时使用 |
|--------|------|------|---------|
| `radius-sm` | 6px | 小元素 | 按钮、标签、小图标 |
| `radius-md` | 8px | 中等元素 | 卡片、输入框、头像 |
| `radius-lg` | 12px | 大元素 | 消息气泡、大卡片 |
| `radius-full` | 9999px | 圆形 | 圆形头像、圆形按钮 |

### 圆角使用规则

#### 嵌套规则

- **内层圆角 < 外层圆角**
- 例：卡片 12px，内部按钮 8px

#### ✅ 正确使用

- 消息气泡：12px
- 输入框：12px
- 按钮：7-8px
- 头像：8px
- Logo：6px

#### ❌ 避免

- 同一层级使用不同圆角
- 内层圆角 ≥ 外层圆角
- 使用 5px、9px、13px 等不规则数值

---

## 六、阴影/层级系统 ⭐⭐⭐⭐⭐

### 阴影等级

| 等级 | CSS 值 | 用途 | 何时使用 |
|------|--------|------|---------|
| `shadow-none` | `none` | 无阴影 | 平面元素、列表项 |
| `shadow-xs` | `0 1px 2px rgba(0,0,0,0.1)` | 极轻微 | 按钮默认态、小卡片 |
| `shadow-sm` | `0 1px 3px rgba(0,0,0,0.08)` | 轻微 | 消息气泡默认态 |
| `shadow-md` | `0 2px 6px rgba(0,0,0,0.12)` | 中等 | 消息气泡悬停态 |
| `shadow-lg` | `0 4px 16px rgba(0,0,0,0.25)` | 明显 | 输入框浮动感（关键） |
| `shadow-xl` | `0 8px 24px rgba(0,0,0,0.25)` | 强烈 | 模态框、抽屉 |

**v4 关键改进**：所有阴影都更柔和，减少视觉重量，避免"廉价感"。

### 特殊阴影

| 类型 | CSS 值 | 用途 |
|------|--------|------|
| `shadow-accent` | `0 2px 8px rgba(74,158,255,0.3)` | Accent 元素 |
| `shadow-accent-hover` | `0 4px 12px rgba(74,158,255,0.4)` | Accent 悬停 |

### 层级使用规则

#### Z-index 层级

| 层级 | Z-index | 用途 |
|------|---------|------|
| Base | 0 | 基础内容 |
| Elevated | 10 | 卡片、消息 |
| Sticky | 100 | 固定导航、侧边栏 |
| Dropdown | 1000 | 下拉菜单 |
| Modal | 10000 | 模态框、抽屉 |

#### ✅ 正确使用

- 消息气泡：`shadow-sm` (0 1px 3px rgba(0,0,0,0.08)) + hover 时 `shadow-md` (0 2px 6px rgba(0,0,0,0.12))
- 按钮：`shadow-xs` (0 1px 2px rgba(0,0,0,0.1)) + hover 时 `shadow-md`
- **输入框（浮动感）**：`shadow-lg` (0 4px 16px rgba(0,0,0,0.25)) + focus 时增强
- Logo/头像：`shadow-accent` (0 2px 6px rgba(74,158,255,0.25))
- 侧边栏右侧：`2px 0 8px rgba(0,0,0,0.1)`（微妙的右侧阴影）

#### ❌ 避免

- 使用纯黑色阴影（`rgba(0,0,0,1)`）
- 阴影过重（破坏层级感）
- 所有元素都加阴影（视觉噪音）

---

## 七、组件状态 ⭐⭐⭐⭐⭐

### 交互状态定义

每个可交互组件必须定义以下 5 种状态：

| 状态 | 视觉变化 | 何时触发 |
|------|---------|---------|
| **默认态** | 基础样式 | 初始状态 |
| **悬停态** | 背景加深 + 阴影增强 | 鼠标悬停 |
| **激活态** | 背景更深 + 阴影减弱 + 轻微下移 | 点击按下 |
| **聚焦态** | 边框变为 accent 色 + accent 阴影 | 键盘聚焦 |
| **禁用态** | 透明度 50% + 鼠标禁用 | 不可操作 |

### 按钮状态示例

```css
/* 默认态 */
.button {
  background: linear-gradient(135deg, #4a9eff 0%, #357abd 100%);
  box-shadow: 0 2px 6px rgba(74, 158, 255, 0.3);
  transition: all 0.2s ease;
}

/* 悬停态 */
.button:hover {
  box-shadow: 0 4px 12px rgba(74, 158, 255, 0.4);
  transform: translateY(-1px);
}

/* 激活态 */
.button:active {
  transform: translateY(0);
  box-shadow: 0 2px 6px rgba(74, 158, 255, 0.3);
}

/* 聚焦态 */
.button:focus-visible {
  outline: 2px solid #4a9eff;
  outline-offset: 2px;
}

/* 禁用态 */
.button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

### 输入框状态示例

```css
/* 默认态 */
.input {
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
}

/* 聚焦态 */
.input:focus-within {
  border-color: #4a9eff;
  box-shadow: 0 2px 12px rgba(74, 158, 255, 0.2);
  background: #2d2d2d;
}

/* 禁用态 */
.input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

---

## 八、布局规则 ⭐⭐⭐

### 整体布局

```
┌─────────────────────────────────────┐
│  Sidebar (280px)  │  Main Content   │
│                   │                 │
│  - Logo           │  - Header       │
│  - New Session    │  - Content Body │
│  - Session List   │  - Input Area   │
└─────────────────────────────────────┘
```

### 侧边栏规则

- **宽度**：280px（固定）
- **背景**：`bg-elevated` (#262626)
- **内边距**：20px（v4 优化：更宽松的呼吸空间）
- **右侧圆角**：`border-radius: 0 12px 12px 0`（关键：让侧边栏像"卡片"浮在主界面上）
- **右侧阴影**：`box-shadow: 2px 0 8px rgba(0,0,0,0.1)`（微妙的右侧阴影）

### 主内容区规则

- **背景**：`bg-base` (#1f1f1e)
- **左侧间距**：8px（v4 优化：与侧边栏留出间距，不贴边）
- **内边距**：顶部 32px，左右 32px（更多空气感）
- **最大宽度**：消息内容 720px（提高可读性）

### 响应式断点

| 设备 | 宽度范围 | 布局调整 |
|------|---------|---------|
| 桌面端 | > 1024px | 侧边栏 + 主内容 |
| 平板 | 768-1024px | 侧边栏可折叠 |
| 移动端 | < 768px | 侧边栏抽屉式 |

---

## 九、核心组件规范

### 1. 按钮（Button）

#### 主要按钮

```css
background: linear-gradient(135deg, #4a9eff 0%, #357abd 100%);
border: none;
color: #ffffff;
padding: 8px 18px;
border-radius: 7px;
font-size: 14px;
font-weight: 500;
box-shadow: 0 2px 6px rgba(74, 158, 255, 0.3);
```

#### 次要按钮

```css
background: #2f2f2f;
border: 1px solid #404040;
color: #e0e0e0;
padding: 10px 16px;
border-radius: 8px;
font-size: 14px;
box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
```

### 2. 输入框（Input）

#### 底部输入框（浮动感设计）

```css
/* 容器：不贴底部，留出间距 */
.input-container {
  padding: 16px 32px 20px;
  background: transparent;
}

/* 输入框包装器：强烈的浮动阴影 */
.input-wrapper {
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 12px;
  padding: 14px 18px;  /* v4 优化：更松弛 */
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);  /* 关键：浮动感 */
  transition: all 0.2s ease;
}

/* 聚焦态：阴影更强 */
.input-wrapper:focus-within {
  border-color: #4a9eff;
  box-shadow: 0 6px 20px rgba(74, 158, 255, 0.15), 0 4px 16px rgba(0, 0, 0, 0.25);
  background: #2d2d2d;
}

/* 输入框文字 */
.input-field {
  font-size: 15px;  /* v4 优化：更大的字号 */
  color: #e0e0e0;
}
```

### 3. 消息气泡（Message Bubble）

#### 助手消息

```css
background: #2a2a2a;
border: 1px solid #333333;
border-radius: 12px;
padding: 18px 20px;  /* v4 优化：上下增大，更方正 */
font-size: 15px;  /* v4 优化：更大的字号 */
line-height: 1.6;
box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);  /* v4 优化：更柔和 */
transition: all 0.2s ease;
```

**悬停态**：
```css
box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
border-color: #3a3a3a;
```

#### 用户消息

```css
background: #1e2936;
border: 1px solid #2a3a4a;
border-radius: 12px;
padding: 18px 20px;
font-size: 15px;
line-height: 1.6;
box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
```

### 4. 会话列表项（Session Item）

```css
padding: 10px 12px;
border-radius: 6px;
font-size: 14px;
font-weight: 400;  /* v4 优化：更轻的字重 */
color: #b0b0b0;
transition: all 0.15s ease;
```

#### 激活态

```css
background: #2f2f2f;
color: #ffffff;
font-weight: 500;  /* v4 优化：激活时稍重 */
box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);  /* v4 优化：更柔和 */
/* 左侧 accent 条 */
position: relative;
```

```css
/* 左侧指示条 */
.session-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 16px;
  background: #4a9eff;
  border-radius: 0 2px 2px 0;
}
```

### 5. 头像（Avatar）

```css
width: 32px;
height: 32px;
border-radius: 8px;
box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
```

---

## 十、动画与过渡

### 过渡时长

| 类型 | 时长 | 用途 |
|------|------|------|
| 快速 | 0.15s | 悬停态、小元素 |
| 标准 | 0.2s | 按钮、输入框 |
| 慢速 | 0.3s | 页面切换、大元素 |

### 缓动函数

```css
transition-timing-function: ease; /* 默认 */
```

### 常用过渡

```css
transition: all 0.2s ease;
```

---

## 十一、可访问性（Accessibility）

### 对比度要求

- **正文文字**：≥ 4.5:1（WCAG AA）
- **大号文字**：≥ 3:1
- **交互元素**：≥ 3:1

### 键盘导航

- 所有交互元素必须支持键盘操作
- 聚焦态必须有明显视觉反馈
- Tab 顺序符合逻辑

### 屏幕阅读器

- 使用语义化 HTML 标签
- 重要元素添加 `aria-label`
- 状态变化提供反馈

---

## 十二、AI 使用指南

### 命名规范

#### ✅ 好的命名（语义化）

```
bg-base              // 基础背景
text-primary         // 主要文字
accent-primary       // 主色调
spacing-4            // 中等间距（16px）
shadow-md            // 中等阴影
```

#### ❌ 差的命名（无意义）

```
color-1              // 不知道用在哪里
blue                 // 不知道是什么蓝
margin-20            // 不知道何时使用
```

### 使用场景说明模板

```markdown
## [变量名]

- **何时使用**：[具体场景]
- **何时不用**：[避免场景]
- **示例**：[代码示例]
- **对比度**：[如果是颜色，说明对比度]
```

### 组合规则

#### ✅ 允许的组合

- `bg-base` + `text-secondary`
- `bg-surface` + `border-default`
- `accent-primary` + `#ffffff`

#### ❌ 禁止的组合

- `bg-base` + `text-quaternary`（对比度不足）
- `accent-primary` + `accent-secondary`（色彩冲突）

---

## 十三、设计决策优先级

当规则冲突时的决策顺序：

1. **可访问性** > 美观性（确保所有人能用）
2. **一致性** > 创新性（保持风格统一）
3. **功能性** > 装饰性（先满足功能需求）
4. **简洁性** > 复杂性（能简单就不复杂）

---

## 十四、常见陷阱

### ❌ 避免的错误

1. **颜色过多**：超过 10 种颜色会导致混乱
2. **间距随意**：不遵循 8px 倍数关系
3. **状态缺失**：忘记定义禁用态、聚焦态
4. **对比度不足**：文字看不清
5. **命名混乱**：使用无意义命名
6. **过度设计**：为了"好看"牺牲可用性

### ✅ 成功的标志

1. **新增元素时不需要思考**：自动匹配现有风格
2. **AI 能理解规则**：命名清晰、场景明确
3. **用户感觉统一**：所有页面像同一个产品
4. **易于维护**：修改一处，全局生效

---

## 十五、设计资源

### 参考原型

- **v1 原型**：`_temp/agents-hub-prototype.html`
- **v2 原型**（修正版）：`_temp/agents-hub-prototype-v2.html`
- **v3 原型**（圆角+浮动感）：`_temp/agents-hub-prototype-v3.html`
- **v4 原型**（最终版，精细化调整）：`_temp/agents-hub-prototype-v4.html` ⭐

### 色值提取工具

- 使用浏览器开发者工具的取色器
- 参考 Claude Code Desktop 实际色值

### 设计检查清单

- [ ] 所有颜色对比度 ≥ 4.5:1
- [ ] 所有间距是 4 的倍数
- [ ] 所有交互元素有 5 种状态
- [ ] 所有变量使用语义化命名
- [ ] 所有组件有使用场景说明

---

## 十六、版本历史

### v1.1（2026-06-01）

**基于 v4 原型的精细化更新**

- **侧边栏圆角**：右侧圆角 `border-radius: 0 12px 12px 0`，让侧边栏像"卡片"浮在主界面上
- **输入框浮动感**：强阴影 `0 4px 16px rgba(0,0,0,0.25)` + 与底部留出间距
- **更柔和的阴影**：所有阴影减轻视觉重量，避免"廉价感"
- **增加空气感**：
  - 侧边栏内边距从 16px → 20px
  - 主内容区左侧留出 8px 间距
  - 消息气泡内边距从 16px 20px → 18px 20px（更方正）
- **字体大小调整**：
  - 消息正文和输入框从 14px → 15px
  - 页面标题字重从 600 → 700
  - 侧边栏列表项字重优化（默认 400，激活 500）

### v1.0（2026-06-01）

- 初始版本
- 基于 Claude Code Desktop 风格
- 定义核心色彩、字体、间距、圆角、阴影系统
- 定义核心组件规范
- 建立 AI 使用指南

---

**准备好后，开始使用这套设计系统构建 agents-hub 的前端界面！**
