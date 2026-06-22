# Agents Hub 助手弹窗

## Problem Statement

Agents Hub 助手是系统级助手，用于创建 Agent、训练 Agent 和创建群组。当前它作为普通单聊显示在侧边栏，与普通对话混在一起，定位不清晰。用户需要一个独立的入口来访问这个系统级功能，而不是在侧边栏的单聊列表中寻找。

## Solution

将 Agents Hub 助手从侧边栏单聊中独立出来，创建一个专用的居中大弹窗。弹窗内复用现有的单聊组件（消息气泡、工具调用卡片、Markdown 渲染等），同时添加技能卡片功能，提供常用操作的快捷入口。会话具有持续性，每次打开弹窗会继续上次的对话。原有的侧边栏入口保留，两个入口共存。

## User Stories

1. 作为用户，我希望点击 Agents Hub 助手按钮后弹出独立弹窗，以便清晰地区分系统助手和普通对话
2. 作为用户，我希望弹窗内显示完整的聊天界面（消息列表、输入框、发送按钮），以便与助手进行交互
3. 作为用户，我希望弹窗内的消息展示复用现有的气泡组件，以便保持一致的视觉体验
4. 作为用户，我希望弹窗内的助手回复支持 Markdown 渲染，以便阅读格式化的内容
5. 作为用户，我希望弹窗内的工具调用以卡片形式展示，以便了解助手执行了哪些操作
6. 作为用户，我希望输入框上方显示技能卡片（创建 Agent、训练 Agent、创建群组），以便快速了解可用功能
7. 作为用户，我希望点击"创建 Agent"技能卡片后，输入框预填"帮助我创建一个 agent"，以便快速开始创建流程
8. 作为用户，我希望点击"训练 Agent"技能卡片后，输入框预填"帮助我训练 agent"，以便快速开始训练流程
9. 作为用户，我希望点击"创建群组"技能卡片后，输入框预填"帮助我创建群组"，以便快速开始创建流程
10. 作为用户，我希望预填的提示词可以修改后再发送，以便根据具体需求调整
11. 作为用户，我希望每次打开弹窗时继续上次的对话，以便保持上下文连贯
12. 作为用户，我希望弹窗提供"开始新对话"按钮，以便在需要时重新开始
13. 作为用户，我希望弹窗支持 ESC 键关闭，以便快速退出
14. 作为用户，我希望弹窗点击遮罩层关闭，以便符合通用交互习惯
15. 作为用户，我希望弹窗标题显示"Agents Hub 助手"，以便明确当前功能
16. 作为用户，我希望弹窗内显示助手头像和名称，以便识别对话对象
17. 作为用户，我希望通过侧边栏的 Agents Hub 助手按钮打开弹窗，而不是直接进入单聊
18. 作为用户，我希望在 Session 列表中点击 Agents Hub 助手的单聊时，也能打开弹窗（或在右侧栏显示，保持现有行为）
19. 作为用户，我希望弹窗内的消息支持流式输出，以便实时看到助手的回复
20. 作为用户，我希望弹窗内的输入框支持 Enter 发送、Shift+Enter 换行，以便符合通用输入习惯

## Implementation Decisions

### 任务拆分

本 PRD 拆分为以下 5 个 issue，可按依赖顺序执行：

| Issue | 标题 | 依赖 | User Stories |
|-------|------|------|--------------|
| 00 | AgentsHubAssistantModal 弹窗组件 | 无 | 1, 2, 3, 4, 5, 13, 14, 15, 16, 19, 20 |
| 01 | AssistantSkillCards 技能卡片组件 | 无 | 6, 7, 8, 9, 10 |
| 02 | 会话查找逻辑 | 无 | 11, 12 |
| 03 | singleChatStore 扩展 | 无 | 17, 18, 19 |
| 04 | 双入口共存集成 | 00, 01, 02, 03 | 17, 18 |

详见 `.scratch/agents-hub-assistant-modal/issues/` 目录。

### 1. 弹窗组件结构

创建新组件 `AgentsHubAssistantModal`，位于 `frontend/src/features/single-chat/components/` 目录下。

弹窗遵循项目统一的 modal 模式：
- overlay + dialog 结构
- `isOpen` prop 控制显隐
- 点击 overlay 关闭
- ESC 键关闭

弹窗尺寸：占屏幕 60-70%，居中显示。

### 2. 组件复用策略

弹窗内部复用以下现有组件：
- `MessageBubble`（来自 `SingleChatPanel`）：处理普通消息和导航标记消息
- `MarkdownRenderer`：渲染助手回复的 Markdown 内容
- `ToolCallCard`：展示工具调用
- `NavigationCard`：处理导航标记
- `AvatarImage`：显示助手头像

不复用 `SingleChatPanel` 整体，因为需要自定义头部和技能卡片区域。

### 3. 技能卡片组件

创建新组件 `AssistantSkillCards`，显示在输入框上方。

