# Chat Markdown Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为聊天消息添加 Markdown 渲染和代码语法高亮能力。

**Architecture:** 在 `shared/components/` 下新建 `MarkdownRenderer` 通用组件，封装 react-markdown + rehype-highlight，然后在 `ChatArea` 的 `MessageBubble` 中集成。

**Tech Stack:** react-markdown, rehype-highlight, highlight.js

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `frontend/src/shared/components/MarkdownRenderer/MarkdownRenderer.tsx` | Markdown 渲染组件 |
| Create | `frontend/src/shared/components/MarkdownRenderer/MarkdownRenderer.module.css` | Markdown 内容样式 |
| Create | `frontend/src/shared/components/MarkdownRenderer/index.ts` | Barrel export |
| Modify | `frontend/src/shared/components/index.ts:1` | 添加 MarkdownRenderer 导出 |
| Modify | `frontend/src/layouts/ChatArea/ChatArea.tsx:35` | 气泡内使用 MarkdownRenderer |
| Modify | `frontend/src/layouts/ChatArea/ChatArea.module.css:104-115` | 调整气泡内 Markdown 元素样式 |

---

### Task 1: 安装依赖

- [ ] **Step 1: 安装三个包**

Run:
```bash
cd frontend && pnpm add react-markdown rehype-highlight highlight.js
```

- [ ] **Step 2: 验证安装**

Run:
```bash
cd frontend && pnpm ls react-markdown rehype-highlight highlight.js
```
Expected: 三个包都有版本号，无报错。

---

### Task 2: 创建 MarkdownRenderer 组件

- [ ] **Step 1: 创建组件文件**

Create `frontend/src/shared/components/MarkdownRenderer/MarkdownRenderer.tsx`:
```tsx
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';
import styles from './MarkdownRenderer.module.css';

interface MarkdownRendererProps {
  content: string;
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div className={styles.markdown}>
      <ReactMarkdown rehypePlugins={[rehypeHighlight]}>{content}</ReactMarkdown>
    </div>
  );
}
```

- [ ] **Step 2: 创建样式文件**

Create `frontend/src/shared/components/MarkdownRenderer/MarkdownRenderer.module.css`:
```css
.markdown p {
  margin: 0;
}

.markdown p + p {
  margin-top: 8px;
}

.markdown pre {
  margin: 8px 0;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.5;
}

.markdown code {
  font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
  font-size: 13px;
}

.markdown :not(pre) > code {
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.06);
}

.markdown ul,
.markdown ol {
  margin: 4px 0;
  padding-left: 20px;
}

.markdown li {
  margin: 2px 0;
}

.markdown blockquote {
  margin: 8px 0;
  padding: 4px 12px;
  border-left: 3px solid var(--accent-color, #8BA5BF);
  color: var(--text-secondary, #666);
}

.markdown table {
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 13px;
}

.markdown th,
.markdown td {
  border: 1px solid var(--border-color, #ddd);
  padding: 6px 10px;
  text-align: left;
}

.markdown th {
  background: var(--bg-bubble, #f8f8f8);
  font-weight: 600;
}

.markdown h1,
.markdown h2,
.markdown h3,
.markdown h4 {
  margin: 8px 0 4px;
  font-weight: 600;
}

.markdown h1 { font-size: 18px; }
.markdown h2 { font-size: 16px; }
.markdown h3 { font-size: 15px; }
.markdown h4 { font-size: 14px; }

.markdown hr {
  border: none;
  border-top: 1px solid var(--border-color, #ddd);
  margin: 8px 0;
}

.markdown a {
  color: var(--accent-color, #8BA5BF);
  text-decoration: none;
}

.markdown a:hover {
  text-decoration: underline;
}
```

- [ ] **Step 3: 创建 barrel export**

Create `frontend/src/shared/components/MarkdownRenderer/index.ts`:
```ts
export { MarkdownRenderer } from './MarkdownRenderer';
```

- [ ] **Step 4: 添加到 shared 导出**

Modify `frontend/src/shared/components/index.ts` — 在末尾追加一行:
```ts
export * from './MarkdownRenderer';
```

- [ ] **Step 5: 验证类型检查**

Run:
```bash
cd frontend && pnpm run type-check
```
Expected: 无报错。

---

### Task 3: 集成到 ChatArea

- [ ] **Step 1: 修改 MessageBubble 使用 MarkdownRenderer**

Modify `frontend/src/layouts/ChatArea/ChatArea.tsx`:

1. 添加导入（第 9 行 Icon 导入之后）:
```tsx
import { MarkdownRenderer } from '@/shared/components';
```

2. 将第 35-37 行:
```tsx
      <div className={`${styles.messageBubble} ${isUser ? styles.bubbleUser : styles.bubbleAgent}`}>
        <p>{msg.content}</p>
      </div>
```

替换为:
```tsx
      <div className={`${styles.messageBubble} ${isUser ? styles.bubbleUser : styles.bubbleAgent}`}>
        <MarkdownRenderer content={msg.content} />
      </div>
```

- [ ] **Step 2: 调整气泡 CSS 兼容 Markdown 内容**

Modify `frontend/src/layouts/ChatArea/ChatArea.module.css`:

将第 113-115 行:
```css
.messageBubble p {
  margin: 0;
}
```

替换为:
```css
.messageBubble p {
  margin: 0;
}

/* 用户气泡内的 Markdown 代码块适配深色文字 */
.bubbleUser pre {
  background: rgba(0, 0, 0, 0.15);
}

.bubbleUser :not(pre) > code {
  background: rgba(0, 0, 0, 0.12);
}

.bubbleUser a {
  color: #fff;
  text-decoration: underline;
}
```

- [ ] **Step 3: 验证类型检查**

Run:
```bash
cd frontend && pnpm run type-check
```
Expected: 无报错。

- [ ] **Step 4: 启动开发服务器验证效果**

Run:
```bash
cd frontend && pnpm run dev
```
Expected: 页面正常加载，发送包含 Markdown 格式的消息（如 `**粗体**`、代码块）应正确渲染。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/shared/components/MarkdownRenderer/ frontend/src/shared/components/index.ts frontend/src/layouts/ChatArea/ChatArea.tsx frontend/src/layouts/ChatArea/ChatArea.module.css frontend/pnpm-lock.yaml
git commit -m "feat: add Markdown rendering to chat messages with syntax highlighting"
```
