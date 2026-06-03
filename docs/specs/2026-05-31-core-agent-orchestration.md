---
version: 1.3
created_at: 2026-05-31
updated_at: 2026-06-04
last_updated: 对齐现有实现中的 GroupChat 组件持有关系和 context.repository 访问
abstract: core/agent 和 core/orchestration 层的正式规格，定义 Agent 执行模型、团队角色体系、群聊编排机制和 MCP 工具入口
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
  - agents_hub/core/orchestration/team.py
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

## Overview

agent 和 orchestration 是 core 的**上层**，共同实现多 Agent 协作的完整流程：

- **agent 层**：定义 Agent 的执行模型——消息循环、上下文加载、LLM 调用、回复投递
- **orchestration 层**：定义群聊的编排机制——团队组建、群聊生命周期、成员管理、MCP 工具入口

两者合为一个 spec，因为 orchestration 直接创建和管理 Agent 实例，Agent 的行为只有在群聊上下文中才有意义。

## Scope

### 范围内

- Agent 基类的消息循环（run loop）和执行流程
- Manager / Worker 角色模型
- Team 定义和成员验证
- GroupChat 的启动、加载、初始化、停止、清理流程
- GroupChatManager 的全局注册表和 MCP 工具入口

### 范围外

- Agent 的具体 LLM 调用实现（属于 agent_bridge）
- 消息路由和调用管理的底层机制（属于 communication 层）
- 上下文和持久化的底层机制（属于 context 层）
- Role 配置的 CRUD 管理（属于 roles 模块）

## Core Behavior

### Agent 执行模型

每个 Agent 运行一个**消息循环**（run loop），从私有队列中取出消息并处理：

```
while _run:
    msg = await message_queue.get()     ← 从 MessageRouter 投递的队列取消息
    if msg 是停止信号: break
    prompt = render_for_llm(msg)         ← 渲染为 LLM prompt
    result = await _process_message(msg, prompt)  ← 执行
    写回群聊记录                           ← 出口 A
    如果是 TASK 且发送者不是 user:         ← 出口 B
        投递通知给发送者
```

**消息处理流程**（_process_message）：
1. 注入 runtime 信息到 work_root/CLAUDE.md（见 Runtime 注入）
2. 更新调用状态为 RUNNING
3. 如果是 MAIN 会话：加载增量上下文 + 拼接 prompt → execute()
4. 如果是 BTW 会话：直接 btw_execute()
5. 更新调用状态为 COMPLETED 或 FAILED

**Runtime 注入**：每次处理消息前，通过 `markdown_injector` 将身份信息（token、团队成员、任务看板）动态注入到 work_root 下的 CLAUDE.md/AGENTS.md 的 `<AGENT_RUNTIME_START/>` 和 `<AGENT_RUNTIME_END/>` 标记之间。详见 `2026-05-31-mcp-tools-design.md` §5。

**渲染分工**：
- 入站 prompt：render_for_llm（msg.content 不被改写）
- 出口 A 写群聊：render_for_chat（写入前调用 `redact_token()` 剥离 token）
- 出口 B 投递回复：传递 result.text 原文

**停止机制**：双重保险——设置 _run=False 标志 + 发送哨兵消息（call_id="__STOP__"）唤醒阻塞的 get()。

### 角色模型

Agent 分为两种角色，当前行为相同，预留扩展点：

| 角色 | 类 | 职责 |
|------|-----|------|
| Manager | Manager(Agent) | 团队管理者，负责任务分配和协调 |
| Worker | Worker(Agent) | 团队工作者，执行具体任务 |

每个 Agent 持有：
- `role_config`：从 Role 获取的配置（名称、平台、工作目录等）
- `message_queue`：私有消息队列
- `group_chat_context`：群聊上下文引用
- `agent_context`：个人上下文（增量加载）
- `message_router`：消息路由器引用
- `agent_call_manager`：调用管理器引用
- `agent_token`：身份令牌，用于 MCP 工具调用时的身份验证
- `task_manager`：任务管理器引用（由 GroupChat 创建并注入）

### Team 定义

Team 是一个 Pydantic 模型，定义团队成员列表：

- `team_members_name`：成员名称列表（必须非空），语义上包含 Manager + Worker 的完整成员
- `team_name`：团队名称（默认 "default_team"）

**验证规则**：创建时通过 RoleManager 验证每个成员名称对应的角色是否存在。

**初始化分离**：虽然 `team_members_name` 包含所有成员，但在 `GroupChat._init_agents()` 中 Manager 和 Worker 分开初始化：
- Manager：始终由系统默认加载（使用 `config.default_manager_name`），与 `team_members_name` 无关
- Worker：遍历 `team_members_name`，跳过与 `default_manager_name` 同名的成员后逐一创建

### GroupChat 生命周期

GroupChat 是核心编排单元，协调 Agent、消息路由和上下文管理。

