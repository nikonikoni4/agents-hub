# 隐藏右侧栏网页预览的地球图标

- **日期**：2026-06-10
- **模块**：前端 - RightSidebar
- **影响范围**：网页预览功能
- **严重程度**：低（UI 问题）

## 问题描述

用户反馈右侧栏"网页" tab 中有一个大的地球图标，影响视觉体验，要求隐藏。

### 现象
- 右侧栏切换到"网页" tab 时，顶部显示一个地球图标 + "网页预览"文字
- 地球图标位于"网页预览"文字左侧，与文字在同一水平线上
- 下方显示提示文字"点击消息中的预览卡片查看网页"

### 用户期望
- 隐藏地球图标，只保留"网页预览"文字标题

## 根本原因

### 代码位置
- **文件**：`frontend/src/layouts/RightSidebar/RightSidebar.tsx`
- **行号**：第 322 行
- **组件**：`GlobeIcon` 组件在 `webPreviewHeader` 中渲染

### 代码结构
```tsx
{activeTab === 'web' && (
  <div className={styles.webPreviewPanel}>
    <div className={styles.webPreviewHeader}>
      <GlobeIcon />  // ← 这里渲染了地球图标
      <span>网页预览</span>
      {/* ... */}
    </div>
    {/* ... */}
  </div>
)}
```

### 相关组件
1. **GlobeIcon**（RightSidebar.tsx 第 76-84 行）
   - 定义在 RightSidebar.tsx 内部
   - SVG 图标，viewBox="0 0 24 24"
   - 用于网页预览 header 的标识

2. **webPreviewHeader**（RightSidebar.module.css 第 736-745 行）
   - 使用 flex 布局
   - font-size: 12px
   - 包含 GlobeIcon 和"网页预览"文字

3. **webPreviewEmpty**（RightSidebar.module.css 第 770-791 行）
   - 空状态容器
   - 只包含文字，无图标

## 修复方案

### 修改内容
**文件**：`frontend/src/layouts/RightSidebar/RightSidebar.tsx`

**修改前**：
```tsx
<div className={styles.webPreviewHeader}>
  <GlobeIcon />
  <span>网页预览</span>
</div>
```

**修改后**：
```tsx
<div className={styles.webPreviewHeader}>
  {/* <GlobeIcon /> */}
  <span>网页预览</span>
</div>
```

### 修改说明
- 注释掉 `<GlobeIcon />` 组件，而不是删除代码
- 保留 GlobeIcon 组件定义，以备后续可能需要
- 不影响其他使用 GlobeIcon 的地方（WebPreviewCard.tsx 中也有使用）

## 影响分析

### 直接影响
- 右侧栏"网页" tab 的 header 区域不再显示地球图标
- "网页预览"文字标题保持不变

### 间接影响
- 无。GlobeIcon 组件定义保留，WebPreviewCard 中的地球图标不受影响

### 相关文件
1. `frontend/src/layouts/RightSidebar/RightSidebar.tsx` - 主要修改文件
2. `frontend/src/layouts/RightSidebar/RightSidebar.module.css` - 样式文件（无需修改）
3. `frontend/src/shared/components/WebPreviewCard/WebPreviewCard.tsx` - 独立的 GlobeIcon 定义（不受影响）

## 验证方法

### 自动化验证
使用 Playwright 脚本验证：

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1400, 'height': 900})
    page.goto('http://localhost:5173')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(2000)

    # 点击"网页" tab
    web_tab = page.locator('button:has-text("网页")')
    if web_tab.count() > 0:
        web_tab.first.click()
        page.wait_for_timeout(500)

    # 检查 webPreviewHeader 中是否有 SVG 元素
    header = page.locator('[class*="webPreviewHeader"]')
    if header.count() > 0:
        svgs = header.first.locator('svg')
        assert svgs.count() == 0, "GlobeIcon should be hidden"

    browser.close()
```

### 手动验证
1. 启动前端开发服务器：`cd frontend && npm run dev`
2. 打开浏览器访问 `http://localhost:5173`
3. 切换到右侧栏的"网页" tab
4. 确认只显示"网页预览"文字，无地球图标

## 回归风险

### 低风险
- GlobeIcon 组件定义保留，不影响其他功能
- WebPreviewCard 中的地球图标独立定义，不受影响
- 修改只是注释掉一行代码，易于回滚

### 潜在问题
- 如果后续需要恢复地球图标，只需取消注释即可
- 不影响网页预览功能的正常使用

## 相关提交

- `ffe5aa6 fix:修复前端网页预览问题` - 最初实现网页预览功能
- `5f52a2d feat: 网页预览卡片全链路实现（后端+前端）` - 网页预览卡片功能实现

## 学习要点

1. **UI 修改要谨慎**：即使是简单的隐藏操作，也要考虑是否会影响其他功能
2. **注释优于删除**：保留代码以备后续可能需要
3. **验证要全面**：不仅要验证修改的功能，还要验证相关功能不受影响
4. **记录要详细**：便于后续维护和回归排查
