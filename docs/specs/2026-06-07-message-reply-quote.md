---
version: 1.0
created_at: 2026-06-07
updated_at: 2026-06-07
last_updated: 创建 spec 初稿
abstract: 消息引用功能规格，定义引用消息的前端交互、引用框展示和 Markdown 引用语法格式
id: message-reply-quote
title: 消息引用功能
status: draft
module: frontend/chat
sourc_spec: 无（需求讨论直接产出）
related_plan: 无（当前无对应执行计划）
code_scope:
  - frontend/src/layouts/ChatArea/ChatArea.tsx
  - frontend/src/layouts/ChatArea/ChatInput.tsx
  - frontend/src/layouts/ChatArea/ChatArea.module.css
contract_refs:
  - frontend/src/shared/types/api-schemas.ts
---

# 消息引用功能

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |

## Overview

消息引用功能允许用户引用之前的消息进行回复，提供上下文关联。用户可以通过点击消息气泡的"引用"按钮选择要引用的消息，引用内容会显示在输入框上方的引用框中，发送时自动用 Markdown 块引用语法包裹。

**技术方案**：
- 前端纯实现，无需后端支持
- 使用 Markdown 块引用语法（`> `）格式化引用内容
- 前端已有 MD 渲染器会自动渲染引用样式

**架构分层**：
- **前端组件层**：ChatArea 增加引用按钮和状态管理，ChatInput 增加引用框展示
- **前端样式层**：新增引用框和引用按钮的 CSS 样式

## Scope

**当前阶段**：
- 引用消息（通过点击消息下方的引用按钮）
- 引用框展示（显示发言者和内容摘要）
- 取消引用（点击引用框的关闭按钮）
- 发送时自动用 MD 引用语法包裹
- 发送失败时保留引用状态（用户可重试）

**不在范围内**：
- 多层引用（引用已包含引用的消息）
- 引用消息的跳转定位
- 后端存储引用关系（reply_to 字段）
- 引用消息的通知机制

## Core Behavior

### 引用操作流程

```
1. 用户 hover 消息气泡 → 底部显示引用按钮（💬）
2. 点击引用按钮
   → 前端设置 quotedMessage 状态
   → 输入框上方显示引用框
3. 引用框内容：
   - 发言者名称（speaker）
   - 消息内容摘要（最多 100 字）
   - 关闭按钮（✕）
4. 用户输入回复内容
5. 点击发送
   → 引用内容用 MD 块引用语法包裹
   → 格式：`> 原消息内容\n\n用户回复`
   → 发送成功后清空引用状态
   → 发送失败时保留引用状态（用户可重试）
```

### 取消引用

**两种方式**：
1. 点击引用框的关闭按钮（✕）
2. 切换到其他会话时自动清空引用状态

### Markdown 引用格式

引用内容使用标准的 Markdown 块引用语法：

```markdown
> 原消息第一行
> 原消息第二行

用户的回复内容
```

**格式化规则**：
- 每行前添加 `> ` 前缀
- 引用内容和回复内容之间空一行
- 多行消息保持换行结构

**渲染效果**：
前端的 MarkdownRenderer 组件会自动将 `>` 开头的行渲染为引用样式（灰色背景 + 左侧边框）。

## Technical Contract

### 前端状态管理

**状态定义**：
```typescript
const [quotedMessage, setQuotedMessage] = useState<MessageApiItem | null>(null);
```

**状态流转**：
```
null → 点击引用按钮 → MessageApiItem
MessageApiItem → 点击关闭按钮 → null
MessageApiItem → 发送成功 → null
MessageApiItem → 切换会话 → null
MessageApiItem → 发送失败 → MessageApiItem（保留）
```

### 组件 Props

**ChatInput 新增 Props**：
```typescript
interface ChatInputProps {
  activeSessionId: string | null;
  members: { name: string }[];
  onSend: (text: string) => void;
  quotedMessage?: MessageApiItem | null;  // 新增
  onClearQuote?: () => void;               // 新增
}
```

**MessageBubble 新增 Props**：
```typescript
interface MessageBubbleProps {
  msg: MessageApiItem;
  avatar?: string | null;
  pinned: boolean;
  onPin: () => void;
  onUnpin: () => void;
  onQuote: () => void;  // 新增
}
```

