# core 模块

## 相关 Spec

| Spec | 路径 | 说明 |
|------|------|------|
| core-overview | `docs/specs/2026-05-31-core-overview.md` | core 层总体概览，描述分层架构、依赖方向和跨层协作模式 |
| core-foundation | `docs/specs/2026-05-31-core-foundation.md` | 基础层规格，定义系统共享的枚举、AgentMessage 结构、渲染三边界契约和异常体系 |
| core-communication | `docs/specs/2026-05-31-core-communication.md` | 通信层规格，定义消息路由机制、AgentCall 状态机、超时检测、自动清理策略和持久化机制 |
| core-context | `docs/specs/2026-05-31-core-context.md` | 上下文层规格，定义会话状态模型、Agent session 管理、上下文压缩策略、增量加载机制和持久化契约 |
| core-agent-orchestration | `docs/specs/2026-05-31-core-agent-orchestration.md` | Agent+编排层规格，定义 Agent 消息循环、Manager/Worker 角色体系、Team 验证、GroupChat 生命周期和 call_agent MCP 入口 |
