## group-chat-file-lock-fix
 - updated_at : 2026-06-19
 - path: `docs/context_feedback/2026-06-19-group-chat-file-lock-fix.md`
 - 触发规则：当修改群聊资源清理、logger 管理或文件句柄释放相关代码时阅读
 - 内容摘要：修复群聊删除时文件被占用问题的上下文反馈，发现 AgentCallManager 和 TaskManager 的 logger 文件句柄未在 cleanup 时关闭，导致 Windows 上 shutil.rmtree 失败。已创建 `docs/flows/logger-file-handle-lifecycle.md` 记录 logger 生命周期