### CSS 样式

**引用按钮**（`.quoteButton`）：
- 样式与 Pin 按钮一致
- 默认透明度 0.5，hover 时 1.0
- Emoji 图标：💬

**引用框**（`.quoteBox`）：
- 背景色：`var(--bg-shadow)`
- 左侧边框：3px，颜色 `var(--border-color)`
- 圆角：6px
- 内边距：12px 16px
- 外边距：8px 12px 0（顶部 8px，左右 12px）

**引用内容**（`.quoteContent`）：
- 布局：垂直 flex，间距 4px
- 发言者名称：12px，粗体 600，颜色 `var(--text-secondary)`
- 消息摘要：13px，颜色 `var(--text-tertiary)`，最大高度 60px

**关闭按钮**（`.quoteCloseBtn`）：
- 尺寸：20x20px
- 无背景，hover 时背景 `var(--bg-hover)`
- 圆角：4px

## Frontend Interaction

### 引用按钮位置

- 位置：消息气泡下方，Pin 按钮右侧
- 触发方式：hover 消息气泡时显示
- 所有消息（user 和 agent）都可以被引用

### 引用框位置

- 位置：输入框正上方
- 布局：独立容器，与输入框视觉分离
- 响应式：随输入框宽度自适应

### 交互细节

**引用按钮状态**：
- 默认：透明度 0.5
- Hover：透明度 1.0，背景 `var(--bg-hover)`
- 点击后：输入框聚焦，引用框出现

**引用框状态**：
- 出现动画：无（立即显示）
- 消失动画：无（立即隐藏）
- 内容截断：超过 100 字显示省略号

**发送行为**：
- 成功：引用框消失，输入框清空
- 失败：引用框保留，输入框内容保留，用户可修改后重试

## Error Handling

### 引用消息不存在

**场景**：用户引用的消息在发送前被删除（极端情况）
**处理**：前端不做校验，直接发送。消息列表只增不减，不会出现此情况。

### 发送失败

**场景**：网络错误、服务器错误等
**处理**：
- 保留 `quotedMessage` 状态
- 保留输入框内容
- 用户可修改回复内容后重试
- 用户可点击关闭按钮取消引用

### 切换会话

**场景**：用户选择引用后切换到其他会话
**处理**：自动清空 `quotedMessage` 状态（引用框消失）

## Test Scenarios

### 正常流程

1. 点击引用按钮后引用框正确显示
2. 引用框内容包含发言者和消息摘要
3. 点击关闭按钮后引用框消失
4. 发送时消息内容包含 MD 引用语法
5. 发送成功后引用框消失

### 边界情况

1. 引用很长的消息时内容正确截断（100 字 + "..."）
2. 引用多行消息时换行结构保持
3. 引用包含特殊字符的消息时正确转义
4. 切换会话时引用状态正确清空

### 错误处理

1. 发送失败后引用框保留
2. 发送失败后可重新编辑并重试
3. 发送失败后可取消引用

## Implementation Notes

### 为什么不使用后端存储？

**决策**：引用功能纯前端实现，不在后端存储 `reply_to` 字段

**原因**：
1. **简化实现**：无需修改 AgentMessage 模型和数据库 schema
2. **灵活性**：MD 引用语法由前端控制，后端无感知
3. **渐进式增强**：未来如需后端支持（跳转、通知），可平滑迁移

### 为什么选择 Markdown 引用语法？

**决策**：使用 `> ` 前缀而非结构化数据

**原因**：
1. **现成渲染器**：前端已有 MarkdownRenderer，无需额外开发
2. **人类可读**：纯文本也能看懂引用关系
3. **跨平台兼容**：Markdown 是通用格式，便于导出和分享

### 性能考虑

**引用框渲染**：
- 状态变化时立即渲染，无动画延迟
- 内容截断在渲染时计算（`slice(0, 100)`）
- 无需防抖或节流（用户操作频率低）

## Out of Spec

以下内容不在本 spec 中长期维护：

1. 后端存储引用关系（reply_to 字段）
2. 点击引用消息跳转到原消息位置
3. 多层引用的展示和格式化
4. 引用消息的通知机制
5. 引用消息的统计和分析
6. 引用消息的搜索和过滤
