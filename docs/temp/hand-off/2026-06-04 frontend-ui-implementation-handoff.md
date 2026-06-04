# Agents Hub v2.0 前端UI实现 - 交接文档

**日期**: 2026-06-04  
**原始分支**: refactor_core (错误)  
**目标分支**: claude/vibrant-nightingale-e053eb (正确)  
**状态**: 需要在正确的 worktree 中重新实施

---

## 背景

用户要求依据 `docs/DESIGN.md` 和参考文件 `agents-hub-new-style.html` 设计前端UI界面。当前实现在错误的分支（refactor_core）中进行，需要在正确的 worktree（vibrant-nightingale-e053eb）中重新实施。

**关键参考文件位置**:
```
D:\desktop\软件开发\agents-hub\.claude\worktrees\vibrant-nightingale-e053eb\_temp\agents-hub-new-style.html
```

---

## 已完成的工作（在错误分支）

### Phase 1.1: 环境搭建 ✅

**已完成操作**:
1. 创建 `frontend/` 目录
2. 使用 Vite 初始化 React + TypeScript 项目
3. 安装依赖：`zustand`, `react-router-dom`, `@types/node`
4. 配置路径别名 `@/` → `src/`
5. 开发服务器成功启动

**关键配置文件**:

**vite.config.ts**:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

**tsconfig.app.json** (需添加路径别名):
```json
{
  "compilerOptions": {
    // ... 其他配置
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

---

### Phase 1.2: 主题系统实现 ✅

**目录结构**:
```
frontend/src/
├── styles/
│   ├── theme.css       # CSS Variables 主题定义
│   ├── reset.css       # CSS Reset
│   └── global.css      # 全局样式
├── core/
│   └── theme/
│       └── ThemeManager.ts  # 主题管理器
└── shared/
    └── types/
        └── theme.ts    # 类型定义
```

**关键文件内容**:

**src/styles/theme.css**:
```css
:root {
  /* 浅色主题 */
  --bg-sidebar: rgb(246, 246, 246);
  --bg-shadow: rgb(234, 234, 234);
  --bg-main: rgb(255, 255, 255);
  --bg-bubble: rgb(246, 246, 246);
  --bg-right-base: rgb(255, 255, 255);
  --bg-right-module: rgb(246, 246, 246);
  --bg-right-shadow: rgb(233, 234, 234);
  --bg-input: rgb(255, 255, 255);

  --text-primary: rgb(30, 30, 30);
  --text-secondary: rgb(100, 100, 100);
  --text-tertiary: rgb(150, 150, 150);
  --border-color: rgb(220, 220, 220);
  --accent-color: rgb(74, 158, 255);

  /* 圆角系统 */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --radius-xl: 12px;
  --radius-2xl: 16px;

  /* 间距系统 (4px 倍数) */
  --spacing-1: 4px;
  --spacing-2: 8px;
  --spacing-3: 12px;
  --spacing-4: 16px;
  --spacing-6: 24px;
}

