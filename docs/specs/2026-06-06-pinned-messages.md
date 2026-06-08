---
version: 1.1
created_at: 2026-06-06
updated_at: 2026-06-08
last_updated: 修改注入方式为 runtime 注入到 md 文件
abstract: 消息置顶功能规格，定义 pin/unpin 操作的 API 契约、前端交互、右侧栏展示和 Agent 上下文注入
id: pinned-messages
title: 消息置顶功能
status: draft
module: api/group_chat, frontend/chat, core/agent
sourc_spec: 无（brainstorming 讨论直接产出）
related_plan: 无（当前无对应执行计划）
code_scope:
  - agents_hub/api/routes/group_chat.py
  - agents_hub/api/schemas/group_chats.py
  - agents_hub/api/services/group_chat_service.py
  - agents_hub/core/agent/base_agent.py
  - frontend/src/core/api/groupChatApi.ts
  - frontend/src/features/chat/hooks/
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
| 1.1 | 添加 Agent Context Integration 章节，定义 Pin 消息自动注入到 Agent 提示词的行为 |
| 1.2 | 修改注入方式：从 `_process_message` 拼接 prompt 改为通过 `_generate_runtime_content` 注入到 `<AGENT_RUNTIME>` md 文件 |

## Overview

消息置顶功能允许用户将重要的聊天消息固定显示在右侧栏中，方便快速回顾。用户可以通过 hover 消息气泡触发 pin 操作，已 pin 的消息展示在右侧栏的 Pinned 模块中，支持取消置顶。

**消息标识方案**：使用 `timestamp + speaker` 复合键标识消息，不修改现有 MessageInfo schema。

**架构分层**：
- **后端**：新增 pin 数据存储和 RESTful 端点
- **前端 API 层**：新增 pin 相关 API 函数
- **前端 Hook 层**：新增 `usePinnedMessages` hook 管理 pin 状态
- **前端组件层**：ChatArea 增加 hover pin 按钮，RightSidebar 增加 Pinned 模块

## Scope

**当前阶段**：
- Pin 消息（通过 hover 气泡底部按钮）
- 取消 Pin（通过右侧栏按钮或再次 hover 点击）
- 右侧栏展示已 pin 消息列表
- Pin 状态通过 WebSocket RefreshSignal 同步

**不在范围内**：
- 点击 pin 消息跳转到原消息位置
- 消息 ID 机制（不修改 MessageInfo schema）
- Pin 消息的排序或搜索
- 批量 pin/unpin

## Core Behavior

### Pin 操作流程

```
Pin: 用户 hover 消息气泡 → 底部显示 pin 按钮 → 点击
  → 前端调用 POST /api/v1/group-chats/{id}/pinned-messages
  → body: { speaker, timestamp }
  → 后端验证消息存在 → 存储 pin 记录 → 返回 ok
  → 前端刷新 pin 列表

Unpin（两种方式）:
  1. 右侧栏：点击已 pin 消息的取消按钮
  2. Hover：再次 hover 已 pin 消息，pin 按钮高亮，点击取消
  → 前端调用 DELETE /api/v1/group-chats/{id}/pinned-messages
  → body: { speaker, timestamp }
  → 后端删除 pin 记录 → 返回 ok
  → 前端刷新 pin 列表
```

### Pin 数据持久化

- Pin 记录独立于消息存储，不修改消息本身
- Pin 记录与 group_chat 关联，删除群聊时级联删除 pin 记录
- 每条消息只能被 pin 一次（重复 pin 返回成功，幂等）

### 右侧栏 Pinned 模块

- 遵循现有 `.rightModule` 卡片模式
- 展示已 pin 消息列表：speaker + 内容摘要
- 每条 pin 消息旁有取消 pin 按钮
- 空状态显示"暂无置顶消息"

## Technical Contract

### 端点总览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/group-chats/{group_chat_id}/pinned-messages` | 获取已 pin 消息列表 |
| POST | `/api/v1/group-chats/{group_chat_id}/pinned-messages` | Pin 一条消息 |
| DELETE | `/api/v1/group-chats/{group_chat_id}/pinned-messages` | 取消 pin 一条消息 |

### Schema 定义

**PinnedMessageCreate**（Pin 请求）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| speaker | str | 是 | 消息发送者名称 |
| timestamp | str | 是 | 消息时间戳（ISO 8601） |

**PinnedMessageDelete**（Unpin 请求）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| speaker | str | 是 | 消息发送者名称 |
| timestamp | str | 是 | 消息时间戳（ISO 8601） |

**PinnedMessageInfo**（Pin 消息响应，GET 返回列表项）：

| 字段 | 类型 | 说明 |
|------|------|------|
| speaker | str | 消息发送者名称 |
| content | str | 消息完整内容 |
| timestamp | str | 消息时间戳 |
| platform | str | 消息来源平台 |
| pinned_at | str | 置顶时间 |

### 异常处理

| HTTP 状态码 | 触发场景 |
|-------------|----------|
| 400 | 请求参数格式错误 |
| 404 | 群聊不存在 |
| 422 | 指定的消息不存在于群聊历史中 |
| 500 | 服务器内部错误 |

