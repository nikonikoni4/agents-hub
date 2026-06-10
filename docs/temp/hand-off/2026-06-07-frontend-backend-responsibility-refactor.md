# 前后端职责划分重构与状态管理优化

**时间**：2026-06-07
**分支**：test_branch
**状态**：🚧 进行中（高优先级已完成，中优先级待完成）

---

## 一、任务目标

重构前后端职责划分，移除后端不合理的 WebSocket broadcast 调用，前端承担状态同步职责，采用乐观更新策略提升用户体验。

---

## 二、已完成的工作

### 阶段 1：后端清理（已完成 ✅）

- [x] 移除 `agents_hub/api/services/group_chat_service.py` 中 5 处不合理的 broadcast 调用
  - `create_group_chat()` - 第 166 行
  - `send_message()` - 第 470 行
  - `pin_message()` - 第 700 行
  - `unpin_message()` - 第 720 行
  - `add_group_chat_members()` - 第 758 行
- [x] 移除 `broadcast_group_chat_refresh` 导入
- [x] 保留 MCP 工具中的 broadcast（`report_progress`、`complete_task`）
- [x] 通过所有测试（类型检查、ESLint、格式化）

### 阶段 2：前端高优先级修复（已完成 ✅）

- [x] **修复创建群聊后列表不刷新**
  - 修改 `frontend/src/features/session/hooks/useCreateGroupChat.ts`
  - 创建成功后调用 `refreshSessions()`
  
- [x] **添加删除群聊功能**
  - 新增 `frontend/src/features/session/hooks/useDeleteGroupChat.ts`
  - 实现乐观更新：立即从列表移除
  - 实现失败回滚：API 失败时重新加载列表
  
- [x] **添加 Docker 开关状态管理**
  - 修改 `frontend/src/features/chat/hooks/useMembers.ts`
  - 新增 `toggleDockerMode(memberName)` 方法
  - 新增 `refresh()` 方法
  - 实现乐观更新和失败回滚

- [x] **编写实施总结文档**
  - 新增 `IMPLEMENTATION_SUMMARY.md`
  - 包含完整的使用示例和 UI 集成指南

### 提交记录

**提交 1**：`5c3eed6` - refactor: 重构前后端职责划分，移除不合理的 broadcast 调用
**提交 2**：`23c36a4` - feat: 添加删除群聊和 Docker 开关状态管理

---

## 三、未完成的任务

### 优先级 1：UI 集成（需要前端开发人员）

- [ ] **RightSidebar 添加 Docker 状态显示**
  - 文件：`frontend/src/layouts/RightSidebar/RightSidebar.tsx`
  - 任务：在成员列表中显示 Docker 图标（🐳 / 💻）
  - 任务：添加点击事件，调用 `useMembers().toggleDockerMode(memberName)`
  - 参考：`IMPLEMENTATION_SUMMARY.md` 中有完整示例代码

- [ ] **SessionList 添加删除群聊菜单**
  - 文件：`frontend/src/features/session/components/SessionList.tsx` 或相关组件
  - 任务：添加右键菜单或三点菜单
  - 任务：添加"删除群聊"选项，调用 `useDeleteGroupChat().deleteChat(chatId)`
  - 参考：`IMPLEMENTATION_SUMMARY.md` 中有完整示例代码

### 优先级 2：中优先级优化（可选）

- [ ] **添加 roles 订阅同步头像变更**
  - 文件：`frontend/src/features/session/hooks/useSessionList.ts`
  - 任务：订阅 `rolesStore` 变化
  - 任务：当 roles 发生变化时，调用 `refreshSessions()`
  - 参考：计划文档中有详细说明

- [ ] **改进消息发送错误处理**
  - 文件：`frontend/src/layouts/ChatArea/ChatArea.tsx`
  - 任务：添加临时 ID 机制（`temp-${Date.now()}`）
  - 任务：发送失败时移除乐观消息
  - 任务：显示错误提示
  - 参考：计划文档中有完整代码示例

- [ ] **优化成员列表乐观更新**
  - 文件：`frontend/src/features/chat/hooks/useMembers.ts`
  - 任务：添加 `addMember()` 方法
  - 任务：添加 `removeMember()` 方法
  - 任务：实现乐观更新和失败回滚
  - 参考：计划文档中有详细说明

