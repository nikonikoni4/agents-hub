# Loop 状态可视化 - 架构约束文件

## 模块职责边界

### 后端模块

| 模块 | 职责 | 变更类型 |
|------|------|---------|
| `agents_hub/core/context/loop_models.py` | Loop/LoopNode 数据结构定义 | 无变更（`name` 字段已存在，spec 描述过时） |
| `agents_hub/core/orchestration/loop_manager.py` | Loop 定义的 CRUD 和持久化 | 无变更（已支持 `name` 字段） |
| `agents_hub/core/orchestration/loop_execution_manager.py` | LoopExecution 执行实例的 CRUD 和内存管理 | 无变更（供 API Service 查询执行状态） |
| `agents_hub/core/orchestration/loop_executor.py` | Loop 执行逻辑 | **修改**：在状态变化时调用 WebSocket 广播 |
| `agents_hub/api/routes/group_chat.py` | Loop API 路由 | **新增**：3 个 Loop API 端点 |
| `agents_hub/api/schemas/group_chats.py` | Loop API Schema | **新增**：LoopDetail、LoopNode、LoopExecution Schema |
| `agents_hub/api/services/group_chat_service.py` | Loop API 服务层 | **新增**：Loop 查询逻辑（从 LoopManager 读定义 + 从 LoopExecutionManager 读状态） |
| `agents_hub/realtime/manager.py` | WebSocket 广播 | 无变更（复用现有机制） |
| `agents_hub/realtime/dependencies.py` | 广播便捷函数 | 无变更 |

### 前端模块

| 模块 | 职责 | 变更类型 |
|------|------|---------|
| `frontend/src/core/api/groupChatApi.ts` | Loop API 函数 | **新增**：3 个 Loop API 函数 |
| `frontend/src/features/chat/components/LoopStatusPanel.tsx` | 侧边栏 Loop 状态面板 | **新增** |
| `frontend/src/features/chat/components/LoopDetailModal.tsx` | 扩展模态框 | **新增** |
| `frontend/src/features/chat/components/LoopNodeDetail.tsx` | 节点详情组件 | **新增** |
| `frontend/src/features/chat/hooks/useLoopStatus.ts` | Loop 状态管理 Hook | **新增** |
| `frontend/src/features/chat/store/loopStore.ts` | Loop 状态 Store | **新增** |
| `frontend/src/shared/types/api-schemas.ts` | Loop API 类型定义 | **新增** |
| `frontend/src/shared/adapters/loopAdapter.ts` | Loop 数据适配器 | **新增** |
| `frontend/src/layouts/RightSidebar/RightSidebar.tsx` | 右侧栏布局 | **修改**：添加 LoopStatusPanel |

## 数据流

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (React)                             │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ LoopStatus   │    │ LoopDetail   │    │ LoopNode     │      │
│  │ Panel        │───→│ Modal        │───→│ Detail       │      │
│  │ (侧边栏)     │    │ (模态框)     │    │ (节点详情)    │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                   │                │
│         └───────────────────┼───────────────────┘                │
│                             │                                    │
│                    ┌────────▼────────┐                          │
│                    │ useLoopStatus   │                          │
│                    │ (Hook)          │                          │
│                    └────────┬────────┘                          │
│                             │                                    │
│                    ┌────────▼────────┐                          │
│                    │ loopStore       │                          │
│                    │ (Zustand)       │                          │
│                    └────────┬────────┘                          │
│                             │                                    │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │ groupChatApi.ts   │
                    │ (API 客户端)      │
                    └─────────┬─────────┘
                              │ HTTP
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        后端 (FastAPI)                           │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ API Routes   │───→│ API Service  │───→│ LoopManager  │      │
│  │ (group_chat) │    │              │    │              │      │
│  └──────────────┘    └──────────────┘    └──────┬───────┘      │
│                                                  │               │
│                                         ┌────────▼────────┐    │
│                                         │ loops.jsonl     │    │
│                                         │ (文件持久化)     │    │
│                                         └─────────────────┘    │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ LoopExecutor │───→│ WebSocket    │───→│ 前端刷新      │      │
│  │ (状态变化)    │    │ Manager      │    │              │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 依赖关系

### 后端依赖

```
API Routes (group_chat.py)
  ├── API Service (group_chat_service.py)
  │   ├── LoopManager (loop_manager.py)
  │   │   └── loop_models.py (数据结构)
  │   └── LoopExecutionManager (loop_execution_manager.py)
  └── WebSocketManager (realtime/manager.py)
```

### 前端依赖

```
RightSidebar.tsx
  └── LoopStatusPanel.tsx
      ├── useLoopStatus.ts (Hook)
      │   ├── loopStore.ts (Zustand)
      │   │   └── groupChatApi.ts (API 客户端)
      │   └── loopAdapter.ts (数据适配)
      └── LoopDetailModal.tsx
          └── LoopNodeDetail.tsx
```

