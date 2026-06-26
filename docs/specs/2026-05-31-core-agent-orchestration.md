---
version: 2.1
created_at: 2026-05-31
updated_at: 2026-06-24
last_updated: 新增 execute_with_first_response 接口，支持群聊首响
abstract: core/agent 和 core/orchestration 层的正式规格，定义 Agent 执行模型、团队角色体系、群聊编排机制、MCP 工具入口
id: spec-core-agent-orchestration
title: Core Agent & Orchestration 层规格
status: draft
module: core/agent, core/orchestration
sourc_spec: null
related_plan: null
code_scope:
  - agents_hub/core/agent/
  - agents_hub/core/orchestration/
contract_refs:
  - agents_hub/core/agent/base_agent.py
  - agents_hub/core/agent/manager.py
  - agents_hub/core/agent/worker.py
  - agents_hub/core/orchestration/group_chat.py
  - agents_hub/core/orchestration/group_chat_manager.py
  - agents_hub/core/foundation/models.py
  - agents_hub/core/foundation/renderer.py
---

# Core Agent & Orchestration 层规格

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |
| 1.1 | 新增 token 生命周期、token 索引、runtime 注入、task_manager、MCP 工具入口更新 |
| 1.2 | Team 语义明确（team_members 包含 manager+worker）、初始化分离机制、user 伪 Agent 注册、config.default_manager_name / default_user_name 替代硬编码 |
| 1.3 | 对齐现有实现中的 GroupChat 组件持有关系和 context.repository 访问 |
| 1.4 | 对齐 Agent.run 显式公开发言、显式 AgentCall 闭环，以及 complete_task 的 Agent 完成通知和 user 群聊回执 |
| 2.0 | 按照新 spec 规则重构：移除执行细节，添加 key_function 标签和 Design Rationale |
| 2.1 | 新增 execute_with_first_response 接口，支持群聊首响 |

## Overview

**业务问题**：如何实现多 Agent 协作的完整流程，包括 Agent 执行、团队组建、群聊编排和工具调用？

**核心职责**：
- **agent 层**：定义 Agent 的执行模型——消息循环、上下文加载、LLM 调用、显式闭环提醒
- **orchestration 层**：定义群聊的编排机制——团队组建、群聊生命周期、成员管理、MCP 工具入口

两者合为一个 spec，因为 orchestration 直接创建和管理 Agent 实例，Agent 的行为只有在群聊上下文中才有意义。

## Scope

### 范围内

- Agent 基类的消息循环（run loop）和执行流程
- Manager / Worker 角色模型
- Team 定义和成员验证
- GroupChat 的启动、加载、初始化、停止、清理流程
- GroupChatManager 的全局注册表和 MCP 工具入口
- Agent Token 的生命周期管理

### 范围外

- Agent 的具体 LLM 调用实现（参见 `docs/specs/` 下的 agent_bridge 相关 spec）
- 消息路由和调用管理的底层机制（参见 `docs/specs/2026-05-31-core-communication.md`）
- 上下文和持久化的底层机制（参见 `docs/specs/2026-05-31-core-context.md`）
- 基础数据模型、枚举和异常体系（参见 `docs/specs/2026-05-31-core-foundation.md`）
- Role 配置的 CRUD 管理（参见 `docs/specs/` 下的 roles 相关 spec）

## Technical Contract

### Agent 层

<key_function last_update="2026-06-26T18:23:55+08:00">
- agents_hub/core/agent/base_agent.py
  - base_agent.Agent.__init__:47
  - base_agent.Agent.run:1080
  - base_agent.Agent.stop:150
  - base_agent.Agent.execute:178
  - base_agent.Agent.execute_with_first_response:209
  - base_agent.Agent.btw_execute:289
  - base_agent.Agent.compress_context:522
- agents_hub/core/agent/manager.py
  - manager.Manager.__init__:52
