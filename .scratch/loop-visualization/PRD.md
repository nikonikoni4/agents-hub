# Loop 状态可视化 PRD

## Problem Statement

用户在使用Agents Hub的Loop功能时，无法直观地看到当前群聊中Loop的执行状态和节点进度。Loop的执行状态（CREATED/RUNNING/PAUSED/COMPLETED/FAILED）和当前执行到哪个节点，这些信息对于监控和管理循环任务至关重要。目前用户只能通过MCP工具查询Loop状态，缺乏可视化的界面来实时监控。

## 关键概念澄清

### "激活"的定义

**激活（Active）**：指Loop存在于内存中，而不是指RUNNING状态。

- **激活条件**：只有通过`start_loop`工具启动的Loop才会被加载到内存中
- **激活状态**：Loop在内存中，可以是RUNNING、PAUSED、COMPLETED、FAILED中的任何状态
- **未激活状态**：Loop不在内存中，只有节点定义（从文件获取），没有执行状态
- **当前群聊同时只能有一个激活的Loop**
- **create_loop不会激活Loop**：`create_loop`只创建Loop定义并保存到文件，不会加载到内存

### Loop状态说明

Loop有5种状态（定义在CONTEXT.md中）：
1. **CREATED**：已创建，未启动（在内存中，但没有执行实例）
2. **RUNNING**：运行中（有执行实例，正在执行）
3. **PAUSED**：已暂停（有执行实例，已暂停）
4. **COMPLETED**：正常完成（有执行实例，已完成）
5. **FAILED**：失败（超时/出错/达到最大循环次数）

**重要区分**：
- **激活 ≠ RUNNING**：激活是指Loop在内存中，可以是任何状态（包括CREATED）
- **执行状态**：只有RUNNING、PAUSED、COMPLETED、FAILED有执行实例（execution不为null）
- **CREATED状态**：Loop是激活的（在内存中），但没有执行状态（execution为null）

### 前端显示逻辑

1. **未激活**：Loop不在内存中，显示灰色状态标识，节点正常显示
2. **激活但无执行状态**（CREATED）：显示"已创建"状态标识，节点正常显示
3. **激活且有执行状态**（RUNNING/PAUSED/COMPLETED/FAILED）：显示对应状态标识，节点根据执行状态显示不同样式

## Solution

在前端右侧栏的群里tab的pinned模块下方，添加Loop可视化模块。该模块提供：

1. **侧边栏缩略图**：以垂直节点列表的形式展示Loop的节点结构和当前执行状态
2. **扩展模态框**：点击缩略图后弹出，以从上到下的节点图形式展示详细的Loop状态，点击节点可查看该节点的提示词信息
3. **下拉菜单**：用于切换显示不同的Loop定义

## User Stories

1. 作为用户，我希望在右侧栏看到当前群聊的Loop状态，以便快速了解循环任务的执行进度
2. 作为用户，我希望看到Loop的节点列表，以便了解循环包含哪些执行步骤
3. 作为用户，我希望看到当前执行到哪个节点，以便监控循环进度
4. 作为用户，我希望看到Loop的执行状态（RUNNING/PAUSED/COMPLETED/FAILED），以便判断循环是否正常运行
5. 作为用户，我希望点击缩略图后查看详细的Loop状态，以便获取更多信息
6. 作为用户，我希望在扩展模态框中点击节点查看该节点的提示词信息，以便了解节点的职责和输出要求
7. 作为用户，我希望通过下拉菜单切换显示不同的Loop，以便查看群聊中的其他Loop定义
8. 作为用户，我希望看到未激活的Loop显示为灰色状态，以便区分当前活跃和非活跃的Loop
9. 作为用户，我希望在扩展模态框中看到Loop的迭代次数，以便了解循环执行了多少轮
10. 作为用户，我希望在扩展模态框中看到Loop的错误信息（如果失败），以便了解失败原因
11. 作为用户，我希望在页面刷新时自动获取最新的Loop状态，以便实时监控
12. 作为用户，我希望在没有Loop时看到空状态提示，以便知道当前群聊没有Loop

## 原型分析与修改说明

**原型位置**：`_temp/loop-status-v4.html`

### 原型现状