html[data-theme="dark"] {
  /* 深色主题 */
  --bg-sidebar: rgb(20, 20, 20);
  --bg-shadow: rgb(38, 38, 38);
  --bg-main: rgb(24, 24, 24);
  --bg-bubble: rgb(20, 20, 20);
  --bg-right-base: rgb(24, 24, 24);
  --bg-right-module: rgb(20, 20, 20);
  --bg-right-shadow: rgb(36, 36, 36);
  --bg-input: rgb(45, 45, 45);

  --text-primary: rgb(230, 230, 230);
  --text-secondary: rgb(180, 180, 180);
  --text-tertiary: rgb(120, 120, 120);
  --border-color: rgb(60, 60, 60);
}
```

**src/styles/reset.css**:
```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html,
body {
  height: 100%;
  overflow: hidden;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

button {
  border: none;
  background: none;
  cursor: pointer;
  font-family: inherit;
}

input,
textarea {
  font-family: inherit;
}

a {
  text-decoration: none;
  color: inherit;
}
```

**src/styles/global.css**:
```css
body {
  background: var(--bg-sidebar);
  color: var(--text-primary);
}

/* 滚动条样式 */
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

/* 过渡动画 */
* {
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}
```

**src/core/theme/ThemeManager.ts**:
```typescript
export type Theme = 'light' | 'dark';

export class ThemeManager {
  private static instance: ThemeManager;
  private currentTheme: Theme;

  private constructor() {
    this.currentTheme = this.loadTheme();
    this.applyTheme(this.currentTheme);
  }

  public static getInstance(): ThemeManager {
    if (!ThemeManager.instance) {
      ThemeManager.instance = new ThemeManager();
    }
    return ThemeManager.instance;
  }

  private loadTheme(): Theme {
    const saved = localStorage.getItem('theme');
    if (saved === 'dark' || saved === 'light') {
      return saved;
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  private applyTheme(theme: Theme): void {
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
  }

  public getTheme(): Theme {
    return this.currentTheme;
  }

  public setTheme(theme: Theme): void {
    this.currentTheme = theme;
    this.applyTheme(theme);
    localStorage.setItem('theme', theme);
  }

  public toggleTheme(): void {
    const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
    this.setTheme(newTheme);
  }

  public watchSystemTheme(callback: (theme: Theme) => void): () => void {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e: MediaQueryListEvent) => {
      const theme = e.matches ? 'dark' : 'light';
      callback(theme);
    };
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }
}
```

**src/shared/types/theme.ts**:
```typescript
export type Theme = 'light' | 'dark';

export interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}
```

**src/main.tsx**:
```typescript
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import { ThemeManager } from '@/core/theme/ThemeManager'

// 引入样式
import '@/styles/reset.css'
import '@/styles/theme.css'
import '@/styles/global.css'

// 初始化主题管理器
ThemeManager.getInstance();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

**src/App.tsx** (演示页面):
```typescript
import { useState, useEffect } from 'react'
import { ThemeManager } from '@/core/theme/ThemeManager'
import type { Theme } from '@/shared/types/theme'

function App() {
  const [theme, setTheme] = useState<Theme>(() => ThemeManager.getInstance().getTheme());

  const handleToggleTheme = () => {
    ThemeManager.getInstance().toggleTheme();
    setTheme(ThemeManager.getInstance().getTheme());
  };

  useEffect(() => {
    const unwatch = ThemeManager.getInstance().watchSystemTheme((newTheme) => {
      setTheme(newTheme);
    });
    return unwatch;
  }, []);

  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexDirection: 'column',
      gap: '24px',
      background: 'var(--bg-main)',
      color: 'var(--text-primary)',
    }}>
      <h1 style={{ fontSize: '32px', fontWeight: 600 }}>
        Agents Hub v2.0
      </h1>
      <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
        当前主题：{theme === 'light' ? '浅色' : '深色'}
      </p>
      <button
        onClick={handleToggleTheme}
        style={{
          padding: '12px 24px',
          background: 'var(--accent-color)',
          color: 'white',
          borderRadius: 'var(--radius-md)',
          fontSize: '14px',
          fontWeight: 500,
          cursor: 'pointer',
        }}
      >
        切换主题
      </button>
      <div style={{
        marginTop: '48px',
        padding: '24px',
        background: 'var(--bg-sidebar)',
        borderRadius: 'var(--radius-xl)',
        maxWidth: '600px',
      }}>
        <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '16px' }}>
          设计系统测试
        </h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{
            padding: '16px',
            background: 'var(--bg-bubble)',
            borderRadius: 'var(--radius-2xl)',
            fontSize: '14px',
          }}>
            消息气泡样式 (16px 圆角)
          </div>
          <div style={{
            padding: '12px 16px',
            background: 'var(--bg-input)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-2xl)',
            fontSize: '14px',
          }}>
            输入框样式 (16px 圆角)
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
```

---

### Phase 1.3: 基础组件库 (部分完成)

**已创建的文件**:

**src/shared/components/Button/Button.module.css**:
```css
.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: none;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s ease;
}

.button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.topBar {
  width: 32px;
  height: 28px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: transparent;
}

.topBar:hover:not(:disabled) {
  background: var(--bg-shadow);
}

.sidebar {
  padding: 8px 12px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  background: transparent;
}

.sidebar:hover:not(:disabled) {
  background: var(--bg-shadow);
}

.icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: transparent;
}

.icon:hover:not(:disabled) {
  background: var(--bg-shadow);
}

.primary {
  padding: 8px 16px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  color: white;
  background: var(--accent-color);
}

.primary:hover:not(:disabled) {
  opacity: 0.9;
}
```

**src/shared/components/Button/Button.tsx**:
```typescript
import { ButtonHTMLAttributes, ReactNode } from 'react';
import styles from './Button.module.css';

export type ButtonVariant = 'topBar' | 'sidebar' | 'icon' | 'primary';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  children?: ReactNode;
}

export function Button({
  variant = 'primary',
  children,
  className = '',
  ...props
}: ButtonProps) {
  return (
    <button
      className={`${styles.button} ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
```

---

## 下一步操作指南

### 1. 切换到正确的 Worktree

```bash
cd D:\desktop\软件开发\agents-hub\.claude\worktrees\vibrant-nightingale-e053eb
```

### 2. 重新执行 Phase 1.1 和 1.2

**按照上面的配置和代码，依次创建**:
1. 初始化 Vite 项目
2. 安装依赖
3. 配置路径别名
4. 创建主题系统文件
5. 测试主题切换功能

### 3. 继续 Phase 1.3 和 1.4

**Phase 1.3 剩余任务**:
- [ ] 完成 Icon 组件（封装 SVG）
- [ ] 完成 Input 组件（搜索框样式）

**Phase 1.4 任务**:
- [ ] 创建 MainLayout 组件
- [ ] 创建 TopBar 组件（40px 高度）
- [ ] 创建 LeftSidebar 组件（280px 宽度，收起动画）
- [ ] 创建 ChatArea 组件（**关键：12px 左圆角**）
- [ ] 创建 RightSidebar 组件（320px 宽度，收起动画）

---

## 关键设计约束（必须遵守）

1. **主对话区左侧圆角（12px）**：`border-radius: 12px 0 0 12px;`
2. **消息气泡和输入框圆角（16px）**：`border-radius: 16px;`
3. **所有颜色使用 CSS Variables**：无硬编码
4. **间距为 4px 的倍数**
5. **侧边栏收起动画**：`transition: width 0.3s, margin-left 0.3s;`

---

## 完整实施计划

详细计划已保存在：
```
C:\Users\15535\.claude\plans\docs-design-md-temp-agents-hub-new-styl-eager-axolotl.md
```

请参考该计划文件获取完整的实施步骤、验证标准和预期时间。

---

## 验证清单

在正确的 worktree 中完成后，确保：
- [ ] 双主题切换正常
- [ ] 所有颜色值与 DESIGN.md 一致
- [ ] 主对话区左侧圆角清晰可见（12px）
- [ ] 开发服务器正常运行
- [ ] 路径别名 `@/` 正常工作

---

## 注意事项

1. 所有操作必须在 `vibrant-nightingale-e053eb` worktree 中进行
2. 参考文件路径已更新为 worktree 内的路径
3. 遵守 SSOT、DRY、SRP 原则
4. CSS Variables 只定义一次，其他地方只引用
