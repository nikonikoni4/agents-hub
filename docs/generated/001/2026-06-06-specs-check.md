现在我已经收集了足够的信息来编写一致性检查报告。

## Specs 一致性检查报告

- **检查日期**：2026-06-06

---

### 1. agent-bridge (2026-05-23-agent-bridge.md)

- **状态**：⚠️ 部分不一致
- **不一致详情**：
  - **Executor 协议签名缺少 `cwd` 参数**
    - 位置：`protocols.py` Executor 协议
    - 文档描述：`execute(self, prompt, config, session_id)` 三个参数
    - 实际情况：实际 `ClaudeExecutor.execute()` 有 `cwd` 参数，但 Protocol 定义中缺少
    - 严重程度：低（Protocol 是接口契约，实际实现更完整）
    - 建议：更新 Protocol 定义添加 `cwd` 参数

---

### 2. roles (2026-05-24-agents-role.md)

- **状态**：⚠️ 部分不一致
- **不一致详情**：
  - **RoleUpdateRequest 不包含 name 字段**
    - 位置：spec §Request Schemas → RoleUpdateRequest
    - 文档描述：RoleUpdateRequest 包含 `name`、`avatar`、`abilities`、`description` 字段
    - 实际情况：代码中 `RoleUpdateRequest` 只有 `avatar`、`abilities`、`description`，`name` 是路径参数
    - 严重程度：中（API 行为不一致）
    - 建议：更新 spec，说明 `name` 通过路径参数传入，不在 request body 中
  - **PATCH 端点不支持更新名称**
    - 位置：spec §API 端点 → PATCH /roles/{name}
    - 文档描述：可更新角色名称
    - 实际情况：代码中 `update_role` 方法只更新 `avatar`、`abilities`、`description`，不更新 `name`
    - 严重程度：中（功能缺失）
    - 建议：要么在代码中实现名称更新，要么更新 spec 说明不支持名称更新

---

### 3. core-overview (2026-05-31-core-overview.md)

- **状态**：✅ 一致
- **说明**：分层架构、依赖方向、跨层协作模式与代码实现一致

---

### 4. core-foundation (2026-05-31-core-foundation.md)

- **状态**：✅ 一致
- **说明**：枚举类型、消息格式、渲染契约、异常体系、路径管理均与代码实现一致

---

### 5. core-communication (2026-05-31-core-communication.md)

- **状态**：✅ 一致
- **说明**：MessageRouter、AgentCallManager、TaskManager 的接口和行为与代码实现一致

---

### 6. core-context (2026-05-31-core-context.md)

- **状态**：⚠️ 部分不一致
- **不一致详情**：
  - **GroupChatContext 不直接创建 Repository**
    - 位置：spec §持久化机制
    - 文档描述：GroupChatContext 创建并持有 GroupChatRepository
    - 实际情况：代码中 GroupChatContext 持有 GroupChatRuntime，由 Runtime 持有 Repository
    - 严重程度：低（架构分层调整，功能不变）
    - 建议：更新 spec 说明 GroupChatContext → GroupChatRuntime → GroupChatRepository 的持有链

---

### 7. core-agent-orchestration (2026-05-31-core-agent-orchestration.md)

- **状态**：✅ 一致
- **说明**：Agent 执行模型、GroupChat 生命周期、GroupChatManager 全局注册表、MCP 工具入口均与代码实现一致

---

### 8. docker-executor (2026-06-03-docker-executor.md)

- **状态**：✅ 一致
- **说明**：容器生命周期、CLI 路径配置、卷挂载策略、git worktree 路径修复机制与代码实现一致

---

### 9. websocket-backend (2026-06-03-websocket-backend.md)

