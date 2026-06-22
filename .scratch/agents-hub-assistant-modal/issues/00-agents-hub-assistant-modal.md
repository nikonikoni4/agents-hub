# Issue 00: AgentsHubAssistantModal 弹窗组件

Status: ready-for-agent
Type: AFK
Blocked by: None - can start immediately
User stories covered: 1, 2, 3, 4, 5, 13, 14, 15, 16, 19, 20

## What to build

创建 Agents Hub 助手的独立弹窗组件，复用现有单聊组件。

**组件结构**：
- 创建 `AgentsHubAssistantModal` 组件，位于 `frontend/src/features/single-chat/components/`
- 遵循项目统一的 modal 模式：overlay + dialog，`isOpen` prop 控制显隐
- 弹窗尺寸：占屏幕 60-70%，居中显示

**功能要求**：
- 弹窗头部：显示"Agents Hub 助手"标题、助手头像、关闭按钮
- 消息列表：复用现有 `MessageBubble` 组件，支持普通消息、Markdown 渲染、工具调用卡片、导航卡片
- 输入框：复用现有 textarea，支持 Enter 发送、Shift+Enter 换行
- 流式输出：支持实时显示助手回复
- 关闭方式：ESC 键、点击 overlay、关闭按钮

**组件复用**：
- `MessageBubble`（来自 `SingleChatPanel`）
- `MarkdownRenderer`
- `ToolCallCard`
- `NavigationCard`
- `AvatarImage`

**不复用**：
- `SingleChatPanel` 整体（需要自定义头部和技能卡片区域）

**架构约束**：
- 弹窗只是 `SingleChatPanel` 的另一种显示方式
- 底层数据流完全相同：`getSingleChatMessages` API、`streamSSE` 发送
- 状态管理：`activeSingleChatId`、`draftChat`

## Acceptance criteria

- [ ] 创建 `AgentsHubAssistantModal` 组件，遵循项目 modal 模式
- [ ] 弹窗尺寸占屏幕 60-70%，居中显示
- [ ] 头部显示标题、助手头像、关闭按钮
- [ ] 消息列表复用现有 `MessageBubble` 组件
- [ ] 支持 Markdown 渲染、工具调用卡片、导航卡片
- [ ] 输入框支持 Enter 发送、Shift+Enter 换行
- [ ] 支持流式输出
- [ ] 支持 ESC 键关闭
- [ ] 支持点击 overlay 关闭
- [ ] 遵循项目统一的 modal 样式

## Blocked by

None - can start immediately

## 相关文档

- PRD：`.scratch/agents-hub-assistant-modal/PRD.md`
- 现有弹窗组件：`frontend/src/shared/components/ConfirmDialog/ConfirmDialog.tsx`
- 单聊组件：`frontend/src/features/single-chat/components/SingleChatPanel.tsx`
