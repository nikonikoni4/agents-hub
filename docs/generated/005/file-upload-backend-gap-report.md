# 文件上传功能后端链路断裂分析报告

> 日期：2026-06-10
> 分支：task-24-image-file
> 相关文件：`docs/superpowers/specs/2026-06-10-file-upload-design.md`、`docs/superpowers/plans/2026-06-10-file-upload-implementation.md`

## 问题概述

文件上传功能的"上传到磁盘"链路已通，但"文件路径传递给 Agent"链路完全断裂。前端发送的 `files` 数据在后端路由层被丢弃，不会进入消息历史，也不会注入到 Agent 的 prompt 中。

## 问题清单

### 问题 1：FileService 位置违反分层架构

| 项目 | 内容 |
|------|------|
| 严重度 | 低（架构规范） |
| 现状 | `agents_hub/services/file_service.py`（顶层 services 目录） |
| 预期 | `agents_hub/api/services/file_service.py`（与其它 service 同级） |
| 依据 | 项目架构 `route → api/service → manager`，所有 service 均在 `agents_hub/api/services/` 下 |

### 问题 2：路由层丢弃 files 数据

| 项目 | 内容 |
|------|------|
| 严重度 | **高（功能缺失）** |
| 现状 | `agents_hub/api/routes/group_chat.py:123` 只传 `content` 和 `members`，丢弃 `request.files` |
| 影响 | 前端发送的 files 数据在路由层即被丢弃，后续全链路无法收到 |

```python
# 现状 — files 被丢弃
await service.send_message(
    group_chat_id,
    content=request.content,
    members=request.members,
)
```

### 问题 3：service 层 send_message 不接收 files

| 项目 | 内容 |
|------|------|
| 严重度 | **高（功能缺失）** |
| 现状 | `GroupChatService.send_message(self, group_chat_id, content, members)` 签名无 files 参数 |
| 影响 | 即使路由传了 files，service 也无法处理 |

### 问题 4：AgentMessage 无 files 字段

| 项目 | 内容 |
|------|------|
| 严重度 | **高（功能缺失）** |
| 现状 | `agents_hub/core/foundation/message.py` 的 AgentMessage dataclass 只有 call_id、content、send_from 等字段 |
| 影响 | files 无法随消息在系统内流转 |

### 问题 5：消息存储不包含 files

| 项目 | 内容 |
|------|------|
| 严重度 | **高（功能缺失）** |
| 现状 | `agents_hub/core/context/group_chat_session.py:52` 的 `add_message` 只存 agent_name、content、timestamp 等，无 files |
| 影响 | 消息历史中不记录文件信息，前端无法回显已发送的文件 |

### 问题 6：render_for_llm 不注入文件路径

| 项目 | 内容 |
|------|------|
| 严重度 | **高（功能缺失）** |
| 现状 | `agents_hub/core/foundation/renderer.py:43` 的 `render_for_llm` 只渲染 send_from、send_to、content |
| 影响 | Agent 收到的 prompt 中没有文件路径，无法读取用户上传的文件 |

### 问题 7：MessageInfo schema 无 files 字段

| 项目 | 内容 |
|------|------|
| 严重度 | 中（前端展示缺失） |
| 现状 | `agents_hub/api/schemas/group_chats.py:87` 的 MessageInfo 没有 files 字段 |
| 影响 | 消息历史 API 不返回文件信息，前端无法渲染已发送文件的预览卡片 |

## 断裂链路图

```
前端 files ──→ 路由 ──✗──→ service ──→ AgentMessage ──→ prompt ──→ Agent
                │
                └─ request.files 在此被丢弃（问题 2）
                   service 无 files 参数（问题 3）
                   AgentMessage 无 files 字段（问题 4）
                   消息存储无 files（问题 5）
                   render_for_llm 不注入（问题 6）
                   MessageInfo 不返回（问题 7）
```

## 根因分析

### Spec vs Plan 的 Gap

**Spec（`2026-06-10-file-upload-design.md`）设计了完整链路：**

- §2.2：消息发送接口扩展（后端 `/messages` 接收 files）
- §3.1：消息格式扩展（SendMessageRequest 带 files）
- §5.1：Agent 收到的消息格式（`[附件]` 块）
- §5.2：文件路径注入到 Agent 提示词（`<uploaded_files>` XML）
- §4.2：清理策略（文件与消息关联）

**Plan（`2026-06-10-file-upload-implementation.md`）只翻译了部分：**

- ✅ Task 1-6：前端类型、API、组件（UploadArea、UploadPreview 等）
- ✅ Task 7-9：后端 schema、FileService、上传/访问 API
- ✅ Task 10-11：前端集成（ChatInput、ChatMessageItem）
- ❌ 缺失：send_message 接收 files 的后端 Task
- ❌ 缺失：AgentMessage 扩展 + 消息存储扩展
- ❌ 缺失：render_for_llm 注入文件路径
- ❌ 缺失：MessageInfo schema 扩展

**结论：Plan 对 Spec 的翻译不完整，漏掉了 files 与消息关联的核心后端链路。实现者忠实执行了 Plan，所以结果也缺失了这部分。**

### Spec 自身的小问题

Spec §5.2 设计用 `<uploaded_files>` XML 标签注入路径，但实际项目的 prompt 渲染统一走 `render_for_llm`（用 `<incoming_message>` 包裹）。Spec 没有考虑现有的渲染架构。

## 已修复内容

以下改动已在 task-24-image-file 分支完成：

| 文件 | 改动 |
|------|------|
| `agents_hub/api/services/file_service.py` | 新建 — 从 `agents_hub/services/` 移入 |
| `agents_hub/api/services/group_chat_service.py` | import 路径更新 + send_message 新增 files 参数 |
| `agents_hub/api/routes/group_chat.py` | 路由传递 request.files 给 service |
| `agents_hub/core/foundation/message.py` | AgentMessage 新增 files 字段 |
| `agents_hub/core/foundation/renderer.py` | render_for_llm 注入 `[附件]` 块到 prompt |
| `agents_hub/agent_bridge/models.py` | AgentResult 新增 files 字段 |
| `agents_hub/core/orchestration/group_chat.py` | send_message_to_agent 保存时传递 files |
| `agents_hub/core/context/group_chat_session.py` | add_message 处理 files 字段 |
| `agents_hub/core/context/group_chat_runtime.py` | get_message_dicts 返回 files 字段 |
| `agents_hub/api/schemas/group_chats.py` | MessageInfo 新增 files 字段 |

## 待处理

- [ ] 旧的 `agents_hub/services/file_service.py` 需要删除（当前无引用但文件仍在）
- [ ] 补充后端单元测试（文件上传+消息发送含 files 的集成测试）
- [ ] 验证前端 MessageApiItem 类型是否同步更新了 files 字段
