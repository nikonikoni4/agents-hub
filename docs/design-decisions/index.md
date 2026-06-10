## codex-system-prompt-strategy
- updated_at: 2026-05-23
- path: `docs/design-decisions/0001-codex-system-prompt-strategy.md`
- 触发规则：当确认 Codex 的 system prompt 接入方式、profile 策略或项目 AGENTS.md 边界时阅读
- 内容摘要：确定 Codex 的 system prompt 不通过修改项目 AGENTS.md 实现，而通过独立 CODEX_HOME profile 派生方案实现跨项目角色注入

## agent-bridge-output-and-session-strategy
- updated_at: 2026-05-23
- path: `docs/design-decisions/0002-agent-bridge-output-and-session-strategy.md`
- 触发规则：当设计或修改 agent_bridge 输出模式、session_id 处理逻辑、A2A 调用接口时阅读
- 内容摘要：底层统一流式输出（Codex 非流式不好解析），上层提供流式/非流式双接口；session_id 采用调用后返回策略，简洁可靠且天然适配 Codex

## agent-bridge-architecture-choice
- updated_at: 2026-05-23
- path: `docs/design-decisions/0003-agent-bridge-architecture-choice.md`
- 触发规则：当设计或修改 agent_bridge 模块架构、职责划分、代码组织时阅读
- 内容摘要：选择扁平化架构（方案B），通过执行器和解析器分离实现职责清晰和高扩展性，符合 SRP 原则和组合优于继承原则

## agent-bridge-sdk-migration-decision
- updated_at: 2026-05-23
- path: `docs/design-decisions/0004-codex-sdk-migration-decision.md`
- 触发规则：当评估是否将 Claude 或 Codex 的接入方式从 CLI Bridge 迁移到官方 SDK、或需要判断何时引入 SDK 后端时阅读
- 内容摘要：确定 Claude 和 Codex 两个平台都继续使用 CLI 子进程方案，不迁移到 SDK。初始设计时因未发现 Codex SDK 而统一走 CLI；调研发现 Codex SDK（实验版）和 Claude SDK（本质仍是 CLI 封装）后，重新评估仍维持 CLI 方案。列出 7 个触发 SDK 迁移的具体条件，按平台分别标注

## multi-agent-message-architecture
- updated_at: 2026-05-28
- path: `docs/design-decisions/0005-multi-agent-message-architecture.md`
- 触发规则：当设计或修改多 Agent 消息传递机制、消息路由方式、Agent 权限控制时阅读
- 内容摘要：拒绝 MetaGPT 双向引用（越权风险）和 AutoGen 公共 Buffer（不符合按需上下文原则）方案，选择 MessageRouter + 私有队列的点对点路由方案。核心原则：避免越权访问、按需提供上下文、点对点优于广播

## explicit-group-chat-speech
- updated_at: 2026-05-31
- path: `docs/design-decisions/0006-explicit-group-chat-speech.md`
- 状态：decided
- 触发规则：当修改 Agent.run() 的出口 A/B 写入逻辑、新增/调整对外发言相关工具、或 LLM 中间过程污染群聊历史的问题再次浮现时阅读
- 内容摘要：群聊发言从隐式自动写入（出口 A/B）改为显式 MCP 工具调用。普通公开发言使用 speak_in_group_chat；需要回复的 AgentCall 使用 finish_agent_call 闭环。目的是分离 LLM 私下执行文本、公开群聊发言和调用状态闭环

## agent-token-identity-model
- updated_at: 2026-05-31
- path: `docs/design-decisions/0007-agent-token-identity-model.md`
- 状态：decided
- 触发规则：当设计或修改 MCP Tool 签名、调用者身份校验逻辑、GroupChatManager 的注册逻辑、agent_member 持久化结构时阅读
- 内容摘要：MCP Tool 调用者的身份模型选用 Agent Token——Server 维护 token→(agent_name, group_chat_id) 索引，LLM 通过 runtime user prompt 拿到 token 并在 tool 调用时回传。否决了"LLM 自报身份"（伪造）和"每 Agent 一个 MCP Server 子进程"（爆炸）。Token 群聊级生命周期，runtime 注入，剥离过滤兜底