#### 侧边栏缩略图（已完成部分）
- ✅ 状态标识（statusBadge）：支持Running、Paused、Failed状态
- ✅ 进度显示（thumbProgress）：显示当前迭代次数
- ✅ 节点列表（thumbNodes）：垂直排列，显示节点名称
- ✅ 节点状态样式：已完成（绿色）、当前执行（蓝色）、待执行（灰色）
- ✅ 空状态（emptyState）：显示"No active loop"

#### 扩展模态框（已完成部分）
- ✅ 状态标识和迭代次数显示
- ✅ 水平节点图（nodeGraph）：显示节点状态和连接箭头
- ✅ loopBack区域：显示循环信息
- ✅ 错误信息展示（modalError）

### 需要添加的元素

#### 侧边栏缩略图
1. **下拉菜单**：在模块标题"Loop"右侧添加下拉菜单，用于切换不同的Loop定义
   - 显示Loop名称（如果有）或loop_id
   - 选中的Loop高亮显示
2. **未激活状态**：添加"未激活"状态标识
   - 节点正常显示，但状态标识为灰色"未激活"
   - 进度显示为空或"--"

#### 扩展模态框
1. **节点图方向修改**：从水平（从左到右）改为垂直（从上到下）
2. **节点详情面板**：在节点图右侧添加详情面板
   - 点击节点后显示该节点的提示词信息
   - 包含：role_description、output_schema_prompt、output_schema_fields
3. **闭环箭头**：当前版本暂不实现，后续迭代添加

### 需要修改的元素

#### 侧边栏缩略图
1. **空状态文案**：从"No active loop"改为"暂无Loop定义"
2. **模块标题**：添加下拉菜单切换功能

#### 扩展模态框
1. **节点图布局**：从水平改为垂直
2. **节点交互**：添加点击事件，显示节点详情

## Implementation Decisions

### API设计

新增3个API端点：

**数据获取策略说明**：
- **Loop定义**（节点信息）：从文件中获取（`loops.jsonl`），不依赖core模块
- **Loop执行状态**：从core模块获取（LoopExecutionManager），只有激活的Loop才有执行状态
- **分离原则**：API返回的数据包含两部分，定义部分从文件读取，状态部分从core获取

1. **获取Loop列表**：`GET /api/v1/group-chats/{group_chat_id}/loops`
   - 返回当前群聊的所有Loop ID列表
   - 响应：`{ loops: [{ loop_id: string }] }`

2. **获取激活的Loop**：`GET /api/v1/group-chats/{group_chat_id}/loops/active`
   - 返回当前群聊中激活的Loop的节点定义和执行状态
   - **数据来源**：节点定义从文件获取，执行状态从core获取
   - 如果没有激活的Loop，返回`list_loops`中的第一个Loop的节点定义（无执行状态）
   - 响应：`{ loop: LoopDetail, execution: LoopExecution | null }`

3. **获取指定的Loop**：`GET /api/v1/group-chats/{group_chat_id}/loops/{loop_id}`
   - 返回指定Loop的节点定义和执行状态（如果激活了）
   - **数据来源**：节点定义从文件获取，执行状态从core获取（仅当Loop激活时）
   - 响应：`{ loop: LoopDetail, execution: LoopExecution | null }`

### 数据获取策略

**重要原则**：Loop定义和Loop执行状态是分离的，获取方式不同：

1. **Loop定义**（节点信息）：从文件中获取
   - 文件路径：`local_data/teams/<team_name>/<project_path>/<group_chat_id>/loops.jsonl`
   - 包含：loop_id、name、nodes、max_iterations
   - 不依赖core模块，直接读取JSONL文件

2. **Loop执行状态**：从core模块获取
   - 通过LoopExecutionManager获取
   - 包含：execution_id、status、current_iteration、current_node_index、error_message
   - 只有激活的Loop才有执行状态

### 数据模型

**LoopDetail**（节点定义，从文件获取）：
- `loop_id`: string
- `name`: string（Loop名称，可选）
- `nodes`: LoopNode[]（节点列表）
- `max_iterations`: number

**LoopNode**（节点定义，从文件获取）：
- `node_id`: string
- `node_type`: "normal" | "terminator"
- `agent_name`: string
- `role_description`: string
- `output_schema_prompt`: string | null
- `output_schema_fields`: string[] | null

**LoopExecution**（执行状态，从core获取）：
- `execution_id`: string
- `status`: "created" | "running" | "paused" | "completed" | "failed"
- `current_iteration`: number
- `current_node_index`: number
- `error_message`: string | null

