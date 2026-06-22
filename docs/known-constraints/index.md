## context-usage-calculation
 - updated_at : 2026-06-20
 - path: `docs/known-constraints/context-usage-calculation.md`
 - 触发规则：修改 AgentBridge token usage 解析、Agent context_usage 计算或成员上下文窗口展示时阅读
 - 内容摘要：记录 Codex resume 输出累计 usage 的限制、差分修复方案、Claude cache_read_input_tokens 的窗口占用口径，以及 OpenCode 暂不处理边界

## tombstone-deletion
 - updated_at : 2026-06-21
 - path: `docs/known-constraints/tombstone-deletion.md`
 - 触发规则：修改 Loop 定义或执行实例的删除逻辑、JSONL 持久化机制时阅读
 - 内容摘要：JSONL 文件使用墓碑记录（Tombstone）实现标记删除的限制，包括追加写入特性、文件只增不减、遍历开销等约束
