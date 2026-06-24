---
version: 2.0
created_at: 2026-06-06
updated_at: 2026-06-18
last_updated: 按新 spec 规则重构：聚焦业务意图 + 技术契约 + 设计决策，移除执行细节
abstract: 消息置顶功能规格，定义 pin/unpin 操作的 API 契约、前端交互规则、右侧栏展示和 Agent 上下文注入机制
id: pinned-messages
title: 消息置顶功能
status: draft
module: api/group_chat, frontend/chat, core/context
source_spec: 无（brainstorming 讨论直接产出）
code_scope:
  - agents_hub/api/routes/group_chat.py
  - agents_hub/api/schemas/group_chats.py
  - agents_hub/api/services/group_chat_service.py
  - agents_hub/core/context/agent_context.py
  - frontend/src/core/api/groupChatApi.ts
  - frontend/src/features/chat/hooks/usePinnedMessages.ts
  - frontend/src/features/chat/store/pinnedMessagesStore.ts
  - frontend/src/layouts/ChatArea/ChatArea.tsx
  - frontend/src/layouts/RightSidebar/RightSidebar.tsx
contract_refs:
  - agents_hub/api/schemas/group_chats.py
  - frontend/src/shared/types/api-schemas.ts
---

# 消息置顶功能

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |
| 1.1 | 添加 Agent Context Integration，定义 Pin 消息自动注入到 Agent 提示词的行为 |
| 1.2 | 修改注入方式：通过 `_generate_runtime_content` 注入到 `<AGENT_RUNTIME>` md 文件 |
| 2.0 | 按新 spec 规则重构：聚焦业务意图 + 技术契约 + 设计决策，移除执行细节 |

## Overview

**业务问题**：群聊中的重要消息（如代码规范、任务约束、用户偏好）容易被后续消息淹没，用户需要一种机制将关键信息固定在可见位置，方便随时回顾。

**核心职责**：
- 提供 Pin/Unpin 操作，让用户标记重要消息
- 在右侧栏展示已 pin 消息列表
- 将 Pin 消息注入 Agent 运行时上下文，使 Agent 自动遵守用户置顶的规则和要求

**不做什么**：
- 不负责消息 ID 机制（使用现有 message_id）
- 不负责消息排序或搜索
- 不负责批量操作

## Scope

### 范围内

- Pin 消息（通过 hover 气泡底部按钮）
- 取消 Pin（通过右侧栏按钮或再次 hover 点击）
- 右侧栏展示已 pin 消息列表
- Pin 状态通过 WebSocket RefreshSignal 同步
- Pin 消息注入 Agent 运行时上下文

### 范围外

- 点击 pin 消息跳转到原消息位置（后续迭代）
- 消息 ID 机制（不修改 MessageInfo schema）
- Pin 消息的排序或搜索
- 批量 pin/unpin

## Technical Contract

### API 端点

<key_function last_update="2026-06-24T22:26:41+08:00">
- agents_hub/api/routes/group_chat.py
  - group_chat.get_pinned_messages:183
  - group_chat.pin_message:199
  - group_chat.unpin_message:215
</key_function>

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/group-chats/{group_chat_id}/pinned-messages` | 获取已 pin 消息列表 |
| POST | `/api/v1/group-chats/{group_chat_id}/pinned-messages` | Pin 一条消息 |
| DELETE | `/api/v1/group-chats/{group_chat_id}/pinned-messages` | 取消 pin 一条消息 |

**请求 Schema**：

| Schema | 字段 | 类型 | 必填 | 说明 |
|--------|------|------|------|------|
| PinMessageRequest | message_id | int | 是 | 消息 id |

**响应 Schema**：

| Schema | 字段 | 类型 | 说明 |
|--------|------|------|------|
| PinnedMessageInfo | message_id | int | 消息 id |
| PinnedMessageInfo | speaker | str | 消息发送者名称 |
| PinnedMessageInfo | content | str | 消息完整内容（快照） |
| PinnedMessageInfo | timestamp | str | 消息原始时间戳 |
| PinnedMessageInfo | platform | str | 消息来源平台 |
| PinnedMessageInfo | pinned_at | str | 置顶操作时间 |
| PinOperationResponse | ok | bool | 操作是否成功（默认 true） |

**异常处理**：

| HTTP 状态码 | 触发场景 |
|-------------|----------|
| 400 | 请求参数格式错误 |
| 404 | 群聊不存在 |
| 422 | 指定的消息不存在于群聊历史中 |
| 500 | 服务器内部错误 |

**业务规则**：
- Pin 记录独立于消息存储，不修改消息本身
- Pin 记录与 group_chat 关联，删除群聊时级联删除 pin 记录
- 每条消息只能被 pin 一次（重复 pin 返回成功，幂等）

### Agent 上下文注入

<key_function last_update="2026-06-18T10:34:37+08:00">
- agents_hub/core/context/agent_context.py
  (无私有方法纳入 key_function，注入逻辑由 _generate_runtime_content 内部调用)
</key_function>

Pin 消息通过 Runtime 注入机制自动写入 Agent 的 CLAUDE.md / AGENTS.md 文件中，作为 `<AGENT_RUNTIME>` 的一部分。

**注入机制**：
- **注入方式**：生成 `<pinned_messages>` XML 片段，随 `<AGENT_RUNTIME>` 一起注入到 CLAUDE.md / AGENTS.md
- **注入时机**：Agent 从队列取出每条消息时
- **幂等性**：多次注入不会产生重复的 `<pinned_messages>` 块

**注入格式**：

```xml
<AGENT_RUNTIME>
<identity>...</identity>
<team>...</team>

