# Issue 05: 节点详情面板

Status: ready-for-agent
Type: AFK
Blocked by: 04-loop-detail-modal
User stories covered: #6 (节点提示词)

## What to build

在扩展模态框中添加节点详情面板，点击节点显示该节点的提示词信息。

**前端组件**：
- 创建 `features/chat/components/LoopNodeDetail.tsx`
  - 显示节点的 role_description（职责描述）
  - 显示节点的 output_schema_prompt（输出格式提示词）
  - 显示节点的 output_schema_fields（必需字段列表）

**集成**：
- 在 LoopDetailModal 中添加点击事件，点击节点显示 LoopNodeDetail
- 节点详情面板显示在节点图右侧

**架构约束**：
- 参考 `.scratch/loop-visualization/architecture.md`
- 遵循前端分层架构

## Acceptance criteria

- [ ] LoopNodeDetail 正确显示节点的 role_description
- [ ] LoopNodeDetail 正确显示节点的 output_schema_prompt
- [ ] LoopNodeDetail 正确显示节点的 output_schema_fields
- [ ] 点击节点正确显示详情面板
- [ ] 测试：组件测试通过

## Blocked by

- 04-loop-detail-modal（需要 LoopDetailModal 组件）
