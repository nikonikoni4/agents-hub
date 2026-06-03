## agent-bridge
 - updated_at : 2026-05-31
 - path: `docs/specs/2026-05-23-agent-bridge.md`
 - 触发规则：当设计、修改或扩展 agent_bridge 模块的接口、事件格式或平台支持时阅读
 - 内容摘要：agent_bridge 模块的正式规格，定义其作为纯执行层的职责边界、统一事件契约（StreamEvent）、三接口设计（execute_stream/execute/bare_claude_call）和会话管理策略

## roles
 - updated_at : 2026-06-02
 - path: `docs/specs/2026-05-24-agents-role.md`
 - 触发规则：当设计、修改或扩展 roles 角色配置模块时阅读，包括角色 CRUD、头像管理、Skill 管理和权限配置
 - 内容摘要：roles 角色配置模块的正式规格，定义角色生命周期管理、配置数据结构（RoleConfig/RoleInfo）、头像引用机制、Skill 引用优先管理、创建角色时固定 agents-hub MCP 初始化，以及权限/原生配置编辑暂不落地边界

## core-overview
 - updated_at : 2026-05-31
 - path: `docs/specs/2026-05-31-core-overview.md`
 - 触发规则：当需要了解 core 层整体架构、分层依赖关系或跨层协作模式时阅读
 - 内容摘要：core 层总体概览，描述分层架构、依赖方向、跨层协作流程和子 spec 索引

## core-foundation
 - updated_at : 2026-06-02
 - path: `docs/specs/2026-05-31-core-foundation.md`
 - 触发规则：当设计、修改或扩展 foundation 层的数据模型、消息格式、渲染逻辑或异常体系时阅读
 - 内容摘要：core/foundation 层规格，定义系统共享的基础枚举（含 TaskStatus/TaskListStatus）、AgentMessage 结构、渲染三边界契约、异常体系、Token 工具函数和 GroupChatPaths 路径集中管理

## core-communication
 - updated_at : 2026-06-02
 - path: `docs/specs/2026-05-31-core-communication.md`
 - 触发规则：当设计、修改或扩展消息路由、AgentCall 生命周期、调用清理策略或任务管理时阅读
 - 内容摘要：core/communication 层规格，定义消息路由机制、AgentCall 状态机、超时检测、自动清理策略、持久化机制和 TaskManager 任务管理（路径管理改用 group_chat_paths）

## core-context
 - updated_at : 2026-06-02
 - path: `docs/specs/2026-05-31-core-context.md`
 - 触发规则：当设计、修改或扩展群聊会话管理、上下文压缩、Agent 增量加载或持久化机制时阅读
 - 内容摘要：core/context 层规格，定义会话状态模型、Agent session 管理（含 token 字段）、上下文压缩策略、增量加载机制和持久化契约（路径管理改用 group_chat_paths）

## core-agent-orchestration
 - updated_at : 2026-06-03
 - path: `docs/specs/2026-05-31-core-agent-orchestration.md`
 - 触发规则：当设计、修改或扩展 Agent 执行模型、团队管理、群聊编排、token 生命周期或 MCP 工具入口时阅读
 - 内容摘要：core/agent 和 core/orchestration 层规格，定义 Agent 消息循环、Manager/Worker 角色、Team 验证（含 team_members 语义和初始化分离）、GroupChat 生命周期（含 token 管理和 user 伪 Agent 注册）、GroupChatManager token 索引和 MCP 工具入口

## docker-executor
 - updated_at : 2026-06-03
 - path: `docs/specs/2026-06-03-docker-executor.md`
 - 触发规则：当设计、修改或扩展 Docker 沙箱执行器时阅读，包括容器生命周期、CLI 路径配置、卷挂载策略和 git worktree 路径修复
 - 内容摘要：Docker 沙箱执行器规格，定义容器创建/复用/销毁生命周期、CLI 路径映射（宿主机与容器）、卷挂载策略、git worktree 路径修复机制和不确定性事件清单