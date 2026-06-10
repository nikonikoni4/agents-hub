# 新建对话弹窗设计优化方案

> **创建日期**：2026-06-10
> **版本**：v1.0
> **状态**：待评审
> **设计师**：UI设计师

---

## 一、当前设计问题分析

### 1.1 布局问题

| 问题 | 描述 | 影响 |
|------|------|------|
| **垂直间距不规整** | 各模块间距缺乏统一标准，Tab区与标签间距、输入框与下一标签间距存在明显差异 | 界面松散，缺乏精致感 |
| **Tab区域与标题栏边界模糊** | 选中的Tab背景与标题栏融合，无清晰区域分割 | 用户难以区分功能层级 |

### 1.2 视觉层次问题

| 问题 | 描述 | 影响 |
|------|------|------|
| **选中态反馈弱** | 单聊/群聊切换仅通过文字颜色区分，无背景差异化 | 用户无法快速识别当前模式 |
| **必填/可选项标识弱** | "Leader（必选）"仅用括号标注，与标签样式一致 | 用户容易忽略必填要求 |
| **创建按钮权重不足** | 浅灰色背景在白色弹窗中区分度低 | 削弱操作引导性 |
| **表单层级模糊** | 标签、输入框、角色标签字号差异过小 | 无法快速抓取信息优先级 |

### 1.3 交互体验问题

| 问题 | 描述 | 影响 |
|------|------|------|
| **交互状态缺失** | Tab切换、角色标签无明确交互反馈 | 用户无法判断可交互性 |
| **前置提示不足** | 必填项未填写时无视觉预警 | 增加操作成本与挫败感 |

---

## 二、设计优化方案

### 2.1 整体布局优化

#### 弹窗结构调整

```
┌─────────────────────────────────────────┐
│  新建对话                           ×   │  ← 标题栏：48px，bg-sidebar
├─────────────────────────────────────────┤
│  ┌─────────────────────────────────┐   │
│  │  单聊    │    群聊              │   │  ← Tab切换：40px，bg-bubble
│  └─────────────────────────────────┘   │
├─────────────────────────────────────────┤
│                                         │
│  [内容区域]                             │  ← 内容区：flex:1，padding: 24px
│                                         │
├─────────────────────────────────────────┤
│           取消        创建              │  ← 操作栏：56px，bg-sidebar
└─────────────────────────────────────────┘
```

#### 关键间距规范

| 元素 | 间距 | 说明 |
|------|------|------|
| 弹窗外边距 | 屏幕居中 | 距顶部20% |
| 标题栏高度 | 48px | 增加高度，增强存在感 |
| Tab切换区高度 | 40px | 独立区域，与标题栏区分 |
| 内容区内边距 | 24px | 保持呼吸感 |
| 表单项间距 | 20px | 统一垂直节奏 |
| 操作栏高度 | 56px | 独立区域，与内容区分隔 |

### 2.2 视觉层次优化

#### 2.2.1 Tab切换设计

**当前问题**：选中态仅文字颜色变化，反馈弱

**优化方案**：
```css
.modeSelector {
  display: flex;
  gap: 4px;
  padding: 4px;
  background: var(--bg-bubble);
  border-radius: 8px;
}

.modeBtn {
  flex: 1;
  padding: 10px 16px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.modeBtnActive {
  background: var(--bg-main);
  color: var(--text-primary);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
```

**改进点**：
- 选中态增加背景色和阴影，形成"浮起"效果
- 增加字重变化（500→600），强化视觉反馈
- 增加hover态，提升交互感知

#### 2.2.2 必填/可选项标识

**当前问题**：仅用括号标注，视觉权重低

**优化方案**：
```css
.fieldLabel {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.fieldLabel .required {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent-color);
  background: rgba(74, 158, 255, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.fieldLabel .optional {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-tertiary);
}
```

**改进点**：
- 必选项：蓝色标签，背景带浅蓝底色
- 可选项：灰色标签，降低视觉权重
- 标签独立于标题文字，更醒目

#### 2.2.3 创建按钮设计

**当前问题**：浅灰色背景，视觉区分度低

**优化方案**：
```css
.submitBtn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--accent-color);
  color: white;
  box-shadow: 0 2px 8px rgba(74, 158, 255, 0.3);
}

.submitBtn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(74, 158, 255, 0.4);
}

.submitBtn:active:not(:disabled) {
  transform: translateY(0);
}

.submitBtn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}
```

**改进点**：
- 使用强调色（accent-color）作为背景
- 增加阴影，形成"浮起"效果
- hover时增加上移动画，强化点击反馈
- disabled态降低透明度，移除阴影

#### 2.2.4 表单层级优化

**字体层级规范**：

| 元素 | 字号 | 字重 | 颜色 | 说明 |
|------|------|------|------|------|
| 标题 | 18px | 600 | text-primary | 最高优先级 |
| Tab文字 | 13px | 500/600 | text-secondary/primary | 选中态加粗 |
| 表单标签 | 14px | 500 | text-primary | 次高优先级 |
| 输入框文字 | 14px | 400 | text-primary | 正文级 |
| 角色标签 | 13px | 400 | text-primary | 辅助级 |
| 提示文字 | 12px | 400 | text-secondary | 最低优先级 |

