## codex-system-prompt-strategy
- updated_at : 2026-05-23
- path: `docs/design-decisions/2026-05-23-codex-system-prompt-strategy.md`
- 触发规则：当确认 Codex 的 system prompt 接入方式、profile 策略或项目 AGENTS.md 边界时阅读
- 内容摘要：确定 Codex 的 system prompt 不通过修改项目 AGENTS.md 实现，而通过独立 CODEX_HOME profile 派生方案实现跨项目角色注入

## agent-bridge-architecture-choice
- updated_at : 2026-05-23
- path: `docs/design-decisions/2026-05-23-agent-bridge-architecture-choice.md`
- 触发规则：当设计或修改 agent_bridge 模块架构、职责划分、代码组织时阅读
- 内容摘要：选择扁平化架构（方案B），通过执行器和解析器分离实现职责清晰和高扩展性，符合 SRP 原则和组合优于继承原则

## agent-bridge-output-and-session-strategy
- updated_at : 2026-05-23
- path: `docs/design-decisions/2026-05-23-agent-bridge-output-and-session-strategy.md`
- 触发规则：当设计或修改 agent_bridge 输出模式、session_id 处理逻辑、A2A 调用接口时阅读
- 内容摘要：底层统一流式输出（Codex 非流式不好解析），上层提供流式/非流式双接口；session_id 采用调用后返回策略，简洁可靠且天然适配 Codex
