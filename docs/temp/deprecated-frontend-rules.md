---
title: 前端编码规则
created_at: 2026-06-02
updated_at: 2026-06-02
trigger: 前端性能优化、新增功能模块、架构深入理解
---
deprecated-reason : ai把规则当作技术手册和说明了


# 前端编码规则

## 触发场景

**何时阅读本文档**：
- ✅ 需要进行性能优化（长列表卡顿、渲染慢、内存占用高）
- ✅ 添加新的 feature 模块（不确定标准流程）
- ✅ 需要深入理解前端架构设计原理
- ✅ 新人入门，需要了解项目整体架构

**日常编码不需要阅读本文档**，请直接查看 `frontend/CLAUDE.md`

---

## 项目概述

agents-hub 前端是一个基于 React + Electron 的桌面应用，采用**分层 + 按功能模块化**的架构。

### 技术栈

| 层面 | 技术选择 | 说明 |
|------|---------|------|
| **框架** | React 18+ | UI 框架 |
| **桌面端** | Electron | 跨平台桌面应用 |
| **状态管理** | Zustand | 轻量、模块化切片，支持 persist/devtools 中间件 |
| **路由** | React Router v6 | 支持嵌套路由，为多视图切换做准备 |
| **样式** | Tailwind CSS + CSS Modules | Tailwind 快速开发，CSS Modules 处理复杂组件样式隔离 |
| **Markdown** | react-markdown + rehype-highlight | 轻量、可扩展、支持代码高亮 |
| **虚拟滚动** | @tanstack/react-virtual | 高性能虚拟滚动 |
| **代码编辑器** | Monaco Editor | 用于预览/编辑代码 |
| **Diff 视图** | react-diff-view | 专业 diff 渲染（side-by-side / unified） |
| **打包** | Vite + Electron | 快速构建 |

### 架构设计原理

采用 **分层 + 按功能模块化** 的组织方式：