## realtime-boundary
- updated_at: 2026-06-04
- path: `docs/design-decisions/0008-realtime-boundary.md`
- 状态：decided
- 触发规则：当设计或修改 WebSocket 连接管理、群聊实时刷新、MCP 工具结束后的前端通知、API/MCP/realtime 依赖边界时阅读
- 内容摘要：为避免 MCP Server 依赖 API WebSocket 模块导致循环依赖和职责混乱，决定将实时广播能力抽离为独立 realtime 边界；API 与 MCP 共同依赖 realtime，当前只广播 refresh signal，未来预留 message payload 推送

## core-runtime-ssot-choice
- updated_at: 2026-06-04
- path: `docs/design-decisions/0009-core-runtime-ssot-choice.md`
- 状态：decided
- 触发规则：当设计或修改 core runtime 运行态状态管理、内存与文件同步机制、GroupChat/Context/Runtime 职责划分时阅读
- 内容摘要：确定运行态 SSOT 以内存为准（文件作为持久化副本），引入 GroupChatRuntime 和 GroupChatRuntimeState 提供统一接口，同步持久化策略，Repository 从业务层穿透访问中退出

## agent-context-and-prompt-architecture
- updated_at: 2026-06-08
- path: `docs/design-decisions/0010-agent-context-and-prompt-architecture.md`
- 状态：decided
- 触发规则：当设计或修改 AgentContext 的上下文交付策略、Agent 提示词的代码组织方式、Manager/Worker 的 context 差异化时阅读
- 内容摘要：Agent Context 按角色差异化交付（Worker 不接收 raw messages），工具提示词从 base_agent 提取到子类作为 ROLE_INSTRUCTIONS 类变量

## agent-tool-semantics-and-blocking-rules
- updated_at: 2026-06-08
- path: `docs/design-decisions/0011-agent-tool-semantics-and-blocking-rules.md`
- 状态：decided
- 触发规则：当设计或修改 speak_in_group_chat/finish_agent_call 的使用边界、Worker 阻塞判定规则、Manager 阻塞处理流程时阅读
- 内容摘要：收窄 speak_in_group_chat 为任务汇报工具，所有成果/问题/风险通过 finish_agent_call 汇报；阻塞判定标准为"影响范围是否超出任务边界"

## mcp-transport-and-platform-migration
- updated_at: 2026-06-09
- path: `docs/design-decisions/0012-mcp-transport-and-platform-migration.md`
- 状态：decided
- 触发规则：当设计或修改 MCP 传输模式、Agent 平台选型时阅读
- 内容摘要：MCP 传输从 HTTP 切到 stdio 后发现跨进程内存隔离问题（token 丢失、消息断裂），决定回归 HTTP；同时放弃 Codex 改用 OpenCode

## prompt-architecture-refactor
- updated_at: 2026-06-10
- path: `docs/design-decisions/0013-prompt-architecture-refactor.md`
- 状态：decided
- 触发规则：当设计或修改 Agent 提示词结构、runtime 信息传递方式、call_id 可见性、CLAUDE/AGENTS.md 写入时机时阅读
- 内容摘要：将 runtime 信息从 system prompt 移到 user message，解决 Agent 找不到 call_id 和身份信息缺失的问题。system prompt 不再动态生成，CLAUDE/AGENTS.md 在 role 创建时写入

## user-design-summary
- updated_at: 2026-06-04
- path: `docs/design-decisions/user-design-summary.md`
- 触发规则：需要了解用户决策偏好、行为模式或为自主决策提供参考时阅读
- 内容摘要：记录用户在重大设计决策中的偏好、判断方式和风险倾向，为后续 agent 自主决策提供参考
