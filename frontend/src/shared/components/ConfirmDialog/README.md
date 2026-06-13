# ConfirmDialog 通用确认弹窗组件

一个简单、可复用的确认/取消弹窗组件，支持多种变体和状态。

## 功能特性

- 支持信息、警告、危险三种变体
- 支持自定义标题、消息和按钮文本
- 支持加载状态
- 支持禁用确认按钮
- 支持键盘导航（ESC 键关闭）
- 支持无障碍访问（ARIA 属性）
- 支持深色/浅色主题
- 平滑的入场动画

## 使用方法

### 基础用法

```tsx
import { useState } from 'react';
import { ConfirmDialog } from '@/shared/components';

function MyComponent() {
  const [showDialog, setShowDialog] = useState(false);

  return (
    <>
      <button onClick={() => setShowDialog(true)}>
        打开确认弹窗
      </button>

      <ConfirmDialog
        isOpen={showDialog}
        onClose={() => setShowDialog(false)}
        onConfirm={() => {
          console.log('确认操作');
          setShowDialog(false);
        }}
        title="确认删除"
        message="确定要删除这条记录吗？此操作无法撤销。"
      />
    </>
  );
}
```

### 不同变体

```tsx
// 信息确认（默认）
<ConfirmDialog
  variant="info"
  title="确认操作"
  message="这是一条信息确认消息"
  onConfirm={handleConfirm}
/>

// 警告确认
<ConfirmDialog
  variant="warning"
  title="警告"
  message="此操作可能会影响系统性能"
  confirmText="继续"
  onConfirm={handleConfirm}
/>

// 危险确认
<ConfirmDialog
  variant="danger"
  title="删除确认"
  message="此操作将永久删除数据"
  confirmText="删除"
  onConfirm={handleConfirm}
/>
```

### 加载状态

```tsx
<ConfirmDialog
  isOpen={showDialog}
  onClose={() => setShowDialog(false)}
  onConfirm={handleAsyncConfirm}
  title="处理中"
  message="正在处理您的请求，请稍候..."
  loading={isLoading}
/>
```

## Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `isOpen` | `boolean` | - | 是否显示弹窗 |
| `onClose` | `() => void` | - | 关闭回调 |
| `onConfirm` | `() => void` | - | 确认回调 |
| `title` | `string` | `'确认操作'` | 弹窗标题 |
| `message` | `string` | - | 消息内容 |
| `confirmText` | `string` | `'确认'` | 确认按钮文本 |
| `cancelText` | `string` | `'取消'` | 取消按钮文本 |
| `confirmDisabled` | `boolean` | `false` | 是否禁用确认按钮 |
| `loading` | `boolean` | `false` | 是否显示加载状态 |
| `variant` | `'info' \| 'warning' \| 'danger'` | `'info'` | 弹窗变体 |

## 无障碍特性

- 支持 `role="dialog"` 和 `aria-modal="true"`
- 支持 `aria-labelledby` 和 `aria-describedby`
- 支持 ESC 键关闭
- 支持焦点管理（打开时自动聚焦确认按钮）
- 支持按钮禁用状态

## 主题支持

组件自动适配深色/浅色主题，使用项目的设计令牌系统。

## 文件结构

```
ConfirmDialog/
├── ConfirmDialog.tsx          # 组件实现
├── ConfirmDialog.module.css   # 样式文件
├── ConfirmDialog.test.tsx     # 测试文件
├── ConfirmDialog.example.tsx  # 使用示例
├── index.ts                   # 导出文件
└── README.md                  # 文档
```