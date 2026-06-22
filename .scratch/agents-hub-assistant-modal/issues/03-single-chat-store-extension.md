# Issue 03: singleChatStore 扩展

Status: ready-for-agent
Type: AFK
Blocked by: None - can start immediately
User stories covered: 17, 18, 19

## What to build

扩展 `singleChatStore`，添加弹窗状态管理。

**状态扩展**：
- 添加 `isAssistantModalOpen: boolean` 状态，控制 Agents Hub 助手弹窗的显隐
- 添加 `openAssistantModal()` 和 `closeAssistantModal()` 方法

**数据复用**：
- 弹窗复用现有的 `singleChats`、`activeSingleChatId`、`draftChat` 等状态
- 不创建新的消息列表或会话列表
- 弹窗内的消息发送/接收与侧边栏单聊完全相同

**双入口同步**：
- 通过弹窗发送的消息，侧边栏单聊也会更新
- 通过侧边栏单聊发送的消息，弹窗内也会显示
- 共享同一个 `activeSingleChatId`

**集成位置**：
- 在 `AgentsHubAssistantModal` 中使用 `isAssistantModalOpen` 控制显隐
- 在 `LeftSidebar` 中调用 `openAssistantModal()` 打开弹窗
- 在 `SessionList` 中点击 Agents Hub 助手单聊时，可选择打开弹窗或保持现有行为

**设计决策**：
- 弹窗状态放在 `singleChatStore` 而不是组件本地状态，因为需要跨组件访问
- 不创建新的 store，保持数据层统一
- 双入口共享同一个 `activeSingleChatId`，确保数据同步

## Acceptance criteria

- [ ] 在 `singleChatStore` 中添加 `isAssistantModalOpen` 状态
- [ ] 添加 `openAssistantModal()` 方法
- [ ] 添加 `closeAssistantModal()` 方法
- [ ] 弹窗复用现有的 `singleChats`、`activeSingleChatId`、`draftChat`
- [ ] 通过弹窗发送的消息，侧边栏单聊也更新
- [ ] 通过侧边栏单聊发送的消息，弹窗内也显示
- [ ] 双入口共享同一个 `activeSingleChatId`

## Blocked by

None - can start immediately

## 相关文档

- PRD：`.scratch/agents-hub-assistant-modal/PRD.md`
- Issue 00：`00-agents-hub-assistant-modal.md`
- singleChatStore：`frontend/src/features/single-chat/store/singleChatStore.ts`
