# Issue 01: Loop 列表 API + 前端类型定义

Status: completed
Type: AFK
Blocked by: None - can start immediately
User stories covered: #1 (看到Loop状态), #12 (空状态提示)

## What to build

创建 Loop 列表 API 端点和前端基础类型定义，为后续 Loop 可视化功能提供数据层支持。

**后端（只读设计，不依赖 core 模块）**：
- 创建 `GET /api/v1/group-chats/{group_chat_id}/loops` API 端点
- 返回当前群聊的所有 Loop 定义列表（包含 loop_id、name、nodes、max_iterations）
- **数据来源**：直接从 `loops.jsonl` 文件读取，不走 core 模块

**实现细节**：
- 在 `agents_hub/api/services/group_chat_service.py` 中增加辅助函数 `_read_loops_from_file(group_chat_id: str) -> list[dict]`
  - 功能：从 JSONL 文件读取所有非墓碑的 Loop 定义
  - 参数：group_chat_id（用于定位文件路径）
  - 返回：Loop 定义列表
- `GET /loops` 端点直接调用此辅助函数，不调用 `LoopManager.list_loops()`

**为什么不使用 core 的已有功能？**
- **解耦设计**：API 层直接读取文件，避免与 core 模块耦合
- **避免干扰**：core 模块的 `LoopManager.list_loops()` 可能有副作用（如内存管理），API 层只需要只读访问
- **有意设计**：这不是重复编写代码，而是有意的分层隔离，确保 API 层不会意外修改 core 状态
- **AI 安全**：耦合在一起时，AI 容易出错（如误调用会修改状态的方法）

**前端**：
- 在 `shared/types/api-schemas.ts` 中添加 Loop 相关类型定义（LoopDetail、LoopNode、LoopExecution）
- 在 `shared/adapters/loopAdapter.ts` 中添加数据适配器
- 在 `core/api/groupChatApi.ts` 中添加 `getLoops()` API 函数

**架构约束**：
- 参考 `.scratch/loop-visualization/architecture.md`
- Loop 数据结构已有 `name` 字段，无需修改后端模型
- API 返回完整 LoopDetail，不是只返回 loop_id
- **只读约束**：API 层不能修改 core loop 本身的状态

## Acceptance criteria

- [ ] 后端：`GET /api/v1/group-chats/{group_chat_id}/loops` 返回 LoopDetail 列表
- [ ] 后端：API 直接从文件读取，不调用 `LoopManager.list_loops()`
- [ ] 后端：API 正确处理空列表情况（返回空数组）
- [ ] 后端：API 正确跳过墓碑记录（`_deleted: true`）
- [ ] 后端：service 中有辅助函数 `_read_loops_from_file()` 实现文件读取逻辑
- [ ] 后端：辅助函数有注释说明"为什么不使用 core 的已有功能"
- [ ] 前端：LoopDetail、LoopNode、LoopExecution 类型定义正确
- [ ] 前端：loopAdapter 正确转换 API 响应
- [ ] 前端：getLoops() API 函数正常工作
- [ ] 测试：API 单元测试通过

## Blocked by

None - can start immediately

## 相关文档

- ADR：`docs/adr/2026-06-23-loop-memory-singleton.md`（单例策略）
- PRD：`.scratch/loop-visualization/PRD.md`（数据获取策略说明）
