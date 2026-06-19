---
version: 2.0
created_at: 2026-06-07
updated_at: 2026-06-18
last_updated: 按新 spec 规则重构：聚焦业务意图 + 技术契约 + 设计决策
abstract: 消息引用功能规格，定义引用机制、交互规则和 Markdown 引用格式规范
id: message-reply-quote
title: 消息引用功能
status: draft
module: frontend/chat
---

# 消息引用功能

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 2.0 | 按新 spec 规则重构 |
| 1.0 | 创建 spec 初稿 |

## Overview

**业务问题**：用户在对话中需要引用之前的消息进行回复，以提供上下文关联，但当前系统不支持消息引用功能。

**核心职责**：
- 提供消息引用的前端交互（引用、展示、取消）
- 将引用内容格式化为 Markdown 块引用语法
- 在发送失败时保留引用状态，支持重试

**不负责**：
- 后端存储引用关系
- 引用消息的跳转定位
- 多层引用

## Scope

### 范围内

- 引用消息（通过点击消息气泡的引用按钮）
- 引用框展示（发言者名称 + 内容摘要，最多 100 字）
- 取消引用（关闭按钮 / 切换会话自动清空）
- 发送时自动用 Markdown 块引用语法包裹
- 发送失败时保留引用状态

### 范围外

- 多层引用（引用已包含引用的消息）
- 引用消息的跳转定位
- 后端存储引用关系（reply_to 字段）
- 引用消息的通知机制

## Technical Contract

### 前端状态契约

<key_function last_update="2026-06-19T09:08:01+08:00">
- frontend/src/layouts/ChatArea/ChatArea.tsx
  - ChatArea.handleQuote
  - ChatArea.handleClearQuote
</key_function>

**状态模型**：

| 状态 | 类型 | 说明 |
|------|------|------|
| quotedMessage | `MessageApiItem \| null` | 当前引用的消息，null 表示无引用 |

**状态转换规则**：

| 当前状态 | 事件 | 下一状态 |
|---------|------|---------|
| null | 点击引用按钮 | MessageApiItem |
| MessageApiItem | 点击关闭按钮 | null |
| MessageApiItem | 发送成功 | null |
| MessageApiItem | 切换会话 | null |
| MessageApiItem | 发送失败 | MessageApiItem（保留） |

### 组件 Props 契约

**ChatInput 新增 Props**：

| Prop | 类型 | 说明 |
|------|------|------|
| quotedMessage | `MessageApiItem \| null` | 当前引用的消息 |
| onClearQuote | `() => void` | 清空引用的回调 |

**MessageBubble 新增 Props**：

| Prop | 类型 | 说明 |
|------|------|------|
| onQuote | `() => void` | 触发引用的回调 |

### Markdown 引用格式规范

引用内容使用标准 Markdown 块引用语法：

```
> 原消息第一行
> 原消息第二行

用户的回复内容
```

**格式化规则**：
- 每行前添加 `> ` 前缀
- 引用内容和回复内容之间空一行
- 多行消息保持换行结构

**渲染**：前端 MarkdownRenderer 自动将 `>` 开头的行渲染为引用样式。

## Design Rationale

**为什么纯前端实现？**
- 简化实现：无需修改 AgentMessage 模型和数据库 schema
- 灵活性：Markdown 引用格式由前端控制，后端无感知
- 渐进式增强：未来如需后端支持（跳转、通知），可平滑迁移

**为什么选择 Markdown 引用语法？**
- 现成渲染器：前端已有 MarkdownRenderer，无需额外开发
- 人类可读：纯文本也能看懂引用关系
- 跨平台兼容：Markdown 是通用格式，便于导出和分享

**已知限制**：
- 不支持多层引用（引用已包含引用的消息）
- 不支持点击引用跳转到原消息位置
- 引用消息在发送前被删除的极端情况不做校验（消息列表只增不减）

## Interaction / UX Notes

**引用按钮**：
- 位置：消息气泡下方，Pin 按钮右侧
- 触发：hover 消息气泡时显示
- 范围：所有消息（user 和 agent）均可被引用

**引用框**：
- 位置：输入框正上方
- 内容：发言者名称 + 消息摘要（超过 100 字截断加省略号）
- 关闭：点击关闭按钮 或 切换会话自动清空

**发送行为**：
- 成功：引用框消失，输入框清空
- 失败：引用框保留，输入框内容保留，用户可重试

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **后端消息存储**：参见相关后端 spec - 引用关系的持久化存储
- **消息跳转定位**：未来功能 - 点击引用消息跳转到原消息位置
- **多层引用**：未来功能 - 引用已包含引用的消息