技能卡片数据：
```
[
  { id: 'create-agent', label: '创建 Agent', prompt: '帮助我创建一个 agent' },
  { id: 'train-agent', label: '训练 Agent', prompt: '帮助我训练 agent' },
  { id: 'create-group', label: '创建群组', prompt: '帮助我创建群组' }
]
```

点击行为：将 `prompt` 预填到输入框（textarea），用户可修改后再发送。不直接发送消息。

### 4. 数据层复用

复用现有的 `singleChatStore`，不创建新的 store。

弹窗只是 `SingleChatPanel` 的另一种显示方式，底层数据流完全相同：
- 消息获取：`getSingleChatMessages` API
- 消息发送：`streamSSE` 到 `/single-chats/messages/stream`
- 状态管理：`activeSingleChatId`、`draftChat`

### 5. 会话查找逻辑

当用户点击 Agents Hub 助手按钮打开弹窗时，需要查找最近的会话：

1. 从 `singleChatStore.singleChats` 中筛选 `agent_name === 'Agents-Hub-Assistant'` 的单聊
2. 按 `last_active_at` 降序排序，取第一个
3. 如果找到，打开该会话（`openSingleChat(id)`）
4. 如果未找到，创建新的 draft 单聊（`openDraftChat({ type: 'new', single_chat_name: 'Agents Hub 助手', agent_name: 'Agents-Hub-Assistant' })`）

### 6. 双入口共存

保留现有的两个入口：
- **入口 A（弹窗）**：侧边栏的 Agents Hub 助手按钮 → 打开弹窗
- **入口 B（侧边栏单聊）**：Session 列表中的 Agents Hub 助手单聊 → 在右侧栏/主界面显示（现有行为）

两个入口共享同一个 `singleChatStore`，数据完全同步。

### 7. "开始新对话"功能

弹窗头部或底部添加"开始新对话"按钮（具体位置由 UI 设计师决定）。

点击行为：
- 清除当前 `activeSingleChatId`
- 创建新的 draft 单聊
- 清空消息列表（等待首次发送时创建后端单聊）

### 8. 弹窗触发逻辑

修改 `LeftSidebar.tsx` 中的 Agents Hub 助手按钮点击逻辑：

当前逻辑：
```typescript
openDraftChat({
  type: 'new',
  single_chat_name: 'Agents Hub 助手',
  agent_name: 'Agents-Hub-Assistant',
});
```

新逻辑：
```typescript
// 1. 查找最近的 Agents Hub 助手单聊
const assistantChat = singleChats
  .filter(c => c.agent_name === 'Agents-Hub-Assistant')
  .sort((a, b) => new Date(b.last_active_at) - new Date(a.last_active_at))[0];

if (assistantChat) {
  openSingleChat(assistantChat.id);
} else {
  openDraftChat({
    type: 'new',
    single_chat_name: 'Agents Hub 助手',
    agent_name: 'Agents-Hub-Assistant',
  });
}

// 2. 打开弹窗
setIsAssistantModalOpen(true);
```

## Testing Decisions

### 测试边界（Seams）

1. **弹窗组件层**：`AgentsHubAssistantModal` 组件的打开/关闭、内容渲染
2. **技能卡片组件**：`AssistantSkillCards` 的点击事件、预填逻辑
3. **会话查找逻辑**：`findLatestAssistantChat` 函数的查找和回退逻辑
4. **singleChatStore 扩展**：弹窗状态管理（如 `isAssistantModalOpen`）

### 好的测试标准

- 只测试外部行为，不测试实现细节
- 测试用户可感知的交互：点击按钮 → 弹窗打开 → 显示内容
- 测试边界情况：无历史会话时的行为、会话列表为空时的行为

### 待测试模块

1. `AgentsHubAssistantModal`：打开/关闭、ESC 键、overlay 点击
2. `AssistantSkillCards`：点击预填、输入框内容更新
3. 会话查找：有历史会话时打开最近的、无历史会话时创建新的
4. 双入口同步：通过弹窗发送消息后，侧边栏单聊也更新

## Out of Scope

1. **上下文自动压缩**：当前版本不实现，仅记录需求
2. **弹窗拖拽/调整大小**：固定尺寸，不支持拖拽
3. **弹窗最小化/最大化**：只支持打开和关闭
4. **技能卡片自定义**：当前固定3个卡片，不支持用户自定义
5. **会话历史列表**：弹窗内不显示历史会话列表，只显示当前会话
6. **多会话切换**：弹窗内不支持切换不同的 Agents Hub 助手会话

## Further Notes

### 与现有单聊的关系

弹窗版本的 Agents Hub 助手与侧边栏单聊版本完全共存：
- 共享同一个 `singleChatStore`
- 共享同一套 API（`/single-chats`）
- 共享同一个后端 Agent（`Agents-Hub-Assistant`）

用户可以选择任意入口访问，数据完全同步。

### 后续迭代方向

1. 技能卡片扩展：支持更多技能（如"查看 Agent 列表"、"管理群组"）
2. 上下文自动压缩：仿照群聊的自动压缩机制
3. 会话历史：在弹窗内提供历史会话列表
4. 快捷键支持：全局快捷键打开弹窗