### 前端交互流程

1. **页面加载**：
   - 打开群聊 → 请求`GET /loops`获取Loop列表 → 请求`GET /loops/active`获取激活的Loop（或第一个Loop的定义）
   - 如果返回的Loop有执行状态，显示具体状态；如果没有，显示"未激活"

2. **下拉菜单切换**：
   - 用户从下拉菜单选择Loop ID → 请求`GET /loops/{loop_id}`获取该Loop的定义和状态
   - 更新侧边栏缩略图和扩展模态框

3. **扩展模态框**：
   - 点击侧边栏缩略图 → 打开扩展模态框
   - 模态框中显示从上到下的节点图
   - 点击节点 → 在右侧显示该节点的提示词信息（role_description, output_schema_prompt, output_schema_fields）

### 前端组件结构

- **LoopStatusPanel**：侧边栏中的Loop状态面板
  - 包含下拉菜单、缩略图、状态标识
- **LoopDetailModal**：扩展模态框
  - 包含节点图、节点详情面板
- **LoopNodeDetail**：节点详情组件
  - 显示节点的提示词信息

### 状态显示规则

- **未激活**：执行数据为null时，显示灰色状态标识
- **RUNNING**：蓝色状态标识，显示当前迭代次数
- **PAUSED**：黄色状态标识，显示当前迭代次数
- **COMPLETED**：绿色状态标识，显示总迭代次数
- **FAILED**：红色状态标识，显示错误信息

### 闭环箭头

当前版本暂不实现闭环箭头，后续迭代考虑添加。

### WebSocket实时更新

当后端Loop状态发生变化时，需要通过WebSocket通知前端刷新：

1. **触发时机**：
   - Loop启动（start_loop）
   - Loop停止（stop_loop）
   - Loop状态变更（RUNNING → PAUSED/COMPLETED/FAILED）
   - Loop节点执行完成（current_node_index变化）

2. **通知机制**：
   - 调用现有的group chat WebSocket回调函数
   - 发送RefreshSignal事件，前端收到后重新请求`GET /loops/active`获取最新状态

3. **前端处理**：
   - 监听WebSocket RefreshSignal事件
   - 收到事件后自动刷新Loop状态显示
   - 保持当前选中的Loop（如果是通过下拉菜单选择的）

## Testing Decisions

### 测试边界

1. **API层测试**：
   - 测试`GET /loops`返回正确的Loop列表
   - 测试`GET /loops/active`在有激活Loop时返回节点定义和执行状态
   - 测试`GET /loops/active`在无激活Loop时返回第一个Loop的节点定义（无执行状态）
   - 测试`GET /loops/{loop_id}`返回指定Loop的节点定义和执行状态

2. **前端组件测试**：
   - 测试LoopStatusPanel在有Loop时正确显示缩略图
   - 测试LoopStatusPanel在无Loop时显示空状态
   - 测试下拉菜单切换Loop后更新显示
   - 测试扩展模态框正确显示节点图
   - 测试点击节点显示节点详情

3. **集成测试**：
   - 测试从页面加载到显示Loop状态的完整流程
   - 测试下拉菜单切换Loop的完整流程

### 测试数据

- 使用现有的Loop测试数据（如果存在）
- 创建测试用的Loop定义和执行状态数据

## Out of Scope

1. **闭环箭头**：当前版本暂不实现节点间的闭环箭头
2. **Loop创建/编辑**：本PRD只涉及可视化，不涉及Loop的创建或编辑功能
3. **Loop执行控制**：本PRD不包含启动/停止Loop的功能
4. **实时更新**：当前版本通过刷新获取最新状态，暂不通过WebSocket实时推送
5. **Loop删除**：本PRD不包含Loop删除功能
6. **节点详情编辑**：本PRD只展示节点提示词，不支持编辑

## Further Notes

### 依赖关系

- 依赖现有的Loop后端实现（LoopManager, LoopExecutionManager）
- 依赖现有的前端右侧栏组件结构
- 依赖现有的API客户端和状态管理机制

### 后续迭代

1. 添加闭环箭头显示
2. 通过WebSocket实现实时状态更新
3. 添加Loop执行控制功能（启动/停止/暂停）
4. 添加Loop创建/编辑功能
5. 添加节点详情编辑功能
