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

## core-foundation
 - updated_at : 2026-06-04
 - path: `docs/specs/2026-05-31-core-foundation.md`
 - 触发规则：当设计、修改或扩展 foundation 层的数据模型、消息格式、渲染逻辑或异常体系时阅读
 - 内容摘要：core/foundation 层规格，定义系统共享的基础枚举、AgentMessage 结构、渲染契约、异常体系、Token 工具函数和 GroupChatPaths 路径集中管理（含 metadata、session 状态字段）

## core-communication
 - updated_at : 2026-06-03
 - path: `docs/specs/2026-05-31-core-communication.md`
 - 触发规则：当设计、修改或扩展消息路由、AgentCall 生命周期、调用清理策略或任务管理时阅读
 - 内容摘要：core/communication 层规格，定义消息路由机制、AgentCall 状态机、显式回复闭环、超时检测、自动清理策略、持久化机制和 TaskManager 任务管理

## core-context
 - updated_at : 2026-06-04
 - path: `docs/specs/2026-05-31-core-context.md`
 - 触发规则：当设计、修改或扩展群聊会话管理、上下文压缩、Agent 增量加载或持久化机制时阅读
 - 内容摘要：core/context 层规格，定义会话状态模型、Agent session 管理（含 token/cwd/use_docker）、上下文压缩、增量加载、GroupChatContext 通过 GroupChatRuntime 间接持有 Repository 的持久化契约

## core-agent-orchestration
 - updated_at : 2026-06-04
 - path: `docs/specs/2026-05-31-core-agent-orchestration.md`
 - 触发规则：当设计、修改或扩展 Agent 执行模型、团队管理、群聊编排、token 生命周期或 MCP 工具入口时阅读
 - 内容摘要：core/agent 和 core/orchestration 层规格，定义 Agent 消息循环、显式群聊发言、显式 AgentCall 闭环、Agent 完成通知唤醒、user 群聊回执、Manager/Worker 角色、GroupChat 生命周期、现有组件持有关系、GroupChatManager token 索引和 MCP 工具入口

## docker-executor
 - updated_at : 2026-06-03
 - path: `docs/specs/2026-06-03-docker-executor.md`
 - 触发规则：当设计、修改或扩展 Docker 沙箱执行器时阅读，包括容器生命周期、CLI 路径配置、卷挂载策略和 git worktree 路径修复
 - 内容摘要：Docker 沙箱执行器规格，定义容器创建/复用/销毁生命周期、CLI 路径映射（宿主机与容器）、卷挂载策略、git worktree 路径修复机制和不确定性事件清单

## websocket-backend
 - updated_at : 2026-06-03
 - path: `docs/specs/2026-06-03-websocket-backend.md`
 - 触发规则：当设计、修改或扩展 WebSocket 连接管理、房间机制、广播功能或异常体系时阅读
 - 内容摘要：WebSocket 后端模块规格，定义连接生命周期、房间模型（按 group_chat_id 隔离）、刷新信号广播机制、API 契约（WebSocket 端点和 HTTP 广播 API）、异常体系（双重继承设计）

## group-chat-api
 - updated_at : 2026-06-03
 - path: `docs/specs/2026-06-03-group-chat-api.md`
 - 触发规则：当设计、修改或扩展群聊 API 接口时阅读，包括群聊生命周期管理、成员管理、消息交互和 Docker 沙箱控制
 - 内容摘要：Group Chat API 模块规格，定义 RESTful 接口（创建/查询/删除群聊、成员查询、消息历史、Docker 开关控制）、Schema 定义、异常处理和架构分层（Route → Service → Manager）

## skills-api
 - updated_at : 2026-06-03
 - path: `docs/specs/2026-06-03-skills-api.md`
 - 触发规则：当设计、修改或扩展全局 skill 库管理、skill API 接口或 SKILL.md 解析逻辑时阅读
 - 内容摘要：skills API 模块规格，定义全局 skill 库管理、CRUD 操作、SKILL.md 解析规则、路径安全校验、API 契约（GET/DELETE/POST 端点）和异常处理

## teams
 - updated_at : 2026-06-06
 - path: `docs/specs/2026-06-06-teams.md`
 - 触发规则：当设计、修改或扩展 teams 团队管理模块时阅读
 - 内容摘要：teams 团队管理模块的正式规格，定义团队 CRUD、成员验证、持久化策略和 HTTP API 契约

## realtime
 - updated_at : 2026-06-06
 - path: `docs/specs/2026-06-06-realtime.md`
 - 触发规则：当设计、修改或扩展 realtime 模块的连接管理、房间模型、广播机制、事件模型或异常体系时阅读
 - 内容摘要：realtime 模块规格，定义 WebSocket 连接管理（connect/disconnect/broadcast）、房间模型（按 group_chat_id 隔离、自动清理空房间）、进程级单例依赖注入、RefreshSignal 事件结构和 WebSocket 异常双重继承体系