- **core/**：业务无关的核心层（WebSocket、API、Storage），可被任意 feature 复用
- **features/**：按业务领域划分的独立功能模块，每个模块自带 components/hooks/store
- **shared/**：跨 feature 复用的通用资源（按钮、输入框、工具函数等）
- **layouts/**：页面级布局组件

**模块隔离原则**：
- features 之间不直接相互依赖，通过 core 层或 shared 层通信
- 每个 feature 内部自治：UI、状态、副作用都封装在模块内
- 新增功能（预览/Diff/任务管理）只需新增 feature 模块，无需改动现有代码

**为什么这样设计**：
- ✅ **可扩展性**：新增功能只需添加 feature 模块，不影响现有代码
- ✅ **可维护性**：每个模块职责清晰，修改不会产生连锁反应
- ✅ **可测试性**：模块独立，可以单独测试
- ✅ **布局灵活性**：feature 组件位置无关，可以在任意布局中复用（支持三栏、四栏、分屏等布局）

---

## 性能优化规则

### 触发场景
- 长消息列表渲染卡顿
- Markdown 渲染慢
- WebSocket 高频消息导致界面卡顿
- 代码高亮耗时长
- 文件预览加载慢

### 优化策略

#### 1. 长列表使用虚拟滚动

**触发条件**：列表项超过 50 条

**实现方式**：
```typescript
import { useVirtualizer } from '@tanstack/react-virtual';

function MessageList({ messages }: { messages: Message[] }) {
  const parentRef = useRef<HTMLDivElement>(null);
  
  const virtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 80, // 预估每项高度
    overscan: 5, // 预渲染 5 项
  });
  
  return (
    <div ref={parentRef} style={{ height: '600px', overflow: 'auto' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={virtualItem.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              transform: `translateY(${virtualItem.start}px)`,
            }}
          >
            <MessageItem message={messages[virtualItem.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

**注意事项**：
- 必须设置固定高度的容器
- `estimateSize` 应该接近实际高度，避免滚动跳动
- `overscan` 控制预渲染数量，平衡性能和用户体验

---

#### 2. 历史消息分页加载

**触发条件**：消息总数超过 100 条

**实现方式**：
```typescript
function useMessages() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  
  const loadMore = useCallback(async () => {
    if (!hasMore) return;
    
    const newMessages = await api.getMessages({ page, limit: 50 });
    setMessages((prev) => [...newMessages, ...prev]); // 旧消息在前
    setHasMore(newMessages.length === 50);
    setPage((p) => p + 1);
  }, [page, hasMore]);
  
  // 滚动到顶部触发加载
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop } = e.currentTarget;
    if (scrollTop === 0 && hasMore) {
      loadMore();
    }
  }, [hasMore, loadMore]);
  
  return { messages, loadMore, handleScroll };
}
```

---

#### 3. Markdown 渲染优化

**触发条件**：Markdown 内容超过 1000 字符

**实现方式**：
```typescript
import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';

// 使用 React.memo 避免不必要的重渲染
const MarkdownRenderer = React.memo(({ content }: { content: string }) => {
  // 使用 useMemo 缓存渲染结果
  const renderedContent = useMemo(() => (
    <ReactMarkdown rehypePlugins={[rehypeHighlight]}>
      {content}
    </ReactMarkdown>
  ), [content]);
  
  return <div className="markdown-body">{renderedContent}</div>;
});

MarkdownRenderer.displayName = 'MarkdownRenderer';
```

**注意事项**：
- 必须使用 `React.memo` 包裹组件
- `useMemo` 的依赖项只包含 `content`
- 避免在 Markdown 组件内部使用频繁变化的 props

---

#### 4. WebSocket 高频消息节流

**触发条件**：WebSocket 消息频率超过 10 条/秒

**实现方式**：
```typescript
import { useCallback } from 'react';
import { throttle } from 'lodash-es';

function useWebSocketMessages() {
  const store = useChatStore();
  
  // 使用 requestAnimationFrame 批量更新
  const throttledUpdate = useCallback(
    throttle((messages: Message[]) => {
      requestAnimationFrame(() => {
        store.addMessages(messages);
      });
    }, 100), // 100ms 批量更新一次
    [store]
  );
  
  useEffect(() => {
    const buffer: Message[] = [];
    
    const handleMessage = (msg: Message) => {
      buffer.push(msg);
      throttledUpdate(buffer.splice(0)); // 清空 buffer 并更新
    };
    
    wsManager.on('message', handleMessage);
    return () => wsManager.off('message', handleMessage);
  }, [throttledUpdate]);
}
```

**注意事项**：
- 使用 `requestAnimationFrame` 确保在浏览器重绘前更新
- 节流间隔根据实际情况调整（建议 100-200ms）
- 必须清空 buffer，避免内存泄漏

---

#### 5. 代码高亮异步处理

**触发条件**：代码块超过 500 行

**实现方式**：
```typescript
import { useEffect, useState } from 'react';

function CodeBlock({ code, language }: { code: string; language: string }) {
  const [highlighted, setHighlighted] = useState<string>('');
  
  useEffect(() => {
    // 使用 Web Worker 异步高亮
    const worker = new Worker('/workers/highlight.worker.js');
    
    worker.postMessage({ code, language });
    worker.onmessage = (e) => {
      setHighlighted(e.data.highlighted);
    };
    
    return () => worker.terminate();
  }, [code, language]);
  
  if (!highlighted) {
    return <pre><code>{code}</code></pre>; // 显示原始代码
  }
  
  return <pre dangerouslySetInnerHTML={{ __html: highlighted }} />;
}
```

**Web Worker 实现**（`public/workers/highlight.worker.js`）：
```javascript
importScripts('https://cdn.jsdelivr.net/npm/highlight.js@11/lib/core.min.js');

self.onmessage = (e) => {
  const { code, language } = e.data;
  const highlighted = hljs.highlight(code, { language }).value;
  self.postMessage({ highlighted });
};
```

---

#### 6. 文件预览懒加载

**触发条件**：预览面板包含多个文件

**实现方式**：
```typescript
import { lazy, Suspense } from 'react';

// 懒加载预览组件
const MonacoEditor = lazy(() => import('@monaco-editor/react'));
const PDFViewer = lazy(() => import('./PDFViewer'));
const ImageViewer = lazy(() => import('./ImageViewer'));

function FilePreview({ file }: { file: File }) {
  const getViewer = () => {
    if (file.type.startsWith('image/')) {
      return <ImageViewer src={file.url} />;
    }
    if (file.type === 'application/pdf') {
      return <PDFViewer src={file.url} />;
    }
    return <MonacoEditor value={file.content} language={file.language} />;
  };
  
  return (
    <Suspense fallback={<div>加载中...</div>}>
      {getViewer()}
    </Suspense>
  );
}
```

**注意事项**：
- 使用 `React.lazy` 动态导入组件
- 必须使用 `Suspense` 包裹，提供 fallback UI
- 避免在循环中使用 `lazy`，应该在模块顶层定义

---

## 新增功能指南

### 触发场景
- 需要添加新的业务功能模块（如预览、Diff、任务管理）
- 不确定如何组织代码结构
- 需要标准化的开发流程

### 添加新功能模块的标准流程

#### 步骤 1：确定是否需要新 feature

**判断标准**：
- ✅ 创建新 feature：独立的业务功能，有自己的 UI、状态、交互逻辑
- ❌ 放在现有 feature：现有功能的扩展或变体

**示例**：
- "单聊功能" → 可以复用 `features/chat/`（通过 props 区分群聊/单聊）
- "消息搜索" → 创建新 feature `features/search/`（独立的搜索 UI 和逻辑）
- "预览功能" → 创建新 feature `features/preview/`（独立的预览面板）

---

#### 步骤 2：创建目录结构

```bash
# 在 features/ 下创建新目录
mkdir -p src/features/new-feature/{components,hooks,store}
touch src/features/new-feature/types.ts
```

**目录结构**：
```
features/new-feature/
├── components/      # UI 组件
│   ├── Panel.tsx
│   ├── List.tsx
│   └── Item.tsx
├── hooks/           # 业务逻辑
│   ├── useNewFeature.ts
│   └── useNewFeatureData.ts
├── store/           # 状态管理
│   └── newFeatureStore.ts
└── types.ts         # 类型定义
```

---

#### 步骤 3：创建 Store

**模板**：
```typescript
// features/new-feature/store/newFeatureStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface NewFeatureState {
  data: DataType[];
  isLoading: boolean;
  error: string | null;
}

interface NewFeatureActions {
  setData: (data: DataType[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

type NewFeatureStore = NewFeatureState & NewFeatureActions;

const initialState: NewFeatureState = {
  data: [],
  isLoading: false,
  error: null,
};

export const useNewFeatureStore = create<NewFeatureStore>()(
  persist(
    (set) => ({
      ...initialState,
      
      setData: (data) => set({ data }),
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
      reset: () => set(initialState),
    }),
    {
      name: 'new-feature-storage', // localStorage key
      partialize: (state) => ({ data: state.data }), // 只持久化 data
    }
  )
);
```

**注意事项**：
- 使用 `persist` 中间件持久化需要保存的数据
- `partialize` 选择性持久化，避免保存临时状态（如 isLoading）
- 提供 `reset` 方法清空状态

---

#### 步骤 4：创建 Hooks

**模板**：
```typescript
// features/new-feature/hooks/useNewFeature.ts
import { useCallback, useEffect } from 'react';
import { useNewFeatureStore } from '../store/newFeatureStore';
import { wsManager } from '@/core/websocket';
import { api } from '@/core/api';

export function useNewFeature() {
  const store = useNewFeatureStore();
  
  // 加载数据
  const loadData = useCallback(async () => {
    store.setLoading(true);
    store.setError(null);
    
    try {
      const data = await api.getNewFeatureData();
      store.setData(data);
    } catch (error) {
      store.setError(error.message);
    } finally {
      store.setLoading(false);
    }
  }, [store]);
  
  // 订阅 WebSocket 消息
  useEffect(() => {
    const handleMessage = (msg: Message) => {
      // 处理消息
      store.setData((prev) => [...prev, msg.data]);
    };
    
    wsManager.on('new-feature-message', handleMessage);
    return () => wsManager.off('new-feature-message', handleMessage);
  }, [store]);
  
  // 初始化加载
  useEffect(() => {
    loadData();
  }, [loadData]);
  
  return {
    data: store.data,
    isLoading: store.isLoading,
    error: store.error,
    loadData,
  };
}
```

**注意事项**：
- hooks 负责所有副作用（API 调用、WebSocket 订阅）
- 使用 `useCallback` 避免不必要的重新创建函数
- 必须清理副作用（WebSocket 取消订阅）

---

#### 步骤 5：创建 Components

**模板**：
```typescript
// features/new-feature/components/Panel.tsx
import { useNewFeature } from '../hooks/useNewFeature';
import { List } from './List';

export function Panel() {
  const { data, isLoading, error, loadData } = useNewFeature();
  
  if (isLoading) {
    return <div>加载中...</div>;
  }
  
  if (error) {
    return (
      <div>
        <p>错误：{error}</p>
        <button onClick={loadData}>重试</button>
      </div>
    );
  }
  
  return (
    <div className="new-feature-panel">
      <List data={data} />
    </div>
  );
}
```

**注意事项**：
- 组件只负责展示，不包含业务逻辑
- 所有数据和方法都从 hooks 获取
- 不直接调用 API 或操作 WebSocket

---

#### 步骤 6：在 Layout 中使用

```typescript
// layouts/MainLayout.tsx
import { Panel as NewFeaturePanel } from '@/features/new-feature/components/Panel';

export function MainLayout() {
  return (
    <div className="main-layout">
      <Sidebar />
      <ChatWindow />
      <NewFeaturePanel />  {/* 新增的功能面板 */}
    </div>
  );
}
```

---

#### 步骤 7：添加路由（如果需要）

```typescript
// App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Panel as NewFeaturePanel } from '@/features/new-feature/components/Panel';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />} />
        <Route path="/new-feature" element={<NewFeaturePanel />} />
      </Routes>
    </BrowserRouter>
  );
}
```

---

### 新增功能检查清单

完成以下检查后，新功能才算完成：

- [ ] 创建了标准的目录结构（components/hooks/store/types.ts）
- [ ] Store 使用 Zustand，需要持久化的数据使用 `persist` 中间件
- [ ] Hooks 封装了所有业务逻辑和副作用
- [ ] Components 只负责展示，不包含业务逻辑
- [ ] 清理了所有副作用（WebSocket 取消订阅、定时器清除）
- [ ] 在 Layout 中正确使用了新组件
- [ ] 如果需要路由，已添加到 App.tsx
- [ ] 类型定义完整，没有使用 `any`
- [ ] 测试了基本功能（加载、交互、错误处理）

---

## 参考资料

- 完整架构设计：`../ARCHITECTURE.md`
- 前端 MVP 设计：`../superpowers/specs/2026-06-01-frontend-mvp-design.md`
- 日常编码规范：`../../frontend/CLAUDE.md`