- agents_hub/core/agent/worker.py
  - worker.Worker.__init__:51
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| Agent.__init__(role_config, message_queue, group_chat_context, agent_context, message_router, agent_call_manager, task_manager) | 初始化 Agent 实例 | 必须提供所有依赖组件 |
| Agent.run() | 启动消息循环，从私有队列取消息并处理 | 异步执行，通过 stop() 停止 |
| Agent.stop() | 停止消息循环（双重保险：设置 _run=False + 发送哨兵消息） | 异步操作，等待当前消息处理完成 |
| Agent.execute(prompt, session_id) | 执行 MAIN 会话（加载增量上下文 + 拼接 prompt） | 委托给 agent_bridge |
| Agent.execute_with_first_response(prompt, use_docker, group_chat_id, system_prompt) | 执行 MAIN 会话并支持首句快速响应 | 委托给 agent_bridge，首句写入群聊历史 |
| Agent.btw_execute(prompt, session_id) | 执行 BTW 会话（直接执行，不加载增量上下文） | 委托给 agent_bridge |
| Agent.compress_context() | 压缩个人上下文 | 异步操作 |

**角色模型**：

Agent 分为两种角色，当前行为相同，预留扩展点：

| 角色 | 类 | 职责 |
|------|-----|------|
| Manager | Manager(Agent) | 团队管理者，负责任务分配和协调 |
| Worker | Worker(Agent) | 团队工作者，执行具体任务 |

**Agent 持有的组件**：
- `role_config`：从 Role 获取的配置（名称、平台、工作目录等）
- `message_queue`：私有消息队列
- `group_chat_context`：群聊上下文引用
- `agent_context`：个人上下文（增量加载）
- `message_router`：消息路由器引用
- `agent_call_manager`：调用管理器引用
- `agent_token`：身份令牌，用于 MCP 工具调用时的身份验证
- `task_manager`：任务管理器引用（由 GroupChat 创建并注入）

### Orchestration 层

<key_function last_update="2026-06-18T10:34:37+08:00">
- agents_hub/core/orchestration/group_chat.py
  - group_chat.GroupChat.__init__:49
  - group_chat.GroupChat.start:88
  - group_chat.GroupChat.load:136
  - group_chat.GroupChat.activate:162
  - group_chat.GroupChat.stop:1012
  - group_chat.GroupChat.cleanup:1027
  - group_chat.GroupChat.send_message_to_agent:563
  - group_chat.GroupChat.add_member:278
  - group_chat.GroupChat.stop_member:732
  - group_chat.GroupChat.start_member:849
  - group_chat.GroupChat.reset_member:925
  - group_chat.GroupChat.compact_history:490
- agents_hub/core/orchestration/group_chat_manager.py
  - group_chat_manager.GroupChatManager.register:61
  - group_chat_manager.GroupChatManager.unregister:153
  - group_chat_manager.GroupChatManager.load_group_chat:100
  - group_chat_manager.GroupChatManager.activate_group_chat:137
  - group_chat_manager.GroupChatManager.create_group_chat:408
  - group_chat_manager.GroupChatManager.register_token:182
  - group_chat_manager.GroupChatManager.unregister_tokens:196
  - group_chat_manager.GroupChatManager.resolve_token:217
</key_function>

**GroupChat 对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| GroupChat.__init__(team, group_chat_id, project_path, base_path) | 初始化群聊，创建并持有 GroupChatRuntime、MessageRouter、AgentCallManager、TaskManager | 必须提供 team 和 project_path |
| GroupChat.start() | 启动群聊（加载上下文、初始化 Agent、注册 Token、启动 run() 任务） | 异步操作，首次创建时保存群聊元数据 |
| GroupChat.load() | 加载已有群聊（恢复上下文、重新注册 Token、启动 run() 任务） | 异步操作，群聊必须已存在 |
| GroupChat.activate() | 激活群聊（启动所有 Agent 的 run() 任务） | 异步操作，Agent 必须已初始化 |
| GroupChat.stop() | 停止群聊（发送停止信号给所有 Agent） | 异步操作 |
| GroupChat.cleanup(timeout) | 清理群聊（停止 Agent、等待任务完成、注销 Token、关闭 Runtime） | 异步操作，超时后强制取消 |
| GroupChat.send_message_to_agent(message) | 发送消息给指定 Agent | 消息必须包含 target_agent |
| GroupChat.add_member(role_name) | 添加新成员到群聊 | 异步操作，角色必须存在 |
| GroupChat.stop_member(agent_name) | 停止指定成员 | 异步操作，返回停止结果 |
| GroupChat.start_member(agent_name) | 启动指定成员 | 异步操作，返回启动结果 |
| GroupChat.reset_member(agent_name) | 重置指定成员（停止、清理、重新初始化） | 异步操作，返回重置结果 |
| GroupChat.compact_history() | 收集所有 Agent 的职责描述，调用 context 层压缩逻辑 | 异步操作 |

