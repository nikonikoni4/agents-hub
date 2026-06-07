# Bug: 前端侧栏抽屉按钮失效 - 内联样式优先级覆盖 CSS 类

**日期**：2026-06-07
**状态**：已修复
**影响范围**：`LeftSidebar`, `RightSidebar`, 前端布局系统

## 问题描述

前端两个侧栏的抽屉按钮点击无响应：
1. **左侧栏抽屉按钮**：顶栏左边的按钮，原本可以收起/展开左侧会话列表栏
2. **右侧栏抽屉按钮**：聊天主界面右上方的按钮，原本可以收起/展开右侧栏

**用户观察到的现象**：
- 点击按钮后，DOM 元素的 CSS 类正确变化（`collapsed` 类被添加/移除）
- 但侧栏的视觉位置和宽度没有变化

**浏览器元素检查结果**：
```
# 右侧栏点击后
_rightSidebar_1mbam_1 _collapsed_1mbam_67 -> _rightSidebar_1mbam_1
（类变化正确，但宽度不变）

# 左侧栏点击后
_leftSidebar_bmn96_1 _collapsed_bmn96_12 -> _leftSidebar_bmn96_1
（类变化正确，但宽度不变）
```

## 根本原因

### 内联样式优先级问题

在 `LeftSidebar.tsx` 和 `RightSidebar.tsx` 组件中，宽度通过内联样式设置：

```typescript
// LeftSidebar.tsx:32-35
<div
  className={`${styles.leftSidebar} ${collapsed ? styles.collapsed : ''}`}
  style={{
    ...(width !== undefined ? { width: `${width}px` } : {}),
    ...(resizing ? { transition: 'none' } : {}),
  }}
>
```

**问题分析**：

1. CSS 类 `.leftSidebar.collapsed` 设置 `width: 0`
2. 但内联样式 `style={{ width: '220px' }}` 始终存在
3. **内联样式的优先级高于 CSS 类**
4. 结果：即使 `collapsed` 类被添加，`width: 0` 被内联样式的 `width: 220px` 覆盖

**CSS 样式定义**：
```css
/* LeftSidebar.module.css */
.leftSidebar {
  width: 220px;
  transition: width 0.3s ease;
}

.leftSidebar.collapsed {
  width: 0;
}

/* RightSidebar.module.css */
.rightSidebar {
  width: 220px;
  transition: width 0.3s ease;
}

.rightSidebar.collapsed {
  width: 0;
  box-shadow: none;
  padding: 0;
}
```

## 修复方案

### 修改内联样式逻辑

当 `collapsed` 为 `true` 时，内联宽度设置为 `0`，而不是使用传入的 `width` 值。

**文件 1**：`frontend/src/layouts/LeftSidebar/LeftSidebar.tsx`

```typescript
// 修复前
style={{
  ...(width !== undefined ? { width: `${width}px` } : {}),
  ...(resizing ? { transition: 'none' } : {}),
}}

// 修复后
style={{
  ...(collapsed ? { width: 0 } : width !== undefined ? { width: `${width}px` } : {}),
  ...(resizing ? { transition: 'none' } : {}),
}}
```

**文件 2**：`frontend/src/layouts/RightSidebar/RightSidebar.tsx`

```typescript
// 修复前
style={{
  ...(width !== undefined ? { width: `${width}px` } : {}),
  ...(resizing ? { transition: 'none' } : {}),
}}

// 修复后
style={{
  ...(collapsed ? { width: 0 } : width !== undefined ? { width: `${width}px` } : {}),
  ...(resizing ? { transition: 'none' } : {}),
}}
```

### 修复逻辑说明

```typescript
// 优先级判断：
// 1. 如果 collapsed 为 true -> width: 0（收起状态）
// 2. 否则如果 width 有值 -> 使用传入的宽度（用户拖拽调整的宽度）
// 3. 否则 -> 不设置内联宽度（使用 CSS 默认值 220px）
```

## 测试验证

### 测试脚本

使用 Playwright 编写自动化测试脚本：

