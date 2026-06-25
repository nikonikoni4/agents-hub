# Issue #5: 前端 UI - 私聊面板 + 退出 + 计时器

Status: ready-for-agent
Labels: needs-triage

## What to build

修改 SingleChatPanel 的退出行为，实现 3 分钟超时自动退出，并确保私聊消息流正常工作。

**退出单聊按钮**：SingleChatPanel 的 X 按钮在私聊模式下改为"退出单聊"。点击后调用 `stopPrivateChat` API，成功后关闭面板、清除私聊状态。

**计时器管理**：在 `privateChatStore` 中实现 3 分钟超时逻辑：
- `startPrivateChat` 时启动计时器
- 用户发送消息时调用 `resetTimer`（重置为 3 分钟）
- 收到 Agent 回复时调用 `resetTimer`
- 超时触发时自动调用 `stopPrivateChat` API，关闭面板，显示 toast 提示"单聊已自动退出"

**消息流复用**：私聊使用 Agent 的 `main_session` 继续对话，通过现有的 SingleChatPanel SSE 流式传输。进入私聊时以 `continue_group_chat` 模式打开 draft chat。

**WebSocket 同步**：监听 WebSocket RefreshSignal，收到后刷新成员列表，确保状态同步。

## Acceptance criteria

- [ ] SingleChatPanel X 按钮在私聊模式下显示为"退出单聊"
- [ ] 点击"退出单聊"调用 `stopPrivateChat` API，成功后关闭面板
- [ ] 3 分钟无活动自动调用 `stopPrivateChat` API
- [ ] 用户发送消息时重置计时器
- [ ] 收到 Agent 回复时重置计时器
- [ ] 超时退出后显示 toast 提示
- [ ] 退出后私聊状态完全清除（store 重置）
- [ ] WebSocket RefreshSignal 触发成员列表刷新
- [ ] 私聊使用 Agent 的 `main_session` 继续对话（消息连续）

## Architecture

参见 `.scratch/private-chat/architecture.md` 第 2 节"数据流方向"和第 6 节"关键设计决策"。

## Blocked by

- Issue #3（需要 `privateChatStore`）
- Issue #4（需要邀请单聊入口和状态显示）
