Now I have all the data needed. Let me compile the report.

---

## ARCHITECTURE.md 一致性检查报告
- 检查日期：2026-06-10

---

### 一致的部分

| 验证项 | 状态 |
|--------|------|
| 后端顶层目录结构（core/, mcp/, api/, realtime/, skills/, teams/, agent_bridge/, roles/, config/, utils/, exceptions.py） | ✅ 全部存在 |
| Core 层 5 个子目录（foundation/, communication/, context/, agent/, orchestration/） | ✅ 全部存在 |
| API Server 子目录（routes/, schemas/, services/, websocket/） | ✅ 全部存在 |
| Agent Bridge 子目录（executors/, parsers/, docker/） | ✅ 全部存在 |
| communication/ 和 context/ 互不依赖（同层隔离） | ✅ 代码验证通过 |
| foundation/ 零反向依赖（不依赖其他 core 层） | ✅ 代码验证通过 |
| orchestration/ 依赖所有下层 | ✅ 代码验证通过 |
| 前端顶层结构（core/, features/, shared/, layouts/） | ✅ 全部存在 |
| 前端 features 包含 chat, session, roles, skills | ✅ 全部存在 |
| 前端 core 包含 api, storage, theme, websocket | ✅ 全部存在 |
| 技术栈描述（FastAPI, React, Electron, Zustand 等） | ✅ 与 package.json / 代码一致 |

---

### 不一致的部分

#### 1. agent/ 层对 context/ 的依赖违反

