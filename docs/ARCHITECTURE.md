---
version: 2.0
created_at: 2026-05-20
updated_at: 2026-05-30
last_updated: 完成核心架构设计，创建分层目录结构
abstract: 项目架构地图，概述仓库物理结构、抽象分层、前后端架构、主干数据流和关键依赖方向。
---

# ARCHITECTURE

## 项目概述

agents-hub 是一个以 Claude Code / Codex 为基础的多 Agent IM 聊天对话平台，实现多 Agent 交互、代码开发、预览、部署等功能。

## 技术栈

- **后端**：Python + FastAPI + WebSocket
- **前端**：React + Electron
- **Agent 通信**：MCP (Model Context Protocol)
- **Agent 平台**：Claude Code、Codex

## 整体架构

agents-hub 是一个**中间层平台**，连接不同的 Agent 平台（Claude Code、Codex 等），实现多 Agent 协作。

```
┌─────────────────────────────────────────────────────────────┐
│                         前端层                               │
│                   React + Electron                          │
└────────────────────┬────────────────────────────────────────┘
                     │ WebSocket
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                      API Server                             │
│                   FastAPI + WebSocket                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                   agents-hub (中间层)                        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  MCP Server (向上暴露 tools)                           │ │
│  │  接收 Agent 平台的 tool_use 调用                        │ │
│  └────────────────────┬───────────────────────────────────┘ │
│                       ↓                                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Core 核心层                                           │ │
│  │  多 Agent 协作、消息路由、上下文管理                     │ │
│  └────────────────────┬───────────────────────────────────┘ │
│                       ↓                                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Agent Bridge (向下调用 Agent 平台)                     │ │
│  │  适配不同 Agent 平台的 CLI                              │ │
│  └────────────────────┬───────────────────────────────────┘ │
└───────────────────────┼──────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ↓                               ↓
┌──────────────────┐          ┌──────────────────┐
│  Claude Code CLI │          │   Codex CLI      │
│  (本地进程)       │          │   (本地进程)      │
└──────────────────┘          └──────────────────┘
```

**关键理解**：
- **agents-hub 是中间层**：连接不同的 Agent 平台，实现跨平台协作
- **向上（MCP Server）**：暴露 MCP tools 给 Agent 平台（Claude Code、Codex 作为 MCP Client）
- **向下（Agent Bridge）**：调用不同 Agent 平台的 CLI（通过子进程）
- **核心层（Core）**：管理消息路由、群聊、上下文等业务逻辑

## 后端架构详解

### 目录结构

```
agents_hub/
├── core/                          # 核心业务逻辑层（分层架构）
│   ├── foundation/                # 🔵 基础层（最底层，无依赖）
│   ├── communication/             # 🟢 通信层（依赖 foundation）
│   ├── agent/                     # 🟡 Agent 层（依赖 foundation + communication）
│   ├── context/                   # 🟠 上下文层（依赖 foundation）
│   └── orchestration/             # 🔴 编排层（依赖所有下层）
│
├── mcp/                           # MCP Server（Agent 间通信）
│   └── server.py                  # MCP Server 主入口
│
├── api/                           # API Server（前端通信）
│   └── main.py                    # FastAPI 主应用
│
├── agent_bridge/                  # Agent 平台适配层
│   ├── bridge.py                  # 统一的 Agent 调用接口
│   ├── executors/                 # 各平台执行器
│   └── parsers/                   # 各平台响应解析器
│
├── roles/                         # Role 管理
│   ├── role.py                    # Role 类
│   └── role_manager.py            # Role 管理器
│
├── config/                        # 配置管理
│   └── types.py                   # 配置类型定义
│
└── utils/                         # 工具函数
    └── logger.py                  # 日志工具
```

### Core 层分层架构

Core 层采用**严格的分层架构**，遵循**单向依赖原则**：上层依赖下层，下层不依赖上层。

```
┌─────────────────────────────────────────────────────────────┐
│  orchestration/  (编排层)                                    │
│  - Team: 团队管理                                            │
│  - GroupChat: 群聊管理                                       │
│  - GroupChatManager: 群聊管理器                              │
├─────────────────────────────────────────────────────────────┤
│  agent/  (Agent 层)                                          │
│  - Agent: Agent 基类                                         │
│  - Manager: 团队管理者                                       │
│  - Worker: 团队工作者                                        │
├─────────────────────────────────────────────────────────────┤
│  communication/  (通信层)        context/  (上下文层)        │
│  - MessageRouter: 消息路由      - GroupChatContext: 上下文   │
│  - AgentCall: 调用记录          - GroupChatSession: 会话     │
│  - AgentCallManager: 调用管理   - AgentContext: Agent上下文  │
├─────────────────────────────────────────────────────────────┤
│  foundation/  (基础层)                                       │
│  - models.py: 基础数据模型（枚举、状态等）                    │
│  - message.py: AgentMessage 消息类                           │
│  - exceptions.py: 异常类定义                                 │
│  - constants.py: 常量定义                                    │
└─────────────────────────────────────────────────────────────┘
```