### 2.3 交互体验优化

#### 2.3.1 输入框聚焦态

```css
.input {
  padding: 12px 14px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 14px;
  color: var(--text-primary);
  background: var(--bg-main);
  outline: none;
  transition: all 0.2s;
}

.input:focus {
  border-color: var(--accent-color);
  box-shadow: 0 0 0 3px rgba(74, 158, 255, 0.1);
}

.input::placeholder {
  color: var(--text-tertiary);
}
```

**改进点**：
- 聚焦时增加蓝色光晕（box-shadow）
- 增加圆角（6px→8px），更现代
- placeholder颜色降低对比度，减少干扰

#### 2.3.2 角色标签交互态

```css
.roleChip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-main);
}

.roleChip:hover {
  border-color: var(--accent-color);
  background: rgba(74, 158, 255, 0.05);
}

.roleChip.selected {
  border-color: var(--accent-color);
  background: var(--accent-color);
  color: white;
  box-shadow: 0 2px 8px rgba(74, 158, 255, 0.3);
}
```

**改进点**：
- hover时边框变蓝，背景带浅蓝底色
- 选中态增加阴影，强化"选中"感知
- 增加圆角（6px→8px），与整体风格统一

#### 2.3.3 必填项验证提示

**方案**：在标签旁显示验证状态图标

```tsx
// 在表单标签中添加验证状态
<label className={styles.fieldLabel}>
  群组名称
  {!name.trim() && <span className={styles.required}>*</span>}
</label>
```

```css
.required {
  color: var(--accent-color);
  font-weight: 600;
  margin-left: 4px;
}
```

**改进点**：
- 必填项未填写时，标签旁显示蓝色星号
- 用户可提前感知必填要求，减少操作失误

---

## 三、完整CSS变量参考

```css
:root {
  /* 弹窗专用变量 */
  --dialog-bg: var(--bg-main);
  --dialog-header-bg: var(--bg-sidebar);
  --dialog-header-height: 48px;
  --dialog-content-padding: 24px;
  --dialog-actions-bg: var(--bg-sidebar);
  --dialog-actions-height: 56px;
  
  /* Tab切换 */
  --tab-bg: var(--bg-bubble);
  --tab-active-bg: var(--bg-main);
  --tab-height: 40px;
  
  /* 表单元素 */
  --input-border-radius: 8px;
  --input-focus-shadow: 0 0 0 3px rgba(74, 158, 255, 0.1);
  --chip-border-radius: 8px;
  --chip-hover-border: var(--accent-color);
  
  /* 按钮 */
  --btn-primary-bg: var(--accent-color);
  --btn-primary-shadow: 0 2px 8px rgba(74, 158, 255, 0.3);
  --btn-primary-hover-shadow: 0 4px 12px rgba(74, 158, 255, 0.4);
}
```

---

## 四、实现优先级

| 优先级 | 优化项 | 预计工时 | 说明 |
|--------|--------|----------|------|
| P0 | Tab切换视觉反馈 | 0.5h | 核心交互，必须优化 |
| P0 | 创建按钮样式 | 0.5h | 核心操作，必须优化 |
| P0 | 必填/可选项标识 | 0.5h | 影响用户体验 |
| P1 | 输入框聚焦态 | 0.5h | 提升交互感知 |
| P1 | 角色标签交互态 | 0.5h | 提升交互感知 |
| P2 | 间距统一 | 1h | 提升精致感 |
| P2 | 字体层级优化 | 0.5h | 提升可读性 |

**总预计工时**：4h

---

## 五、设计参考

### 5.1 参考案例

| 案例 | 参考点 |
|------|--------|
| Cursor新建项目弹窗 | Tab切换样式、按钮设计 |
| Notion新建页面 | 表单布局、间距规范 |
| Linear创建任务 | 必填项标识、交互反馈 |

### 5.2 设计原则

1. **极简主义**：去除不必要的装饰，聚焦核心功能
2. **视觉层次**：通过字号、字重、颜色建立清晰的信息层级
3. **交互反馈**：每个可交互元素都有明确的状态变化
4. **一致性**：遵循项目设计系统（DESIGN.md）

---

## 六、验收标准

- [ ] Tab切换有明确的选中态（背景+阴影+字重）
- [ ] 必选项有醒目标识（蓝色标签）
- [ ] 创建按钮使用强调色，有阴影效果
- [ ] 输入框聚焦时有蓝色光晕
- [ ] 角色标签hover/选中态有明确反馈
- [ ] 间距统一，符合4px网格系统
- [ ] 支持浅色/深色主题
- [ ] 符合DESIGN.md设计规范

---

## 七、附录

### 7.1 相关文件

- 设计系统：`docs/DESIGN.md`
- 组件代码：`frontend/src/features/session/components/CreateGroupChatDialog.tsx`
- 样式文件：`frontend/src/features/session/components/CreateGroupChatDialog.module.css`

### 7.2 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-06-10 | v1.0 | 初始设计方案 |
