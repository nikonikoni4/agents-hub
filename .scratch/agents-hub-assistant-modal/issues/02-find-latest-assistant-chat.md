# Issue 02: 会话查找逻辑

Status: ready-for-agent
Type: AFK
Blocked by: None - can start immediately
User stories covered: 11, 12

## What to build

实现会话查找逻辑，确保每次打开弹窗时继续上次的对话。

**查找逻辑**：
1. 从 `singleChatStore.singleChats` 中筛选 `agent_name === 'Agents-Hub-Assistant'` 的单聊
2. 按 `last_active_at` 降序排序，取第一个
3. 如果找到，打开该会话（`openSingleChat(id)`）
4. 如果未找到，创建新的 draft 单聊（`openDraftChat(...)`）

**函数定义**：
- 创建 `findLatestAssistantChat` 函数，位于 `frontend/src/features/single-chat/utils/` 或 hooks 中
- 输入：`singleChats: SingleChatApiResponse[]`
- 输出：`SingleChatApiResponse | null`

**"开始新对话"功能**：
- 弹窗头部添加"开始新对话"按钮（具体位置由 UI 设计师决定）
- 点击行为：
  - 清除当前 `activeSingleChatId`
  - 创建新的 draft 单聊
  - 清空消息列表（等待首次发送时创建后端单聊）

**集成位置**：
- 在 `AgentsHubAssistantModal` 中，打开弹窗时调用查找逻辑
- "开始新对话"按钮集成到弹窗头部

**设计决策**：
- 会话查找基于 `agent_name` 而不是 `single_chat_name`
- 使用 `last_active_at` 而不是 `created_at`，确保找到最近活跃的会话
- 如果没有历史会话，自动创建新的 draft 单聊

## Acceptance criteria

- [ ] 创建 `findLatestAssistantChat` 函数
- [ ] 按 `agent_name === 'Agents-Hub-Assistant'` 筛选
- [ ] 按 `last_active_at` 降序排序，取第一个
- [ ] 如果找到，调用 `openSingleChat(id)`
- [ ] 如果未找到，调用 `openDraftChat(...)`
- [ ] 弹窗头部添加"开始新对话"按钮
- [ ] 点击"开始新对话"清除当前会话，创建新的 draft
- [ ] 集成到 `AgentsHubAssistantModal` 中

## Blocked by

None - can start immediately

## 相关文档

- PRD：`.scratch/agents-hub-assistant-modal/PRD.md`
- Issue 00：`00-agents-hub-assistant-modal.md`
- singleChatStore：`frontend/src/features/single-chat/store/singleChatStore.ts`
