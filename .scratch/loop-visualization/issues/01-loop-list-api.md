# Issue 01: Loop 列表 API + 前端类型定义

Status: ready-for-agent
Type: AFK
Blocked by: None - can start immediately
User stories covered: #1 (看到Loop状态), #12 (空状态提示)

## What to build

创建 Loop 列表 API 端点和前端基础类型定义，为后续 Loop 可视化功能提供数据层支持。

**后端**：
- 创建 `GET /api/v1/group-chats/{group_chat_id}/loops` API 端点
- 返回当前群聊的所有 Loop 定义列表（包含 loop_id、name、nodes、max_iterations）
- 数据来源：从 `loops.jsonl` 文件读取 Loop 定义（复用 LoopManager.list_loops()）

**前端**：
- 在 `shared/types/api-schemas.ts` 中添加 Loop 相关类型定义（LoopDetail、LoopNode、LoopExecution）
- 在 `shared/adapters/loopAdapter.ts` 中添加数据适配器
- 在 `core/api/groupChatApi.ts` 中添加 `getLoops()` API 函数

**架构约束**：
- 参考 `.scratch/loop-visualization/architecture.md`
- Loop 数据结构已有 `name` 字段，无需修改后端模型
- API 返回完整 LoopDetail，不是只返回 loop_id

## Acceptance criteria

- [ ] 后端：`GET /api/v1/group-chats/{group_chat_id}/loops` 返回 LoopDetail 列表
- [ ] 后端：API 正确处理空列表情况（返回空数组）
- [ ] 前端：LoopDetail、LoopNode、LoopExecution 类型定义正确
- [ ] 前端：loopAdapter 正确转换 API 响应
- [ ] 前端：getLoops() API 函数正常工作
- [ ] 测试：API 单元测试通过

## Blocked by

None - can start immediately