```python
from playwright.sync_api import sync_playwright
import time

def test_sidebar_toggle():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        page.goto('http://localhost:5173')
        page.wait_for_load_state('networkidle')
        time.sleep(2)

        # 选择一个会话
        session_item = page.locator('[class*="sessionItem"]').first
        if session_item.count() > 0:
            session_item.click()
            time.sleep(1)

        # 获取左侧栏
        left_sidebar = page.locator('[class*="leftSidebar"]').first
        left_width = left_sidebar.evaluate('el => el.offsetWidth')

        # 点击左侧栏切换按钮
        toggle_left_btn = page.locator('button[aria-label*="侧栏"]').first
        toggle_left_btn.click()
        time.sleep(0.5)

        left_width_after = left_sidebar.evaluate('el => el.offsetWidth')
        assert left_width_after == 0, f"左侧栏收起失败: {left_width_after}px"

        # 再次点击展开
        toggle_left_btn.click()
        time.sleep(0.5)

        left_width_expanded = left_sidebar.evaluate('el => el.offsetWidth')
        assert left_width_expanded > 0, f"左侧栏展开失败: {left_width_expanded}px"

        # 测试右侧栏
        right_sidebar = page.locator('[class*="rightSidebar"]').first
        toggle_right_btn = page.locator('button[aria-label="切换右侧栏"]').first
        toggle_right_btn.click()
        time.sleep(0.5)

        right_width_after = right_sidebar.evaluate('el => el.offsetWidth')
        assert right_width_after == 0, f"右侧栏收起失败: {right_width_after}px"

        toggle_right_btn.click()
        time.sleep(0.5)

        right_width_expanded = right_sidebar.evaluate('el => el.offsetWidth')
        assert right_width_expanded > 0, f"右侧栏展开失败: {right_width_expanded}px"

        print("✓ 所有测试通过")
        browser.close()
```

### 测试结果

```
初始状态: 左侧栏 220px, 右侧栏 220px

--- 测试左侧栏收起 ---
点击后左侧栏: class=_leftSidebar_bmn96_1 _collapsed_bmn96_12, width=0px
✓ 左侧栏收起成功
再次点击后左侧栏: class=_leftSidebar_bmn96_1 , width=220px
✓ 左侧栏展开成功

--- 测试右侧栏收起 ---
点击后右侧栏: class=_rightSidebar_1mbam_1 _collapsed_1mbam_67, width=0px
✓ 右侧栏收起成功
再次点击后右侧栏: class=_rightSidebar_1mbam_1 , width=220px
✓ 右侧栏展开成功
```

## 影响

### 修复前
- 侧栏抽屉按钮点击无响应
- 用户无法收起/展开侧栏
- 界面布局固定，无法根据需要调整

### 修复后
- 侧栏抽屉按钮正常工作
- 用户可以自由收起/展开左侧栏和右侧栏
- 侧栏宽度可以拖拽调整（160-400px 范围内）
- 收起/展开动画平滑（0.3s ease）

## 相关文件

- `frontend/src/layouts/LeftSidebar/LeftSidebar.tsx`
- `frontend/src/layouts/RightSidebar/RightSidebar.tsx`
- `frontend/src/layouts/LeftSidebar/LeftSidebar.module.css`
- `frontend/src/layouts/RightSidebar/RightSidebar.module.css`
- `frontend/src/layouts/MainLayout/MainLayout.tsx`

## 经验教训

1. **内联样式优先级高于 CSS 类**：当需要通过 CSS 类控制样式时，避免同时设置冲突的内联样式
2. **状态驱动的样式应该在状态变化时更新**：当组件有 `collapsed` 等状态时，内联样式应该根据状态动态调整
3. **CSS Modules 的类名会被编译**：浏览器中看到的 `_leftSidebar_xxxxx` 是 CSS Modules 编译后的类名，源码中是 `.leftSidebar`
4. **测试要覆盖交互场景**：不仅要测试静态样式，还要测试用户交互（点击、拖拽）后的样式变化
