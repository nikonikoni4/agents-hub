# Code Review Report

**审查范围**: 历史记录添加工具调用信息功能（12 个文件）
**审查时间**: 2026-06-19T15:00:00+08:00
**审查技能**: local-code-review
**变更文件**:

| # | 文件 | 变更类型 |
|---|------|---------|
| 1 | gents_hub/utils/session_parser.py | 修改 - 新增 ToolCallInfo、解析 tool_use block |
| 2 | gents_hub/api/schemas/group_chats.py | 修改 - 导入 ToolCallInfo、新增 tool_calls 字段 |
| 3 | gents_hub/api/schemas/single_chat.py | 修改 - 导入 ToolCallInfo、新增 tool_calls 字段 |
| 4 | gents_hub/api/services/group_chat_service.py | 修改 - 传递 tool_calls |
| 5 | gents_hub/api/services/single_chat_service.py | 修改 - 传递 tool_calls |
| 6 | rontend/src/shared/types/api-schemas.ts | 修改 - MemberHistoryMessage 新增 tool_calls |
| 7 | rontend/src/shared/components/ToolCallCard/ | 新增 - 从 single-chat 迁移到 shared |
| 8 | rontend/src/shared/components/index.ts | 修改 - 导出 ToolCallCard |
| 9 | rontend/src/features/chat-history/components/ChatHistoryPanel.tsx | 修改 - 渲染 tool_calls |
| 10 | rontend/src/features/chat-history/components/ChatHistoryPanel.module.css | 修改 - 新增 .toolCalls 样式 + 修复 bg-secondary → bg-bubble |
| 11 | rontend/src/features/single-chat/components/SingleChatPanel.tsx | 修改 - 更新导入路径 |

## 架构上下文

### 相关 ADR
- 无直接关联 ADR

### 相关 Spec
- docs/specs/2026-06-19-chat-history.md (draft) - 定义 MemberHistoryMessage/SessionMessage 数据结构（**未包含 tool_calls 字段**）
- docs/specs/2026-06-08-single-chat.md - 定义 SessionMessageResponse 数据结构（**未包含 tool_calls 字段**）
- docs/specs/2026-06-06-frontend-features.md - 定义 shared 层职责和跨 feature 通信规则

### 决策覆盖
- 3/11 变更文件有 Spec 关联
- ToolCallCard 迁移到 shared 符合 frontend-features spec 的跨 feature 组件共享规则
- schemas 导入 session_parser.ToolCallInfo 符合 SSOT 原则

## 审查结果

Found 1 issue:

### Issue 1: Spec 数据结构表未更新 tool_calls 字段
- **类型**: Documentation
- **置信度**: 85
- **位置**: docs/specs/2026-06-19-chat-history.md:88-94, docs/specs/2026-06-19-chat-history.md:112-117, docs/specs/2026-06-08-single-chat.md:38-44
- **详情**: 代码已在 SessionMessage、MemberHistoryMessage、SessionMessageResponse 三个数据结构中新增 	ool_calls: list[ToolCallInfo] | None 字段，但对应的 spec 文档中的数据结构表未同步更新。具体缺失：
  1. chat-history spec 的 MemberHistoryMessage 表缺少 	ool_calls 行
  2. chat-history spec 的 SessionMessage 表缺少 	ool_calls 行
  3. single-chat spec 的 SessionMessageResponse 表缺少 	ool_calls 行
  4. ToolCallInfo 数据结构（id, 
ame, input）未在任何 spec 中定义
- **依据**: docs/specs/2026-06-19-chat-history.md 数据结构表（行 88-94）定义了 5 个字段（id, role, content, timestamp, model, token_usage），代码已新增第 7 个字段 	ool_calls。根据 CLAUDE.md「修改或为某个模块增加功能前必须先读 spec」的规则，spec 应与代码保持同步。

## 正面评价

1. **SSOT 落地良好**: ToolCallInfo 仅在 session_parser.py 定义一次，两个 schema 文件通过 import 复用，无重复定义
2. **架构合规**: ToolCallCard 从 eatures/single-chat/ 迁移到 shared/components/，符合 frontend-features spec 的「feature 之间不能直接依赖」规则，旧文件已清理
3. **边界处理完整**: 	ool_calls if tool_calls else None 避免空列表序列化；前端 msg.tool_calls && msg.tool_calls.length > 0 防御性判断
4. **CSS 层级修复**: .messageAssistant .messageBubble 从 ar(--bg-secondary)（未定义变量）修正为 ar(--bg-bubble)（符合三层颜色规范），是顺带的正确修复
5. **Codex 支持**: parse_codex_session 同步补充了 tool_use 解析，确保两个平台历史记录一致

## 变更摘要

本次变更在后端 session_parser 新增 ToolCallInfo 数据模型和 	ool_use block 解析逻辑（Claude + Codex），通过 schemas 层透传到 API 响应。前端将 ToolCallCard 组件从 single-chat feature 迁移到 shared 层，在 chat-history 的 ChatHistoryPanel 中复用该组件展示工具调用信息。变更涉及 11 个文件，净增约 40 行代码，数据流清晰（parser → schema → service → API → frontend type → component），无架构违规。
