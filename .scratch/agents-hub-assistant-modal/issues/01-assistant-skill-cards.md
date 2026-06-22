# Issue 01: AssistantSkillCards 技能卡片组件

Status: ready-for-agent
Type: AFK
Blocked by: None - can start immediately
User stories covered: 6, 7, 8, 9, 10

## What to build

创建技能卡片组件，显示在输入框上方，提供常用操作的快捷入口。

**组件结构**：
- 创建 `AssistantSkillCards` 组件，位于 `frontend/src/features/single-chat/components/`
- 显示 3 个技能卡片：创建 Agent、训练 Agent、创建群组
- 卡片样式：水平排列，可点击，有 hover 效果

**技能数据**：
```
[
  { id: 'create-agent', label: '创建 Agent', prompt: '帮助我创建一个 agent' },
  { id: 'train-agent', label: '训练 Agent', prompt: '帮助我训练 agent' },
  { id: 'create-group', label: '创建群组', prompt: '帮助我创建群组' }
]
```

**交互行为**：
- 点击卡片：将 `prompt` 预填到输入框（textarea）
- 不直接发送消息，用户可修改后再发送
- 预填后，输入框获得焦点

**集成位置**：
- 在 `AgentsHubAssistantModal` 中，技能卡片显示在输入框上方
- 输入框和技能卡片之间有视觉分隔

**设计决策**：
- 技能卡片是提示用户可用功能的 UI 元素
- 点击后预填提示词，而不是直接发送
- 用户可以根据具体需求修改提示词后再发送

## Acceptance criteria

- [ ] 创建 `AssistantSkillCards` 组件
- [ ] 显示 3 个技能卡片：创建 Agent、训练 Agent、创建群组
- [ ] 卡片水平排列，有 hover 效果
- [ ] 点击卡片将 prompt 预填到输入框
- [ ] 预填后输入框获得焦点
- [ ] 不直接发送消息
- [ ] 集成到 `AgentsHubAssistantModal` 中

## Blocked by

None - can start immediately

## 相关文档

- PRD：`.scratch/agents-hub-assistant-modal/PRD.md`
- Issue 00：`00-agents-hub-assistant-modal.md`
