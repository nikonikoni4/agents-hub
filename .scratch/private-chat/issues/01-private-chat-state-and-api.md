# Issue #1: 后端核心 - 私聊状态定义 + API 端点

Status: ready-for-agent
Labels: needs-triage

## What to build

在 Agent 状态体系中新增 `in_private_chat` 状态，并提供进入/退出私聊的 API 端点。

**状态定义**：在 `AgentMemberInfo.status` 字段中新增 `"in_private_chat"` 值，与现有的 `idle`、`busy`、`stopped`、`error`、`in_loop` 并列。只有 `idle` 状态的 Agent 才能进入私聊，`in_private_chat` 状态只能回到 `idle`。

**API 端点**：
- `POST /{group_chat_id}/members/{agent_name}/start-private-chat` — 进入私聊，返回 Agent 的 `main_session_id` 供前端复用
- `POST /{group_chat_id}/members/{agent_name}/stop-private-chat` — 退出私聊

**Manager 限制**：后端检查 Agent 是否为 Manager（`config.default_manager_name`），是则返回 403。

**状态变化通知**：进入/退出私聊后通过 WebSocket 发送 RefreshSignal，通知前端刷新成员列表。

## Acceptance criteria

- [ ] `AgentMemberInfo.status` 包含 `"in_private_chat"` 值
- [ ] `POST /{group_chat_id}/members/{agent_name}/start-private-chat` 成功返回 200，响应包含 `agent_name`、`status`、`main_session_id`
- [ ] `POST /{group_chat_id}/members/{agent_name}/stop-private-chat` 成功返回 200，响应包含 `agent_name`、`status`
- [ ] 非 `idle` 状态调用 `start-private-chat` 返回 409（StateError）
- [ ] 非 `in_private_chat` 状态调用 `stop-private-chat` 返回 409（StateError）
- [ ] Manager 调用 `start-private-chat` 返回 403
- [ ] 群聊或 Agent 不存在时返回 404
- [ ] 进入/退出私聊后发送 WebSocket RefreshSignal

## Architecture

参见 `.scratch/private-chat/architecture.md` 第 4 节"接口契约"和第 5 节"实现位置"。

## Blocked by

None - can start immediately
