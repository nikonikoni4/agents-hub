# Context Compact - manager - 2026-06-20T18:05:31.038915

## 原 Session
- session_id: 0e73d1ae-6e01-4387-a2a6-425272d257fa
- context_usage: 211K tokens

## 摘要
## 当前工作上下文总结

### 1. 已完成的工作

**功能实现**：
- 前端历史界面增加工具调用信息（ToolCallCard 迁移到 shared，前后端 Schema 同步）
- Codex session 解析支持 function_call（重构 parse_codex_session）
- NOTIFICATION 消息在接收方保存到群聊历史（_run_loop 增加保存逻辑）
- 前端预览/diff 容器高度修复（改为 flex 布局占满右侧栏）
- Markdown 表格渲染修复（安装 remark-gfm）
- 群成员历史聊天添加刷新按钮
- 创建新群聊后左侧栏列表刷新修复

**文档更新**：
- 更新 flow 文档（message-lifecycle.md, agent-call-lifecycle.md）
- 更新 spec 文档（message-flow-and-persistence.md, chat-history, single-chat）
- 新增 bug 记录（NOTIFICATION 消息不保存的设计漏洞）

**团队成员**：manager（我）、通用审查助手、通用执行助手、codex（新增）

### 2. 当前状态

所有任务已完成，团队空闲，等待新任务。

### 3. 关键决策

- NOTIFICATION 消息保存：在 `_run_loop` 中增加逻辑，不改动 `_fallback_close_task`
- complete_task 被禁用原因：Codex 平台不支持、过度设计、调用不稳定（ADR 2026-06-16）

### 4. 重要约束

- 派活时给够上下文和约束，不要只说"处理一下"
- 变更展示需要 `<changes>` 块
- Agent 间消息必须通过 `GroupChat.send_message_to_agent()` 包装

## 新 Session
- session_id: 8f56ece6-5b0b-48d4-87b7-b4d977deb65d
