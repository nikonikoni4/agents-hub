# Issue 03: 侧边栏 Loop 状态面板（基础）

Status: completed
Type: AFK
Blocked by: 02-loop-active-api
User stories covered: #1 (看到Loop状态), #2 (节点列表), #3 (执行节点), #4 (执行状态), #7 (下拉菜单), #8 (未激活状态), #12 (空状态)

## What to build

在右侧栏 Pinned 模块下方添加 Loop 状态面板，显示 Loop 节点列表和执行状态。

**前端组件**：
- 创建 `features/chat/components/LoopStatusPanel.tsx`
  - 下拉菜单：切换显示不同的 Loop 定义（显示 Loop 名称，无名称时显示 loop_id）
  - 节点列表：垂直排列，显示节点名称和状态样式
    - 已完成节点：绿色
    - 当前执行节点：蓝色
    - 待执行节点：灰色
  - 状态标识：显示 Loop 执行状态（Running/Paused/Completed/Failed/未激活）
  - 进度显示：显示当前迭代次数
  - 空状态：显示"暂无Loop定义"

**集成**：
- 修改 `layouts/RightSidebar/RightSidebar.tsx`，在 Pinned 模块下方添加 LoopStatusPanel

**架构约束**：
- 参考 `.scratch/loop-visualization/architecture.md`
- 遵循前端分层架构：components -> hooks -> store -> core
- 遵循前端样式层级规则（docs/coding-rules/frontend-style-layers.md）

## Acceptance criteria

- [ ] LoopStatusPanel 组件正确显示 Loop 节点列表
- [ ] 下拉菜单可以切换不同的 Loop 定义
- [ ] 节点状态样式正确（已完成/当前执行/待执行）
- [ ] 状态标识正确显示 Loop 执行状态
- [ ] 未激活的 Loop 显示为灰色状态
- [ ] 空状态正确显示"暂无Loop定义"
- [ ] RightSidebar 中正确集成 LoopStatusPanel
- [ ] 测试：组件测试通过

## Blocked by

- 01-loop-list-api（需要 getLoops() 获取 Loop 列表用于下拉菜单）
- 02-loop-active-api（需要 getActiveLoop() 和 Loop Store）