- **状态**：⚠️ 部分不一致
- **不一致详情**：
  - **广播 API 端点未实现**
    - 位置：spec §广播 API → POST /api/v1/ws/broadcast/{group_chat_id}
    - 文档描述：提供 HTTP 广播 API 端点
    - 实际情况：代码中只有 WebSocketManager 的 `broadcast` 方法，没有 HTTP 路由端点
    - 严重程度：中（API 契约未实现）
    - 建议：实现 HTTP 广播 API 端点，或更新 spec 说明当前只支持内部调用

---

### 10. group-chat-api (2026-06-03-group-chat-api.md)

- **状态**：⚠️ 部分不一致
- **不一致详情**：
  - **消息历史查询参数不一致**
    - 位置：spec §查询参数 → GET /api/v1/group-chats/{group_chat_id}/messages
    - 文档描述：`limit` 和 `offset` 分页参数
    - 实际情况：代码中使用 `limit` 和 `before`（游标分页）
    - 严重程度：中（API 行为不一致）
    - 建议：更新 spec 说明使用游标分页
  - **发送消息请求体不一致**
    - 位置：spec §Schema 定义 → MessageCreate
    - 文档描述：包含 `content` 和 `send_to` 字段
    - 实际情况：代码中包含 `content` 和 `members` 字段
    - 严重程度：中（API 行为不一致）
    - 建议：更新 spec 说明 `members` 字段的用途
  - **GroupChatInfo 包含额外字段**
    - 位置：spec §Schema 定义 → GroupChatInfo
    - 文档描述：不包含 `last_speaker`、`last_message`、`last_update_time` 字段
    - 实际情况：代码中包含这些字段
    - 严重程度：低（功能增强）
    - 建议：更新 spec 添加这些字段

---

### 11. skills-api (2026-06-03-skills-api.md)

- **状态**：✅ 一致
- **说明**：API 端点、数据结构、异常处理与代码实现一致

---

### 12. teams (2026-06-03-team-management-design.md)

- **状态**：✅ 一致
- **说明**：TeamManager 接口、API 端点、异常处理与代码实现一致

---

### 13. message-flow-and-persistence (2026-06-05-message-flow-and-persistence.md)

- **状态**：✅ 一致
- **说明**：MessageRouter 职责边界、GroupChat.send_message_to_agent() 统一包装、消息保存规则与代码实现一致

---

### 代码中未被 Spec 覆盖的功能

| 功能 | 位置 | 说明 |
|------|------|------|
| GroupChatRuntime | `core/context/group_chat_runtime.py` | 新增的运行时状态管理层，spec 中未描述 |
| GroupMetadata | `core/context/group_metadata.py` | 群聊元数据模型，spec 中未详细描述 |
| markdown_injector | `core/utils/markdown_injector.py` | Runtime 注入工具，spec 中提到但未详细定义 |
| WebSocket 依赖注入 | `realtime/dependencies.py` | realtime 模块的依赖注入，spec 中未描述 |
| 测试端点 | `api/routes/group_chat.py` | `/test/bridge-execute` 和 `/test/subprocess` 测试端点 |

---

### 已过期的 Spec 内容

| Spec | 过期内容 | 说明 |
|------|----------|------|
| group-chat-api | `send_to` 字段 | 代码中改为 `members` 字段 |
| group-chat-api | `offset` 分页 | 代码中改为 `before` 游标分页 |
| websocket-backend | HTTP 广播 API | 代码中未实现 HTTP 端点 |

---

### 总结

**整体一致性评分**：75/100

**主要问题**：
1. **API 契约不一致**：group-chat-api 和 websocket-backend 的 API 端点与 spec 定义不完全一致
2. **功能缺失**：websocket-backend 的 HTTP 广播 API 未实现
3. **架构调整**：core-context 层的组件持有关系有调整，spec 未同步更新

**建议优先修复**：
1. 更新 group-chat-api spec 对齐实际 API 实现（游标分页、members 字段）
2. 实现或更新 websocket-backend 的 HTTP 广播 API
3. 更新 core-context spec 说明 GroupChatRuntime 的引入