**依赖关系**：
```
orchestration → agent → communication → foundation
                  ↓           ↓
              context ────────┘
```

**关键设计原则**：
- `communication/` 和 `context/` 是**同层**，互不依赖
- `agent/` 依赖 `communication/`，但不依赖 `context/`
- `orchestration/` 是唯一可以同时依赖 `agent/` 和 `context/` 的层
- 所有层都可以依赖 `foundation/`

### 各层职责说明

#### 1. foundation/ - 基础层
**职责**：定义基础数据结构、枚举、异常类、常量，**零依赖**

**文件**：
- `models.py`: 基础数据模型
  - `SessionType`: 会话类型（MAIN/BTW）
  - `MessageType`: 消息类型（TASK/NOTIFICATION）
  - `CallStatus`: 调用状态（PENDING/RUNNING/COMPLETED/FAILED/TIMEOUT）
  - `GroupChatType`: 群聊类型（SEQUENCE_EXECUTE/MANAGER_ORCHESTRATE）

- `message.py`: 消息类
  - `AgentMessage`: Agent 之间传递的消息

- `exceptions.py`: 异常类
  - `AgentsHubError`: 所有异常的基类
  - `AgentNotFoundError`: Agent 不存在
  - `GroupChatNotFoundError`: GroupChat 不存在
  - `MessageDeliveryError`: 消息投递失败
  - 其他业务异常...

- `constants.py`: 常量
  - `MAX_TOKEN`: 压缩阈值
  - `LOCAL_DATA_PATH`: 本地数据存储路径

#### 2. communication/ - 通信层
**职责**：消息路由和调用管理，**只依赖 foundation**

**文件**：
- `message_router.py`: 消息路由器
  - `MessageRouter`: 管理 Agent 的消息队列，负责消息投递

- `agent_call.py`: 调用记录
  - `AgentCall`: 记录一次 Agent 调用的完整信息（状态、结果、错误等）

- `agent_call_manager.py`: 调用管理器
  - `AgentCallManager`: 管理所有 AgentCall，提供创建、查询、更新等功能

#### 3. context/ - 上下文层
**职责**：管理群聊上下文、历史消息、压缩等，**只依赖 foundation**

**文件**：
- `group_chat_session.py`: 群聊会话
  - `GroupChatSession`: 群聊的消息历史、元数据

- `group_chat_context.py`: 群聊上下文
  - `GroupChatContext`: 管理群聊的持久化、压缩、上下文加载

- `agent_context.py`: Agent 上下文（未来实现）
  - `AgentContext`: 为 Agent 提供个性化的上下文

#### 4. agent/ - Agent 层
**职责**：Agent 执行逻辑，**依赖 foundation + communication**

**文件**：
- `base_agent.py`: Agent 基类
  - `Agent`: 所有 Agent 的基类，包含消息处理、执行逻辑

- `manager.py`: 管理者
  - `Manager`: 团队管理者，负责任务分配和协调

- `worker.py`: 工作者
  - `Worker`: 团队工作者，执行具体任务

- `llm_call.py`: LLM 调用
  - `LLMCall`: 临时的非角色 LLM 调用（用于压缩等场景）

#### 5. orchestration/ - 编排层
**职责**：团队和群聊的编排管理，**依赖所有下层**

**文件**：
- `team.py`: 团队
  - `Team`: 团队定义，包含成员列表

- `group_chat.py`: 群聊
  - `GroupChat`: 群聊管理，协调 Agent、消息路由、上下文

- `group_chat_manager.py`: 群聊管理器
  - `GroupChatManager`: 全局管理所有 GroupChat 实例

### MCP Server

**职责**：向上暴露 MCP Tools，让 Agent 平台（Claude Code、Codex）可以调用 agents-hub 的功能

**通信方式**：STDIO（标准输入/输出）

**协议**：JSON-RPC over STDIO

**角色**：agents-hub 作为 MCP Server，Agent 平台作为 MCP Client

**文件**：
- `server.py`: MCP Server 主入口
  - 使用 FastMCP 框架
  - 注册 MCP Tools
  - 处理 Agent 平台的 tool_use 请求

**提供的 MCP Tools**：
- `call_agent`: Agent 调用另一个 Agent
- `list_agents`: 列出群聊中的所有 Agent
- `get_chat_history`: 获取群聊历史消息

### API Server

**职责**：提供 REST API 和 WebSocket，让前端可以与后端通信

**通信方式**：HTTP + WebSocket

**文件**：
- `main.py`: FastAPI 主应用
  - WebSocket 端点：`/ws/group_chat/{group_chat_id}`
  - REST API：创建群聊、获取 Agent 列表、获取历史消息等

### Agent Bridge

**职责**：向下调用不同 Agent 平台的 CLI，适配不同平台的接口差异

**通信方式**：子进程调用本地 CLI

**角色**：agents-hub 调用 Agent 平台的 CLI（Claude Code CLI、Codex CLI）

