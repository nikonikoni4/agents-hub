---
version: 2.0
created_at: 2026-05-20
updated_at: 2026-05-31
last_updated: 同步文档与代码库实际状态
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
├── exceptions.py                  # 顶层异常基类（所有模块异常的根）
│
├── core/                          # 核心业务逻辑层（分层架构）
│   ├── foundation/                # 🔵 基础层（最底层，无依赖）
│   │   ├── models.py              # 基础数据模型（枚举、状态等）
│   │   ├── message.py             # AgentMessage 消息类
│   │   ├── exceptions.py          # 基础层异常
│   │   ├── constants.py           # 常量定义
│   │   └── renderer.py            # 渲染层（AgentMessage ↔ 可读字符串）
│   │
│   ├── communication/             # 🟢 通信层（依赖 foundation）
│   │   ├── message_router.py      # 消息路由器
│   │   ├── agent_call.py          # 调用记录
│   │   └── agent_call_manager.py  # 调用管理器
│   │
│   ├── context/                   # 🟠 上下文层（依赖 foundation）
│   │   ├── group_chat_session.py  # 群聊会话
│   │   ├── group_chat_context.py  # 群聊上下文
│   │   ├── group_chat_repository.py # 群聊持久化层
│   │   └── agent_context.py       # Agent 上下文（未来实现）
│   │
│   ├── agent/                     # 🟡 Agent 层（依赖 foundation + communication）
│   │   ├── base_agent.py          # Agent 基类
│   │   ├── manager.py             # 管理者
│   │   └── worker.py              # 工作者
│   │
│   └── orchestration/             # 🔴 编排层（依赖所有下层）
│       ├── team.py                # 团队
│       ├── group_chat.py          # 群聊
│       └── group_chat_manager.py  # 群聊管理器
│
├── mcp/                           # MCP Server（Agent 间通信）
│   └── __init__.py                # [待实现] MCP Server 主入口
│
├── api/                           # API Server（前端通信）
│   └── __init__.py                # [待实现] FastAPI 主应用
│
├── agent_bridge/                  # Agent 平台适配层
│   ├── bridge.py                  # 统一的 Agent 调用接口
│   ├── models.py                  # 数据模型（StreamEvent、AgentResult 等）
│   ├── protocols.py               # Executor 和 Parser 协议定义
│   ├── exceptions.py              # Agent Bridge 异常类
│   ├── executors/                 # 各平台执行器
│   │   ├── claude.py              # Claude Code CLI 执行器
│   │   └── codex.py               # Codex CLI 执行器
│   └── parsers/                   # 各平台响应解析器
│       ├── claude.py              # Claude 响应解析器
│       └── codex.py               # Codex 响应解析器
│
├── roles/                         # Role 管理
│   ├── role.py                    # Role 类
│   ├── role_manager.py            # Role 管理器
│   ├── models.py                  # 数据模型（RoleConfig、RoleType 等）
│   └── exceptions.py              # Roles 异常类
│
├── config/                        # 配置管理
│   ├── config.py                  # SystemConfig 单例（路径管理）
│   └── types.py                   # 配置类型定义（AgentPlatform、RoleType 等）
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
│  - AgentCallManager: 调用管理   - GroupChatRepository: 持久化│
│                                 - AgentContext: Agent上下文  │
├─────────────────────────────────────────────────────────────┤
│  foundation/  (基础层)                                       │
│  - models.py: 基础数据模型（枚举、状态等）                    │
│  - message.py: AgentMessage 消息类                           │
│  - exceptions.py: 异常类定义                                 │
│  - constants.py: 常量定义                                    │
│  - renderer.py: 渲染层（消息 ↔ 可读字符串）                  │
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
**职责**：定义基础数据结构、枚举、异常类、常量、渲染函数，**零依赖**

**文件**：
- `models.py`: 基础数据模型
  - `SessionType`: 会话类型（MAIN/BTW）
  - `MessageType`: 消息类型（TASK/NOTIFICATION）
  - `CallStatus`: 调用状态（PENDING/RUNNING/COMPLETED/FAILED/TIMEOUT）
  - `GroupChatType`: 群聊类型（SEQUENCE_EXECUTE/MANAGER_ORCHESTRATE）