## 接口契约

### 后端 API

#### 1. GET /api/v1/group-chats/{group_chat_id}/loops

**请求参数**：无

**响应 Schema**：
```typescript
interface LoopListResponse {
  loops: LoopDetail[];
}

interface LoopDetail {
  loop_id: string;
  name: string | null;  // 新增字段
  nodes: LoopNode[];
  max_iterations: number;
}

interface LoopNode {
  node_id: string;
  node_type: "normal" | "terminator";
  agent_name: string;
  role_description: string;
  output_schema_prompt: string | null;
  output_schema_fields: string[] | null;
}
```

**数据来源**：从 `loops.jsonl` 文件读取 Loop 定义。

#### 2. GET /api/v1/group-chats/{group_chat_id}/loops/active

**请求参数**：无

**响应 Schema**：
```typescript
interface ActiveLoopResponse {
  loop: LoopDetail;
  execution: LoopExecution | null;  // 没有激活的 Loop 时为 null
}

interface LoopExecution {
  execution_id: string;
  status: "created" | "running" | "paused" | "completed" | "failed";
  current_iteration: number;
  current_node_index: number;
  error_message: string | null;
}
```

**数据来源**：
- Loop 定义：从 `loops.jsonl` 文件读取
- Loop 执行状态：从 `LoopExecutionManager` 获取（仅当 Loop 激活时）
- 如果没有激活的 Loop，返回 `list_loops` 中的第一个 Loop 的节点定义（无执行状态）

#### 3. GET /api/v1/group-chats/{group_chat_id}/loops/{loop_id}

**请求参数**：无

**响应 Schema**：同 `ActiveLoopResponse`

**数据来源**：同上

### WebSocket 通知

**触发时机**：
- Loop 启动（start_loop）
- Loop 停止（stop_loop）
- Loop 状态变更（RUNNING → PAUSED/COMPLETED/FAILED）
- Loop 节点执行完成（current_node_index 变化）

**通知机制**：调用 `broadcast_group_chat_refresh(group_chat_id)` 发送 RefreshSignal。

**前端处理**：
- 监听 WebSocket RefreshSignal 事件
- 收到事件后自动重新请求 `GET /loops/active` 获取最新状态
- 保持当前选中的 Loop（如果是通过下拉菜单选择的）

## 实现位置

### 后端文件修改

1. **Loop 数据结构**：`agents_hub/core/context/loop_models.py`
   - 无变更（`name` 字段已存在，spec 描述过时）
   - 验证：`name: str | None = None` 在第 148 行

2. **LoopManager**：`agents_hub/core/orchestration/loop_manager.py`
   - 无变更（已支持 `name` 字段的创建和查询）
   - 验证：`create_loop()` 参数中有 `name`，`list_loops()` 返回中包含 `name`

3. **MCP 工具**：`agents_hub/mcp/server.py`
   - 无变更（`create_loop` 工具已支持 `name` 参数）
   - 验证：第 1097-1158 行

4. **新增 API Schema**：`agents_hub/api/schemas/group_chats.py`
   - LoopDetailSchema
   - LoopNodeSchema
   - LoopExecutionSchema
   - LoopListResponseSchema
   - ActiveLoopResponseSchema

5. **新增 API 路由**：`agents_hub/api/routes/group_chat.py`
   - `get_loops()` - 获取 Loop 列表
   - `get_active_loop()` - 获取激活的 Loop
   - `get_loop()` - 获取指定 Loop

6. **新增 API 服务**：`agents_hub/api/services/group_chat_service.py`
   - `get_loops()` - 从文件读取 Loop 定义
   - `get_active_loop()` - 从文件读取定义 + 从 core 获取执行状态
   - `get_loop()` - 同上

7. **WebSocket 通知**：`agents_hub/core/orchestration/loop_executor.py`
   - **新增**：在 `_cleanup()` 方法中调用 `broadcast_group_chat_refresh()`
   - **新增**：在 `_emergency_stop()` 方法中调用 `broadcast_group_chat_refresh()`
   - **新增**：在 `_handle_node_completion()` 方法中调用 `broadcast_group_chat_refresh()`（当 current_node_index 变化时）
   - 验证：当前 LoopExecutor 没有 WebSocket 广播调用，需要新增

### 前端文件新增/修改

1. **新增 API 类型**：`frontend/src/shared/types/api-schemas.ts`
   - LoopDetail、LoopNode、LoopExecution 类型定义

2. **新增适配器**：`frontend/src/shared/adapters/loopAdapter.ts`
   - `adaptLoopDetail()` - API 响应 -> 前端领域模型
   - `adaptLoopNodeList()` - 批量转换