**GroupChatManager 对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| GroupChatManager.register(group_chat_id, group_chat) | 注册群聊到全局注册表 | group_chat_id 必须唯一 |
| GroupChatManager.unregister(group_chat_id) | 注销群聊（先 cleanup 再删除引用，幂等） | 异步操作 |
| GroupChatManager.load_group_chat(group_chat_id) | 加载群聊（从磁盘恢复或创建新实例） | 异步操作，返回 GroupChat 实例 |
| GroupChatManager.activate_group_chat(group_chat_id) | 激活群聊 | 异步操作，群聊必须已注册 |
| GroupChatManager.create_group_chat(team, group_chat_id, project_path, base_path) | 创建新群聊并注册 | 异步操作，返回 GroupChat 实例 |
| GroupChatManager.register_token(token, agent_name, group_chat_id) | 注册 Agent Token 到索引 | 线程安全（RLock） |
| GroupChatManager.unregister_tokens(group_chat_id) | 注销群聊的所有 Token | 线程安全（RLock） |
| GroupChatManager.resolve_token(token) | 解析 Token 获取 (agent_name, group_chat_id) | 线程安全（RLock），不存在返回 None |

**Team 定义**：

Team 是一个 Pydantic 模型，定义团队成员列表：

- `team_members_name`：成员名称列表（必须非空），语义上包含 Manager + Worker 的完整成员
- `team_name`：团队名称（默认 "default_team"）

**验证规则**：创建时通过 RoleManager 验证每个成员名称对应的角色是否存在。

**初始化分离**：虽然 `team_members_name` 包含所有成员，但在 `GroupChat._init_agents()` 中 Manager 和 Worker 分开初始化：
- Manager：始终由系统默认加载（使用 `config.default_manager_name`），与 `team_members_name` 无关
- Worker：遍历 `team_members_name`，跳过与 `default_manager_name` 同名的成员后逐一创建

### MCP 工具入口

MCP Server 提供 6 个工具，Agent 通过 token 身份调用：

| 工具 | 权限 | 用途 |
|------|------|------|
| `call_agent` | Leader | 派活给团队成员 |
| `assign_tasks_to_team` | Leader | 覆盖式更新任务列表 |
| `archive_task_list` | Leader | 归档当前 ACTIVE 任务列表 |
| `check_agent_call` | 任意 agent | 查询自己发起的调用状态 |
| `report_progress` | 任意 agent | 在群聊中公开发言，不改变 AgentCall 生命周期 |
| `complete_task` | 调用接收者 | 结束需要回复的 TASK 调用，并写入最终群聊回复 |

**身份验证流程**：
1. 解析 `agent_token` → `(agent_name, group_chat_id)`
2. 校验权限（Leader-only 工具检查 RoleType）
3. 执行业务逻辑
4. 返回结果或统一格式的错误响应

**MCP Tool 契约**：
- `call_agent` 返回 call_id，调用方可通过此 ID 查询调用状态
- `complete_task` 只能用于需要回复的 TASK 调用；如果用于 notification 调用、非接收者调用或重复闭环，返回 MCP 错误响应
- `report_progress` 不创建、不关闭 AgentCall

### 状态机规则

**Agent 生命周期**：
```
INITIALIZED → RUNNING → STOPPED
                ↓
            COMPLETED (正常完成)
                ↓
            ERROR (异常退出)
```

**GroupChat 生命周期**：
```
CREATED → STARTED/LOADED → ACTIVE → STOPPED → CLEANED
                ↓
            MEMBER_ADDED (动态添加成员)
                ↓
            MEMBER_REMOVED (动态移除成员)
```