---

## 四、下一步行动

1. **UI 集成（最优先）**
   - 在 RightSidebar 中添加 Docker 状态显示和切换按钮
   - 在 SessionList 中添加删除群聊的菜单项
   - 手动测试所有功能是否正常工作

2. **验证测试**
   - 测试创建群聊后列表是否立即刷新
   - 测试删除群聊后列表是否立即更新
   - 测试 Docker 开关切换是否立即反应在 UI 上
   - 测试 WebSocket 推送是否仍正常工作（Agent 回复消息）

3. **中优先级优化**（可选）
   - 根据需要实现 roles 订阅、消息错误处理、成员列表优化

---

## 五、相关文件

### 后端文件

| 文件 | 修改状态 | 说明 |
|------|----------|------|
| `agents_hub/api/services/group_chat_service.py` | ✅ 已修改 | 移除 5 处 broadcast 调用和导入 |
| `agents_hub/mcp/server.py` | 未修改 | 保留正确的 broadcast 使用（report_progress、complete_task） |

### 前端文件

| 文件 | 修改状态 | 说明 |
|------|----------|------|
| `frontend/src/features/session/hooks/useCreateGroupChat.ts` | ✅ 已修改 | 添加创建后刷新列表 |
| `frontend/src/features/session/hooks/useDeleteGroupChat.ts` | 📝 新建 | 删除群聊 hook，乐观更新 + 失败回滚 |
| `frontend/src/features/chat/hooks/useMembers.ts` | ✅ 已修改 | 添加 toggleDockerMode 和 refresh 方法 |
| `IMPLEMENTATION_SUMMARY.md` | 📝 新建 | 完整的实施总结和使用指南 |

### 待修改文件（UI 集成）

| 文件 | 修改状态 | 说明 |
|------|----------|------|
| `frontend/src/layouts/RightSidebar/RightSidebar.tsx` | ⏳ 待修改 | 需要添加 Docker 状态显示 |
| `frontend/src/features/session/components/SessionList.tsx` | ⏳ 待修改 | 需要添加删除群聊菜单 |

---

## 六、决策记录

### 决策 1：前后端职责划分原则

**背景**：
之前代码中，前端操作（创建群聊、pin 消息等）后，后端会通过 WebSocket broadcast 通知前端刷新。这导致：
- UI 响应延迟（需要等待网络往返）
- 架构混乱（前端已知操作结果，却要等后端通知）
- 状态不一致风险（API 返回和 WebSocket 消息顺序不确定）

**决策**：
- ✅ **后端 broadcast**：仅用于 Agent 产生的内容（前端无法预知）
- ❌ **后端 broadcast**：不用于前端主动操作（前端已知结果）
- ✅ **前端状态管理**：采用乐观更新 + API 响应驱动 + WebSocket 仅监听后端推送

**原因**：
- 提升用户体验：操作立即反馈，无需等待
- 职责清晰：前端管理自己的操作结果，后端推送未知内容
- 减少复杂度：避免前后端状态同步的竞态条件

### 决策 2：乐观更新策略

**背景**：
前端操作后需要更新 UI 状态，可以选择：
1. 等待 API 返回后更新
2. 立即更新（乐观更新），失败时回滚

**决策**：
采用乐观更新策略，所有前端操作立即更新本地状态，API 失败时自动回滚。

**原因**：
- 用户体验更好：操作立即生效
- 失败率低：大部分操作都会成功
- 回滚机制完善：失败时可以重新加载数据

---

## 七、注意事项

### 1. WebSocket broadcast 的正确使用

⚠️ **重要**：不要随意在 API Service 中添加 broadcast！

- ✅ **应该 broadcast**：Agent 发言、Agent 完成任务（后端产生内容）
- ❌ **不应该 broadcast**：前端操作（创建、删除、修改）

### 2. 前端乐观更新的实现模式

所有乐观更新都应遵循以下模式：

```typescript
const operation = async () => {
  // 1. 乐观更新：立即修改本地状态
  setLocalState(newValue);
  
  try {
    // 2. 调用 API
    await apiCall();
  } catch (error) {
    // 3. 失败时回滚：重新加载数据
    await refresh();
    throw error;
  }
};
```