**文件**：
- `bridge.py`: 统一的 Agent 调用接口
  - 提供统一的 `execute()` 方法
  - 根据平台类型选择对应的执行器

- `executors/`: 各平台的执行器
  - `claude.py`: Claude Code CLI 执行器（通过子进程调用 `claude` 命令）
  - `codex.py`: Codex CLI 执行器（通过子进程调用 `codex` 命令）

- `parsers/`: 各平台的响应解析器
  - `claude.py`: 解析 Claude Code CLI 的输出
  - `codex.py`: 解析 Codex CLI 的输出

- `models.py`: 数据模型
  - `AgentResult`: Agent 执行结果（统一格式）
  - `AgentPlatform`: Agent 平台枚举（CLAUDE/CODEX）

### Roles

**职责**：管理 Agent 的角色配置

**文件**：
- `role.py`: Role 类
  - `Role`: 角色定义

- `role_manager.py`: Role 管理器
  - `RoleManager`: 管理所有角色，提供创建、查询等功能

- `models.py`: 数据模型
  - `RoleConfig`: 角色配置
  - `RoleType`: 角色类型（LEADER/TEAM_MEMBER）

## 数据流

### 1. User 发送消息给 Agent

```
User (前端)
  → WebSocket 发送消息
    → API Server 接收
      → Core 层路由消息
        → Agent Bridge 调用对应平台 CLI
          → Agent 平台执行
            → 返回结果
              → 保存到上下文
                → WebSocket 推送给前端
```

### 2. Agent 调用另一个 Agent（跨平台协作）

```
Agent A (Claude Code)
  → 调用 MCP tool: call_agent
    → agents-hub MCP Server 接收
      → Core 层路由消息
        → Agent Bridge 调用 Agent B 的平台 CLI
          → Agent B (Codex) 执行
            → 返回结果
              → 保存到上下文
                → 如果需要回复，返回给 Agent A
```

**关键点**：
- Agent 之间的通信通过 agents-hub 中转
- agents-hub 负责消息路由、上下文管理、持久化
- 不同平台的 Agent 可以无缝协作

## 持久化

### 本地数据存储

```
local_data/
├── agents/                        # Agent 工作目录
│   └── <role_name>/
│       └── <work_root>/
│
└── teams/                         # Team 数据
    └── <team_name>/
        └── <project_path>/
            └── <group_chat_id>/
                ├── <group_chat_id>.jsonl          # 群聊消息历史
                ├── agent_session_id.json          # Agent session 映射
                └── memory/
                    └── compact_history.jsonl      # 压缩历史
```

### 文件格式

**<group_chat_id>.jsonl**：
```jsonl
{"_type": "meta_data", "last_compact_loc": 0, "created_at": "...", "updated_at": "..."}
{"agent_name": "Leader", "content": "...", "timestamp": "...", "platform": "claude"}
{"agent_name": "小李", "content": "...", "timestamp": "...", "platform": "codex"}
```

**agent_session_id.json**：
```json
{
  "Leader": {
    "main_session": "session_id_1",
    "btw_session": ["session_id_2"]
  },
  "小李": {
    "main_session": "session_id_3",
    "btw_session": []
  }
}
```

**compact_history.jsonl**：
```jsonl
{
  "create_at": "...",
  "content": {
    "summary": "整体对话摘要",
    "Leader": "针对 Leader 的关键信息",
    "小李": "针对小李的关键信息"
  }
}
```

## 前端架构

技术栈：React + Electron

**目录结构**： [暂定结构，未最终确认]
```
frontend/
├── src/
│   ├── components/                # React 组件
│   │   ├── ChatList/              # 对话列表
│   │   ├── ChatWindow/            # 聊天窗口
│   │   └── MessageItem/           # 消息项
│   │
│   ├── services/                  # 服务层
│   │   ├── websocket.ts           # WebSocket 连接
│   │   └── api.ts                 # REST API 调用
│   │
│   ├── store/                     # 状态管理
│   │   └── chatStore.ts           # 聊天状态
│   │
│   └── App.tsx                    # 主应用
│
└── electron/                      # Electron 主进程
    └── main.ts
```

## 开发计划

### 阶段 1：核心层实现（当前阶段）
- [x] 创建分层目录结构
- [ ] 实现 foundation 层
- [ ] 实现 communication 层
- [ ] 实现 context 层
- [ ] 实现 agent 层
- [ ] 实现 orchestration 层

### 阶段 2：MCP Server
- [ ] 实现 MCP Server 框架
- [ ] 注册 call_agent tool
- [ ] 在 Claude Code 中测试

### 阶段 3：API Server
- [ ] 实现 WebSocket 端点
- [ ] 实现 REST API
- [ ] 用浏览器控制台测试

### 阶段 4：前端
- [ ] 实现 IM 界面
- [ ] 连接 WebSocket
- [ ] 完整测试

## 参考资料

- [MCP (Model Context Protocol)](https://modelcontextprotocol.io/)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Electron](https://www.electronjs.org/)