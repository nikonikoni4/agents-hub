---
version: 2.0
created_at: 2026-06-05
updated_at: 2026-06-18
last_updated: 按新 spec 规则重构：移除执行细节和调用链路，添加 key_function 标签和 Design Rationale
abstract: 定义消息流转与持久化的技术契约：MessageRouter 职责边界（纯投递层）、GroupChat.send_message_to_agent() 统一包装投递和保存、群聊历史保存规则
id: spec-message-flow-and-persistence
title: 消息流转与持久化规格
status: draft
module: core/communication, core/orchestration, mcp
source_spec: null
related_plan: null
code_scope:
  - agents_hub/core/communication/message_router.py
  - agents_hub/mcp/server.py
  - agents_hub/core/orchestration/group_chat.py
contract_refs:
  - agents_hub/core/communication/message_router.py
  - agents_hub/core/context/group_chat_context.py
  - agents_hub/mcp/server.py
---

# 消息流转与持久化规格

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |
| 1.1 | 修正：所有消息都保存到群聊历史，GroupChat 提供统一包装方法 |
| 1.2 | 修正：complete_task 参数补充、Heartbeat 消息流、Agent 停止清理流程、工具注册状态标注、send_message_to_agent 行为契约补充 |
| 2.0 | 按新 spec 规则重构：移除执行细节和调用链路，添加 key_function 标签和 Design Rationale |

## Overview

**业务问题**：系统中存在多种消息流转场景（user 发消息给 agent、agent 调用 agent、agent 公开发言），需要统一的投递和持久化机制，确保消息可追踪、前端可展示。

**核心职责**：
1. **定义消息投递的统一入口**：所有业务消息通过 `GroupChat.send_message_to_agent()` 完成投递和保存
2. **划清 MessageRouter 的职责边界**：MessageRouter 是纯投递层，不承担业务逻辑和持久化
3. **规定群聊历史保存规则**：明确哪些消息保存、哪些不保存、保存时机

## Scope

### 范围内

- MessageRouter 的职责边界（投递 vs 保存的分离）
- GroupChat 统一包装方法 `send_message_to_agent()` 的行为契约
- 群聊历史保存规则（保存时机、消息类型判断）
- MCP 工具的消息流转契约（call_agent、complete_task、report_progress）

### 范围外

- MessageRouter 的接口定义和实现细节（参考 `docs/specs/2026-05-31-core-communication.md`）
- AgentCall 状态机（参考 `docs/specs/2026-05-31-core-communication.md`）
- Agent 内部执行逻辑（参考 `docs/specs/2026-05-31-core-agent-orchestration.md`）
- 群聊上下文压缩和增量加载（参考 `docs/specs/2026-05-31-core-context.md`）
- 消息渲染格式（参考 `docs/specs/2026-05-31-core-foundation.md`）
- 前端消息拉取和 WebSocket 刷新通知

## Technical Contract

### GroupChat 统一包装方法

<key_function last_update="2026-06-19T08:25:17+08:00">
- agents_hub/core/orchestration/group_chat.py
  - group_chat.GroupChat.send_message_to_agent:563
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| send_message_to_agent(message) | 发送消息到目标 Agent 并保存到群聊历史 | 目标 Agent 必须非 stopped 状态；自动调用 activate() 确保群聊已激活 |

**行为契约**：确保群聊已激活 → 校验目标 Agent 非 stopped → 投递消息 → 保存到群聊历史

**使用方**：
- MCP tool `call_agent`：agent 调用 agent
- MCP tool `complete_task`：发送 NOTIFICATION 给原调用方
- API `send_message_to_agent`：user 发送消息给 agent
- `_cleanup_agent_queue`：Agent 停止时发送清理通知

### MCP 工具接口

<key_function last_update="2026-06-18T17:00:00+08:00">
- agents_hub/mcp/server.py
  - mcp_server.call_agent:182
  - mcp_server.complete_task:569
  - mcp_server.report_progress:501
</key_function>

#### call_agent

| 参数 | 说明 | 约束 |
|------|------|------|
| agent_token | 身份令牌 | 必须有效 |
| send_to | 目标 Agent 名称 | 必须已注册 |
| content | 消息内容 | 非空 |
| need_response | 是否需要响应 | 默认 True；True → TASK，False → NOTIFICATION |
| timeout_seconds | 超时时间 | 整数秒，默认 300 |

**行为契约**：验证令牌 → 获取 GroupChat → 创建 AgentCall → 通过 `send_message_to_agent()` 投递并保存 → 返回 call_id

#### complete_task