当前实现中，GroupChat 在初始化时创建并持有 `GroupChatContext`、`MessageRouter`、`AgentCallManager` 和 `TaskManager`。`GroupChatContext` 内部创建并持有 `GroupChatRepository`；部分编排逻辑会通过 `group_chat_context.repository` 读取 `project_path`、保存群聊元数据或保存 Agent session 状态。

**启动流程**（start / load）：
1. 加载上下文数据（GroupChatContext.load()）
2. 首次创建时保存群聊元数据
3. 初始化 Manager 和 Workers（通过 RoleManager 获取角色配置，Worker 跳过与 `config.default_manager_name` 同名的成员）
4. 生成或恢复 Agent Token 并注册到 GroupChatManager 索引
5. 注册所有 Agent 到 MessageRouter，并注册 `config.default_user_name` 伪 Agent（空队列，支持用户 API 发消息）
6. 初始化新成员（首次进入群聊的 Agent 执行打招呼）
7. 首次创建或激活群聊时启动所有 Agent 的 run() 任务

**新成员初始化**：
- 检查哪些成员没有 session_id
- Manager：介绍自己是团队领导，列出成员
- Worker：介绍自己，说明直属领导
- 并发执行所有新成员的初始化

**群聊类型**：
- `SEQUENCE_EXECUTE`：流水线顺序执行
- `MANAGER_ORCHESTRATE`：由 Manager 动态决定安排

**清理流程**（cleanup）：
1. 停止所有 Agent（发送停止信号）
2. 等待任务完成（超时后强制取消）
3. 停止 AgentCallManager 清理任务
4. 清空 MessageRouter
5. 从 GroupChatManager 注销所有 Agent Token
6. 关闭 GroupChatContext
7. 清空所有引用

**压缩历史**：compact_history() 方法收集所有 Agent 的职责描述，调用 context 层的压缩逻辑。

### GroupChatManager 全局注册表

GroupChatManager 是全局单例，管理所有 GroupChat 实例和 Token 索引：

- `register(group_chat_id, group_chat)`：注册群聊
- `get_group_chat(group_chat_id)`：获取群聊（不存在抛 GroupChatNotFoundError）
- `unregister(group_chat_id)`：注销群聊（先 cleanup 再删除引用，幂等）

**Token 索引**（线程安全，使用 RLock）：
- `register_token(token, agent_name, group_chat_id)`：GroupChat.start/load 时调用
- `unregister_tokens(group_chat_id)`：GroupChat.cleanup 时调用
- `resolve_token(token) -> (agent_name, group_chat_id) | None`：MCP 工具调用时解析身份

### MCP 工具入口

MCP Server 提供 4 个工具，Agent 通过 token 身份调用（设计详见 `2026-05-31-mcp-tools-design.md` §3）：

| 工具 | 权限 | 用途 |
|------|------|------|
| `call_agent` | Leader | 派活给团队成员 |
| `assign_tasks_to_team` | Leader | 覆盖式更新任务列表 |
| `archive_task_list` | Leader | 归档当前 ACTIVE 任务列表 |
| `check_agent_call` | 任意 agent | 查询自己发起的调用状态 |

**身份验证流程**：
1. 解析 `agent_token` → `(agent_name, group_chat_id)`
2. 校验权限（Leader-only 工具检查 RoleType）
3. 执行业务逻辑
4. 返回结果或统一格式的错误响应

## Technical Contract

### 跨层依赖

```
orchestration → agent → communication → foundation
                  ↓           ↓
              context ────────┘
```

- agent 层依赖 communication（MessageRouter、AgentCallManager）和 context（GroupChatContext、AgentContext）
- orchestration 层依赖 agent（Agent、Manager、Worker）和 context（GroupChatContext）
- orchestration 层的 GroupChat 是当前实现中唯一同时持有 communication、context 和 task/call 管理组件的编排单元
- 当前实现中，GroupChat 不直接创建 Repository；Repository 由 GroupChatContext 创建并暴露给 GroupChat 的部分生命周期逻辑使用

### MCP Tool 契约

call_agent 返回 call_id（字符串），调用方可通过此 ID 查询调用状态。错误时返回 MCP 响应格式的错误信息。

### 与 agent_bridge 的协作

Agent.execute() 和 Agent.btw_execute() 委托给 agent_bridge 的 agent_platform_client，传入渲染好的 prompt、role_config 和 session_id。Agent 不直接管理 CLI 进程。

## Out of Spec

- Manager 和 Worker 的行为差异（当前无差异，未来由编排策略决定）
- GroupChatType 的具体编排实现（SEQUENCE_EXECUTE 和 MANAGER_ORCHESTRATE 的调度逻辑待实现）
- Agent 的 set_run() 方法（当前占位，未来用于暂停/恢复 Agent）
- Role 配置的详细结构（属于 roles 模块 spec）
- agent_bridge 的执行细节（属于 agent_bridge spec）