- `message.py`: 消息类
  - `AgentMessage`: Agent 之间传递的消息

- `exceptions.py`: 异常类
  - `InvalidMessageError`: 无效消息
  - `FileSystemError`: 文件系统错误
  - 其他基础异常...

- `constants.py`: 常量
  - `MAX_TOKEN`: 压缩阈值
  - `LOCAL_DATA_PATH`: 本地数据存储路径

- `renderer.py`: 渲染层
  - `render_for_llm`: AgentMessage → LLM prompt 字符串
  - `render_for_chat`: Agent 输出 → 群聊记录字符串
  - `parse_chat_input`: 前端输入 → (send_to, content)
  - `Tag`: 预定义 XML 标签常量

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
  - `AgentSessionInfo`: Agent 会话信息
  - `AgentContextState`: Agent 上下文状态

- `group_chat_context.py`: 群聊上下文
  - `GroupChatContext`: 管理群聊的压缩、上下文加载

- `group_chat_repository.py`: 群聊持久化层
  - `GroupChatRepository`: 文件读写和并发控制（锁保护）
  - 负责 GroupChatSession、agent_session_state、compact_history 的持久化

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

#### 5. orchestration/ - 编排层
**职责**：团队和群聊的编排管理，**依赖所有下层**

**文件**：
- `team.py`: 团队
  - `Team`: 团队定义，包含成员列表

- `group_chat.py`: 群聊
  - `GroupChat`: 群聊管理，协调 Agent、消息路由、上下文

- `group_chat_manager.py`: 群聊管理器
  - `GroupChatManager`: 全局管理所有 GroupChat 实例

### 异常体系

采用**统一异常基类 + 模块专属异常**的分层设计：

```
agents_hub/exceptions.py (顶层)
├── AgentsHubError           # 所有异常基类
│   ├── ValidationError      # 验证错误
│   ├── ResourceNotFoundError # 资源不存在
│   ├── StateError           # 状态错误
│   └── ExternalServiceError # 外部服务错误
└── RecoverableError         # 可恢复错误标记（支持重试）
```

各模块继承顶层异常，定义专属错误：
- `core/foundation/exceptions.py`: InvalidMessageError、FileSystemError 等
- `agent_bridge/exceptions.py`: AgentBridgeError（继承 ExternalServiceError）
- `roles/exceptions.py`: RoleNotFoundError、SkillNotFoundError 等

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

- `protocols.py`: 协议定义
  - `Executor`: 执行器协议（Protocol）
  - `Parser`: 解析器协议（Protocol）

- `executors/`: 各平台的执行器
  - `claude.py`: Claude Code CLI 执行器（通过子进程调用 `claude` 命令）
  - `codex.py`: Codex CLI 执行器（通过子进程调用 `codex` 命令）

- `parsers/`: 各平台的响应解析器
  - `claude.py`: 解析 Claude Code CLI 的输出
  - `codex.py`: 解析 Codex CLI 的输出

- `models.py`: 数据模型
  - `StreamEvent`: 流式事件格式
  - `AgentEventType`: 事件类型枚举（INIT/TEXT_DELTA/TOOL_USE/TURN_COMPLETE/RESULT）
  - `AgentResult`: Agent 执行结果（统一格式）

- `exceptions.py`: Agent Bridge 异常类
  - `AgentBridgeError`: Agent Bridge 错误基类

### Config

**职责**：管理系统配置和类型定义

**文件**：
- `config.py`: SystemConfig 单例
  - 管理三种路径：开发环境、打包环境默认、数据迁移
  - 优先级：数据迁移路径 > 打包环境默认路径 > 开发环境路径

- `types.py`: 配置类型定义
  - `AgentPlatform`: Agent 平台枚举（CLAUDE/CODEX）
  - `RoleType`: 角色类型枚举

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