## production-deployment
 - updated_at : 2026-06-06
 - path: `docs/specs/2026-06-06-production-deployment.md`
 - 触发规则：当设计、修改生产环境部署方案、Docker 配置、容器编排或运维流程时阅读
 - 内容摘要：生产部署规格，定义 Docker 多阶段镜像构建、容器服务架构（后端+前端+Redis）、网络拓扑、数据持久化卷策略、环境配置注入、部署/升级/回滚流程和健康检查机制

## config
 - updated_at : 2026-06-06
 - path: `docs/specs/2026-06-06-config.md`
 - 触发规则：当设计、修改或扩展 config 模块的配置项、路径策略、枚举定义或 CLI 路径映射时阅读
 - 内容摘要：config 模块规格，定义系统配置管理（三级路径优先级策略）、配置持久化到 YAML、AgentPlatform/RoleType 枚举、CLI 路径映射（宿主机与 Docker）、User 名称后缀处理规则

## message-flow-and-persistence
 - updated_at : 2026-06-05
 - path: `docs/specs/2026-06-05-message-flow-and-persistence.md`
 - 触发规则：当设计、修改消息传递流程、MessageRouter 职责、GroupChat.send_message_to_agent() 方法或消息持久化策略时阅读
 - 内容摘要：消息流转与持久化规格，定义 user/agent 之间的消息传递路径、MessageRouter 职责边界（纯投递层，不保存消息）、GroupChat.send_message_to_agent() 统一包装投递和保存、所有消息都保存到群聊历史的规则

## frontend-core
 - updated_at : 2026-06-06
 - path: `docs/specs/2026-06-06-frontend-core.md`
 - 触发规则：当设计、修改或扩展前端 core 层的 WebSocket 管理器、API 客户端、IndexedDB 存储或主题管理器时阅读
 - 内容摘要：前端核心层规格，定义 WebSocket 连接策略（指数退避重连、消息队列、事件订阅）、REST API 客户端职责（拦截器、统一错误处理、Mock 支持）、Storage 的 IndexedDB 用途（last_view_at 持久化）、Theme 的 CSS 变量注入方式和所有 API 函数分组（groupChat/role/skill/team）

## agent-prompt-system
 - updated_at : 2026-06-06
 - path: `docs/specs/2026-06-06-agent-prompt-system.md`
 - 触发规则：当设计、修改或扩展 Agent 提示词系统时阅读，包括 Runtime 注入、工具使用说明注入、消息渲染、Heartbeat 和 Task 闭环提醒
 - 内容摘要：Agent 提示词系统规格，定义发送给 Agent 的所有提示词来源、注入机制、渲染规则和平台标识

## frontend-features
 - updated_at : 2026-06-06
 - path: `docs/specs/2026-06-06-frontend-features.md`
 - 触发规则：当设计、修改或扩展前端 features 层（chat/session/roles/skills）时阅读，包括模块职责划分、状态管理模式、模块间通信规则或 shared 层定位
 - 内容摘要：前端功能层规格，定义 chat/session/roles/skills 四个业务模块的职责边界、Zustand 独立 store 状态管理模式、跨 feature 通信规则（store 订阅/props/core 中转）、shared 层分层职责（types 定义契约、adapters 转换数据、components 提供复用）

## pinned-messages
 - updated_at : 2026-06-07
 - path: `docs/specs/2026-06-06-pinned-messages.md`
 - 触发规则：当设计、修改或扩展消息置顶功能时阅读，包括 pin/unpin API、右侧栏 Pinned 模块、hover pin 按钮交互和 Agent 上下文注入
 - 内容摘要：消息置顶功能规格，定义 RESTful 端点（GET/POST/DELETE pinned-messages）、使用 message_id 标识消息、hover 气泡底部 pin 按钮交互、右侧栏 Pinned 模块展示、取消置顶操作和 Pin 消息自动注入到 Agent 提示词的行为（XML 格式、MAIN 会话触发、按时间升序排列）

## message-reply-quote
 - updated_at : 2026-06-07
 - path: `docs/specs/2026-06-07-message-reply-quote.md`
 - 触发规则：当设计、修改或扩展消息引用功能时阅读，包括引用按钮交互、引用框展示、Markdown 引用语法格式和错误处理
 - 内容摘要：消息引用功能规格，定义前端纯实现的引用机制（无需后端支持）、hover 气泡显示引用按钮（💬）、输入框上方引用框展示（发言者+内容摘要）、Markdown 块引用语法格式化（`> `前缀）、发送失败时保留引用状态的错误处理策略

## permission-request
 - updated_at : 2026-06-08
 - path: `docs/specs/2026-06-08-permission-request.md`
 - 触发规则：当设计、修改或扩展权限请求功能时阅读，包括 MCP request_permission 工具、消息内嵌权限卡片、PATCH 审批 API 和前端交互
 - 内容摘要：权限请求功能规格，定义 Agent 通过 MCP 工具发起权限请求、消息内嵌 permission_request 字段设计、PATCH 审批端点、AgentCallManager 通知机制和前端 PermissionRequest 卡片交互
