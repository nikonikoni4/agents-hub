# ARCHITECTURE.md 一致性检查报告

- 检查日期：2026-06-06
- 检查范围：后端代码结构、前端代码结构、模块/类/函数存在性、依赖关系

## 一致的部分

### 后端核心分层架构
- ✅ foundation 层（基础数据模型、消息类、异常类、常量、渲染器）与文档描述一致
- ✅ communication 层（消息路由器、调用记录、调用管理器）与文档描述一致
- ✅ context 层（群聊会话、群聊上下文、群聊持久化）与文档描述一致
- ✅ agent 层（Agent 基类、Manager、Worker）与文档描述一致
- ✅ orchestration 层（GroupChat、GroupChatManager）与文档描述一致
- ✅ 异常体系（统一基类 + 模块专属异常）与文档描述一致
- ✅ 配置模块（SystemConfig + types）与文档描述一致

### 前端核心架构
- ✅ 技术栈（React 18+、Electron、Zustand、React Router v6、Tailwind CSS）与文档描述一致
- ✅ 核心层（websocket、api、storage）与文档描述一致
- ✅ 功能模块组织规范（components/hooks/store/types）与文档描述一致

### 依赖关系
- ✅ 核心分层依赖关系基本与文档描述一致
- ✅ communication 层只依赖 foundation 层
- ✅ agent 层依赖 foundation + communication 层
- ✅ orchestration 层依赖所有下层

## 不一致的部分

### 1. MCP Server 工具定义
- **位置**：MCP Server 章节
- **文档描述**：提供了 3 个 MCP Tools（call_agent、list_agents、get_chat_history）
- **实际情况**：代码中提供了 6 个 MCP Tools（call_agent、assign_tasks_to_team、archive_task_list、check_agent_call、speak_in_group_chat、complete_task）
- **严重程度**：Critical
- **建议修复**：更新文档，反映实际的 MCP Tools 列表

### 2. Team 管理模块位置
- **位置**：后端架构详解 - 目录结构
- **文档描述**：Team 在 `core/orchestration/team.py` 中
- **实际情况**：Team 管理在 `agents_hub/teams/team_manager.py` 中，是独立模块
- **严重程度**：Warning
- **建议修复**：更新文档，将 Team 管理作为独立模块描述

### 3. 缺少 realtime 模块
- **位置**：后端架构详解 - 目录结构
- **文档描述**：未提到 realtime 模块
- **实际情况**：存在 `agents_hub/realtime/` 模块，包含 WebSocket 管理器
- **严重程度**：Warning
- **建议修复**：在文档中添加 realtime 模块的描述

### 4. 缺少 skills 模块
- **位置**：后端架构详解 - 目录结构
- **文档描述**：未提到 skills 模块
- **实际情况**：存在 `agents_hub/skills/` 模块，包含技能管理器
- **严重程度**：Warning
- **建议修复**：在文档中添加 skills 模块的描述

### 5. 缺少 teams 独立模块
- **位置**：后端架构详解 - 目录结构
- **文档描述**：Team 在 core/orchestration 中
- **实际情况**：存在独立的 `agents_hub/teams/` 模块
- **严重程度**：Warning
- **建议修复**：更新文档，反映 teams 独立模块的存在

### 6. Agent Bridge Docker 支持
- **位置**：Agent Bridge 章节
- **文档描述**：只提到 Claude Code CLI 和 Codex CLI 执行器
- **实际情况**：存在 `agents_hub/agent_bridge/docker/` 目录，包含容器管理器
- **严重程度**：Info
- **建议修复**：在文档中添加 Docker 支持的描述

### 7. 通信层任务管理
- **位置**：communication 层职责说明
- **文档描述**：只提到消息路由器、调用记录、调用管理器
- **实际情况**：存在 `task.py` 和 `task_manager.py`，提供任务管理功能
- **严重程度**：Warning
- **建议修复**：更新文档，添加任务管理的描述

### 8. 上下文层运行时状态
- **位置**：context 层职责说明
- **文档描述**：只提到群聊会话、群聊上下文、群聊持久化、Agent 上下文
- **实际情况**：存在 `group_chat_runtime_state.py`，提供运行时状态管理
- **严重程度**：Info
- **建议修复**：在文档中添加运行时状态的描述

### 9. API Server 结构
- **位置**：API Server 章节
- **文档描述**：只有一个 `main.py` 文件
- **实际情况**：有完整的路由、服务、模式等结构（routes、schemas、services、websocket）
- **严重程度**：Warning
- **建议修复**：更新文档，反映实际的 API Server 结构

### 10. 前端功能模块
- **位置**：前端架构 - 目录结构
- **文档描述**：有 preview、diff、tasks 等功能模块
- **实际情况**：这些模块不存在，实际有 roles、session、skills 等模块
- **严重程度**：Critical
- **建议修复**：更新文档，反映实际的前端功能模块

### 11. 前端核心层主题管理
- **位置**：前端架构 - 核心模块说明
- **文档描述**：只提到 websocket、api、storage
- **实际情况**：存在 `core/theme/` 模块，提供主题管理
- **严重程度**：Info
- **建议修复**：在文档中添加主题管理的描述

### 12. 前端共享层适配器
- **位置**：前端架构 - 共享资源
- **文档描述**：只提到 components、hooks、utils、types
- **实际情况**：存在 `shared/adapters/` 模块，提供数据适配器
- **严重程度**：Info
- **建议修复**：在文档中添加适配器的描述

## 文档缺失覆盖

### 后端缺失模块
1. **realtime 模块**：WebSocket 连接管理，用于实时通信
2. **skills 模块**：技能管理器，管理 Agent 的技能
3. **teams 模块**：团队管理器，管理团队配置
4. **task/task_manager**：任务管理，用于 Agent 任务分配和跟踪
5. **group_chat_runtime_state**：运行时状态，管理群聊的运行时状态
6. **Docker 支持**：Agent Bridge 的 Docker 容器支持

### 前端缺失模块
1. **roles 模块**：角色管理功能
2. **session 模块**：会话管理功能
3. **skills 模块**：技能管理功能
4. **theme 模块**：主题管理功能
5. **adapters 模块**：数据适配器

## 总结

### 一致性评分
- **后端架构一致性**：70%（核心分层一致，但模块定义和工具有较大差异）
- **前端架构一致性**：60%（核心架构一致，但功能模块和细节有较大差异）
- **总体一致性**：65%

### 主要问题
1. **MCP Tools 定义严重过时**：文档描述的 3 个工具与实际的 6 个工具不符
2. **前端功能模块完全过时**：文档描述的 preview、diff、tasks 模块不存在
3. **多个后端模块未在文档中描述**：realtime、skills、teams 等模块
4. **API Server 结构描述过于简单**：实际有完整的路由、服务、模式等结构

### 建议优先级
1. **Critical**：更新 MCP Tools 定义和前端功能模块描述
2. **Warning**：添加 realtime、skills、teams 等模块的描述
3. **Info**：补充 Docker 支持、主题管理、适配器等细节描述

### 修复建议
1. 重新生成 ARCHITECTURE.md，基于当前代码实际状态
2. 重点关注 MCP Server、前端功能模块、API Server 结构的更新
3. 添加新模块的描述（realtime、skills、teams、task 等）
4. 更新依赖关系图，反映实际的模块依赖
