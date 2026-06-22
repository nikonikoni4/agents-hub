# Issue 04: 扩展模态框（基础）

Status: ready-for-agent
Type: AFK
Blocked by: 03-loop-status-panel
User stories covered: #5 (详细状态), #9 (迭代次数), #10 (错误信息)

## What to build

创建 Loop 详情模态框，以垂直节点图形式展示详细的 Loop 状态。

**前端组件**：
- 创建 `features/chat/components/LoopDetailModal.tsx`
  - 垂直节点图：从上到下展示节点结构和连接箭头
  - 节点状态样式：与侧边栏一致（已完成/当前执行/待执行）
  - 状态标识：显示 Loop 执行状态
  - 迭代次数：显示当前迭代次数和最大迭代次数
  - 错误信息：当 Loop 失败时显示错误信息
  - **loopBack 区域**（循环回路可视化）：
    - **布局位置**：节点图底部
    - **展示内容**：
      - 当前迭代/最大迭代（例如 "第 2 轮 / 共 5 轮"）
      - 循环连线：从最后一个节点底部出发，用弧线箭头回到第一个节点顶部，表示循环回路
    - **样式**：
      - 运行中（RUNNING）：蓝色弧线箭头
      - 已完成（COMPLETED）：绿色弧线箭头
      - 已暂停（PAUSED）：黄色弧线箭头
      - 失败（FAILED）：红色弧线箭头
    - **交互**：弧线箭头上方显示当前迭代次数标签

**集成**：
- 在 LoopStatusPanel 中添加点击事件，点击缩略图打开 LoopDetailModal

**架构约束**：
- 参考 `.scratch/loop-visualization/architecture.md`
- 模态框使用垂直节点图（从上到下），不是水平（从左到右）
- 遵循前端样式层级规则

## Acceptance criteria

- [ ] LoopDetailModal 正确显示垂直节点图
- [ ] 节点状态样式正确（已完成/当前执行/待执行）
- [ ] 状态标识正确显示 Loop 执行状态
- [ ] 迭代次数正确显示
- [ ] 错误信息正确显示（当 Loop 失败时）
- [ ] 点击缩略图正确打开模态框
- [ ] 测试：组件测试通过

## Blocked by

- 03-loop-status-panel（需要 LoopStatusPanel 组件）
