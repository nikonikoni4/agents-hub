# Code Review Report

**审查范围**: a1fdd19..HEAD（5 个提交，14 个文件，420 行新增）
**审查时间**: 2026-06-25
**变更文件**:
- agents_hub/api/routes/group_chat.py
- agents_hub/api/services/group_chat_service.py
- agents_hub/core/orchestration/group_chat.py
- frontend/src/core/api/groupChatApi.ts
- frontend/src/core/api/index.ts
- frontend/src/features/chat/hooks/useMembers.ts
- frontend/src/features/private-chat/index.ts
- frontend/src/features/private-chat/store/privateChatStore.ts
- frontend/src/features/single-chat/components/SingleChatPanel.module.css
- frontend/src/features/single-chat/components/SingleChatPanel.tsx
- frontend/src/layouts/ChatArea/ChatArea.tsx
- frontend/src/layouts/RightSidebar/RightSidebar.module.css
- frontend/src/layouts/RightSidebar/RightSidebar.tsx
- frontend/src/shared/types/api-schemas.ts

## 架构上下文

### 相关 ADR
- ADR-0006: 显式群聊发言 (decided)
- ADR-0009: Core Runtime SSOT 选择 (decided)

### 相关 Spec
- docs/specs/2026-06-08-single-chat.md: 单聊通道模块规格
- docs/specs/2026-06-06-frontend-features.md: Frontend Features 层规格

### 决策覆盖
- 后端变更符合 Core CLAUDE.md 中的状态访问规则
- 前端变更部分违反 Features CLAUDE.md 中的分层架构规则

## 审查结果

Found 8 issues:

### Issue 1: 组件直接调用 API，违反分层架构
- **类型**: Architecture
- **置信度**: 95
- **位置**: frontend/src/features/single-chat/components/SingleChatPanel.tsx:23
- **详情**: 组件直接导入并调用 `stopPrivateChatApi`，违反了 `components -> hooks -> store -> core` 的单向依赖规则。根据 Features CLAUDE.md，组件禁止直接调用 API，必须通过 hooks 调用。
- **依据**: Features CLAUDE.md 明确规定："❌ 直接调用 `wsManager.send()` 或 `api.xxx()`"

### Issue 2: 缺少测试覆盖
- **类型**: Testing
- **置信度**: 90
- **位置**: frontend/src/features/private-chat/store/privateChatStore.ts
- **详情**: 新增的私聊功能（privateChatStore、SingleChatPanel 中的私聊逻辑）没有对应的测试文件。根据 Frontend CLAUDE.md 的测试文件放置规则，测试文件必须共置在源码旁边。
- **依据**: Frontend CLAUDE.md 规定："测试文件**必须共置**在源码旁边，禁止集中放在独立的 `tests/` 目录"

### Issue 3: 直接操作 store state，违反 Zustand 最佳实践
- **类型**: Best Practices
- **置信度**: 85
- **位置**: frontend/src/features/single-chat/components/SingleChatPanel.tsx:121
- **详情**: 使用 `usePrivateChatStore.setState({ timerId: newTimerId })` 直接操作 store state，而不是通过 store 提供的方法。这破坏了封装性，使得状态变更难以追踪。
- **依据**: Zustand 最佳实践建议通过 store 提供的方法修改状态，而不是直接使用 setState

### Issue 4: 重复的状态检查代码
- **类型**: Code Quality
- **置信度**: 85
- **位置**: agents_hub/core/orchestration/group_chat.py:1032, 1117, 1324, 1550
- **详情**: 在 `_compress_context_all`、`send_message_to_agent`、`_stop_member_locked`、`_reset_member_locked` 四个方法中，都有相同的私聊状态检查逻辑（`agent_member_info.status == "in_private_chat"`）。应该提取为公共方法。
- **依据**: DRY 原则（Don't Repeat Yourself）

### Issue 5: 缺少更新 Spec 文档
- **类型**: Documentation
- **置信度**: 85
- **位置**: docs/specs/2026-06-08-single-chat.md
- **详情**: 新增的私聊功能（start_private_chat/stop_private_chat）没有更新 single-chat spec。根据 CLAUDE.md 的规则，修改或为某个模块增加功能前，必须先读取对应的 spec 并更新。
- **依据**: CLAUDE.md 规定："修改或为某个模块增加功能前：先读 `docs/specs/index.md`，查看当前是否已经存在该模块的 spec"

### Issue 6: 嵌套三元表达式难以阅读
- **类型**: Code Quality
- **置信度**: 80
- **位置**: frontend/src/layouts/RightSidebar/RightSidebar.tsx:200-210, 222-232
- **详情**: 状态到样式和状态到文本的映射使用了多层嵌套的三元表达式，可读性差。应该使用 if-else、switch-case 或提取为工具函数。
- **依据**: 代码可读性原则，嵌套超过2层的三元表达式应该重构

### Issue 7: 重复的状态映射逻辑
- **类型**: Code Quality
- **置信度**: 80
- **位置**: frontend/src/layouts/RightSidebar/RightSidebar.tsx:200-232
- **详情**: 状态到样式（className）和状态到文本（title）的映射逻辑重复了两次，每次新增状态都需要修改两处。应该提取为工具函数。
- **依据**: DRY 原则

### Issue 8: 注释与代码行为不符
- **类型**: 代码注释合规
- **置信度**: 80
- **位置**: frontend/src/features/private-chat/store/privateChatStore.ts:75-80
- **详情**: `resetTimer` 方法的注释说"计时器由 hooks 设置和管理"，但方法将 `timerId` 设置为 `null`。这可能导致 store 中的 timerId 与实际的计时器不同步。
- **依据**: 注释应该准确描述代码行为

## 变更摘要

本次变更为群聊功能添加了私聊（单独聊天）能力：

**后端**：
- 新增 `start_private_chat` 和 `stop_private_chat` 方法到 GroupChat
- 在消息投递、压缩上下文、停止/重置 Agent 时检查私聊状态
- 消息投递时自动拦截并返回通知
- 将 Manager 私聊限制从 PermissionError 改为 StateError

**前端**：
- 新增 `private-chat` feature 模块和 store
- 在 SingleChatPanel 中添加私聊退出按钮和 3 分钟超时机制
- 在 RightSidebar 中添加"邀请单聊"菜单项
- 新增 `startPrivateChat` 和 `stopPrivateChat` API
- 更新 Agent 状态类型支持 `in_private_chat` 和 `in_loop`
