# 群聊 Fork 功能实现计划

## 1. 需求概述

为群聊系统添加 fork（复制/分叉）功能，让用户可以从现有群聊创建一个新的群聊副本。

**核心要求**：
- 前端：群聊下拉菜单添加 "fork" 选项，点击后弹出重命名框
- 后端：创建新群聊，复制聊天记录（不复制 runtime 数据）
- Session 处理：通过平台 fork 功能获取新 session_id

## 2. 技术方案

### 2.1 整体流程

```
用户点击 "fork" → 输入新名称 → 调用 fork API →
  1. 读取源群聊消息历史
  2. 创建新群聊目录（新 group_chat_id）
  3. 复制消息历史到新群聊
  4. 创建 agent_member.json（保留源 session_id 作为 fork_from）
  5. 保存元数据
  6. 启动新群聊（_initialize_new_members 使用 fork 机制）
  7. 返回新群聊信息
```

### 2.2 Session Fork 机制

**关键发现**：agent_bridge 已支持 `fork_from` 参数：
- Claude: `--fork-session --resume <session_id>`
- Codex: `fork <session_id> <prompt>`

**问题**：`Agent.execute()` 和 `AgentBridge.execute()` 都不支持 `fork_from` 参数，只有 `execute_stream()` 支持。

**方案**：
1. 给 `AgentBridge.execute()` 添加 `fork_from` 参数（透传给底层 executor）
2. 给 `Agent.execute()` 添加 `fork_from` 参数（透传给 agent_bridge）
3. 在 `_initialize_new_members()` 中检测 fork 模式
4. fork 模式下使用 `agent.execute(greeting_prompt, fork_from=source_session_id)` 替代普通 execute

**OpenCode 平台降级策略**：OpenCode executor 不支持 `fork_from`（代码注释明确标注），fork 模式下降级为普通初始化（不 fork session），并在日志中提示。

### 2.3 数据复制策略

**复制**：
- 消息历史（`<id>.jsonl`）：完整复制，重新分配 message_id

**不复制（runtime 数据）**：
- `agent_calls.jsonl` / `agent_calls.log`：Agent 调用记录
- `tasks.jsonl` / `tasks.log`：任务列表
- `file_snapshots/`：文件快照
- `pins.json`：置顶消息
- `memory/compact_history.jsonl`：压缩历史

**特殊处理**：
- `agent_member.json`：创建新文件，保留 agent 名称和源 main_session（用于 fork），重置 context_state、token、status
- `group_metadata.json`：创建新文件，使用新 group_chat_id 和用户提供的名称

## 3. 任务分解

### Task 1: 后端 - AgentBridge.execute() 和 Agent.execute() 支持 fork_from

**文件**：`agents_hub/agent_bridge/bridge.py`、`agents_hub/core/agent/base_agent.py`

**改动**：
- **Step 1**：`AgentBridge.execute()` 方法添加 `fork_from: str | None = None` 参数，透传给底层 executor
- **Step 2**：`Agent.execute()` 方法添加 `fork_from: str | None = None` 参数，透传给 `agent_bridge.execute()`

**复杂度**：低
**风险**：低（向后兼容）

### Task 2: 后端 - GroupChat._initialize_new_members() 支持 fork 模式

**文件**：`agents_hub/core/orchestration/group_chat.py`

**改动**：
- 添加 `fork_from_sessions: dict[str, str] | None` 属性（agent_name → source_session_id）
- 修改 `_initialize_new_members()`：检测 fork 模式，使用 `execute(prompt, fork_from=source_session_id)` 替代普通 execute
- fork 模式下不发送打招呼消息，而是使用一个简短的 fork 确认提示
- **OpenCode 降级**：检测 agent 平台，若为 OpenCode 则跳过 fork，降级为普通初始化，并记录 WARN 日志

**复杂度**：中
**风险**：中（需要测试 fork 机制在不同平台的表现）

### Task 3: 后端 - GroupChatService.fork_group_chat()

**文件**：`agents_hub/api/services/group_chat_service.py`

**改动**：
- 新增 `fork_group_chat(source_group_chat_id, new_name)` 方法
- 流程：
  1. 加载源群聊，验证存在
  2. 获取源群聊的 team_members、project_path
  3. 读取消息历史（从 repository）
  4. 生成新 group_chat_id
  5. 创建新群聊目录
  6. 复制消息历史（重新分配 message_id，从 1 开始递增）
  7. 创建 agent_member.json（保留源 session，重置状态）
  8. 保存元数据
  9. 创建 GroupChat 实例并启动（带 fork_from_sessions）
  10. 注册到 GroupChatManager
  11. **广播 WebSocket 通知**：调用 `await broadcast_group_chat_refresh(new_group_chat_id)` 通知前端刷新会话列表