- `exceptions.py`: Roles 异常类
  - `RoleNotFoundError`: 角色不存在
  - `SkillNotFoundError`: Skill 不存在
  - `PlatformConfigNotFoundError`: 平台配置目录不存在

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

### 技术栈

| 层面 | 技术选择 | 说明 |
|------|---------|------|
| **框架** | React 18+ | UI 框架 |
| **桌面端** | Electron | 跨平台桌面应用 |
| **状态管理** | Zustand | 轻量、模块化切片，支持 persist/devtools 中间件 |
| **路由** | React Router v6 | 支持嵌套路由，为多视图切换做准备 |
| **样式** | Tailwind CSS + CSS Modules | Tailwind 快速开发，CSS Modules 处理复杂组件样式隔离 |
| **Markdown** | react-markdown + rehype-highlight | 轻量、可扩展、支持代码高亮 |
| **虚拟滚动** | @tanstack/react-virtual | 高性能虚拟滚动 |
| **代码编辑器** | Monaco Editor | 用于预览/编辑代码 |
| **Diff 视图** | react-diff-view | 专业 diff 渲染（side-by-side / unified） |
| **打包** | Vite + Electron | 快速构建 |

### 架构原则

采用 **分层 + 按功能模块化** 的组织方式：

- **core/**：业务无关的核心层（WebSocket、API、Storage），可被任意 feature 复用
- **features/**：按业务领域划分的独立功能模块，每个模块自带 components/hooks/store
- **shared/**：跨 feature 复用的通用资源（按钮、输入框、工具函数等）
- **layouts/**：页面级布局组件

**模块隔离原则**：
- features 之间不直接相互依赖，通过 core 层或 shared 层通信
- 每个 feature 内部自治：UI、状态、副作用都封装在模块内
- 新增功能（预览/Diff/任务管理）只需新增 feature 模块，无需改动现有代码

### 目录结构

```
frontend/
├── src/
│   ├── core/                       # 核心层（业务无关）
│   │   ├── websocket/              # WebSocket 管理（连接、重连、消息分发）
│   │   │   └── WebSocketManager.ts
│   │   ├── api/                    # REST API 封装
│   │   │   └── client.ts
│   │   └── storage/                # 本地存储（IndexedDB 封装）
│   │       └── index.ts
│   │
│   ├── features/                   # 功能模块（按业务领域划分）
│   │   ├── chat/                   # 聊天功能（MVP 核心）
│   │   │   ├── components/         # ChatWindow、MessageList、InputArea 等
│   │   │   ├── hooks/              # useChat、useMessages 等
│   │   │   ├── store/              # chatStore.ts（Zustand）
│   │   │   └── types.ts
│   │   │
│   │   ├── session/                # 会话管理（会话列表、切换）
│   │   │   ├── components/         # SessionList、SessionItem 等
│   │   │   ├── hooks/
│   │   │   ├── store/
│   │   │   └── types.ts
│   │   │
│   │   ├── preview/                # 预览功能（Phase 2）
│   │   │   ├── components/         # PreviewPanel、FileTree、LivePreview 等
│   │   │   ├── hooks/              # useFileSystem、usePreviewServer
│   │   │   ├── store/
│   │   │   └── types.ts
│   │   │
│   │   ├── diff/                   # Diff 视图（Phase 2）
│   │   │   ├── components/         # DiffPanel、DiffViewer、FileChanges
│   │   │   ├── hooks/              # useDiff
│   │   │   ├── store/
│   │   │   └── types.ts
│   │   │
│   │   └── tasks/                  # Agent 任务管理（Phase 2）
│   │       ├── components/         # TaskPanel、TaskList、TaskProgress
│   │       ├── hooks/              # useTasks
│   │       ├── store/
│   │       └── types.ts
│   │
│   ├── shared/                     # 共享资源
│   │   ├── components/             # 通用组件（Button、Input、Modal 等）
│   │   ├── hooks/                  # 通用 hooks
│   │   ├── utils/                  # 工具函数
│   │   └── types/                  # 全局类型定义
│   │
│   ├── layouts/                    # 布局组件
│   │   ├── MainLayout.tsx          # 主布局（TopBar + 两栏）
│   │   └── ChatLayout.tsx          # 聊天布局
│   │
│   └── App.tsx                     # 主应用入口
│
└── electron/                       # Electron 主进程
    └── main.ts
```

### 核心模块说明

#### core/websocket
**职责**：统一管理 WebSocket 连接、自动重连、消息分发

**关键能力**：
- 单例模式管理连接生命周期
- 指数退避重连策略（最多 5 次）
- 基于事件类型的消息订阅/分发（`on(event, callback)`）
- 消息发送队列（断连时缓存，恢复后重发）

#### core/api
**职责**：封装所有 REST API 调用

**关键能力**：
- 统一的请求/响应拦截
- 错误处理和重试
- TypeScript 类型自动推导

#### core/storage
**职责**：本地数据持久化（用户偏好、未发送消息草稿等）

**关键能力**：
- IndexedDB 封装（支持大数据量）
- 与 Zustand persist 中间件集成

### Feature 模块组织规范

每个 feature 模块遵循统一结构：

```
features/<feature_name>/
├── components/      # UI 组件，仅消费本模块的 hooks 和 store
├── hooks/           # 业务逻辑封装，调用 core 层和 store
├── store/           # Zustand store，管理本模块状态
└── types.ts         # 模块专属类型定义
```

**依赖方向**：
```
components → hooks → store
              ↓
            core/
```

- `components` 只关心展示，不直接调用 API 或操作 WebSocket
- `hooks` 负责副作用（API 调用、WebSocket 订阅）和状态变更
- `store` 只负责状态存储和派生计算

### 状态管理策略

使用 **Zustand** 进行模块化状态管理：

- **每个 feature 拥有独立 store**，避免单一全局状态膨胀
- **跨模块状态共享**通过 store 之间的订阅实现，而非提升到全局
- **持久化数据**（如会话列表、未发送消息）使用 `persist` 中间件
- **临时状态**（如 UI 展开/收起）放在组件内部 useState

### 性能优化策略

| 场景 | 优化方案 |
|------|---------|
| 长消息列表渲染 | 虚拟滚动（@tanstack/react-virtual） |
| 历史消息加载 | 分页加载 + 滚动到顶部触发加载 |
| WebSocket 高频消息 | 批量更新（requestAnimationFrame 节流） |
| Markdown 渲染 | React.memo + useMemo 缓存渲染结果 |
| 代码高亮 | Web Worker 异步处理 |
| 文件预览 | 懒加载 + 按需渲染 iframe |

### 扩展性设计

后续功能直接以 feature 模块形式新增，无需改动现有架构：

| 功能 | 落点 | 关键依赖 |
|------|------|---------|
| **预览** | `features/preview/` | iframe 隔离 + Monaco Editor + WebSocket 实时同步 |
| **Diff 视图** | `features/diff/` | react-diff-view + 语法高亮 |
| **Agent 任务管理** | `features/tasks/` | WebSocket 状态推送 + 任务日志查看 |
| **文件上传** | `features/files/` | core/api 扩展上传接口 |
| **消息搜索** | `features/search/` | 复用 core/storage 做索引 |

## 开发计划

### 阶段 1：核心层实现 ✅
- [x] 创建分层目录结构
- [x] 实现 foundation 层（models/message/exceptions/constants/renderer）
- [x] 实现 communication 层（message_router/agent_call/agent_call_manager）
- [x] 实现 context 层（group_chat_session/group_chat_context/group_chat_repository）
- [x] 实现 agent 层（base_agent/manager/worker）
- [x] 实现 orchestration 层（team/group_chat/group_chat_manager）
- [x] 实现异常体系（统一基类 + 模块专属异常）
- [x] 实现 config 模块（SystemConfig + types）

### 阶段 2：MCP Server（当前阶段）
- [x] 实现 MCP Server 框架
- [x] 注册 call_agent tool
- [x] 在 Claude Code 中测试

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