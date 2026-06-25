# Issue #2: 后端核心 - 消息拦截 + 操作限制

Status: ready-for-agent
Labels: needs-triage

## What to build

在 `send_message_to_agent` 中拦截发往私聊 Agent 的群聊消息，并在 stop/reset/compress 操作中增加 `in_private_chat` 状态检查。

**消息拦截**：在 `GroupChat.send_message_to_agent()` 方法中，现有 `stopped` 检查之后、消息投递之前，新增 `in_private_chat` 检查。如果目标 Agent 处于私聊状态，创建一条 `NOTIFICATION` 类型的自动回复消息写入群聊历史，然后 return（不投递到 Agent 队列）。自动回复内容格式：`"当前{agent_name}正在与user进行单独聊天，无法处理当前的消息：{message.content[:20]}，请稍后再发送该任务"`。

**操作限制**：在以下方法中新增 `in_private_chat` 状态检查，抛出 `StateError`（409）：
- `GroupChat.stop_member()` — 检查需在锁内（`_stop_member_locked` 入口处），确保并发安全
- `GroupChat.reset_member()`
- `GroupChatService.compress_agent_context()`

**全量压缩跳过**：在 `GroupChatService.compress_all_agents()` 中，遍历 Agent 列表时跳过 `in_private_chat` 状态的 Agent，结果中标记为 `{"status": "skipped", "reason": "in_private_chat"}`。

## Acceptance criteria

- [ ] 向 `in_private_chat` 状态的 Agent 发送群聊消息时，不投递到 Agent 队列
- [ ] 自动回复消息写入群聊历史，类型为 `NOTIFICATION`
- [ ] 自动回复内容包含 Agent 名称和原始消息前 20 字符
- [ ] 对 `in_private_chat` 状态的 Agent 执行 `stop_member` 返回 409
- [ ] 对 `in_private_chat` 状态的 Agent 执行 `reset_member` 返回 409
- [ ] 对 `in_private_chat` 状态的 Agent 执行 `compress_agent_context` 返回 409
- [ ] `compress_all_agents` 跳过 `in_private_chat` 状态的 Agent，不报错

## Architecture

参见 `.scratch/private-chat/architecture.md` 第 4 节"修改的接口"。

## Blocked by

- Issue #1（需要 `in_private_chat` 状态定义）
