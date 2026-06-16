<index-write-guide>
导航文档每一项模板：
## xxxx
 - updated_at : YYYY-MM-DD
 - path: 
 - 触发规则：
 - 内容摘要：

当写入第一条数据之后删除该内容（index-write-guide）
</index-write-guide>

## Agent 错误状态前端反馈机制

- updated_at: 2026-06-16
- path: `docs/badcase/2026-06-16-agent-error-state-feedback.md`
- 触发规则：排查 CLI 错误无法传达到前端、agent 状态卡在 busy、用户无法感知错误时阅读
- 内容摘要：当 Agent 执行过程中遇到错误（CLI 失败、超时、限流等）时，前端无法感知真实状态。通过增加 error 状态和 error_info 字段，在右侧栏成员列表显示错误图标和 tooltip 详情，让用户了解错误并采取行动（重置/重启）

## 大参数工具调用导致模型"卡住"或"空洞承诺"

- updated_at: 2026-06-16
- path: `docs/badcase/2026-06-16-large-tool-call-hang.md`
- 触发规则：排查模型"空洞承诺"（说做但不做）、生成大文件时卡住、agents hub 长任务失败时阅读
- 内容摘要：当任务需要生成大文件（>100行）时，模型可能只输出文本承诺而不调用工具，或在 thinking 后卡住。根因是工具调用参数接近上限时的保守行为。解决方案：在任务指令中明确要求分块写入（每次 50 行）

## CLI 断开导致前端卡住的体验问题

- updated_at: 2026-06-15
- path: `docs/badcase/2026-06-15-cli-disconnect-frontend-stuck.md`
- 触发规则：排查前端卡住、CLI 断开、用户体验问题时阅读
- 内容摘要：记录 CLI 运行过程中因外部原因（如模型限流）断开时，前端直接停止或卡住的体验问题，包含问题场景、表现和优化方向