3. **新增 API 函数**：`frontend/src/core/api/groupChatApi.ts`
   - `getLoops(chatId)` - 获取 Loop 列表
   - `getActiveLoop(chatId)` - 获取激活的 Loop
   - `getLoop(chatId, loopId)` - 获取指定 Loop

4. **新增 Store**：`frontend/src/features/chat/store/loopStore.ts`
   - `useLoopStore` - 管理 Loop 状态（列表、当前选中、执行状态）

5. **新增 Hook**：`frontend/src/features/chat/hooks/useLoopStatus.ts`
   - `useLoopStatus()` - 封装 Loop 状态查询和切换逻辑

6. **新增组件**：
   - `frontend/src/features/chat/components/LoopStatusPanel.tsx` - 侧边栏 Loop 状态面板
   - `frontend/src/features/chat/components/LoopDetailModal.tsx` - 扩展模态框
   - `frontend/src/features/chat/components/LoopNodeDetail.tsx` - 节点详情组件

7. **修改右侧栏**：`frontend/src/layouts/RightSidebar/RightSidebar.tsx`
   - 在 Pinned 模块下方添加 LoopStatusPanel

## 相关文档

### Spec 文档
- **Loop 循环执行**：`docs/specs/2026-06-21-loop.md` - Loop 功能的完整规格定义
- **Realtime 模块**：`docs/specs/2026-06-06-realtime.md` - WebSocket 连接管理和广播机制
- **Frontend Features**：`docs/specs/2026-06-06-frontend-features.md` - 前端模块组织和状态管理
- **Pinned Messages**：`docs/specs/2026-06-06-pinned-messages.md` - 右侧栏 Pinned 模块参考

### Flow 文档
- **Loop 生命周期**：`docs/flows/loop-lifecycle.md` - Loop 的状态流转和生命周期

### 编码规则
- **后端编码风格**：`docs/coding-rules/backend-style.md` - Schema 定义规范
- **前端样式层级**：`docs/coding-rules/frontend-style-layers.md` - 组件样式规范
- **前端测试放置**：`frontend/CLAUDE.md` - 测试文件放置规则

## 设计决策

### 1. Loop 数据结构 name 字段（已存在）

**现状**：Loop 数据结构已有 `name: str | None = None` 字段（loop_models.py 第 148 行）。

**验证结果**：
- Loop.to_dict() 包含 name 字段
- Loop.from_dict() 支持 name 字段（向后兼容旧数据）
- LoopManager.create_loop() 支持 name 参数
- LoopManager.list_loops() 返回 name 字段
- MCP create_loop 工具支持 name 参数

**约束**：
- `name` 字段可选，为 `None` 时前端显示 loop_id
- 无需修改后端代码，spec 描述过时

### 2. 分离 Loop 定义和执行状态

**决策**：API 返回的数据包含两部分，定义部分从文件读取，状态部分从 core 获取。

**理由**：
- Loop 定义是持久化的，存储在 `loops.jsonl` 文件中
- Loop 执行状态是内存中的，由 `LoopExecutionManager` 管理
- 分离设计符合 SSOT 原则

**约束**：
- 只有激活的 Loop 才有执行状态
- 没有激活的 Loop 时，返回第一个 Loop 的定义（无执行状态）

### 3. WebSocket 通知机制（需要新增）

**现状**：LoopExecutor 当前没有 WebSocket 广播调用。

**决策**：在 LoopExecutor 的关键状态变化时调用 `broadcast_group_chat_refresh()`。

**理由**：
- 复用现有的 WebSocket 通知机制（RefreshSignal）
- 前端已有处理 RefreshSignal 的逻辑（用于 Pinned 消息等）
- 保持实时性，用户无需手动刷新

**需要新增广播的位置**：
1. `_cleanup()` - Loop 完成或失败时
2. `_emergency_stop()` - Loop 紧急停止时
3. `_handle_node_completion()` - 当 current_node_index 变化时（节点执行完成）

**约束**：
- 需要注入 `broadcast_group_chat_refresh` 回调或直接调用
- 前端需要保持当前选中的 Loop（如果是通过下拉菜单选择的）

## 已知风险

1. **spec 描述过时**：Loop spec 中没有列出 `name` 字段，但实际代码已有。需要更新 spec 文档。

2. **WebSocket 通知新增**：LoopExecutor 当前没有 WebSocket 广播调用，需要在关键位置新增。需要确保广播调用不会阻塞主循环。

3. **前端状态管理**：下拉菜单切换 Loop 时，需要正确管理当前选中的 Loop，避免状态混乱。

4. **空状态处理**：当群聊没有 Loop 时，需要显示空状态提示。

5. **数据分离一致性**：Loop 定义从文件读取，执行状态从 core 获取，需要确保两者的数据一致性。