### 3. useMembers 的使用

`useMembers` hook 现在返回 4 个值：
- `members` - 成员列表
- `loading` - 加载状态
- `refresh()` - 手动刷新方法
- `toggleDockerMode(memberName)` - 切换 Docker 状态

所有使用 `useMembers` 的组件都可以直接使用这些方法。

### 4. SessionItem 的字段名

⚠️ **注意**：SessionItem 使用 `id` 字段，不是 `group_chat_id`！

```typescript
// ✅ 正确
sessions.filter(s => s.id !== chatId)

// ❌ 错误
sessions.filter(s => s.group_chat_id !== chatId)
```

### 5. API 函数的签名

⚠️ **注意**：`updateMemberDockerMode` 的第三个参数是 `boolean`，不是对象！

```typescript
// ✅ 正确
updateMemberDockerMode(chatId, memberName, true)

// ❌ 错误
updateMemberDockerMode(chatId, memberName, { use_docker: true })
```

---

## 八、参考文档

### 实施文档
- `IMPLEMENTATION_SUMMARY.md` - 完整的实施总结、使用示例、UI 集成指南

### 计划文档
- `D:\数据文档\claude_yunyi\plans\1-2-dreamy-adleman.md` - 原始计划文档

### 设计决策
- 建议创建：`docs/design-decisions/0011-frontend-state-management-responsibility.md`
  - 记录前后端职责划分原则
  - 记录 broadcast 的正确使用边界
  - 记录前端状态管理策略

### 相关 Spec
- `docs/specs/2026-06-03-websocket-backend.md` - WebSocket 后端规格
- `docs/specs/2026-06-03-group-chat-api.md` - Group Chat API 规格
- `docs/design-decisions/0008-realtime-boundary.md` - Realtime 边界决策

---

## 九、验证清单

### 已验证 ✅
- [x] 后端类型检查通过
- [x] 前端类型检查通过
- [x] 前端 ESLint 通过（只有警告，无错误）
- [x] 前端代码格式化完成
- [x] Git pre-commit hooks 通过
- [x] MCP 工具中的 broadcast 仍然保留

### 待验证 ⏳
- [ ] 创建群聊后，列表立即显示新群聊
- [ ] 删除群聊后，列表立即移除（需先完成 UI 集成）
- [ ] Docker 开关切换后，UI 立即更新（需先完成 UI 集成）
- [ ] Agent 回复消息时，仍能收到 WebSocket 推送
- [ ] 所有操作失败时，状态正确回滚

---

## 十、接手建议

### 如果你是前端开发人员

1. **先阅读** `IMPLEMENTATION_SUMMARY.md`，了解所有功能的使用方式
2. **UI 集成优先**：先完成 Docker 状态显示和删除群聊菜单
3. **手动测试**：完成后手动测试所有场景
4. **可选优化**：根据需要完成中优先级任务

### 如果你是后端开发人员

1. **不要添加 broadcast**：除非是 Agent 产生的内容，否则不要在 Service 层添加 broadcast
2. **保持职责清晰**：API 层只负责处理请求和返回响应，不负责前端状态同步

### 如果你是全栈开发人员

1. **理解架构原则**：前端管理自己的操作，后端推送未知内容
2. **完成 UI 集成**：这是最优先的工作
3. **考虑创建决策文档**：记录这次重构的原因和原则

---

## 十一、潜在风险

### 风险 1：多端同步问题

**现象**：如果用户在多个设备登录，当前方案只更新当前设备状态。

**影响**：另一个设备不会立即看到状态变化。

**解决方案**（未来）：
- 方案 A：后端按用户而非群聊 broadcast
- 方案 B：前端在操作完成后，通过 WebSocket 通知其他设备

**当前处理**：接受这个限制，优先保证单设备体验。

### 风险 2：网络延迟导致的状态不一致

**现象**：乐观更新后，API 调用可能需要较长时间才返回。

**影响**：短暂的状态不一致。

**当前处理**：已实现失败回滚机制，API 失败时会重新加载正确状态。

---

**交接完成时间**：2026-06-07
**下一个接手 Agent 请使用**：`/hand-on` 命令读取此文档
