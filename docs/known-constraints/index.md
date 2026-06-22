## context-usage-calculation
 - updated_at : 2026-06-20
 - path: `docs/known-constraints/context-usage-calculation.md`
 - 触发规则：修改 AgentBridge token usage 解析、Agent context_usage 计算或成员上下文窗口展示时阅读
 - 内容摘要：记录 Codex resume 输出累计 usage 的限制、差分修复方案、Claude cache_read_input_tokens 的窗口占用口径，以及 OpenCode 暂不处理边界

## cli-platform-limitations
 - updated_at : 2026-06-22
 - path: `docs/known-constraints/cli-platform-limitations.md`
 - 触发规则：修改 AgentBridge executor、MCP 配置、角色工具禁用、fork 逻辑、系统提示词注入时阅读
 - 内容摘要：Claude/Codex/OpenCode 三个平台 CLI 在 fork、系统提示词、MCP 连接、工具禁用四个维度的功能差异与限制，包括 Codex fork workaround、OpenCode 文件式提示词注入、MCP 必须项目级配置的根因、仅 Claude 支持工具禁用

## tombstone-deletion
 - updated_at : 2026-06-21
 - path: `docs/known-constraints/tombstone-deletion.md`
 - 触发规则：修改 Loop 定义或执行实例的删除逻辑、JSONL 持久化机制时阅读
 - 内容摘要：JSONL 文件使用墓碑记录（Tombstone）实现标记删除的限制，包括追加写入特性、文件只增不减、遍历开销等约束