| 参数 | 说明 | 约束 |
|------|------|------|
| agent_token | 身份令牌 | 必须有效 |
| call_id | AgentCall ID | 必须存在，类型必须为 TASK |
| content | 成果汇报 | 非空 |
| success | 完成状态 | True 表示完成，False 表示阻塞或失败 |
| modified_files | 修改的文件列表 | 可选，相对路径 |
| git_diff_range | Git diff 范围 | 可选，配合 modified_files 使用 |
| web_preview_url | 网页预览 URL | 可选 |
| web_preview_title | 网页预览标题 | 可选 |

**行为契约**：验证权限 → 闭环 AgentCall → 根据调用方类型通知（user → 直接保存；Agent → 通过 `send_message_to_agent()` 发送 NOTIFICATION）

#### report_progress

| 参数 | 说明 | 约束 |
|------|------|------|
| agent_token | 身份令牌 | 必须有效 |
| content | 发言内容 | 非空 |
| send_to | 目标 Agent | 可选，None 表示群聊公开发言 |

**行为契约**：直接调用 `GroupChatRuntime.add_message()` 保存到群聊历史，不经过 MessageRouter

**工具注册状态**（2026-06-16）：`report_progress`、`complete_task`、`request_permission` 当前在 `mcp/server.py` 中已被注释掉，未注册到 FastMCP。

### GroupChatRuntime 持久化接口

<key_function last_update="2026-06-18T17:00:00+08:00">
- agents_hub/core/context/group_chat_runtime.py
  - group_chat_runtime.GroupChatRuntime.add_message:319
</key_function>

| 接口 | 说明 | 约束 |
|------|------|------|
| add_message(agent_result) | 保存消息到群聊历史 | 接收 AgentResult 对象 |

### 群聊历史保存规则

| 消息场景 | 是否保存 | 保存位置 |
|---------|---------|---------|
| user → agent TASK（发送消息） | 保存 | `GroupChat.send_message_to_agent()` |
| user → agent TASK 完成（回复内容） | 保存 | `complete_task` 中判断 `is_user_name()` |
| agent → agent TASK（发送消息） | 保存 | `GroupChat.send_message_to_agent()` |
| agent → agent NOTIFICATION（完成通知） | 保存 | `GroupChat.send_message_to_agent()` |
| report_progress（公开发言） | 保存 | 直接调用 `add_message()` |
| Agent 初始化打招呼 | 保存 | `_initialize_new_members()` / `_initialize_single_member()` |
| Agent 停止清理通知 | 保存 | `_cleanup_agent_queue` 通过 `send_message_to_agent()` 或 `add_message()` |
| Heartbeat 系统消息 | **不保存** | 直接通过 `MessageRouter.send_message()` 投递 |

**判断原则**：
- 所有通过 `GroupChat.send_message_to_agent()` 投递的业务消息都保存
- 公开发言直接保存（不经过 MessageRouter）
- Heartbeat 等系统消息直接调用 `MessageRouter.send_message()` 投递，不保存

### Agent 停止清理契约

当 Agent 被停止时：标记其所有 PENDING/RUNNING AgentCall 为 FAILED → 按调用方类型通知（Agent → send_message_to_agent()；user → 直接保存） → 清空消息队列

## Design Rationale

**为什么 MessageRouter 不负责消息保存？**
- MessageRouter 属于 communication 层，不应依赖 context 层（违反分层原则）
- 消息保存是业务逻辑，应由编排层（GroupChat）统一处理
- MessageRouter 应该是可复用的通用组件，不耦合群聊历史的概念

**为什么需要 `GroupChat.send_message_to_agent()` 统一包装？**
- 消息投递和保存是紧密耦合的操作，必须保证原子性
- 分散调用容易遗漏保存步骤，导致消息丢失
- 统一入口便于添加拦截逻辑（如状态检查、格式化）

**为什么 Heartbeat 消息不保存到群聊历史？**
- Heartbeat 是系统内部的定时唤醒机制，对用户无可见价值
- 保存会污染群聊历史，干扰前端展示和上下文管理
- Heartbeat 使用虚拟身份 `__HEARTBEAT__`，不是真正的业务消息

**有哪些已知限制？**
- `report_progress`、`complete_task`、`request_permission` 当前在 MCP 中未注册（已注释），函数定义存在但无法通过 MCP 协议调用

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **MessageRouter 接口定义**：`docs/specs/2026-05-31-core-communication.md` - 消息队列注册/注销、投递失败处理
- **AgentCall 状态机**：`docs/specs/2026-05-31-core-communication.md` - 调用生命周期状态转换
- **Agent 执行逻辑**：`docs/specs/2026-05-31-core-agent-orchestration.md` - Agent 消息循环和执行模型
- **群聊上下文管理**：`docs/specs/2026-05-31-core-context.md` - 上下文压缩、增量加载、GroupChatRuntime 持久化实现
- **消息渲染格式**：`docs/specs/2026-05-31-core-foundation.md` - render_for_chat / render_for_llm
