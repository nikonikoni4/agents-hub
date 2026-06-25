# Issue #3: 前端基础 - API 函数 + Store + Hook

Status: ready-for-agent
Labels: needs-triage

## What to build

在前端新增私聊相关的 API 调用函数、状态管理和 Hook 方法，为后续 UI 层提供基础。

**API 函数**：在 `groupChatApi.ts` 中新增 `startPrivateChat(groupChatId, agentName)` 和 `stopPrivateChat(groupChatId, agentName)` 函数，分别调用后端的 `start-private-chat` 和 `stop-private-chat` 端点。

**私聊 Store**：新建 `privateChatStore.ts`（Zustand），管理私聊特有的状态：
- `activeGroupChatId`：关联的群聊 ID
- `activeAgentName`：私聊中的 Agent 名称
- `lastActivityTime`：最后活动时间戳
- `timerId`：3 分钟超时计时器 ID
- 方法：`startPrivateChat`、`stopPrivateChat`、`resetTimer`、`clearTimer`

**Hook 扩展**：在 `useMembers.ts` 中新增 `startPrivateChat(agentName)` 和 `stopPrivateChat(agentName)` 方法，封装 API 调用和状态更新。

## Acceptance criteria

- [ ] `startPrivateChat` API 函数正确调用 `POST /{group_chat_id}/members/{agent_name}/start-private-chat`
- [ ] `stopPrivateChat` API 函数正确调用 `POST /{group_chat_id}/members/{agent_name}/stop-private-chat`
- [ ] `privateChatStore` 管理 `activeGroupChatId`、`activeAgentName`、`lastActivityTime`、`timerId`
- [ ] `privateChatStore.startPrivateChat` 设置活跃私聊状态
- [ ] `privateChatStore.stopPrivateChat` 清除所有状态并清除计时器
- [ ] `privateChatStore.resetTimer` 重置 3 分钟计时器
- [ ] `useMembers` 暴露 `startPrivateChat` 和 `stopPrivateChat` 方法

## Architecture

参见 `.scratch/private-chat/architecture.md` 第 5 节"实现位置"中前端相关部分。

## Blocked by

- Issue #1（需要后端 API 端点可用）