**复杂度**：高
**风险**：中（需要处理文件复制的并发和错误）

### Task 4: 后端 - Fork API 端点

**文件**：`agents_hub/api/routes/group_chat.py`、`agents_hub/api/schemas/group_chats.py`

**改动**：
- 新增 Schema：`GroupChatForkRequest(name: str)`
- 新增路由：`POST /api/v1/group-chats/{group_chat_id}/fork`
- 调用 `service.fork_group_chat()`

**复杂度**：低
**风险**：低

### Task 5: 前端 - Fork API 函数

**文件**：`frontend/src/core/api/groupChatApi.ts`

**改动**：
- 新增 `forkGroupChat(chatId: string, name: string)` API 函数

**复杂度**：低
**风险**：低

### Task 6: 前端 - useForkGroupChat hook

**文件**：`frontend/src/features/session/hooks/useForkGroupChat.ts`（新建）

**改动**：
- 创建 hook，封装 fork 逻辑
- 调用 forkGroupChat API
- 成功后刷新列表并切换到新群聊

**复杂度**：低
**风险**：低

### Task 7: 前端 - SessionItem 下拉菜单添加 fork 选项

**文件**：`frontend/src/features/session/components/SessionItem.tsx`、`SessionItem.css`

**改动**：
- 在下拉菜单中添加 "Fork 群聊" 选项
- 点击后显示内联输入框（重命名框）
- 确认后调用 useForkGroupChat hook

**复杂度**：中
**风险**：低（UI 交互）

### Task 8: 测试

**测试内容**：
- 后端：fork API 创建新群聊、消息复制正确、session fork 正确
- 前端：下拉菜单显示 fork 选项、输入名称后创建成功

**复杂度**：中

## 4. 文件修改清单

### 后端

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `agents_hub/agent_bridge/bridge.py` | 修改 | execute() 添加 fork_from 参数 |
| `agents_hub/core/agent/base_agent.py` | 修改 | execute() 添加 fork_from 参数 |
| `agents_hub/core/orchestration/group_chat.py` | 修改 | _initialize_new_members() 支持 fork 模式，OpenCode 降级处理 |
| `agents_hub/api/services/group_chat_service.py` | 修改 | 新增 fork_group_chat() 方法 + WebSocket 广播 |
| `agents_hub/api/routes/group_chat.py` | 修改 | 新增 fork 端点 |
| `agents_hub/api/schemas/group_chats.py` | 修改 | 新增 GroupChatForkRequest schema |

### 前端

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `frontend/src/core/api/groupChatApi.ts` | 修改 | 新增 forkGroupChat API |
| `frontend/src/features/session/hooks/useForkGroupChat.ts` | 新建 | fork 逻辑 hook |
| `frontend/src/features/session/components/SessionItem.tsx` | 修改 | 添加 fork 菜单项和输入框 |
| `frontend/src/features/session/components/SessionItem.css` | 修改 | fork 输入框样式 |
| `frontend/src/features/session/hooks/index.ts` | 修改 | 导出 useForkGroupChat |

## 5. 风险点

1. **Session Fork 可靠性**：不同平台（Claude/Codex/OpenCode）的 fork 机制可能有差异，需要测试
2. **大群聊复制性能**：消息历史很大时，复制可能耗时较长
3. **并发安全**：fork 过程中源群聊可能被修改，需要处理一致性
4. **OpenCode 平台降级**：OpenCode executor 不支持 `fork_from` 参数（代码注释明确标注"OpenCode 不支持此参数"），fork 模式下 OpenCode agent 将降级为普通初始化（不 fork session），并在日志中记录 WARN 提示。这意味着 OpenCode agent 在 fork 后的群聊中不会继承源 session 上下文。

## 6. 测试策略

1. **单元测试**：fork_group_chat() 方法的各个步骤
2. **集成测试**：完整 fork 流程（API → Service → GroupChat → Agent）
3. **前端测试**：SessionItem 下拉菜单交互

## 7. 实施顺序

1. Task 1（AgentBridge.execute + Agent.execute fork_from）→ Task 2（_initialize_new_members fork 模式）
2. Task 3（fork_group_chat + WebSocket 广播）→ Task 4（API 端点）
3. Task 5（前端 API）→ Task 6（hook）→ Task 7（UI）
4. Task 8（测试）
