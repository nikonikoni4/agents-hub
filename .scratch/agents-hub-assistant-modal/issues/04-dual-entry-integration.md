# Issue 04: 双入口共存集成

Status: ready-for-agent
Type: AFK
Blocked by: 00, 01, 02, 03
User stories covered: 17, 18

## What to build

实现双入口共存逻辑，确保弹窗入口和侧边栏入口数据同步。

**入口 A（弹窗）**：
- 侧边栏的 Agents Hub 助手按钮 → 打开弹窗
- 修改 `LeftSidebar.tsx` 中的点击逻辑：
  - 当前：`openDraftChat(...)` → 直接进入单聊
  - 新逻辑：查找最近会话 → 打开弹窗

**入口 B（侧边栏单聊）**：
- Session 列表中的 Agents Hub 助手单聊 → 在右侧栏/主界面显示（现有行为）
- 保持现有逻辑不变

**双入口同步**：
- 两个入口共享同一个 `singleChatStore`
- 通过弹窗发送的消息，侧边栏单聊也会更新
- 通过侧边栏单聊发送的消息，弹窗内也会显示
- 共享同一个 `activeSingleChatId`

**修改文件**：
- `frontend/src/layouts/LeftSidebar/LeftSidebar.tsx`：修改 Agents Hub 助手按钮点击逻辑
- 可选：在 `SessionList` 中点击 Agents Hub 助手单聊时，提供"在弹窗中打开"选项

**设计决策**：
- 弹窗入口和侧边栏入口并存，不冲突
- 数据层完全共享，确保一致性
- 用户可以选择任意入口访问，体验相同

## Acceptance criteria

- [ ] 修改 `LeftSidebar.tsx` 中的 Agents Hub 助手按钮点击逻辑
- [ ] 点击按钮时查找最近会话并打开弹窗
- [ ] 保留 Session 列表中的单聊入口（现有行为）
- [ ] 双入口共享同一个 `singleChatStore`
- [ ] 通过弹窗发送的消息，侧边栏单聊也更新
- [ ] 通过侧边栏单聊发送的消息，弹窗内也显示
- [ ] 双入口共享同一个 `activeSingleChatId`

## Blocked by

- Issue 00：弹窗组件需要先创建
- Issue 01：技能卡片组件需要先创建
- Issue 02：会话查找逻辑需要先实现
- Issue 03：singleChatStore 扩展需要先完成

## 相关文档

- PRD：`.scratch/agents-hub-assistant-modal/PRD.md`
- Issue 00：`00-agents-hub-assistant-modal.md`
- Issue 01：`01-assistant-skill-cards.md`
- Issue 02：`02-find-latest-assistant-chat.md`
- Issue 03：`03-single-chat-store-extension.md`
- LeftSidebar：`frontend/src/layouts/LeftSidebar/LeftSidebar.tsx`
