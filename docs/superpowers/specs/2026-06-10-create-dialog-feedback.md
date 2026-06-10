# 新建对话弹窗设计对比分析

> **创建日期**：2026-06-10
> **版本**：v1.0
> **状态**：待评审
> **设计师**：UI设计师

---

## 一、当前界面效果分析

### 1.1 群聊模式截图分析

**优点**：
- 布局结构清晰，垂直流式布局符合用户习惯
- 分区标题（"基本信息"、"配置成员"）建立了基本的信息层级
- 必填/可选项有文字标识

**问题**：
- Tab切换区与标题栏视觉边界模糊，选中态反馈弱
- 角色选择器为简单的标签列表，视觉层次扁平
- 必填/可选项仅用括号标注，视觉权重低
- 创建按钮样式普通，缺乏视觉引导力
- 整体间距不够统一，缺乏精致感

### 1.2 单聊模式截图分析

**优点**：
- 双层Tab切换（单聊/群聊 + 全新/群组）逻辑清晰
- Agent选择区使用卡片网格布局，比群聊模式更好
- 有"必选"标签提示

**问题**：
- 第一层Tab切换选中态不明显
- Agent卡片选中态反馈弱（仅边框变化）
- "对话名称"输入框样式普通
- 整体视觉层次仍需加强

---

## 二、HTML原型设计方案

### 2.1 核心改进点

| 维度 | 当前设计 | HTML原型设计 |
|------|----------|--------------|
| **标题栏** | 纯文字标题 | 蓝色图标 + 标题 + 副标题 |
| **Tab切换** | 纯文字，选中态弱 | 图标 + 文字 + 阴影效果 |
| **角色选择** | 标签列表 | 卡片网格布局 |
| **必填标识** | 括号标注 | 独立badge标签 |
| **表单分区** | 无明确分区 | form-section-title分区 |
| **输入框** | 基础样式 | 圆角10px + 聚焦光晕 |
| **按钮** | 普通样式 | 阴影 + hover动画 |
| **主题** | 无 | 支持浅色/深色双主题 |

---

## 三、差距分析与修改建议

### 3.1 P0 优先级（必须修改）

#### 3.1.1 Tab切换视觉反馈

**当前问题**：
- 选中态仅文字颜色变化，反馈弱
- 无图标，视觉引导不足

**HTML原型方案**：
```css
.mode-btn {
    padding: 12px 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
}

.mode-btn.active {
    background: var(--bg-main);
    font-weight: 600;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
```

**修改建议**：
- 为Tab按钮添加SVG图标
- 选中态增加背景色和阴影
- 字重从500增加到600

#### 3.1.2 角色选择器重构

**当前问题**：
- 群聊模式：简单的标签列表，视觉层次扁平
- 单聊模式：卡片网格但样式普通

**HTML原型方案**：
```css
.role-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 8px;
}

.role-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 16px 12px;
    border: 1px solid var(--border-color);
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s;
}

.role-card:hover {
    border-color: var(--accent-color);
    background: var(--accent-light);
    transform: translateY(-2px);
}

.role-card.selected {
    border-color: var(--accent-color);
    background: var(--accent-color);
    color: white;
    box-shadow: 0 4px 12px var(--accent-shadow);
}
```

**修改建议**：
- 群聊模式：将标签列表改为卡片网格
- 统一单聊和群聊的角色选择器样式
- 增加hover态（边框变蓝 + 上移2px）
- 增强选中态（蓝色背景 + 白色文字 + 阴影）

#### 3.1.3 必填/可选项标识

**当前问题**：
- 仅用括号标注（"必选"、"可选"）
- 与标签文字样式一致，视觉权重低

**HTML原型方案**：
```css
.field-badge {
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    line-height: 1.4;
}

.field-badge.required {
    background: var(--accent-light);
    color: var(--accent-color);
}

.field-badge.optional {
    background: var(--bg-shadow);
    color: var(--text-tertiary);
}
```

**修改建议**：
- 将括号标注改为独立badge标签
- 必选项：蓝色背景 + 蓝色文字
- 可选项：灰色背景 + 灰色文字
- 标签独立于标题文字，更醒目

#### 3.1.4 创建按钮优化

**当前问题**：
- 样式普通，缺乏视觉引导力
- 禁用态不明显

**HTML原型方案**：
```css
.submit-btn {
    background: var(--accent-color);
    color: white;
    box-shadow: 0 4px 12px var(--accent-shadow);
    min-width: 120px;
}

.submit-btn:hover:not(:disabled) {
    background: var(--accent-hover);
    transform: translateY(-1px);
    box-shadow: 0 6px 16px var(--accent-shadow);
}

.submit-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    box-shadow: none;
}
```

**修改建议**：
- 增加蓝色阴影效果
- hover时增加上移动画
- 增加最小宽度（120px）
- disabled态降低透明度，移除阴影

### 3.2 P1 优先级（建议修改）

#### 3.2.1 标题栏升级

**当前问题**：
- 纯文字标题，缺乏品牌感
- 无副标题引导

**HTML原型方案**：
```css
.header-icon {
    width: 36px;
    height: 36px;
    background: var(--accent-color);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
}

.header-subtitle {
    font-size: 13px;
    color: var(--text-secondary);
    margin-top: 2px;
}
```