**消息处理状态机**：
```
RECEIVED → PROCESSING → COMPLETED (普通消息)
                ↓
            WAITING_REPLY (TASK 调用，等待 complete_task 闭环)
                ↓
            COMPLETED (显式闭环后)
```

**显式公开与闭环规则**：
- Agent 的普通 LLM text 输出默认不进入群聊历史
- 公开群聊发言必须通过 `report_progress`
- 需要回复的 TASK 调用必须通过 `complete_task` 闭环
- `complete_task` 会更新 AgentCall；原调用方是 Agent 时投递 NOTIFICATION 唤醒下一轮处理，原调用方是 user 时写入群聊历史并触发前端刷新

### 跨层依赖

```
orchestration → agent → communication → foundation
                  ↓           ↓
              context ────────┘
```

- agent 层依赖 communication（MessageRouter、AgentCallManager）和 context（GroupChatRuntime、AgentContext）
- orchestration 层依赖 agent（Agent、Manager、Worker）和 context（GroupChatRuntime）
- orchestration 层的 GroupChat 是当前实现中唯一同时持有 communication、context 和 task/call 管理组件的编排单元
- 当前实现中，GroupChat 持有 GroupChatRuntime，Runtime 持有 GroupChatRepository

### 与 agent_bridge 的协作

Agent.execute()、Agent.execute_with_first_response() 和 Agent.btw_execute() 委托给 agent_bridge 的 agent_platform_client，传入渲染好的 prompt、role_config 和 session_id。Agent 不直接管理 CLI 进程。

**首响机制**：Agent.execute_with_first_response() 调用 agent_bridge 的同名方法获取首句文本，然后将首句写入群聊历史（runtime.add_message），使前端能更快看到 Agent 的响应。

## Design Rationale

**为什么这样设计？**
- **Agent 与 Orchestration 合并**：orchestration 直接创建和管理 Agent 实例，Agent 的行为只有在群聊上下文中才有意义，两者必须一起理解
- **显式公开与闭环**：避免 Agent 的中间思考过程污染群聊历史，只有通过工具显式声明的内容才进入公共视野
- **Token 身份验证**：MCP 工具调用时需要身份验证，Token 机制提供轻量级的身份标识和权限控制
- **双重停止保险**：设置 _run=False 标志 + 发送哨兵消息，确保 Agent 能从阻塞的 queue.get() 中唤醒
- **初始化分离**：Manager 始终由系统默认加载，Worker 从 team_members_name 创建，确保 Manager 的稳定性

**有哪些约束？**
- Agent 的 LLM 调用必须委托给 agent_bridge，不直接管理 CLI 进程
- GroupChat 是唯一同时持有 communication、context 和 task/call 管理组件的编排单元
- Token 索引必须线程安全（使用 RLock），因为多个 Agent 可能并发调用 MCP 工具
- Team 成员名称必须通过 RoleManager 验证，确保角色存在

**有哪些已知限制？**
- Manager 和 Worker 的行为差异当前无差异，未来由编排策略决定
- GroupChatType 的具体编排实现（SEQUENCE_EXECUTE 和 MANAGER_ORCHESTRATE 的调度逻辑待实现）
- Agent 的 set_run() 方法当前占位，未来用于暂停/恢复 Agent

**相关 ADR**：
- 无

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **Agent 执行细节**：Agent 的消息循环、Runtime 注入、渲染分工等具体实现（参见 `docs/flows/` 相关 flow 文档）
- **通信层**：消息路由和调用管理的底层机制（参见 `docs/specs/2026-05-31-core-communication.md`）
- **上下文层**：上下文和持久化的底层机制（参见 `docs/specs/2026-05-31-core-context.md`）
- **基础数据模型**：枚举、AgentMessage、异常体系等基础定义（参见 `docs/specs/2026-05-31-core-foundation.md`）
- **Agent Bridge**：Agent 的具体 LLM 调用实现（参见 `docs/specs/` 下的 agent_bridge 相关 spec）
