# Issue #4: 前端 UI - 邀请单聊 + 状态显示

Status: ready-for-agent
Labels: needs-triage

## What to build

在群聊成员管理弹窗中增加"邀请单聊"功能入口，并在成员列表中显示"单聊中"状态。

**邀请单聊按钮**：在 `RightSidebar` 的 `MemberItem` 组件中，`⋮` 按钮触发的下拉菜单中新增"邀请单聊"选项（与停止、重置并列）。点击后：
1. 检查 `useCompressStatusStore`，如果 Agent 正在压缩中，弹出 toast 拒绝
2. 调用 `startPrivateChat` API
3. 成功后，右侧栏切换到单聊 tab，显示 SingleChatPanel

**Manager 限制**：通过 `agent_name === config.default_manager_name` 判断，Manager 成员的下拉菜单中不显示"邀请单聊"选项。

**状态显示**：在 `RightSidebar` 的 `MemberItem` 组件中，新增 `in_private_chat` 状态标签，显示为"单聊中"，使用独立的样式类（如 `statusPrivateChat`）。

**补充修复**：当前 `MemberItem` 状态渲染缺少 `in_loop` 显示，实现时需一并修复，添加 `in_loop` 状态标签。

## Acceptance criteria

- [ ] 非 Manager 成员的 `⋮` 下拉菜单中显示"邀请单聊"选项
- [ ] Manager 成员的下拉菜单中不显示"邀请单聊"选项
- [ ] 点击"邀请单聊"调用 `startPrivateChat` API
- [ ] API 成功后右侧栏切换到单聊 tab
- [ ] 成员列表中该 Agent 显示"单聊中"状态标签
- [ ] 压缩中（`pendingAgents` 包含该 Agent）点击邀请弹出 toast 拒绝
- [ ] API 失败（409/403）时显示对应的错误 toast

## Architecture

参见 `.scratch/private-chat/architecture.md` 第 5 节"实现位置"中 RightSidebar 部分。

## Blocked by

- Issue #3（需要 `privateChatStore` 和 `useMembers` 中的私聊方法）