**修改建议**：
- 左侧增加蓝色图标（accent-color）
- 增加副标题"选择对话模式并配置团队成员"
- 增强品牌感和引导性

#### 3.2.2 表单分区设计

**当前问题**：
- 表单项垂直堆砌，缺乏逻辑分组
- 信息层级不清晰

**HTML原型方案**：
```css
.form-section-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border-color);
}
```

**修改建议**：
- 使用form-section-title将表单分为多个逻辑区域
- 每个区域有标题（大写字母+间距）
- 区域间使用分隔线，增强结构感

#### 3.2.3 输入框增强

**当前问题**：
- 圆角较小（6px）
- 聚焦态仅有边框颜色变化

**HTML原型方案**：
```css
.input {
    padding: 12px 16px;
    border: 1px solid var(--border-color);
    border-radius: 10px;
    transition: all 0.2s;
}

.input:focus {
    border-color: var(--accent-color);
    box-shadow: 0 0 0 3px var(--accent-shadow);
}
```

**修改建议**：
- 圆角从6px增加到10px
- 聚焦态增加蓝色光晕（box-shadow）
- placeholder颜色降低对比度

#### 3.2.4 团队选择器

**当前问题**：
- 无团队快速选择功能
- 需要手动选择Leader和Workers

**HTML原型方案**：
```css
.team-chip {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
}

.team-chip:hover {
    border-color: var(--accent-color);
    background: var(--accent-light);
}

.team-chip.selected {
    border-color: var(--accent-color);
    background: var(--accent-color);
    color: white;
}
```

**修改建议**：
- 增加"快速选择团队"区域
- 使用chip标签样式
- 包含团队图标、名称、人数
- 选中态：蓝色背景 + 白色文字

### 3.3 P2 优先级（可选优化）

#### 3.3.1 主题切换支持

**当前问题**：
- 无主题切换功能
- 不支持深色模式

**HTML原型方案**：
- 右下角增加主题切换按钮
- 支持浅色/深色双主题
- 切换时图标变化（月亮/太阳）

**修改建议**：
- 实现CSS变量系统
- 添加主题切换按钮
- 支持浅色/深色双主题

#### 3.3.2 动画效果

**当前问题**：
- 无入场动画
- 交互反馈不够流畅

**HTML原型方案**：
```css
@keyframes dialog-in {
    from {
        opacity: 0;
        transform: scale(0.95) translateY(10px);
    }
    to {
        opacity: 1;
        transform: scale(1) translateY(0);
    }
}
```

**修改建议**：
- 弹窗增加入场动画（scale + translateY）
- 所有交互元素增加transition效果
- hover态增加轻微动画

#### 3.3.3 响应式设计

**当前问题**：
- 固定宽度，移动端体验差

**HTML原型方案**：
```css
@media (max-width: 640px) {
    .dialog {
        width: 100%;
        max-height: 90vh;
        border-radius: 12px;
    }

    .role-grid {
        grid-template-columns: repeat(2, 1fr);
    }

    .actions {
        flex-direction: column;
    }
}
```

**修改建议**：
- 移动端弹窗全宽显示
- 角色网格调整为2列
- 操作按钮改为垂直布局

---

## 四、实施优先级

| 优先级 | 优化项 | 预计工时 | 说明 |
|--------|--------|----------|------|
| **P0** | Tab切换视觉反馈 | 0.5h | 核心交互，必须优化 |
| **P0** | 角色选择器重构 | 1.5h | 核心功能，视觉提升大 |
| **P0** | 必填/可选项标识 | 0.5h | 影响用户体验 |
| **P0** | 创建按钮优化 | 0.5h | 核心操作，必须优化 |
| **P1** | 标题栏升级 | 0.5h | 增强品牌感 |
| **P1** | 表单分区设计 | 1h | 提升信息层级 |
| **P1** | 输入框增强 | 0.5h | 提升交互感知 |
| **P1** | 团队选择器 | 1h | 提升易用性 |
| **P2** | 主题切换支持 | 2h | 提升用户体验 |
| **P2** | 动画效果 | 1h | 提升精致感 |
| **P2** | 响应式设计 | 1.5h | 移动端适配 |

**总预计工时**：10.5h

---

## 五、验收标准

### 5.1 P0 验收标准

- [ ] Tab切换有明确的选中态（背景+阴影+字重）
- [ ] 角色选择器使用卡片网格布局
- [ ] 必选项有醒目标识（蓝色badge标签）
- [ ] 创建按钮使用强调色，有阴影效果
- [ ] 所有交互元素有hover态反馈

### 5.2 P1 验收标准

- [ ] 标题栏有蓝色图标和副标题
- [ ] 表单有明确的分区标题
- [ ] 输入框聚焦时有蓝色光晕
- [ ] 有团队快速选择功能

### 5.3 P2 验收标准

- [ ] 支持浅色/深色双主题
- [ ] 弹窗有入场动画
- [ ] 移动端有良好的响应式布局

---

## 六、相关文件

- HTML原型：`docs/superpowers/specs/2026-06-10-create-dialog-redesign-v2.html`
- 设计系统：`docs/DESIGN.md`
- 组件代码：`frontend/src/features/session/components/CreateGroupChatDialog.tsx`
- 样式文件：`frontend/src/features/session/components/CreateGroupChatDialog.module.css`

---

## 七、变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-06-10 | v1.0 | 初始对比分析 |
