# HTML样式指南

## 设计风格参考

本skill的HTML可视化采用以下设计风格：

### 字体
- **标题字体**：Noto Serif SC（衬线字体，用于标题和强调）
- **正文字体**：Noto Sans SC（无衬线字体，用于正文）
- **等宽字体**：JetBrains Mono（用于代码和标签）

### 颜色方案

```css
:root {
  --ink: #1a1a1a;           /* 主文字颜色 */
  --ink-light: #555;        /* 次要文字颜色 */
  --ink-muted: #888;        /* 弱化文字颜色 */
  --bg: #f8f6f1;            /* 页面背景 */
  --bg-card: #ffffff;       /* 卡片背景 */
  --accent-1: #c04a1a;      /* 赤陶橙（主强调色） */
  --accent-2: #2d6a4f;      /* 墨绿 */
  --accent-3: #1d3557;      /* 深蓝 */
  --accent-4: #7b2d8b;      /* 紫 */
  --accent-5: #b5651d;      /* 暖棕 */
  --border: #e0dcd4;        /* 边框颜色 */
  --shadow: 0 2px 20px rgba(0,0,0,0.06);  /* 阴影 */
}
```

### 布局结构

#### 1. Hero区域
- 页面顶部的标题区域
- 包含徽章（badge）、标题、副标题
- 居中对齐，最大宽度800px

#### 2. 导航区域
- 可选的章节导航
- 水平排列的链接按钮
- 支持hover效果

#### 3. 内容区域
- 卡片式布局
- 每个章节一个卡片
- 包含头部（图标+标题）和内容体

#### 4. 信息块
- 用于展示分类信息
- 支持多种颜色主题（blue, green, purple, orange）
- 左边框颜色标识

### 图表支持

#### Mermaid图表
- 支持流程图（flowchart）
- 支持序列图（sequenceDiagram）
- 支持类图（classDiagram）
- 支持状态图（stateDiagram-v2）

#### 图表容器
```html
<div class="diagram-section">
  <div class="mermaid">
    graph LR
      A[节点A] --> B[节点B]
  </div>
</div>
```

### 响应式设计
- 移动端适配
- 网格布局自适应
- 字体大小响应式

## 使用模板

### 基本结构
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{标题}</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    /* 样式代码 */
  </style>
</head>
<body>
  <div class="hero">
    <div class="hero-badge">{徽章}</div>
    <h1>{标题}</h1>
    <p>{副标题}</p>
  </div>

  <nav class="section-nav">
    <!-- 导航链接 -->
  </nav>

  <div class="content-section">
    <div class="section-card">
      <div class="section-header">
        <div class="section-icon" style="background: {颜色};">1</div>
        <div class="section-title-block">
          <h2>{章节标题}</h2>
          <div class="subtitle">{副标题}</div>
        </div>
      </div>
      <div class="section-body">
        <!-- 内容 -->
      </div>
    </div>
  </div>

  <script>
    mermaid.initialize({
      startOnLoad: true,
      theme: 'default',
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis'
      }
    });
  </script>
</body>
</html>
```

### 颜色使用建议

| 章节类型 | 推荐颜色 | 用途 |
|----------|----------|------|
| 知识框架 | accent-3（深蓝） | 主体结构 |
| 关系层 | accent-2（墨绿） | 关系连接 |
| 思考层 | accent-4（紫色） | 深度思考 |
| 主题锚点 | accent-1（赤陶橙） | 重点突出 |