### 前端 API 函数

在 `core/api/groupChatApi.ts` 中新增：

| 函数 | 说明 |
|------|------|
| `getPinnedMessages(chatId)` | 获取已 pin 消息列表 |
| `pinMessage(chatId, data)` | Pin 一条消息 |
| `unpinMessage(chatId, data)` | 取消 pin 一条消息 |

遵循现有 `mockableRequest` 模式。

## Interaction / UX Notes

### Hover Pin 按钮

- 鼠标悬停在消息气泡上时，气泡底部显示操作栏
- 操作栏包含 pin 按钮（📌 图标）
- 已 pin 的消息：pin 按钮高亮显示，点击执行 unpin
- 未 pin 的消息：pin 按钮默认样式，点击执行 pin
- 操作栏与气泡对齐：agent 消息左对齐，user 消息右对齐

### 右侧栏 Pinned 模块

- 位于右侧栏，遵循 `.rightModule` 卡片样式
- 标题："Pinned"
- 列表项：speaker 名称 + 消息内容截断（单行）
- 每项右侧有取消 pin 按钮（× 图标）
- 空状态：居中显示"暂无置顶消息"

## Acceptance Notes

1. 用户 hover 消息气泡时正确显示 pin 按钮
2. 点击 pin 按钮后消息出现在右侧栏 Pinned 模块
3. 右侧栏点击取消 pin 后消息从列表移除
4. 已 pin 消息再次 hover 时 pin 按钮高亮，点击可取消
5. 空状态正确显示提示文字
6. 不同会话的 pin 数据互相隔离

## Out of Spec

以下内容不在本 spec 中长期维护：

1. 消息 ID 机制（当前使用 timestamp + speaker 复合键）
2. 点击 pin 消息跳转到原消息位置（后续迭代）
3. WebSocket 事件的具体实现细节（由 realtime spec 处理）
4. 前端组件的具体实现（TypeScript 类型、状态管理、样式）
5. Pin 消息的排序策略
6. 批量 pin/unpin 操作

## Agent Context Integration

### 概述

Pin 消息通过 Runtime 注入机制自动写入 Agent 的 CLAUDE.md / AGENTS.md 文件中，作为 `<AGENT_RUNTIME>` 的一部分。Agent 在每次处理消息时，Pin 消息随 runtime 一起更新到 md 文件，而不是在每次 prompt 中单独拼接。

### 注入机制

- **注入方式**：通过 `_generate_runtime_content()` 生成 `<pinned_messages>` XML 片段，随 `<AGENT_RUNTIME>` 一起注入到 CLAUDE.md / AGENTS.md
- **注入时机**：Agent 从队列取出每条消息时，在 `run()` 循环中调用 `_inject_runtime_to_files()`
- **注入目标**：`work_root/CLAUDE.md` 和 `work_root/AGENTS.md` 的 `<AGENT_RUNTIME>` 标记内
- **幂等性**：多次注入不会产生重复的 `<pinned_messages>` 块（由 `replace_marked_section` 保证）

### 注入格式

Pin 消息以 XML 格式嵌入 `<AGENT_RUNTIME>` 内：

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

### 实现细节

**核心方法**：
- `_get_pinned_messages_content()`：读取 pins.json 并生成 `<pinned_messages>` XML 片段
- `_generate_runtime_content()`：调用 `_get_pinned_messages_content()` 并拼入 runtime 内容
- `_inject_runtime_to_files()`：将 runtime 内容写入 CLAUDE.md / AGENTS.md

**数据来源**：
- 直接读取 `pins.json` 文件（遵循 SSOT 原则）
- 路径：`{group_chat_session_path}/pins.json`

**异常处理**：
- 文件不存在：返回空字符串
- 文件为空或无有效数据：返回空字符串
- 读取失败（IOError 等）：记录警告日志，返回空字符串

### 使用场景示例

**场景 1：代码规范**
```
用户 Pin: "所有代码必须添加类型注解"
→ Agent 在编写代码时会自动遵守此规则
```

**场景 2：任务约束**
```
Manager Pin: "提交前必须运行测试"
→ Agent 完成任务后会主动运行测试
```

**场景 3：偏好设置**
```
用户 Pin: "使用简洁的变量命名，避免过长的名称"
→ Agent 在重构代码时会遵循此偏好
```

### 测试契约

Pin 消息注入功能的测试覆盖：
- 文件不存在时返回空字符串
- 文件为空时返回空字符串
- 有 Pin 消息时生成正确的 XML 格式
- Pin 消息按时间升序排列
- 读取失败时返回空字符串（异常处理）
- Pin 消息包含在 `_generate_runtime_content()` 输出中
- 无 Pin 时不出现 `<pinned_messages>` 标签
- 幂等性：多次调用返回一致结果
- 幂等性：多次 `_inject_runtime_to_files()` 后文件内容一致

**测试文件**：`tests/unit/test_agent_pin_injection.py`