- **位置**：Core 层分层架构 → 依赖关系图 + 各层职责说明
- **文档描述**：`agent/` 依赖 `foundation + communication`，**不依赖 context/**。依赖关系图明确标注 `agent → communication → foundation`，agent 不直接指向 context。
- **实际情况**：`agent/` 下 3 个文件均导入了 `context/` 模块：
  - `agent/base_agent.py:17` → `from agents_hub.core.context import AgentContext, GroupChatContext`
  - `agent/manager.py:8` → `from agents_hub.core.context import GroupChatContext`
  - `agent/worker.py:8` → `from agents_hub.core.context import GroupChatContext`
- **严重程度**：**Critical** — 核心分层约束被违反，可能导致层间耦合加剧
- **建议修复**：二选一：(a) 重构 agent 层，通过接口/协议注入 context 依赖，消除直接导入；(b) 更新文档，承认 agent 层依赖 context，并修正依赖关系图

#### 2. agent_bridge 缺少 opencode 平台

- **位置**：技术栈 → Agent 平台 / Agent Bridge 章节
- **文档描述**：仅列出 Claude Code、Codex 两个 Agent 平台
- **实际情况**：代码中存在第三个平台 `opencode`：
  - `agent_bridge/executors/opencode.py`
  - `agent_bridge/parsers/opencode.py`
- **严重程度**：**Warning** — 遗漏了已实现的平台支持
- **建议修复**：在技术栈和 Agent Bridge 章节补充 opencode 平台描述

#### 3. 前端 features 遗漏 single-chat 模块

- **位置**：前端架构 → 目录结构
- **文档描述**：features 包含 `chat、session、roles、skills`
- **实际情况**：代码中存在 `features/single-chat/`，包含完整的组件、hooks、store：
  - `SingleChatPanel.tsx`、`ToolCallCard.tsx`
  - `useSingleChatMessages.ts`、`useSingleChatList.ts`、`useSingleChatMembers.ts`
  - `singleChatStore.ts`
- **严重程度**：**Warning** — 重要的业务模块未被文档覆盖
- **建议修复**：在前端 features 列表中补充 `single-chat`，并简述其职责

#### 4. 后端目录树遗漏 tools/ 模块

- **位置**：后端架构详解 → 目录结构
- **文档描述**：目录树中未列出 `tools/` 目录
- **实际情况**：`agents_hub/tools/` 存在，包含 `catalog.py`（被 `api/services/role_service.py` 引用），负责工具注册与目录管理
- **严重程度**：**Warning** — 被 API 层依赖的模块未被文档记录
- **建议修复**：在目录树和"其他模块"表格中补充 `tools/` 模块

#### 5. 后端目录树遗漏 bootstrap.py

- **位置**：后端架构详解 → 目录结构
- **文档描述**：目录树中未列出 `bootstrap.py`
- **实际情况**：`agents_hub/bootstrap.py` 存在，被 `api/app.py` 导入，负责 `initialize_default_roles` 和 `initialize_resources`
- **严重程度**：**Info** — 启动初始化模块，影响范围有限
- **建议修复**：在目录树中补充 `bootstrap.py`，或在"其他模块"表格中说明

#### 6. 后端目录树遗漏 core/utils/

- **位置**：后端架构详解 → 目录结构 → Core 层
- **文档描述**：Core 层只列出 5 个子目录（foundation, communication, context, agent, orchestration）
- **实际情况**：`core/utils/` 存在，包含 `markdown_injector.py` 和 `path_utils.py`
- **严重程度**：**Info** — 工具函数层，不影响核心架构理解
- **建议修复**：在 Core 层目录树中补充 `utils/`

#### 7. agent_bridge 目录树遗漏关键文件

- **位置**：后端架构详解 → 目录结构 → agent_bridge/
- **文档描述**：仅列出 `executors/`、`parsers/`、`docker/` 三个子目录
- **实际情况**：`agent_bridge/` 根目录下还有：
  - `bridge.py` — 核心桥接逻辑
  - `models.py` — 数据模型定义
  - `protocols.py` — 协议/接口定义
  - `exceptions.py` — 虽然文档有列出 exceptions.py 但在 agent_bridge 下也有一份
- **严重程度**：**Info** — 补充性文件
- **建议修复**：在 agent_bridge 目录树中补充这些文件

#### 8. realtime/ 目录树遗漏文件

- **位置**：后端架构详解 → 目录结构 → realtime/
- **文档描述**：目录树中未详细展开 realtime/ 内部结构
- **实际情况**：`realtime/` 包含 `manager.py`、`events.py`、`dependencies.py`、`exceptions.py`
- **严重程度**：**Info** — 补充性信息
- **建议修复**：可选择性展开 realtime/ 内部文件

---

### 文档缺失覆盖

| 代码中存在的模块/文件 | 重要性 | 说明 |
|----------------------|--------|------|
| `agents_hub/tools/` | 高 | 工具注册目录，被 API 层引用，是 MCP tools 的上游 |
| `agents_hub/bootstrap.py` | 中 | 应用启动初始化逻辑 |
| `agents_hub/agent_bridge/executors/opencode.py` | 中 | 第三个 Agent 平台适配 |
| `agents_hub/agent_bridge/parsers/opencode.py` | 中 | opencode 响应解析器 |
| `frontend/src/features/single-chat/` | 高 | 独立单聊功能模块，完整实现 |
| `agents_hub/core/utils/` | 低 | Core 层工具函数 |
| `agents_hub/agent_bridge/bridge.py` | 中 | 核心桥接调度逻辑 |
| `agents_hub/agent_bridge/protocols.py` | 中 | 接口协议定义 |

---

### 总结

**一致性评分：7/10**

**主要问题**：
1. **Critical**：`agent/` 层实际依赖 `context/`，与文档描述的分层约束直接矛盾。这是最严重的问题，需要决定是修复代码还是更新文档。
2. **Warning**：opencode 平台和 single-chat 功能是已实现的重要特性，但文档完全没有提及。
3. **Info**：多个辅助模块（tools/, bootstrap.py, core/utils/）未在目录树中列出，不影响架构理解但降低了文档完整性。

**建议优先级**：
1. 先解决 agent↔context 依赖问题（Critical）
2. 补充 opencode 平台和 single-chat feature 的文档描述（Warning）
3. 更新目录树以覆盖遗漏的辅助文件（Info）