<pinned_messages>
以下是用户置顶的重要消息，请在处理任务时遵守这些规则和要求：

[speaker]: 消息内容
[speaker]: 消息内容

</pinned_messages>
</AGENT_RUNTIME>
```

**排序规则**：按 `pinned_at` 时间升序排列（最早 pin 的在前）

**异常处理**：
- 文件不存在或为空：返回空字符串
- 读取失败：记录警告日志，返回空字符串
- 无 Pin 消息时不出现 `<pinned_messages>` 标签

### 前端 API 函数

<key_function last_update="2026-06-18T10:34:37+08:00">
- frontend/src/core/api/groupChatApi.ts
  - groupChatApi.getPinnedMessages:734
  - groupChatApi.pinMessage:744
  - groupChatApi.unpinMessage:757
</key_function>

| 函数 | 说明 |
|------|------|
| `getPinnedMessages(chatId)` | 获取已 pin 消息列表 |
| `pinMessage(chatId, data)` | Pin 一条消息 |
| `unpinMessage(chatId, data)` | 取消 pin 一条消息 |

遵循现有 `mockableRequest` 模式。

### 前端状态管理

- **Store**：`pinnedMessagesStore` 管理 pin 状态，保证所有组件共享同一份数据
- **Hook**：`usePinnedMessages` 封装 pin/unpin 操作和状态查询
- **同步机制**：通过 WebSocket RefreshSignal 触发列表刷新

## Design Rationale

**为什么使用 message_id 而不是 timestamp + speaker 复合键？**
- message_id 是消息的唯一标识，语义清晰，避免时间戳精度和同名用户的歧义
- 与现有 MessageInfo schema 保持一致，无需额外维护复合键逻辑

**为什么 Pin 记录独立于消息存储？**
- 遵循 SSOT 原则：消息内容不因 pin 操作而改变
- Pin 是用户行为，不应污染消息数据模型
- 删除群聊时可级联清理，不影响消息历史

**为什么注入 Agent 运行时上下文？**
- Pin 消息的核心价值是让 Agent 遵守用户置顶的规则和要求
- 注入到 `<AGENT_RUNTIME>` 而非每次 prompt 拼接，遵循 runtime 统一管理机制
- 幂等性由 `replace_marked_section` 保证，避免重复注入

**有哪些约束？**
- 消息必须存在于群聊历史中才能被 pin（422 错误）
- Pin 消息内容是快照，消息编辑后 pin 内容不会同步更新
- 注入到 Agent 上下文依赖 runtime 文件系统，需要 work_root 目录存在

**有哪些已知限制？**
- 不支持点击 pin 消息跳转到原消息位置
- 不支持 pin 消息的排序或搜索
- 不支持批量 pin/unpin 操作

**相关 ADR**：
- 无

## Interaction / UX Notes

### Hover Pin 按钮

- 鼠标悬停在消息气泡上时，气泡底部显示操作栏
- 操作栏包含 pin 按钮（图标）
- 已 pin 的消息：pin 按钮高亮显示，点击执行 unpin
- 未 pin 的消息：pin 按钮默认样式，点击执行 pin
- 操作栏与气泡对齐：agent 消息左对齐，user 消息右对齐

### 右侧栏 Pinned 模块

- 位于右侧栏，遵循 `.rightModule` 卡片样式
- 标题："Pinned"
- 列表项：speaker 名称 + 消息内容截断（单行）
- 每项右侧有取消 pin 按钮
- 空状态：居中显示"暂无置顶消息"

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **消息 ID 机制**：使用现有 message_id，不修改 MessageInfo schema
- **WebSocket 事件实现**：由 realtime spec 处理
- **Pin 消息跳转**：后续迭代功能
- **Pin 消息排序策略**：当前按 pinned_at 升序，后续可扩展
- **批量 pin/unpin**：当前不支持
