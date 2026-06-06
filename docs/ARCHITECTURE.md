---
version: 2.3
created_at: 2026-05-20
updated_at: 2026-06-06
last_updated: 瘦身：精简分层图、移除核心组件列表和开发计划，细节下沉至 spec
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
├── exceptions.py
│
├── core/                          # 核心业务逻辑层（分层架构）
│   ├── foundation/                # 基础层（最底层，无依赖）
│   ├── communication/             # 通信层（依赖 foundation）
│   ├── context/                   # 上下文层（依赖 foundation）
│   ├── agent/                     # Agent 层（依赖 foundation + communication）
│   └── orchestration/             # 编排层（依赖所有下层）
│
├── mcp/                           # MCP Server
├── api/                           # API Server（REST + WebSocket）
│   ├── routes/
│   ├── schemas/
│   ├── services/
│   └── websocket/
│
├── realtime/                      # 实时通信（连接管理、房间、广播）
├── skills/                        # 技能管理
├── teams/                         # 团队管理
│
├── agent_bridge/                  # Agent 平台适配层
│   ├── executors/                 # 各平台执行器（claude、codex）
│   ├── parsers/                   # 各平台响应解析器
│   └── docker/                    # Docker 容器支持
│
├── roles/                         # Role 管理
├── config/                        # 配置管理
└── utils/                         # 工具函数
```

### Core 层分层架构

Core 层采用**严格的分层架构**，遵循**单向依赖原则**：上层依赖下层，下层不依赖上层。

```
┌─────────────────────────────────────────────────────────────┐
│  orchestration/  (编排层)  — 群聊编排与管理                  │
├─────────────────────────────────────────────────────────────┤
│  agent/  (Agent 层)  — Agent 执行与角色管理                  │
├─────────────────────────────────────────────────────────────┤
│  communication/  (通信层)        context/  (上下文层)        │
│  消息路由、调用管理、任务管理    群聊上下文、历史、持久化     │
├─────────────────────────────────────────────────────────────┤
│  foundation/  (基础层)  — 数据模型、消息类、异常、常量        │
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

> 详细的数据结构、接口定义和行为契约请参见对应的 spec 文档。

| 层 | 职责 | Spec |
|----|------|------|
| foundation/ | 基础数据结构、枚举、异常类、常量、渲染函数，**零依赖** | [core-foundation](specs/2026-05-31-core-foundation.md) |
| communication/ | 消息路由、调用管理和任务管理，**只依赖 foundation** | [core-communication](specs/2026-05-31-core-communication.md) |
| context/ | 管理群聊上下文、历史消息、压缩等，**只依赖 foundation** | [core-context](specs/2026-05-31-core-context.md) |
| agent/ | Agent 执行逻辑，**依赖 foundation + communication** | [core-agent-orchestration](specs/2026-05-31-core-agent-orchestration.md) |
| orchestration/ | 群聊的编排管理，**依赖所有下层** | [core-agent-orchestration](specs/2026-05-31-core-agent-orchestration.md) |

### 异常体系

采用统一异常基类 + 模块专属异常的分层设计。详见 [core-foundation](specs/2026-05-31-core-foundation.md)。

### MCP Server

**职责**：向上暴露 MCP Tools，让 Agent 平台（Claude Code、Codex）可以调用 agents-hub 的功能

**通信方式**：STDIO（标准输入/输出），JSON-RPC 协议。详见 [core-agent-orchestration](specs/2026-05-31-core-agent-orchestration.md)。

### 其他模块

| 模块 | 职责 | 通信方式 | Spec |
|------|------|---------|------|
| API Server | 提供 REST API 和 WebSocket | HTTP + WebSocket | [group-chat-api](specs/2026-06-03-group-chat-api.md)、[roles](specs/2026-05-24-agents-role.md)、[skills-api](specs/2026-06-03-skills-api.md)、[websocket-backend](specs/2026-06-03-websocket-backend.md) |
| Agent Bridge | 向下调用不同 Agent 平台的 CLI，适配接口差异 | 子进程调用本地 CLI | [agent-bridge](specs/2026-05-23-agent-bridge.md) |
| Config | 管理系统配置和类型定义 | - | [config](specs/2026-06-06-config.md) |
| Roles | 管理 Agent 的角色配置 | - | [roles](specs/2026-05-24-agents-role.md) |

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
├── agents/
│   ├── assets/
│   └── <role_name>/
│       ├── role.json
│       └── work_root/
│
├── teams/
│   └── <team_name>/
│       └── <project_path>/
│           └── <group_chat_id>/
│               ├── <group_chat_id>.jsonl
│               ├── agent_member.json
│               ├── group_metadata.json
│               └── memory/
│                   └── compact_history.jsonl
│
├── skills/
└── config/
    └── config.yaml
```

**Spec**：[core-context](specs/2026-05-31-core-context.md)（持久化机制）、[roles](specs/2026-05-24-agents-role.md)（角色目录结构）

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
frontend/src/
├── core/                       # 核心层（WebSocket、API、Storage、Theme）
├── features/                   # 功能模块（chat、session、roles、skills）
├── shared/                     # 共享资源（components、adapters、types）
├── layouts/                    # 布局组件
└── App.tsx
```

**Spec**：[frontend-core](specs/2026-06-06-frontend-core.md)（Core 层规格）、[frontend-features](specs/2026-06-06-frontend-features.md)（Features 层规格）

Feature 模块组织规范和状态管理策略详见 [frontend-features](specs/2026-06-06-frontend-features.md)。

## 参考资料

- [MCP (Model Context Protocol)](https://modelcontextprotocol.io/)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Electron](https://www.electronjs.org/)